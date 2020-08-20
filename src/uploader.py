#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division
import sys, os, re
import pandas as pd

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
    }

}


def help():
        return """
USAGE:
    python uploader.py <project_request_spreadsheet> <output_directory> [-h]

    Positional Arguments:
    [1] project_request_sheet     Type [File]: A filled out project request out form.
                                  This spreadsheet is sent out to the PI or post-doc
                                  that is requesting our assistance. Please see
                                  "data/experiment_metadata.xlsx" as an example.

    [2] output_directory          Type [Path]: Absolute or relative PATH for output
                                  files. If the PATH does not exist, it will be
                                  automatically created during runtime.

    Optional Arguments:
    [-h, --help]  Displays usage and help information for the script.

    Example:
    $ python uploader.py data/experiment_metadata.xlsx /scratch/$USER/DME_Upload/

    Requirements:
    python >= 2.7
      + pandas
      + xlrd
"""


def args(argslist):
    """Parses command-line args from "sys.argv". Returns a list of args to parse."""
    # Input list of filenames to parse
    user_args = argslist[1:]

    # Check for optional args
    if '-h' in user_args or '--help' in user_args:
        print(help())
        sys.exit(0)
    # Check to see if user provided input files to parse
    elif len(user_args) != 2:
        print("\n{}Error: Failed to provide all required arguments{}".format(*config['.error']), file=sys.stderr)
        print(help())
        sys.exit(1)

    return user_args


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

    meta_sheet, output_path = user_inputs
    file_exists(meta_sheet)
    path_exists(output_path)
    sheets = contains_sheets(meta_sheet)

    return meta_sheet, output_path, sheets


def _parsed_meta(excel_df, indexes):
    """Private function for 'meta_dictionary' to parse the Data Dictionary sheet.
    This function generates the following parsed values: collection_type, is_required,
    field_name, dme_name.
    """
    metadata = {}
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
    for col, req, field, dme in _parsed_meta(df, indices):
        outfh.write("{}\t{}\t{}\t{}\n".format(col, req, field, dme))
        if col not in metadata:
            metadata[col] = {}

        metadata[col][field] = [dme, req]

    return metadata

def project():
    """Parses the 'Project Template' sheet in the project_request_spreadsheet
    to extract PI-level and Project-level metadata. Returns a nested dictionary where
    [key1] = collection_type (PI, Project), [key2] = field, and the value is a list
    of values where each value is metadata for a sub-project [Proj-1_attr, Proj-2_attr].
    A log file gets created in '{user-defined-outpath}/logs/project_template.txt'.
    """
    pass

def main():

    # @args(): Parses positional command-line args
    # @validate(): Checks if user inputs are vaild
    metadata, opath, sheets = validate(args(sys.argv))

    # Log file directory
    logs = os.path.join(opath, "logs")
    path_exists(logs)

    # Get specification for parsing 'Data Dictionary'
    data_catelog = config["data_dictionary"]["sheet_name"]
    sort = config["data_dictionary"]["order"]
    indices = config["data_dictionary"]["index"]

    # Generate Data Dictionary: dict[collection_type][field_name] = list(dme_name, is_required)
    meta_dictionary = meta(sheet = data_catelog, spreadsheet = metadata, order=sort, index=indices, log_route=logs)

    # Get all project metadata from Project Template


if __name__ == '__main__':

    main()