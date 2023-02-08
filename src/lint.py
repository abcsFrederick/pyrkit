#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
import pandas as pd
import sys, os, re, json

# Configuration for defining valid sheets and other default values
config = {
    ".warning": ["\033[93m", "\033[00m"], ".error": ["\033[91m", "\033[00m"],
    ".sheets": ["Data Dictionary", "Project Template", "Sample Template"],
    "data_dictionary": {
        "sheet_name": "Data Dictionary",
        "skip_lines": [0],
        "order": ["collection_type", "is_required", "field_name", "dme_name"],
        "index": {
            "collection_type": 0,
            "is_required": 0,
            "field_name": 1,
            "dme_name": 2,
            "description": 3,
            "example": 4
        }
    },
    "project_template": {
        "sheet_name": "Project Template",
        "test_sheet": "Example Project",
        "skip_lines": [0,1],
        "singularities": [
                            'PI Name', 'PI Affiliation', 'Project Title',
                            'Project Description', 'Start Date',
                            'Project POC', 'Contact Email'
                        ],
        "mvds": [
                    'Nature of Request', 'Type of Project', 'Origin of Data',
                    'Access', 'Organism(s)', 'Number of Samples',
                    'Summary of Samples', 'Project Supplementary file',
                    'Collaborators', 'Publication Status', 'PubMed ID',
                    'DOI', 'Public Data Accession ID', 'Other Affiliation',
                    'Other Related CCBR Project', 'Project Priority Comment',
                    'Study Disease', 'Assembly Name', 'Platform Name',
                    'Cell Line Name'
                ]
    },
    "sample_template": {
        "sheet_name": "Sample Template",
        "test_sheet": "Example Sample",
        "skip_lines": [0,1],
    }
}


def help():
        return """
lint.py: Parses user-provided metadata spreadsheet and checks for errors.

USAGE:
    python lint.py <project_request_spreadsheet> <output_directory> [-h]

Required Positional Arguments:
    [1] project_request_sheet     Type [File]: A filled out project request out form.
                                  This spreadsheet is sent out to the PI or post-doc
                                  that is requesting our assistance. Please see
                                  "data/experiment_metadata.xlsx" as an example.

    [2] output_directory          Type [Path]: Absolute or relative PATH for output
                                  files. If the PATH does not exist, it will be
                                  automatically created during runtime.
Options:
    [-h, --help]                  Displays usage and help information for the script.
    [-n, --dry-run]               Dry-run using the included example sheets.

Example:
    # Run against user-provided information: "Project Template", "Sample Template"
    $ python lint.py data/experiment_metadata.xlsx /scratch/$USER/DME_Upload/

    # Dry-run against included examples: "Example Project", "Example Sample"
    $ python lint.py data/experiment_metadata.xlsx /scratch/$USER/DME_Upload/ -n

Requirements:
    python >= 3.5
      + pandas
      + xlrd
"""


def args(argslist, dryrun = False):
    """Parses command-line args from "sys.argv". Returns a list of args to parse."""
    # Input list of filenames to parse
    user_args = argslist[1:]

    # Check for optional args
    if '-h' in user_args or '--help' in user_args:
        print(help())
        sys.exit(0)

    # Check for dry-run boolean flag
    elif '-n' in user_args or '--dry-run' in user_args:
        print('Dry-running with included example sheets: "Example Project", "Example Sample"')
        user_args = [arg for arg in user_args if arg not in ['-n', '--dry-run']]
        dryrun = True

    # Check to see if user provided input files to parse
    if len(user_args) != 2:
        print("\n{}Error: Failed to provide all required arguments{}".format(*config['.error']), file=sys.stderr)
        print(help())
        sys.exit(1)

    return user_args + [dryrun]


