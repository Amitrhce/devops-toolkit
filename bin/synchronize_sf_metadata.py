#!/usr/bin/env python

# author        : Stepan Ruzicka
# date          : 2018.05.24

import sys
import os
import argparse
from argparse import RawTextHelpFormatter
import json
import subprocess

'''
import json
import subprocess
import io
import csv
import fileinput
import argparse
from pathlib import Path
from argparse import RawTextHelpFormatter
import os
import commands
import re
import sys
from distutils.spawn import find_executable
import platform
import utils
'''

# script context variables
SCRIPT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
CURRENT_WORKING_PATH = os.getcwd()
this = sys.modules[__name__]

# default config values
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1

# configuration folders and files
SF_SYNC_JSON_CONFIG = 'salesforce_metadata_sync_config.json'
CONFIG = '../etc'

# load synchronization configuration
def load_sf_sync_config(sf_sync_config_file_path):
   with open(SCRIPT_FOLDER_PATH + '/' + CONFIG + '/' + sf_sync_config_file_path, 'r') as sf_sync_json:
      sf_sync_json_data = json.load(sf_sync_json)

   return sf_sync_json_data

def get_sf_folder_config(metadata_folder, sf_sync_json_data):
   if metadata_folder not in sf_sync_json_data:
      return None
   else:
      return sf_sync_json_data[metadata_folder] 

def get_folder_list(path):
   folder_list = []
   for name in os.listdir(path):
      if os.path.isdir(path + '/' + name):
          folder_list.append(name)
   return folder_list

def synchronize_folders(source_folder_path, destination_folder_path):
   if not os.path.exists(destination_folder_path):
      os.makedirs(destination_folder_path)

   sync_cmd = 'rsync -acv ' + source_folder_path + '/ ' + destination_folder_path
   try:
      result = subprocess.check_output(sync_cmd, shell=True)
   except subprocess.CalledProcessError as e:
      if(not IGNORE_ERRORS):
         raise RuntimeError("Synchronizatin of folders failed (Command: '{}' returned error (code {}). If you want to ignore errors during the synchronization you can run it with --ignore-errors parameter. Please, also use -d parameter for more details".format(e.cmd, e.returncode))
      result = e.output 


def main():
   parser = argparse.ArgumentParser(description='Synchronizes two folders with SF metadata using configuration file.\n' +
                                                'Example:\n' +
                                                '\t.py -d',
						formatter_class=RawTextHelpFormatter)
   parser.add_argument(
        "-d", "--debug", dest="debug",
        help="Debug mode", action="store_true")

   parser.add_argument(
        "--ignore-errors", dest="ignore_errors",
        help="Will keep on processing despite errors", action="store_true")

   parser.add_argument(
        "-s", "--source", dest="source",
        help="Source folder", required=True)

   parser.add_argument(
        "-t", "--target", dest="target",
        help="Destination folder", required=True)

   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   args = parser.parse_args()

   # arguments assignment to global variables
   this.DEBUG = args.debug
   this.IGNORE_ERRORS = args.ignore_errors
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2

   # load sf synchronization configuration
   sf_sync_config = load_sf_sync_config(SF_SYNC_JSON_CONFIG)

   # source folder
   for name in get_folder_list(args.source):
      folder_config = get_sf_folder_config(name, sf_sync_config)
      if 'synchronization' in folder_config and folder_config['synchronization'] == 'on':
         if 'preprocessing' in folder_config and folder_config['preprocessing'] == 'on':
            # run preprocessing
            pass
         if 'fileReplace' in folder_config and folder_config['fileReplace'] == 'off':
            # xml merge
            pass
         else:
            # simply replace files in folder
            source_folder_path = args.source + '/' + name
            destination_folder_path = args.target + '/' + name
            synchronize_folders(source_folder_path, destination_folder_path)
   
if __name__ == "__main__":
   main()
