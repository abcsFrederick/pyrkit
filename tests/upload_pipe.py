#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, division
import pandas as pd
import sys, os, re, json

# Configuration for defining valid sheets and other default values
config = {
    ".warning": ["\033[93m", "\033[00m"],
    ".error": ["\033[91m", "\033[00m"],
    ".vaults": ["CCBR_Archive", "CCBR_EXT_Archive"],
}


def help():
        return """
test_upload.py: Create the pipeline to test the upload of data to DME.

USAGE:
    python test_upload.py <requested_metadata> <data_input_directory> <output_directory>
        <Archive_vault>  <multiQC_directory> [-h]

Required Positional Arguments:
    [1] requested_metadata        Type [File]: A filled out project request out form.
                                  This spreadsheet is sent out to the PI or post-doc
                                  that is requesting our assistance. Please see
                                  "data/experiment_metadata.xlsx" as an example.
    [2] data_input_directory      Type [Path]: Absolute or relative PATH where sample
                                  data files are located.
    [3] output_directory          Type [Path]: Absolute or relative PATH for output
                                  files. If the PATH does not exist, it will be
                                  automatically created during runtime.
    [4] Archive_vault             Type [Path]: Vault to be used for archiving.
    [5] multiQC_directory         Type [Path]: Absolute or relative PATH for the multi
                                  QC files. Not mandatory.
Options:
    [-h, --help]                  Displays usage and help information for the script.
    [-n, --dry-run]               Dry-run using the included example sheets.
    [-u, --update]                Only update metadata but do not upload data files.
    [-f, --full]                  Run full pipeline including other scripts.

Requirements:
    python >= 3.5
      + pandas
      + xlrd
"""


def args(argslist, dryrun = False, update = False, full_pipe = False):
    """Parses command-line args from "sys.argv". Returns a list of args to parse."""
    # Input list of filenames to parse
    user_args = argslist[1:]

    # Check for optional args
    if '-h' in user_args or '--help' in user_args:
        print(help())
        sys.exit(0)

    # Check for dry-run boolean flag
    if '-n' in user_args or '--dry-run' in user_args:
        print(f"Dry-running.")
        user_args = [arg for arg in user_args if arg not in ['-n', '--dry-run']]
        dryrun = True

    # Check for update flag
    if '-u' in user_args or '--update' in user_args:
        print(f"Updating pipe.")
        user_args = [arg for arg in user_args if arg not in ['-u', '--update']]
        update = True

    # Check for full pipe flag
    if '-f' in user_args or '--full' in user_args:
        print(f"Full pipe.")
        user_args = [arg for arg in user_args if arg not in ['-f', '--full']]
        full_pipe = True

    # Check to see if user provided input files to parse
    if len(user_args) < 4:
        print("\n{}Error: Failed to provide all required arguments{}".format(*config['.error']), file=sys.stderr)
        print(help())
        sys.exit(1)

    return user_args + [dryrun] + [update] + [full_pipe]


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


def valid_config(parameter, field):
    """Checks to see if the parameter is valid within the configuration."""
    cstart, cend = config['.error']
    try:
        if parameter not in config[field]:
            print("{}Error:{} parameter {} not foind in config! Please user one of the following: {}\n".format(cstart, cend, parameter, config[field]), file=sys.stderr)
            sys.exit(1)
    # Field not accessibe in config
    except:
        print("{}Error:{} {} not in config!\n".format(cstart, cend, field), file=sys.stderr)
        sys.exit(1)
    return

def _create_parser(multqc_path,sample_meta_path):
    """Create the parser to add informations to the group file."""
    create_file = f"echo \"Sample\tTissueType\"  > \"{multqc_path}/sample_group.txt\""
    add_sample_info = f"jq -r 'to_entries[] | [.value.\"Sample Name\", .value.Group] | @tsv' \"{sample_meta_path}/sample.json\" | sed 's/\tnan$/\tUnknown/g' >> \"{multqc_path}/sample_group.txt\""
    exit_code(os.system(create_file))
    exit_code(os.system(add_sample_info))


def validate(user_inputs):
    """Checks user input to see if file/directory exists or is accessible.
    If a file does not exist, the error is redirected to stderr and exits with
    exit-code 1. If a directory does not exist, it will attempt to create it.
    """
    
    if len(user_inputs) == 7:
        meta_sheet, input_path, output_path, vault, dryrun, update, full_pipe = user_inputs
        multiQC_path = ''
    elif len(user_inputs) == 8:
        meta_sheet, input_path, output_path, vault, multiQC_path, dryrun, update, full_pipe = user_inputs
        path_exists(multiQC_path)

    file_exists(meta_sheet)
    path_exists(input_path)
    path_exists(output_path)
    valid_config(vault,'.vaults')

    return meta_sheet, input_path, output_path, vault, multiQC_path, dryrun, update, full_pipe