def path_exists(path):
    """Checks to see if output directory already exists or is accessible.
    If the PATH does not exist, it will attempt to create the directory and it's parent
    directories.
    """
    cstart, cend = config['.warning']

    if not os.path.isdir(path):
        print("{}WARNING:{} Output directory '{}' does not exist... creating it now!".format(cstart, cend, path), file=sys.stderr)
        try:
            os.makedirs(path)
        except OSError as e:
            cstart, cend = config['.error']
            print("{}Error:{} Failed to create {}... PATH not accessible!\n{}".format(cstart, cend, path, e), file=sys.stderr)
            sys.exit(1)
    return


def file_exists(filename):
    """Checks to see if file exists or is accessible.
    Avoids problem with inconsistencies across python2.7 and >= python3.4 and
    works in both major versions of python"""
    try:
        fh = open(filename)
        fh.close()
    # File cannot be opened for reading (may not exist) or permissions problem
    except IOError as e:
        cstart, cend = config['.error']
        print("{}Error:{} Failed to open {}... Input file not accessible!\n{}".format(cstart, cend, filename, e), file=sys.stderr)
        sys.exit(1)
    return


def contains_sheets(spreadsheet):
    """Checks to see if user-provided spreadsheet contains all the required sheets
    that are defined in the config specification. Please see config['.sheets']
    for all required sheets.
    """

    required = config['.sheets']
    df = pd.read_excel(spreadsheet, sheet_name=None, header=None)
    valid_sheets = [sheet for sheet in df.keys() if sheet in required]

    if sorted(valid_sheets) != sorted(required):
        # Required sheet not in spreadsheet
        missing = set(required) - set(valid_sheets)
        raise Exception('Spreadsheet is missing the following sheet(s): {}'.format(missing))
        sys.exit(1)

    return valid_sheets


def validate(user_inputs):
    """Checks user input to see if file/directory exists or is accessible.
    If a file does not exist, the error is redirected to stderr and exits with
    exit-code 1. If a directory does not exist, it will attempt to create it.
    """

    meta_sheet, output_path, dryrun = user_inputs
    file_exists(meta_sheet)
    path_exists(output_path)
    sheets = contains_sheets(meta_sheet)

    return meta_sheet, output_path, sheets, dryrun


def _parsed_meta(excel_df, indexes):
    """Private function for 'meta()' to parse the Data Dictionary sheet.
    This function generates the following parsed values: collection_type, is_required,
    field_name, dme_name.
    """
    for i, row in excel_df.iterrows():
        # Remove any leading or trailing whitespace and parse the columns of interest
        collection_name, is_required, field_name, dme_name = [str(row[index]).lstrip().rstrip() for index in indexes]
        # skip over over empty lines or nan values
        if not is_required or is_required == 'nan':
            continue
        # Get collection type: PI, Project, Sample
        elif "collection" in collection_name.lower():
            collection_type = collection_name.split()[0]
            continue

        yield collection_type, is_required, field_name, dme_name


def meta(sheet, spreadsheet, order, index, log_route):
    """Parses the 'Data Dictionary' sheet located in the project_request_spreadsheet.
    Returns a nested dictionary where [key1] = collection_type (PI, Project, Sample),
    [key2] = field and the value is a list [dme_name, is_requred]. A log file get
    created in '{user-defined-outpath}/logs/data_dictionary.txt'.
    """
    skipover = config["data_dictionary"]["skip_lines"]
    metadata = {}

    # Skip over reading the first line or header
    df = pd.read_excel(spreadsheet, sheet_name=sheet, header=None, skiprows=skipover)
    # Creating logging output file
    outfh = open(os.path.join(log_route, "data_dictionary.txt"), "w")

    # Get sorted indices of important fields to parse
    indices = [index[f] for f in order]
    # Required Fields
    required = []
    for col, req, field, dme in _parsed_meta(df, indices):
        outfh.write("{}\t{}\t{}\t{}\n".format(col, req, field, dme))
        if req.lower() == 'required':
            required.append(field)

        if col not in metadata:
            metadata[col] = {}

        metadata[col][field] = [dme, req]

    outfh.close()

    return metadata, required


