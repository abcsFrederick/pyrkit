#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
import pandas as pd
import sys, os, re, json

# Configuration for defining valid sheets and other default values
config = {
    ".warning": ["\033[93m", "\033[00m"], ".error": ["\033[91m", "\033[00m"],
    ".sheets": ['Derived Fields', 'Required Fields - User Form', 'Recommended Fields for dbGaP',
                'Recommended Fields for CDS', 'Recommended Fields for GEO', 'Recommended Fields for GDC',
                'Data Dictionary', 'Disease, Diagnoses, Antibodies'],
    ".min_required": [
        'Data Owner', 'Data Owner Affiliation', 'Data Generator (for the Data Owner)', #Pi_Lab level
        'Project Title', 'Project Description', 'Data Generating Facility', 'Library Strategy', 'Start Date', 'Access', 'Summary of Samples', #Project level
        'Raw Data Sample Name', 'Sample Name', 'Sequencing Platform', 'Analyte Type', 'Organism'], #Sample level
    ".project_to_sample": [['Sequencing Platform', 'Sequencing Platform'],
                           ['Organism', 'Source Organism']],
    ".sample_to_project": ['Library Strategy'],
    ".add_project_field": {'Access': 'Closed Access'},
    ".sample_summary_fields": ['Disease','Library Strategy','Analyte Type','Tissue','Tissue Type','Age','Gender','Race'],
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
        "sheet_name": "Required Fields - User Form",
        "test_sheet": "Required Fields - User Form",
        "skip_lines": [0],
        "nrows": 14,
        "nrows_PI_Lab": 3,
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
        "sheet_name": "Required Fields - User Form",
        "test_sheet": "Required Fields - User Form",
        "skip_lines": 17
    },
    "project_dbGaP": {
        "sheet_name": "Recommended Fields for dbGaP",
        "test_sheet": "Recommended Fields for dbGaP",
        "skip_lines": 3,
        "nrows": 6,
        "nrows_PI_Lab": 0
    },
    "sample_dbGaP": {
        "sheet_name": "Recommended Fields for dbGaP",
        "test_sheet": "Recommended Fields for dbGaP",
        "skip_lines": 11
    },
    "project_CDS": {
        "sheet_name": "Recommended Fields for CDS",
        "test_sheet": "Recommended Fields for CDS",
        "skip_lines": 3,
        "nrows": 1,
        "nrows_PI_Lab": 0
    },
    "sample_CDS": {
        "sheet_name": "Recommended Fields for CDS",
        "test_sheet": "Recommended Fields for CDS",
        "skip_lines": 6
    },
    "project_GEO": {
        "sheet_name": "Recommended Fields for GEO",
        "test_sheet": "Recommended Fields for GEO",
        "skip_lines": 3,
        "nrows": 6,
        "nrows_PI_Lab": 0
    },
    "sample_GEO": {
        "sheet_name": "Recommended Fields for GEO",
        "test_sheet": "Recommended Fields for GEO",
        "skip_lines": 11,
    },
    "project_GDC": {
        "sheet_name": "Recommended Fields for GDC",
        "test_sheet": "Recommended Fields for GDC",
        "skip_lines": 3,
        "nrows": 7,
        "nrows_PI_Lab": 0
    },
    "sample_GDC": {
        "sheet_name": "Recommended Fields for GDC",
        "test_sheet": "Recommended Fields for GDC",
        "skip_lines": 12,
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
        print(f"Dry-running with included example sheets: {config['project_template']['test_sheet']}, {config['sample_template']['test_sheet']}")
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


def contains_sheets(spreadsheet,print_sheets=False):
    """Checks to see if user-provided spreadsheet contains all the required sheets
    that are defined in the config specification. Please see config['.sheets']
    for all required sheets.
    """

    required = config['.sheets']
    df = pd.read_excel(spreadsheet, sheet_name=None, header=None)
    valid_sheets = [sheet for sheet in df.keys() if sheet in required]
    if print_sheets:
        print([sheet for sheet in df.keys()])

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


def _parsed_project(excel_df, config_id):
    """Private function for 'project()' to parse the Project Template sheet.
    This function generates the following parsed values: collection_type, field,
    project_value_list.
    """
    nrows_collection_PI_Lab = config[config_id]["nrows_PI_Lab"]
    for i, row in excel_df.iterrows():
        # Project information follows a key, value_list pattern
        attr, *project_value_list = [str(field).lstrip().rstrip() for field in row]
        # Pass over lines with no attribute or key
        if not attr or attr == 'nan' or attr.lower().startswith('optional field'):
            continue
        # Get collection type: PI, Project
        collection_type = 'PI_Lab' if i < nrows_collection_PI_Lab else 'Project'
        
        # Remove trailing empty cells or nan's
        project_value_list = _remove_trailing_nan(project_value_list)

        yield collection_type, attr, project_value_list



def project(config_id, sheet, spreadsheet, log_route):
    """Parses the 'Project Template' sheet in the project_request_spreadsheet
    to extract PI-level and Project-level metadata. Returns a nested dictionary where
    [key1] = collection_type (PI, Project), [key2] = field, and the value is a list
    of values where each value is metadata for a sub-project [Proj-1_attr, Proj-2_attr, ...].
    A log file gets created in '{user-defined-outpath}/logs/project_information.txt'.
    """
    skipover = config[config_id]["skip_lines"]
    nrows = config[config_id]["nrows"]
    metadata = {}

    # Skip over reading the first line or header
    df = pd.read_excel(spreadsheet, sheet_name=sheet, header=None, usecols=[0,1], skiprows=skipover, nrows=nrows)

    # Creating logging output file
    outfh = open(os.path.join(log_route, "project_information.txt"), "w")

    mvds = [] # Find the number of sub-projects or the number of MVDs an attribute can have
    for col, field, pro_attr_list in _parsed_project(excel_df = df,config_id = config_id):
        outfh.write("{}\t{}\t{}\n".format(col, field, "\t".join(pro_attr_list)))
        if col not in metadata:
            metadata[col] = {}

        metadata[col][field] = pro_attr_list
        mvds.append(len(pro_attr_list))

    outfh.close()
    
    return (metadata, sorted(mvds)[-3]) if config_id == 'project_template' else metadata


def _parsed_sample(excel_df, config_id):
    """Private function for 'sample()' to parse the Sample Template sheet.
    This function generates the following parsed values: SampleID, field,
    sample_metadata_value.
    """
    cstart, cend = config['.warning']
    estart, eend = config['.error']
    attr_id = -1
    for i, row in excel_df.iterrows():
        project_value_list = [str(field) for field in row]
        
        #Find equivalent of the sample id
        if attr_id < 0:
            for j in range(len(project_value_list)):
                if (project_value_list[j].lower() == 'raw data sample name'):
                    attr_id = j
        
        if (attr_id < 0):
            print("{}Error:{} Failed to provide required field 'Raw Data Sample Name' on sheet {}...".format(estart, eend, config_id), file=sys.stderr)
            sys.exit(1)
        attr = project_value_list[attr_id]
        
        # Pass over lines with no attribute or key
        if not attr or attr == 'nan' or attr.lower().startswith('optional field'):
            continue
            
        # Check if header and clean
        if str(attr).lower() == 'raw data sample name':
            header = _remove_trailing_nan(project_value_list)
            sid_field = attr
            continue
        
        for j in range(0,len(header),1):
            yield attr, header[j], project_value_list[j]
        else:
            # Yield add Sample ID last
            yield attr, sid_field, attr


def sample(config_id, sheet, spreadsheet, log_route):
    """Parses the 'Sample Template' sheet in the project_request_spreadsheet
    to extract Sample-level metadata. Returns a nested dictionary where
    [key1] = SampleID, [key2] = field, and value = user-provided info.
    A log file gets created in '{user-defined-outpath}/logs/sample_information.txt'.
    """
    skipover = config[config_id]["skip_lines"]
    metadata = {}

    # Skip over reading the first line or header
    df = pd.read_excel(spreadsheet, sheet_name=sheet, header=None, skiprows=skipover)
    if (config_id == 'sample_template'):
        df.drop([1,2],inplace=True)
    
    # Creating logging output file
    outfh = open(os.path.join(log_route, "sample_information.txt"), "w")

    for sid, field, value in _parsed_sample(excel_df = df, config_id = config_id):
        outfh.write("{}\t{}\t{}\n".format(sid, field, value))
        if sid not in metadata:
            metadata[sid] = {}

        metadata[sid][field] = value

    outfh.close()

    return metadata


def project_to_sample_metadata(project, sample):
    """Add to Sample metadata some general information from the Project level,
    defined in config.project_to_sample
    """
    for field in config['.project_to_sample']:
        in_project = field[0]
        in_sample = field[1]
        for sid in sample.keys():
            sample[sid][in_sample] = project[in_project][0]
    return sample


def count_sample_field(sample, field):
    """Return the number of times each value in a given field has been filled.
    """
    values  = []
    counter = {}
    for sid in sample.keys():
        if field not in sample[sid].keys():
            return counter
        values.append(sample[sid][field])
    for v in values:
        if v in counter.keys():
            counter[v] += 1
        else:
            counter[v] = 1
    return counter

def get_max_counter_field(counter):
    """Return the value of the fild that has been filled the most.
    """
    max_count = ''
    n_counts = -1
    for fid in counter.keys():
        if counter[fid] > n_counts:
            max_count = fid
    return max_count

def sample_to_project_metadata(sample, project):
    """Add to Project metadata some summarized information from the Project level,
    defined in config.sample_to_project
    """
    for field in config['.sample_to_project']:
        counter = count_sample_field(sample,field)
        project[field] = [get_max_counter_field(counter)]
        
    return project


def create_summary_of_samples(sample):
    """Returns the summary of the samples,
    based in config.sample_summary_fields
    """
    summary = f"This project contains {len(sample)} samples."
    for field in config['.sample_summary_fields']:
        counter = count_sample_field(sample,field)
        if len(counter) == 0:
            continue
        breaker = False
        for value in counter.keys():
            if value is None or value == 'None':
                breaker = True
        if breaker:
            continue
        for value in counter.keys():
            summary += f" {counter[value]} samples have {value},"
        summary = summary[:-1]
        summary += f" as the {field}."

    return summary

def add_default_project_metadata(project, sample):
    """Add to Project metadata some default metadata,
    defined in config.add_project_field
    """
    project = sample_to_project_metadata(sample,project)
    for field in config['.add_project_field'].keys():
        project[field] = [config['.add_project_field'][field]]
    project['Summary of Samples'] = [create_summary_of_samples(sample)]
    project['Number of Samples'] = [len(sample)]
    return project
    

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
            
            if is_req.lower() == 'required' or field in requirements:
                mvd_fields = [v for v in uvalue if v.strip() and v.lower() != 'nan']

                # Check for any missing required sub-project fields
                #if field in mvd_attr and len(mvd_fields) != Nsubprojects:
                #    print("{}Error:{} Failed to provide required field ({}) for all sub-projects...exiting".format(estart, eend, field), file=sys.stderr)
                #    sys.exit(1)

                # Check for singular required fields (no MVD relationship)
                #elif
                if field not in mvd_attr and not mvd_fields:
                    print("{}Error:{} Failed to provide required field ({})...exiting".format(estart, eend, field), file=sys.stderr)
                    sys.exit(1)
                provided.append(field)

    missing = set(requirements) - set(provided)

    return missing


def merge_metadata(meta1, meta2, key='Project', update_if_exists=True):
    """Merge metadata from different dictionaries. Adds the information
    of dictionary 2 into dictionary 1 and returns the merged dictionary.
    To update keys that already existis in dictionary 1 let the
    update_if_exists to be True, or False otherwise.
    """
    for i in meta2[key].keys():
        if update_if_exists or i not in meta1[key].keys():
            meta1[key][i] = meta2[key][i]
    return meta1


def main():

    # @args(): Parses positional command-line args
    # @validate(): Checks if user inputs are vaild
    metadata, opath, sheets, dryrun = validate(args(sys.argv))

    # Set warnings and error configs
    cstart, cend = config['.warning']
    estart, eend = config['.error'] 

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
    project_dictionary, subprojects = project(config_id = 'project_template', sheet = project_info, spreadsheet = metadata, log_route = logs)
    # Get all project metadata from additional sheets 
    additionals = ['project_dbGaP', 'project_CDS', 'project_GEO', 'project_GDC']
    project_additionals = [project(config_id = add, sheet = config[add]['sheet_name'], spreadsheet = metadata, log_route = logs) for add in additionals]
    # Merge additional metadata into project_dictionary
    for add in project_additionals:
        project_dictionary = merge_metadata(project_dictionary,add,'Project')

    # Get specification for parsing 'Sample Template'
    sample_info = config["sample_template"][this_template]
    # Get all sample metadata from Sample Template
    sample_dictionary = sample(config_id = "sample_template", sheet = sample_info, spreadsheet = metadata, log_route = logs)
    # Get all project metadata from additional sheets 
    additionals = ['sample_dbGaP', 'sample_CDS', 'sample_GEO', 'sample_GDC']
    sample_additionals = [sample(config_id = add, sheet = config[add]['sheet_name'], spreadsheet = metadata, log_route = logs) for add in additionals]
    # Merge additional metadata into sample_dictionary
    for add in sample_additionals:
        for sample_id in add.keys():
            if (sample_id not in sample_dictionary.keys()):
                print("{}Error:{} Attempt to include additional metadata on inexistent Sample ID {}, please verify... exiting".format(estart, eend, sample_id), file=sys.stderr)
                sys.exit(1)
            sample_dictionary = merge_metadata(sample_dictionary,add,sample_id)
    sample_dictionary = project_to_sample_metadata(project_dictionary['Project'],sample_dictionary)
    project_dictionary['Project'] = add_default_project_metadata(project_dictionary['Project'], sample_dictionary)
            
    # Check if user has provided all the minimum requirements
    missing = missing_fields(parsed_dict=project_dictionary, data_dict=meta_dictionary, collection_type="Project", requirements=config['.min_required'], Nsubprojects=subprojects)
    missing = missing_fields(parsed_dict=sample_dictionary, data_dict=meta_dictionary, collection_type="Sample", requirements=missing, ext=['Sample ID'])

    if missing:
        print("{}Error:{} Failed to provide required field(s) {}... exiting".format(estart, eend, missing), file=sys.stderr)
        sys.exit(1)
    
    # Check if user has provided all required check_fields extracted from dictionary sheet
    missing = missing_fields(parsed_dict=project_dictionary, data_dict=meta_dictionary, collection_type="Project", requirements=req_fields, Nsubprojects=subprojects)
    missing = missing_fields(parsed_dict=sample_dictionary, data_dict=meta_dictionary, collection_type="Sample", requirements=missing, ext=['Sample ID'])

    if missing:
        print("{}WARNING:{} Failed to provide field(s) {}...".format(cstart, cend, missing), file=sys.stderr)

    # Save parsed data as JSON file
    with open(os.path.join(opath, "data_dictionary.json"), 'w') as file:
        json.dump(meta_dictionary, file, sort_keys=True, indent=4)

    with open(os.path.join(opath, "project.json"), 'w') as file:
        json.dump(project_dictionary, file, sort_keys=True, indent=4)

    with open(os.path.join(opath, "sample.json"), 'w') as file:
        json.dump(sample_dictionary, file, sort_keys=True, indent=4)

if __name__ == '__main__':

    main()
