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
import xml.etree.ElementTree as ElementTree

# script context variables
SCRIPT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
CURRENT_WORKING_PATH = os.getcwd()
this = sys.modules[__name__]

# default config values
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1
DEFAULT_NAMESPACE = "http://soap.sforce.com/2006/04/metadata"

# configuration folders and files
DEFAULT_SF_CLEANUP_JSON_CONFIG = 'salesforce_metadata_cleanup_config.json'
CONFIG = '../etc'

class Color:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    GREY = '\033[90m'
    BLACK = '\033[90m'
    DEFAULT = '\033[99m'
    ENDC = '\033[0m'

class Format:
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'

def color_string(string, color):
   if(color == Color.BLUE):
      return Color.BLUE + string + Color.ENDC
   elif(color == Color.RED):
      return Color.RED + string + Color.ENDC
   elif(color == Color.GREEN):
      return Color.GREEN + string + Color.ENDC
   elif(color == Color.CYAN):
      return Color.CYAN + string + Color.ENDC
   elif(color == Color.WHITE):
      return Color.WHITE + string + Color.ENDC
   elif(color == Color.MAGENTA):
      return Color.MAGENTA + string + Color.ENDC
   elif(color == Color.GREY):
      return Color.GREY + string + Color.ENDC
   elif(color == Color.BLACK):
      return Color.BLACK + string + Color.ENDC
   elif(color == Color.YELLOW):
      return Color.YELLOW + string + Color.ENDC
   else:
      return string

def format_string(string, format):
   if(color == Color.UNDERLINE):
      return Format.UNDERLINE + string + Format.ENDC
   elif(color == Format.BOLD):
      return Format.BOLD + string + Format.ENDC
   else:
      return string

def print_info(info):
   if(DEBUG):
      print(info)

def print_error(message):
   print color_string(message, Color.RED)

def is_tool(name):
   return find_executable(name) is not None   

# load synchronization configuration
def load_config(config_file_path):
   with open(config_file_path, 'r') as json_file:
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

                     print_info("Element to be removed (if exists) " + color_string(element, Color.MAGENTA) + " matching " + color_string(matching, Color.MAGENTA) + " from " + color_string(path + "/" + folder_name + "/" + file_name, Color.MAGENTA))
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
        
                     print_info("Removing element " + color_string(element, Color.MAGENTA) + " from " + color_string(path + "/" + folder_name + "/" + file_name, Color.MAGENTA)) 
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
                     print_info("Replacing tag " + color_string(element, Color.MAGENTA) + " value " + color_string(replace_value, Color.MAGENTA) + " by "  + color_string(replace_value, Color.MAGENTA) + ' in ' + color_string(path + "/" + folder_name + "/" + file_name, Color.MAGENTA)) 
                     try:
                        result = subprocess.check_output(cmd, shell=True)
                     except subprocess.CalledProcessError as e:
                        if(not IGNORE_ERRORS):
                           raise RuntimeError("replace-tag-value command failed (Command: '{}' returned error (code {}). If you want to ignore errors during the processing you can run it with --ignore-errors parameter. Please, also use -d parameter for more details".format(e.cmd, e.returncode))
                        result = e.output 
  
def remove_files(sf_cleanup_config, path, folder_list):
    if 'remove-file' in sf_cleanup_config:
      config = sf_cleanup_config['remove-file']
      for folder_name in folder_list:
         if folder_name in config:
            folder_config = config[folder_name]
            for rule in folder_config:
               file_list = []
               if 'fileMask' in rule:
                  file_list = get_file_list(path + "/" + folder_name, rule['fileMask'])
               else:
                  file_list = get_file_list(path + "/" + folder_name)

               for file_name in file_list:
                  file_path = path + "/" + folder_name + "/" + file_name
                  print_info("Removing file " + color_string(file_path, Color.MAGENTA))
                  try:
                     os.remove(file_path)
                  except Exception as e:
                     error_message = "Unable to remove file " + file_path
                     if(not IGNORE_ERRORS):
                        raise RuntimeError(error_message)
                     else:
                        print_error(error_message)
               
               # if there is not file left in the folder then delete the folder as well
               if 'fileMask' in rule:
                  file_list = get_file_list(path + "/" + folder_name, rule['fileMask'])
               else:
                  file_list = get_file_list(path + "/" + folder_name)
 
               if len(file_list) == 0:
                  print_info("Folder is empty - removing folder: " + color_string(path + "/" + folder_name, Color.MAGENTA))
                  os.rmdir(path + "/" + folder_name)

