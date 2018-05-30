#!/usr/bin/env python

# author        : Stepan Ruzicka
# date          : 2018.05.24

import sys
import os
import argparse
from argparse import RawTextHelpFormatter
import json
import subprocess
import re

# script context variables
SCRIPT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
CURRENT_WORKING_PATH = os.getcwd()
this = sys.modules[__name__]

# default config values
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1

# configuration folders and files
SF_CLEANUP_JSON_CONFIG = 'salesforce_metadata_cleanup_config.json'
CONFIG = '../etc'

def is_tool(name):
   return find_executable(name) is not None   

# load synchronization configuration
def load_config(config_file_path):
   with open(SCRIPT_FOLDER_PATH + '/' + CONFIG + '/' + config_file_path, 'r') as json_file:
      json_data = json.load(json_file)

   return json_data

def get_folder_list(path):
   folder_list = []
   for name in os.listdir(path):
      if os.path.isdir(path + '/' + name):
          folder_list.append(name)
   return folder_list

def get_file_list(path, fileMask = '.*'):
   file_list = []

   for name in os.listdir(path):
      file_matcher = re.compile(fileMask)
      if not os.path.isdir(path + '/' + name) and file_matcher.match(name):
          file_list.append(name)
   return file_list

def remove_element_matching(sf_cleanup_config, path, folder_list):
   if 'remove-element-matching' in sf_cleanup_config:
      config = sf_cleanup_config['remove-element-matching']
      for folder_name in folder_list:
         if folder_name in config:
            folder_config = config[folder_name]
            for rule in folder_config:
               if 'matching' in rule  and 'element-name' in rule:
                  file_list = []
                  matching = rule['matching']

                  if 'fileMask' in rule:
                     file_list = get_file_list(path + "/" + folder_name, rule['fileMask'])
                  else:
                     file_list = get_file_list(path + "/" + folder_name)
                  
                  for file_name in file_list:
                     element = rule['element-name']
                     cmd = 'metadata-xml-tool remove-element-matching ' + element + ' "' +  matching + '" ' + path + "/" + folder_name + "/" + file_name

                     try:
                        result = subprocess.check_output(cmd, shell=True)
                     except subprocess.CalledProcessError as e:
                        if(not IGNORE_ERRORS):
                           raise RuntimeError("remove-element_matching command failed (Command: '{}' returned error (code {}). If you want to ignore errors during the processing you can run it with --ignore-errors parameter. Please, also use -d parameter for more details".format(e.cmd, e.returncode))
                        result = e.output 

def remove_element(sf_cleanup_config, path, folder_list):
   if 'remove-element' in sf_cleanup_config:
      config = sf_cleanup_config['remove-element']
      for folder_name in folder_list:
         if folder_name in config:
            folder_config = config[folder_name]
            for rule in folder_config:
               if 'element-name' in rule:
                  file_list = []

                  if 'fileMask' in rule:
                     file_list = get_file_list(path + "/" + folder_name, rule['fileMask'])
                  else:
                     file_list = get_file_list(path + "/" + folder_name)
                  
                  for file_name in file_list:
                     element = rule['element-name']
                     cmd = 'metadata-xml-tool remove-element ' + element + ' ' + path + "/" + folder_name + "/" + file_name
        
                     try:
                        result = subprocess.check_output(cmd, shell=True)
                     except subprocess.CalledProcessError as e:
                        if(not IGNORE_ERRORS):
                           raise RuntimeError("remove-element command failed (Command: '{}' returned error (code {}). If you want to ignore errors during the processing you can run it with --ignore-errors parameter. Please, also use -d parameter for more details".format(e.cmd, e.returncode))
                        result = e.output 

def replace_tag_value(sf_cleanup_config, path, folder_list):
    if 'replace-tag-value' in sf_cleanup_config:
      config = sf_cleanup_config['replace-tag-value']
      for folder_name in folder_list:
         if folder_name in config:
            folder_config = config[folder_name]
            for rule in folder_config:
               if 'element-name' in rule and 'value' in rule and 'replace-value' in rule:
                  file_list = []

                  if 'fileMask' in rule:
                     file_list = get_file_list(path + "/" + folder_name, rule['fileMask'])
                  else:
                     file_list = get_file_list(path + "/" + folder_name)
                  
                  for file_name in file_list:
                     element = rule['element-name']
                     value = rule['value']
                     replace_value = rule['replace-value']
                     cmd = 'metadata-xml-tool replace-tag-value ' + element + ' "' + value + '" "' + replace_value + '" ' +  path + "/" + folder_name + "/" + file_name 
        
                     try:
                        result = subprocess.check_output(cmd, shell=True)
                     except subprocess.CalledProcessError as e:
                        if(not IGNORE_ERRORS):
                           raise RuntimeError("replace-tag-value command failed (Command: '{}' returned error (code {}). If you want to ignore errors during the processing you can run it with --ignore-errors parameter. Please, also use -d parameter for more details".format(e.cmd, e.returncode))
                        result = e.output 
  


def main():
   parser = argparse.ArgumentParser(description='Removes unwanted content from  SF metadata using configuration file.\n' +
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
        help="Destination folder", required=False)

   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   args = parser.parse_args()

   # arguments assignment to global variables
   this.DEBUG = args.debug
   this.IGNORE_ERRORS = args.ignore_errors
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2

   # load sf cleanup  configuration
   sf_cleanup_config = load_config(SF_CLEANUP_JSON_CONFIG)
   
   # get list of folders first
   folder_list = get_folder_list(args.source)

   # remove-element-matching
   remove_element_matching(sf_cleanup_config, args.source, folder_list)

   # replace-tag-value
   replace_tag_value(sf_cleanup_config, args.source, folder_list)

   # remove-element 
   remove_element(sf_cleanup_config, args.source, folder_list)

   # remove_element_matching_dict = get_sf_cleanup_dict(sf_cleanup_config, 'remove-element-matching')

if __name__ == "__main__":
   main()