def _remove_trailing_nan(linelist):
    """Private function to clean project_value_list. Removes trailing nan's which
    are empty sub-project cells. As an example, input ["nan", 1, 2, "nan", "nan"]
    will return ["nan", 1, 2].
    """
    clean = linelist
    # Looping through reversed list to get trailing values
    for field in linelist[::-1]:
        # skip over over empty lines or nan values
        if not field or field == 'nan':
            removed = clean.pop()
        else:
            break # break when encountering first non-empty string or non-nan

    return clean


def _parsed_project(excel_df):
    """Private function for 'project()' to parse the Project Template sheet.
    This function generates the following parsed values: collection_type, field,
    project_value_list.
    """
    for i, row in excel_df.iterrows():
        # Project information follows a key, value_list pattern
        attr, *project_value_list = [str(field).lstrip().rstrip() for field in row]
        # Pass over lines with no attribute or key
        if not attr or attr == 'nan' or attr.lower().startswith('optional field'):
            continue
        # Get collection type: PI, Project, Sample
        elif "collection" in attr.lower():
            collection_type = project_value_list[0]
            continue

        # Remove trailing empty cells or nan's
        project_value_list = _remove_trailing_nan(project_value_list)

        yield collection_type, attr, project_value_list



def project(sheet, spreadsheet, log_route):
    """Parses the 'Project Template' sheet in the project_request_spreadsheet
    to extract PI-level and Project-level metadata. Returns a nested dictionary where
    [key1] = collection_type (PI, Project), [key2] = field, and the value is a list
    of values where each value is metadata for a sub-project [Proj-1_attr, Proj-2_attr, ...].
    A log file gets created in '{user-defined-outpath}/logs/project_information.txt'.
    """
    skipover = config["project_template"]["skip_lines"]
    metadata = {}

    # Skip over reading the first line or header
    df = pd.read_excel(spreadsheet, sheet_name=sheet, header=None, skiprows=skipover)
    # Creating logging output file
    outfh = open(os.path.join(log_route, "project_information.txt"), "w")

    mvds = [] # Find the number of sub-projects or the number of MVDs an attribute can have
    for col, field, pro_attr_list in _parsed_project(excel_df = df):
        outfh.write("{}\t{}\t{}\n".format(col, field, "\t".join(pro_attr_list)))
        if col not in metadata:
            metadata[col] = {}

        metadata[col][field] = pro_attr_list
        mvds.append(len(pro_attr_list))

    outfh.close()

    return metadata, sorted(mvds)[-3]


def _parsed_sample(excel_df):
    """Private function for 'sample()' to parse the Sample Template sheet.
    This function generates the following parsed values: SampleID, field,
    sample_metadata_value.
    """
    for i, row in excel_df.iterrows():
        attr, *project_value_list = [str(field).lstrip().rstrip() for field in row]
        # Pass over lines with no attribute or key
        if not attr or attr == 'nan' or attr.lower().startswith('optional field'):
            continue
        # Check if header and clean
        if attr.lower() == 'sample id':
            header = _remove_trailing_nan(project_value_list)
            sid_field = attr
            continue

        for j in range(0,len(header),1):
            yield attr, header[j], project_value_list[j]
        else:
            # Yield add Sample ID last
            yield attr, sid_field, attr


def sample(sheet, spreadsheet, log_route):
    """Parses the 'Sample Template' sheet in the project_request_spreadsheet
    to extract Sample-level metadata. Returns a nested dictionary where
    [key1] = SampleID, [key2] = field, and value = user-provided info.
    A log file gets created in '{user-defined-outpath}/logs/sample_information.txt'.
    """
    skipover = config["sample_template"]["skip_lines"]
    metadata = {}

    # Skip over reading the first line or header
    df = pd.read_excel(spreadsheet, sheet_name=sheet, header=None, skiprows=skipover)
    # Creating logging output file
    outfh = open(os.path.join(log_route, "sample_information.txt"), "w")

    for sid, field, value in _parsed_sample(excel_df = df):
        outfh.write("{}\t{}\t{}\n".format(sid, field, value))
        if sid not in metadata:
            metadata[sid] = {}

        metadata[sid][field] = value

    outfh.close()

    return metadata