def adjust_package_xml(sf_cleanup_config, path, folder_list, package_xml, namespace):
    if 'remove-file' in sf_cleanup_config:
      config = sf_cleanup_config['remove-file']
      for folder_name in folder_list:
         if folder_name in config:
            folder_config = config[folder_name]
            for rule in folder_config:
               file_list = []
               if 'fileMask' in rule:
                  file_list = get_file_list(path + "/" + folder_name, rule['fileMask'])
               else:
                  file_list = get_file_list(path + "/" + folder_name)

               for file_name in file_list:
                  if 'package_xml_type' in rule:
                     # TODO: optimize - pass dictionary with names and members
                     remove_from_package_xml(package_xml, rule['package_xml_type'], get_filename_without_extension(file_name), namespace)

def remove_from_package_xml(package_xml, name, member, namespace):
   root = package_xml.getroot()
   for child in root:
      element_name = child.find('{' + namespace  + '}' + 'name') 
      if element_name is not None and get_element_local_name(element_name) == 'name' and element_name.text == name:
         element_members = child.findall('{' + namespace  + '}' + 'members')
         for element_member in element_members:
            if element_member.text == member:
               print_info("Removing element from package.xml " + color_string(name + "." + member, Color.MAGENTA))
               child.remove(element_member)
               # check whether it's empty if yes, delete the parent as well
               temp_element_members = child.findall('{' + namespace  + '}' + 'members')
               if len(temp_element_members) == 0:
                  print_info("Parent element " + color_string(element_name.text, Color.MAGENTA) + " is empty, removing this as well.")
                  root.remove(child)

def get_element_local_name(element):
   match = re.search('\{.*\}(.*)', element.tag)
   return match.group(1) if match else ''

def get_filename_without_extension(file_name):
   return file_name.split('.')[0]

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
        "-c", "--cleanup-config", dest="cleanup_config",
        help="Cleanup config file path", required=False)

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

   if(args.cleanup_config):
      sf_cleanup_config_path = args.cleanup_config
   else:
      sf_cleanup_config_path = SCRIPT_FOLDER_PATH + '/' + CONFIG + '/' + DEFAULT_SF_CLEANUP_JSON_CONFIG

   # default namespace
   ElementTree.register_namespace('', DEFAULT_NAMESPACE)
   package_xml_path = args.source + "/package.xml"

   package_xml = None   
   if os.path.isfile(package_xml_path):
      package_xml = ElementTree.parse(package_xml_path)
   else:
      print_error(package_xml_path + " not found!")

   # load sf cleanup  configuration
   sf_cleanup_config = load_config(sf_cleanup_config_path)
   
   # get list of folders first
   folder_list = get_folder_list(args.source)

   # remove-element-matching
   remove_element_matching(sf_cleanup_config, args.source, folder_list)

   # replace-tag-value
   replace_tag_value(sf_cleanup_config, args.source, folder_list)

   # remove-element 
   remove_element(sf_cleanup_config, args.source, folder_list)

   if package_xml:   
      adjust_package_xml(sf_cleanup_config, args.source, folder_list, package_xml, DEFAULT_NAMESPACE)
      # write out the adjusted package.xml
      package_xml.write(package_xml_path, encoding="UTF-8", xml_declaration = True)

   # remove files and folder (if folder is empty)
   remove_files(sf_cleanup_config, args.source, folder_list)

if __name__ == "__main__":
   main()