def _replace(s):
    """Replace issue characters of the input string to be handled by bash."""
    s = s.replace('(','\(').replace(')','\)')
    return s


def _get_sample_id(sample_metadata):
    """Returns the sample id from the sample_metadata dictionary."""
    for m in sample_metadata:
        if m['attribute'] == 'raw_file_1':
            return m['value']
    return None


def exit_code(val):
    """Breaks if the exit code from a bash command receives an error signal."""
    if (val == 1):#Update != 0
        estart, eend = config['.error']
        print("{}Error:{} in pipeline... exiting".format(estart, eend), file=sys.stderr)
        sys.exit(1)


def main():
    # @args(): Parses positional command-line args
    # @validate(): Checks if user inputs are vaild
    meta_sheet, input_path, output_path, vault, multiQC_path, dryrun, update, full_pipe = validate(args(sys.argv))

    # Set warnings and error configs
    cstart, cend = config['.warning']
    estart, eend = config['.error']

    # Execute all of the previous steps from the pyrkit pipeline
    if (full_pipe):
        exit_code(os.system(f"python src/lint.py {meta_sheet} {output_path}"))
        if (multiQC_path != ''):
            _create_parser(multiQC_path,output_path)
            exit_code(os.system(f"python src/pyparser.py {multiQC_path}/*.txt"))
            file = "multiqc_matrix.tsv"
            exit_code(os.system(f"python src/initialize.py {output_path} {output_path}/meta {vault} --convert -m {file}"))
        else:
            exit_code(os.system(f"python src/initialize.py {output_path} {output_path}/meta {vault} --convert"))

    # With the data/metadata created, register PI_Lab collection
    pi_dir = [f for f in os.listdir(f"{output_path}/meta") if ".metadata.json" not in f][0]
    pi_meta_fadd = f"{output_path}/meta/{pi_dir}.metadata.json"
    pi_meta_file = open(pi_meta_fadd)
    pi_meta = json.load(pi_meta_file)
    pi_command = _replace(f"dm_register_collection {pi_meta_fadd} /{vault}/{pi_dir}")
    print('- Uploading PI_Lab metadata')
    exit_code(os.system(pi_command))

    # With the data/metadata created, register Project collection
    project_dir = [f for f in os.listdir(f"{output_path}/meta/{pi_dir}") if ".metadata.json" not in f][0]
    project_meta_fadd = f"{output_path}/meta/{pi_dir}/{project_dir}.metadata.json"
    project_meta_file = open(project_meta_fadd)
    project_meta = json.load(project_meta_file)
    project_command = _replace(f"dm_register_collection {project_meta_fadd} /{vault}/{pi_dir}/{project_dir}")
    print('- Uploading Project metadata')
    exit_code(os.system(project_command))

    # With the data/metadata created, register Sample collections
    samples_dir = [f for f in os.listdir(f"{output_path}/meta/{pi_dir}/{project_dir}") if ".metadata.json" not in f]
    samples_meta_fadd = [f"{output_path}/meta/{pi_dir}/{project_dir}/{sd}.metadata.json" for sd in samples_dir]
    samples_meta_file = [open(sa) for sa in samples_meta_fadd]
    samples_meta = [json.load(f) for f in samples_meta_file]
    print(f"- Uploading Sample metadata{' (but not files - update mode)' if update else ''}")
    for i in range(len(samples_dir)):
        print(f"  > Sample {i+1}/{len(samples_dir)}")
        sample_command = _replace(f"dm_register_collection {samples_meta_fadd[i]} /{vault}/{pi_dir}/{project_dir}/{samples_dir[i]}")
        exit_code(os.system(sample_command))

        if (update):
            continue
        data_name = _get_sample_id(samples_meta[i]['metadataEntries'])
        print(f"    - Uploading {data_name} (R1) data")
        data_command = _replace(f"dm_register_dataobject {samples_meta_fadd[i]} /{vault}/{pi_dir}/{project_dir}/{samples_dir[i]}/{data_name}.R1.fastq.gz {input_path}/{data_name}.R1.fastq.gz")
        exit_code(os.system(data_command))
        print(f"    - Uploading {data_name} (R2) data")
        data_command = _replace(f"dm_register_dataobject {samples_meta_fadd[i]} /{vault}/{pi_dir}/{project_dir}/{samples_dir[i]}/{data_name}.R2.fastq.gz {input_path}/{data_name}.R2.fastq.gz")
        exit_code(os.system(data_command))


if __name__ == '__main__':
    main()
