#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
from datetime import datetime
import sys, os, json, re
import dme_utils as dme

# Configuration for defining valid sheets and other default values
config = {
    ".warning": ["\033[93m", "\033[00m"], ".error": ["\033[91m", "\033[00m"],
    ".vaults": ["CCBR_Archive", "CCBR_EXT_Archive", "CCR_DTB_Archive"]
}

def help():
        return """
validate.py: Validates the entries to be uploaded to DME

USAGE:
    python validate.py <input_directory> <dme_vault> [-h]

SYNOPSIS:
    Validate the parsed data from previous steps to check if the project is not already
at DME. If it is, check all of the metadata that is already on DME to cross check with
the used if they really want to apply those modifications.

Required Positional Arguments:
    [1] input_directory           Type [Path]: The output directory PATH provided in
                                  the previous steps. This is the full directory that
                                  will be uploaded to DME.

    [2] dme_vault                 Type [String]: DME vault to store data and metadata.
                                  Valid choices are 'CCBR_EXT_Archive' or 'CCBR_Archive'.
                                  NOTE:
                                    @ 'CCBR_EXT_Archive' is for public datasets.
                                    @ 'CCBR_Archive' is data from outside vendors.

Options:
    [-h, --help]                  Displays usage and help information for the script.

Example:
    $ python validate.py /scratch/DME/ CCBR_EXT_Archive

Requirements:
    python >= 3.5
"""


def args(argslist):
    """Parses command-line args from "sys.argv". Returns a list of args to parse."""
    # Input list of filenames to parse
    user_args = argslist[1:]
    convert = False
    project_id = ''
    metafile = ''
    analysisfile = ''

    # Check for optional args
    if '-h' in user_args or '--help' in user_args:
        print(help())
        sys.exit(0)

    # Check to see if user provided input files to parse
    if len(user_args) != 2:
        print("\n{}Error: Failed to provide all required arguments{}".format(*config['.error']), file=sys.stderr)
        print(help())
        sys.exit(1)

    return user_args


def path_exists(path):
    """Checks to see if output directory already exists or is accessible.
    If the PATH does not exist, it will attempt to create the directory and it's parent
    directories.
    """
    if not os.path.isdir(path):
        cstart, cend = config['.error']
        print("{}Error:{} PATH {} not accessible!".format(cstart, cend, path), file=sys.stderr)
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


def validate_args(user_inputs):
    """Checks user input to see if file/directory exists or is accessible.
    If a file does not exist, the error is redirected to stderr and exits with
    exit-code 1. If a directory does not exist, it will attempt to create it.
    """

    valid_vaults = config[".vaults"]
    ipath, vault = user_inputs
    
    assert vault in valid_vaults, "{} is not a vaild DME vault! Please choose from one of the following: {}".format(vault, valid_vaults)
    path_exists(ipath)

    return ipath, vault

def json2dict(file):
    """Reads in JSON file into memory as a dictionary. Checks to see if
    file exists or is accessible before reading in the file.
    """
    file_exists(file)

    with open(file, 'r') as f:
        data = json.load(f)

    return data

def get_pi_lab(path):
    files = [f for f in os.listdir(path) if 'PI_Lab' in f and '.metadata.json' in f]
    cstart, cend = config['.error']
    if len(files) != 1:
        print("{}Error:{} Could not find an unique PI_Lab inside the folder {}...".format(cstart, cend, path), file=sys.stderr)
        sys.exit(1)

    directory = path + '/' + files[0].split('.')[0]
    meta = json2dict(f"{path}/{files[0]}")
    return meta, directory

def get_project(path):
    files = [f for f in os.listdir(path) if 'Project_' in f and '.metadata.json' in f]
    cstart, cend = config['.error']
    if len(files) != 1:
        print("{}Error:{} Could not find an unique Project inside the folder {}...".format(cstart, cend, path), file=sys.stderr)
        sys.exit(1)

    directory = path + '/' + files[0].split('.')[0]
    meta = json2dict(f"{path}/{files[0]}")
    return meta, directory

def get_analysis_objects(path):
    files = [f for f in os.listdir(path) if '.metadata.json' in f]
    directories = [path + '/' + f.split('.')[0] for f in files]
    metas = [json2dict(f"{path}/{f}") for f in files]
    return metas, directories

