#!/usr/bin/env python

# author        : Stepan Ruzicka
# date          : 2018.03.02

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
import xmltodict
import xml.etree.ElementTree as ElementTree

# default global values
this = sys.modules[__name__]
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1

ORGS_JSON_PATH = 'config'
ORGS_JSON_FILENAME = '.orgs.json'
CONFIG = 'etc'
TEMP = 'temp'
SCRIPT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
CURRENT_WORKING_PATH = os.getcwd()
CODE_COVERAGE_LIMIT = 85

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

def load_remotes(orgs_json_file_path):
   with open(orgs_json_file_path, 'r') as orgs_json:
      orgs_json_data = json.load(orgs_json)

   if 'remotes' not in orgs_json_data:
      raise ValueError(orgs_json_file_path + " is invalid")
   else:
      return orgs_json_data['remotes']

def get_remote(remote_name, remotes):
   if remote_name not in remotes:
      raise SystemExit('Environment ' + remote_name + ' is not configured!')
   else:
      return remotes[remote_name] 

def print_info(info, color=None):
   if(DEBUG):
      if(color):
         print(color_string(info, color))
      else:
         print(info)

def print_error(message, color = None):
   if(color):
      print >> sys.stderr, color_string(message, color)
   else:
      print >> sys.stderr, message

def get_remote_org_configuration(org_json_file_path):
   orgs_json_file = Path(org_json_file_path)
   if(orgs_json_file.is_file()):
      remotes = load_remotes(ORGS_JSON_PATH + '/' + ORGS_JSON_FILENAME)
   else:
      orgs_json_file = Path(ORGS_JSON_FILENAME)
      if(orgs_json_file.is_file()):
         remotes = load_remotes(ORGS_JSON_FILENAME)
      else:
         raise SystemExit(ORGS_JSON_FILENAME + ' not found!')
   return remotes

def process_result(result, item):
   # transform result to dictionary
   result_dict = {}
   for line in result.splitlines():
      result_array = line.split('>>')
      if(len(result_array) > 1):
         if result_array[0].strip() not in result_dict:
            result_dict[result_array[0].strip()] = [result_array[1].strip()]
         else:
            result_dict[result_array[0].strip()].append(result_array[1].strip())
      else:
         result_dict[result_array[0].strip()] = ''  

def is_tool(name):
    return find_executable(name) is not None

def write_csv_output(deployed_components):
   # write csv output if debug mode is not turned on
   if(not this.DEBUG):
      #fieldnames_output = list(csv_reader.fieldnames)
      #fieldnames_output.append("Deployment_Status")
      fieldnames_output = {'Backlog_Item__r.Name', 'Retrieval_Status', 'Retrieval_Error_Message', 'Retrieval_Details', 'Deployment_Status', 'Deployment_Details', 'Job_File_Path', 'Output_Folder'}
      csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames_output, quoting=csv.QUOTE_ALL)
      csv_writer.writeheader()   
   if(this.DEBUG):
      print_info('\nSummary:')
   #print(deployed_components)
   for item in deployed_components:
      # write csv output if debug mode is not turned on
      if(not this.DEBUG):
         row_out = {'Backlog_Item__r.Name': item, 'Retrieval_Status': deployed_components[item]['Retrieval_Status'], 'Retrieval_Error_Message': deployed_components[item]['Retrieval_Error_Message'], 'Retrieval_Error_Message': deployed_components[item]['Retrieval_Details'], 'Deployment_Status': deployed_components[item]['Deployment_Status'], 'Deployment_Details': deployed_components[item]['Deployment_Error_Message'], 'Job_File_Path': deployed_components[item]['Job_File_Path'], 'Output_Folder': deployed_components[item]['Output_Folder']}
         csv_writer.writerow(row_out)
      if(deployed_components[item]['Deployment_Status'] != 'Success'):
         print_info('For item ' + color_string(item, Color.BLUE) + ' deployment failed! Error message is: ' + deployed_components[item]['Deployment_Error_Message'])
      elif 'Components' in deployed_components[item]:
         print_info('For item ' + color_string(item, Color.BLUE) + ' deployed components are:')
         for component in deployed_components[item]['Components']:         
            print_info('\t' + component)

def check_test_class_presence(class_list, test_class_list):
   missing_test_classes = []
   for class_name in class_list:
      if(class_name + '_Test' not in test_class_list):
         missing_test_classes.append(class_name + '_Test')
         #print_info(color_string('Test class is missing ' + class_name + '_Test', Color.RED))
   return missing_test_classes

def check_class_presence(class_list, test_class_list):
   missing_classes = []
   for test_class_name in test_class_list:
      test_suffix = re.compile(r'_Test')
      class_name = test_suffix.sub('', test_class_name)
      if(class_name not in class_list):
         missing_classes.append(class_name)
         #print_info(color_string('Class is missing ' + class_name, Color.RED))
   return missing_classes