def missing_fields(parsed_dict, data_dict, collection_type, requirements, Nsubprojects = None, ext = []):
    """Checks the parsed fields in the user-provided spreadsheet against the
    data dictionary to see if all the required fields were provided.
    """
    cstart, cend = config['.warning']
    estart, eend = config['.error']
    mvd_attr = config['project_template']['mvds']
    provided = [] + ext

    for k, fdict in parsed_dict.items():
        if collection_type == 'Sample':
            k = 'Sample'
        for field, uvalue in fdict.items():
            try: # Get whether a field is required or optional
                is_req = data_dict[k][field][-1]
            except KeyError:
                print("{}WARNING:{} Provided fields ({}, {}) are not defined in data dictionary... skipping over now!".format(cstart, cend, k, field), file=sys.stderr)
                continue

            if is_req.lower() == 'required':
                mvd_fields = [v for v in uvalue if v.strip() and v.lower() != 'nan']

                # Check for any missing required sub-project fields
                if field in mvd_attr and len(mvd_fields) != Nsubprojects:
                    print("{}Error:{} Failed to provide required field ({}) for all sub-projects...exiting".format(estart, eend, field), file=sys.stderr)
                    sys.exit(1)

                # Check for singular required fields (no MVD relationship)
                elif field not in mvd_attr and not mvd_fields:
                    print("{}Error:{} Failed to provide required field ({})...exiting".format(estart, eend, field), file=sys.stderr)
                    sys.exit(1)
                provided.append(field)

    missing = set(requirements) - set(provided)

    return missing


def main():

    # @args(): Parses positional command-line args
    # @validate(): Checks if user inputs are vaild
    metadata, opath, sheets, dryrun = validate(args(sys.argv))

    # Log file directory and parsed pickled data
    logs = os.path.join(opath, "logs")
    path_exists(logs)

    # Determining whether to use the user-provided templates or the test sheets
    this_template = 'sheet_name'
    if dryrun:
        this_template = 'test_sheet'

    # Get specification for parsing 'Data Dictionary'
    data_catelog = config["data_dictionary"]["sheet_name"]
    sort = config["data_dictionary"]["order"]
    indices = config["data_dictionary"]["index"]

    # Generate Data Dictionary: dict[collection_type][field_name] = list(dme_name, is_required)
    meta_dictionary, req_fields = meta(sheet = data_catelog, spreadsheet = metadata, order=sort, index=indices, log_route=logs)

    # Get specification for parsing 'Project Template'
    project_info = config["project_template"][this_template]
    # Get all project metadata from Project Template
    project_dictionary, subprojects = project(sheet = project_info, spreadsheet = metadata, log_route = logs)

    # Get specification for parsing 'Sample Template'
    sample_info = config["sample_template"][this_template]
    # Get all sample metadata from Sample Template
    sample_dictionary = sample(sheet = sample_info, spreadsheet = metadata, log_route = logs)

    # Check if user has provided all required check_fields
    missing = missing_fields(parsed_dict=project_dictionary, data_dict=meta_dictionary, collection_type="Project", requirements=req_fields, Nsubprojects=subprojects)
    missing = missing_fields(parsed_dict=sample_dictionary, data_dict=meta_dictionary, collection_type="Sample", requirements=missing, ext=['Sample ID'])

    if missing:
        estart, eend = config['.error']
        print("{}Error:{} Failed to provide required field(s) {}...exiting".format(estart, eend, missing), file=sys.stderr)
        sys.exit(1)

    # Save parsed data as JSON file
    with open(os.path.join(opath, "data_dictionary.json"), 'w') as file:
        json.dump(meta_dictionary, file, sort_keys=True, indent=4)

    with open(os.path.join(opath, "project.json"), 'w') as file:
        json.dump(project_dictionary, file, sort_keys=True, indent=4)

    with open(os.path.join(opath, "sample.json"), 'w') as file:
        json.dump(sample_dictionary, file, sort_keys=True, indent=4)

if __name__ == '__main__':

    main()