def get_analysis(path):
    files = [f for f in os.listdir(path) if 'Primary_Analysis_' in f and '.metadata.json' in f]
    cstart, cend = config['.error']
    if len(files) != 1:
        print("{}Error:{} Could not find an unique Project inside the folder {}...".format(cstart, cend, path), file=sys.stderr)
        sys.exit(1)

    directory = path + '/' + files[0].split('.')[0]
    meta = json2dict(f"{path}/{files[0]}")
    objects, objects_dir = get_analysis_objects(directory)
    return meta, directory, objects, objects_dir

def get_sample_objects(path):
    files = [f for f in os.listdir(path) if '.metadata.json' in f]
    directories = [path + '/' + f.split('.')[0] for f in files]
    metas = [json2dict(f"{path}/{f}") for f in files]
    return metas, directories

def get_samples(path):
    files = [f for f in os.listdir(path) if 'Sample_' in f and '.metadata.json' in f]
    directories = [path + '/' + f.split('.')[0] for f in files]
    metas = [json2dict(f"{path}/{f}") for f in files]
    objs = [get_sample_objects(d) for d in directories]
    objects = [o[0] for o in objs]
    objects_dir = [o[1] for o in objs]
    return metas, directories, objects, objects_dir

def get_dme_directory(full_path,initial_path,vault):
    path = vault + '/' + full_path[len(initial_path):]
    path = path.replace('//','/')
    if path[0] != '/':
        path = '/' + path
    return path

def get_different_fields(meta_dme,meta_local):
    print(meta_dme,meta_local)
    items_only_dme = []
    items_only_local = []
    items_both = []
    for i in range(len(meta_dme)):
        att_i = meta_dme[i]['attribute']
        has_attribute = False
        for j in range(len(meta_local)):
            att_j = meta_local[j]['attribute']
            if att_i == att_j:
                items_both.append(att_i)
                has_attribute = True
        if not has_attribute:
            items_only_dme.append(att_i)
    for i in range(len(meta_local)):
        att_i = meta_local[i]['attribute']
        has_attribute = False
        for j in range(len(meta_dme)):
            att_j = meta_dme[j]['attribute']
            if att_i == att_j:
                has_attribute = True
        if not has_attribute:
            items_only_local.append(att_i)
    return items_only_dme, items_only_local, items_both

def evaluate_differences(meta_dme,meta_local):
    items_only_dme, items_only_local, items_both = get_different_fields(meta_dme,meta_local)
    print(f"There are:\n - {len(items_only_dme)} attributes only on DME\n - {len(items_only_local)} attributes to be append\n - {len(items_both)} attributes in both lists.")
    for att_i in items_only_local:
        for i in range(len(meta_local)):
            att = meta_local[i]['attribute']
            if (att == att_i):
                print(f"The attribute \'{att}\' will be appended with value as \'{meta_local[i]['value']}\'")
    for att in items_both:
        for i in range(len(meta_local)):
            att_i = meta_local[i]['attribute']
            if att != att_i:
                continue
            for j in range(len(meta_dme)):
                att_j = meta_dme[j]['attribute']
                if att != att_j:
                    continue
                
                if meta_local[i]['value'] != meta_dme[j]['value']:
                    print(f"The attribute \'{att}\' will be modified from \'{meta_dme[j]['value']}\' to \'{meta_local[i]['value']}\'")
    print(items_only_dme, items_only_local, items_both)

def evaluate_metadata_differences(session,meta_dir,meta):
    #meta0 = session.get_dataObject_dme_meta(meta_dir)
    #print(meta0)
    evaluate_differences(meta['metadataEntries'][:-1],meta['metadataEntries'][1:])

def main():

    # @args(): Parses positional command-line args
    # @validate_args(): Checks if user inputs are vaild
    ipath, vault = validate_args(args(sys.argv))
    print(ipath,vault)

    # Read in JSON files as dictionary
    pi_meta, pi_dir = get_pi_lab(ipath)
    proj_meta, proj_dir = get_project(pi_dir)
    analysis_meta, analysis_dir, analysis_objs, analysis_objs_dir = get_analysis(proj_dir)
    samples_meta, samples_dir, sample_objs, sample_objs_dir = get_samples(proj_dir)
    
    # Create DME Session
    dme_session = dme.DMESession()
    print(dme_session.dme_url)

    # Evaluate the existence of the project at the DME and the differences between meta to be added and already in DME
    pi_dir_dme = get_dme_directory(pi_dir,ipath,vault)
    pi_exists = evaluate_metadata_differences(dme_session,pi_dir_dme,pi_meta)

if __name__ == '__main__':

    main()