def get_list_of_classes(package_xml, class_list, test_class_list):
   test_class_pattern = re.compile(r'^.+_Test')
   
   if os.path.isfile(package_xml):
      with open(package_xml) as package_xml_fd:
         package_xml_dict = xmltodict.parse(package_xml_fd.read())
      
      if 'types' in package_xml_dict['Package']:
	 # is types list or dictionary?
	 if isinstance(package_xml_dict['Package']['types'], dict):
	    type_element = package_xml_dict['Package']['types']
	    if type_element['name'] == 'ApexClass':
	       if isinstance(type_element['members'], dict):
		  class_name = type_element['members']
		  if not re.search(test_class_pattern, class_name):
		     print_info('Adding class into a list of classes: ' + color_string(class_name, Color.MAGENTA))
		     class_list.append(class_name)
		  else:
		     print_info('Adding class into a list of test classes: ' + color_string(class_name, Color.MAGENTA))
		     test_class_list.append(class_name)
	      
	       else:
		  for class_name in type_element['members']:
		     if not re.search(test_class_pattern, class_name):
			print_info('Adding class into a list of classes: ' + color_string(class_name, Color.MAGENTA))
			class_list.append(class_name)
		     else:
			print_info('Adding class into a list of test classes: ' + color_string(class_name, Color.MAGENTA))
			test_class_list.append(class_name)
	
	 else:
	    for type_element in package_xml_dict['Package']['types']:
	       if type_element['name'] == 'ApexClass':
		  if isinstance(type_element['members'], dict):
		     class_name = type_element['members']
		     if not re.search(test_class_pattern, class_name):
			print_info('Adding class into a list of classes: ' + color_string(class_name, Color.MAGENTA))
			class_list.append(class_name)
		     else:
			print_info('Adding class into a list of test classes: ' + color_string(class_name, Color.MAGENTA))
			test_class_list.append(class_name)
		  else:
		     for class_name in type_element['members']:
			if not re.search(test_class_pattern, class_name):
			   print_info('Adding class into a list of classes: ' + color_string(class_name, Color.MAGENTA))
			   class_list.append(class_name)
			else:
			   print_info('Adding class into a list of test classes: ' + color_string(class_name, Color.MAGENTA))
			   test_class_list.append(class_name)
   return class_list

def force_login(remote):
   login_cmd = 'force login -i=' + remote['serverUrl'] + ' -u=' + remote['username'] + ' -p=' + remote['password']
   print_info('Running command: ' + color_string(login_cmd, Color.BLUE))
   result = subprocess.check_output(login_cmd, shell=True)
   return result

def prepare_test_run_command(test_class):
   test_cmd = 'force test' + ' ' + test_class
   return test_cmd

def process_test_result(test_class_name, result):
   test_results = {}
   coverage = {}
   percentage_pattern = re.compile(r'[0-9]+%')
   for line in result.splitlines():
      result_array = line.split()

      if(len(result_array) > 1 and result_array[1].strip() not in test_results and re.search(percentage_pattern, result_array[0].strip())):
         test_results[result_array[1].strip()] = result_array[0].strip()
   test_suffix = re.compile(r'_Test')
   class_name = test_suffix.sub('', test_class_name)
   if(class_name in test_results):
      coverage[class_name] = test_results[class_name]
   else:
      coverage[class_name] = '0'
   return coverage

def get_code_coverage(test_class_list, target_env, remotes):
   coverage_dict = {}
   if(len(test_class_list) > 0):
      if(platform.system() != 'Windows' and not is_tool("force")):
         raise SystemExit('Please install force first!\nFor more information look at\n"http    s://..."')
      remote = get_remote(target_env, remotes)
 
      force_login(remote)
      for test_class in test_class_list:
         test_cmd = prepare_test_run_command(test_class)
         print_info('Running command: ' + color_string(test_cmd, Color.BLUE))
         result = ''
         try:
            result = subprocess.check_output(test_cmd, shell=True, stderr=subprocess.STDOUT)
         except subprocess.CalledProcessError as e:
            error_message = test_class + ' failed'
            print_info(color_string(error_message, Color.RED))
         result = process_test_result(test_class, result)
         coverage_dict.update(result)
   return coverage_dict

def percentage_to_int(percentage):
   int_value = int(percentage.replace("%", ""))
   return int_value

