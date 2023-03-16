# pyrkit

[![GitHub releases](https://img.shields.io/github/release/skchronicles/pyrkit)](https://github.com/skchronicles/pyrkit/releases) [![Build](https://github.com/skchronicles/pyrkit/workflows/ci/badge.svg)](https://github.com/skchronicles/pyrkit/actions)  [![GitHub issues](https://img.shields.io/github/issues/skchronicles/pyrkit)](https://github.com/skchronicles/pyrkit/issues) [![GitHub license](https://img.shields.io/github/license/skchronicles/pyrkit)](https://github.com/skchronicles/pyrkit/blob/master/LICENSE)  

a tool to archive and co-locate NGS data with project-level, sample-level, and analysis-level metadata.

### Table of Contents
1. [Overview](#1-Overview)   
2. [Getting Started](#2-Getting-Started)    
    2.1 [Dependencies](#21-Dependencies)   
    2.2 [Installation](#22-Installation)   
3. [Run pyrkit](#3-Run-pyrkit)   
    3.1 [Usage](#31-Usage)  
    3.2 [Required Arguments](#32-Required-Arguments)  
    3.3 [OPTIONS](#33-OPTIONS)   
    3.4 [Example](#34-Example)

### 1. Overview

pyrkit, pronouced `park-it`, automates the process of moving data from the cluster into object storage in HPC DME. It instantiates a collection heirarchy to archive raw data and results. pyrkit parses a project request template, a pipeline's output directory, and a MultiQC directory to capture project, analysis, quality-control metadata. pyrkit was created to enable FAIR scientific data management and stewardship.

![DME Heirarchy](./assets/DME_Upload_Hierarchy.svg)

> **Please Note**: Some of the metadata listed in the example above is pipeline-specific (i.e. only for the [RNA-seq pipeline](https://ccbr.github.io/pipeliner-docs/RNA-seq/Gene-and-isoform-expression-overview/)).

### 2. Getting Started

#### 2.1 Dependencies 
pykrit has a few required dependencies. It requires the installation of the following programs:
  - [`jq`](https://stedolan.github.io/jq/download/)
  - [`python3`](https://www.python.org/downloads/) 
  - [`HPC DME toolkit`](https://wiki.nci.nih.gov/display/DMEdoc/Getting+Started)

Please note that if you running pyrkit on Biowulf, the only dependency you will need to install in the [`HPC DME toolkit`](https://wiki.nci.nih.gov/display/DMEdoc/Getting+Started). pyrkit will attempt to module load jq and python/3.5 (which meets any python requirements), if they are not in your $PATH.

#### 2.2 Installation

Installation of pyrkit is easy! Please clone the repository from Github, create a virtual enviroment, and install any dendencies. Again, if you are on Biowulf, all you will need to do is clone the repository.

```bash
# Clone the Repository
git clone https://github.com/skchronicles/pyrkit.git

# Steps below are optional for biowulf users
# Create a virtual environment
python3 -m venv .venv
# Activate the virtual environment
. .venv/bin/activate
# Update pip
pip install --upgrade pip
# Download Dependencies
pip install -r requirements.txt
```

#### 3. Run pyrkit

#### 3.1 Usage

``` bash
usage: pyrkit -i INPUT_DIRECTORY -o OUTPUT_VAULT -r REQUEST_TEMPLATE
              -m MULTIQC_DIRECTORY -d DME_REPO [-p PROJECT_ID] [-n]
              [-l] [-v] [-h] [--version]
```

#### 3.2 Required Arguments 

| Argument                 | Type    | Description                       | Example                                |  
| ------------------------ | ------- | --------------------------------- | -------------------------------------- |  
| -i, --input-directory    | Path    | Pipeline output directory         | `/scratch/RNA_hg38/`                   |  
| -o, --output-vault       | String  | HPC DME vault to upload data      | `/CCBR_Archive`                        |  
| -r, --request-template   | File    | Project Request Template          | `experiment_metadata.xlsx`             |  
| -m, --multiqc-directory  | Path    | MultiQC Output Directory          | `/scratch/RNA_hg38/multiqc_data/`      |        
| -d, --dme-repo           | Path    | Path to a HPC DME toolkit install | `~/DME/HPC_DME_APIs/`                  |  

#### 3.3 OPTIONS

| Argument                 | Type    | Description                           | Example             |  
| ------------------------ | ------- | ------------------------------------- | ------------------- | 
| -p, --project-id         | String  | Project ID                            | `ccbr-123`          | 
| -n, --dry-run            | Flag    | Dry-run the entire pyrkit workflow    | `-n`                |
| -n, --local-run          | Flag    | Upload to DME without job submission  | `-l`                |
| -v, --validate           | Flag    | Validate entries before submission    | `-v`                |
| -h, --help               | Flag    | Display help message and exit         | `-h`                |
| --version                | Flag    | Display version information and exit  | `--version`         |

##### 3.4 Example 
```bash 
# Grab an interactive node or submit pyrkit command to cluster
# Do not run this on the head node!
sinteractive --mem=8g --cpus-per-task=2

# Dry runs pyrkit and submits job to upload data to cluster
./pyrkit -i /scratch/ccbr123/RNA_hg38/ \
         -o /CCBR_Archive \
         -r experiment_metadata.xlsx \
         -m /scratch/ccbr123/RNA_hg38/multiqc_data/ \
         -d ~/DME/HPC_DME_APIs/ \
         -p ccbr-123
```