def main():
   parser = argparse.ArgumentParser(description='Runs tests in target environment and gets code coverage.\n' +
                                                'Example:\n' +
                                                '\t' + os.path.basename(__file__)  + ' -d',
						formatter_class=RawTextHelpFormatter)
   parser.add_argument(
        "-d", "--debug", dest="debug",
        help="Debug mode", action="store_true")

   parser.add_argument(
        "--ignore-errors", dest="ignore_errors",
        help="Will keep on processing despite errors", action="store_true")

   parser.add_argument(
        "-t", "--target", dest="environments",type=str,required=True,
        help="Destination environments", )

   parser.add_argument(
        "-p", "--package_xml", dest="package_xml",type=str,required=False,
        help="Destination environments", )
 
   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   args = parser.parse_args()
   this.DEBUG = args.debug
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2
   environments = args.environments.split(',')

   this.IGNORE_ERRORS = args.ignore_errors

   # remotes
   orgs_json_file_path = Path(ORGS_JSON_PATH + '/' + ORGS_JSON_FILENAME)
   remotes = get_remote_org_configuration(orgs_json_file_path)

   # TODO check whether is force installed
   #if(platform.system() != 'Windows' and not is_tool("force-dev-tool")):
   if(platform.system() != 'Windows' and not is_tool("force")):
      raise SystemExit('Please install force first!\nFor more information look at\n"http://force-cli.herokuapp.com/"')

   # loop through input (stdin)
   counter = 0

   #input_list = list(iter(sys.stdin.readline, ''))
   # comma separated values?
   #comma_separated_values = input_list[0].count(",")
   comma_separated_values = ""

   # process input as csv
   if(comma_separated_values):
      # CSV on input
      for target_env in environments:
         csv_reader = csv.DictReader(input_list)
         #print(target_env)
         #print(csv_reader)
    
         test_results = {}
         counter = 0
         for row in csv_reader:
            counter = counter + 1
       
            # print new line
            if(counter > 1):
               print_info('\n')
            output_folder = ''

            print_info(color_string('Running tests for package #' + str(counter) + ' (' + row['Backlog_Item__r.Name'] + ')', Color.GREEN))
            
            class_list = []
            # read class list from package.xml
            package_xml = row['Output_Folder'] + '/src/' + 'package.xml'
            get_list_of_classes(package_xml, class_list, test_class_list)
      
            # construct the command, run tests and get code coverage for all the classes from package.xml
            code_coverage = get_code_coverage(row, target_env, remotes)
            print 'jsem tady'
            for class_coverage in code_coverage:
               print_error(class_coverage)

   elif(args.package_xml):
      class_list = []
      test_class_list = []
      coverage = {}
      for target_env in environments:
         package_xml_path = Path(args.package_xml)
         package_xml = ""
                        
         if(not package_xml_path.is_file()):
            print_error(args.package_xml + ' not found!')
         else:
            package_xml = ElementTree.parse(args.package_xml)

         get_list_of_classes(args.package_xml, class_list, test_class_list)
         missing_test_classes = check_test_class_presence(class_list, test_class_list)
         missing_classes = check_class_presence(class_list, test_class_list)

         for class_name in missing_test_classes:
            if(this.DEBUG):
               print_info('Info: Test class is missing ' + class_name, Color.RED)
            else:
               print_info('Info: Test class is missing ' + class_name)

         for class_name in missing_classes:
            if(this.DEBUG):
               print_info('Info: Class is missing ' + class_name, Color.RED)
            else:
               print_info('Info: Class is missing ' + class_name)

         code_coverage = get_code_coverage(test_class_list, target_env, remotes)
         error_flag = False
         for class_name in code_coverage:
            coverage_value = percentage_to_int(code_coverage[class_name])
            if(coverage_value < CODE_COVERAGE_LIMIT):
               error_flag = True
               if(this.DEBUG):
                  print_error('Error: ' + class_name + ' - test failed - code coverage is: ' + code_coverage[class_name], Color.RED)
               else:
                  print_error('Error: ' + class_name + ' - test failed - code coverage is: ' + code_coverage[class_name])
            else:
               print_info(class_name + ' successfully tested - code coverage is: ' + code_coverage[class_name])
 
         if(error_flag):
            sys.exit(1)

         if not(missing_test_classes):
            print_info('Info: No missing test classes')

         if not(missing_classes):
            print_info('Info: No missing classes')
   else:
      for target_env in environments:
         #process input as list of package paths
         # we need to create yaml file for each item
         counter = 0 
         for package_path in input_list:
            counter = counter + 1
            # print new line
            if(counter > 1):
               print_info('\n')

            package_name = os.path.basename(package_path.rstrip())
            package_folder = Path(package_path.rstrip())
                        
            if(not package_folder.is_dir()):
               raise SystemExit('Package folder: ' + package_path.rstrip() + ' not found!')
            
            row = {}
            row['Backlog_Item__r.Name'] = package_name
            row['Output_Folder'] = package_path.rstrip() + '/src'
            row['Package_XML'] = package_path.rstrip() + '/src/package.xml'

            print_info(color_string('Running tests for package #' + str(counter) + ' (' + row['Backlog_Item__r.Name'] + ')', Color.GREEN))

            class_list = get_list_of_classes(package_xml, class_list)
            test_class_list = get_list_of_test_classes(package_xml, class_list)
            check_test_class_presence(class_list, test_class_list)
            print(get_code_coverage(row, target_env, remotes))
 
if __name__ == "__main__":
   main()
