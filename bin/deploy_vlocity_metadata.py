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

# default global values
this = sys.modules[__name__]
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1

ORGS_JSON_PATH = 'config'
ORGS_JSON_FILENAME = '.orgs.json'
CONFIG = 'etc'
TEMPLATES_FOLDER = 'jobTemplates'
VLOCITY_YAML_TEMPLATE = 'VlocityTypeTemplate.yaml'
TEMP = 'temp'
#DEPLOYMENT_PATH = 'config'
DEPLOYMENT_PATH = ''
DEPLOYMENT_FOLDER = 'packages'
#SCRIPT_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))
SCRIPT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
CURRENT_WORKING_PATH = os.getcwd()
VLOCITY_OBJECT_MAP_FILENAME = 'vlocity_sobject_map.csv'
QUERY_TEMPLATE_STRING = "Select Id FROM %vlocity_namespace%__%sobject% where Name='%name%'%otherConditions%"
VLOCITY_NAMESPACE = 'vlocity_cmt'

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

def print_info(info):
   if(DEBUG):
      print(info)

def print_error(message):
   raise SystemExit(color_string(message, Color.RED))

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

def deploy_vlocity_metadata(row, target_env, remotes, deployed_components):
   skipped = False
   deploy_cmd = ''
   result = ''
      
   remote = get_remote(target_env, remotes)
   if('Backlog_Item__r.Name' not in row):
      raise SystemExit("'Backlog_Item__r.Name' key is missing in input data")
   elif('Retrieval_Status' not in row):
      raise SystemExit("'Retrieval_Status' key is missing in input data")
   elif('Job_File_Path' not in row):
      raise SystemExit("'Job_File_Path' key is missing in input data")

   item = row['Backlog_Item__r.Name']
               
   if(row['Retrieval_Status'] == 'Success' or this.IGNORE_ERRORS):
      if('Job_File_Path' in row and os.path.exists(row['Job_File_Path'])):
         deploy_cmd = 'vlocity packDeploy -job="' + row['Job_File_Path'] + '" -sf.username="'  + remote['username'] + '" -sf.password="' + remote['password'] + '" -sf.loginUrl="' + remote['serverUrl'] + '"'
         print_info('Running command: ' + color_string(deploy_cmd, Color.BLUE))
         #result = commands.getoutput(deploy_cmd)
         result = subprocess.check_output(deploy_cmd, shell=True)
         #print(commands.getoutput(deploy_cmd))
      else:
         print_info(color_string('Package path not specified or doesn\'t exist!', Color.RED))
   else:
      print_info('Skipping ' + color_string(item, Color.BLUE) + ' as it wasn\'t successfully retrieved (' + row['Retrieval_Details'] + ')')
      skipped = True

   if(this.DEBUG and this.DEBUG_LEVEL == 2):
      print_info(result)      

   # remove formatting from the result
   ansi_escape = re.compile(r'[\s]?\x1b\[[0-?]*[ -/]*[@-~]')
   result = ansi_escape.sub('', result)

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
  
   #print(result_dict) 

   # initialize deployment_components with values from retrieval
   deployed_components[row['Backlog_Item__r.Name']] = row.copy()

   # default values
   deployment_status = ''
   if(skipped):
      deployment_status = 'Skipped'
   else:
      deployment_status = 'Success'

   deployment_details = row['Job_File_Path']
   deployment_error_message = ''
  
   # check errors
   if(get_error(result_dict)):
      deployment_status = 'Failed'
      deployment_error_message = 'Errors for item: ' + row['Backlog_Item__r.Name'] + ' (' + deployment_detials + ')'
      deployment_error_message = deployment_error_message + '\n' + get_error_message(result_dict)
      if(IGNORE_ERRORS):
         print_info(color_string(deployment_error_message, Color.RED))
      else:
         raise SystemExit(color_string(deployment_error_message, Color.RED))
 
   # if successfully deployed add component to deployed_components dictionary
   if(row['Backlog_Item__r.Name'] not in deployed_components):
      # add the original csv row to the result
      deployed_components[row['Backlog_Item__r.Name']] = row.copy()
      
   # update deployment status
   deployed_components[row['Backlog_Item__r.Name']]['Deployment_Status'] = deployment_status
   deployed_components[row['Backlog_Item__r.Name']]['Deployment_Error_Message'] = deployment_error_message
   deployed_components[row['Backlog_Item__r.Name']]['Deployment_Details'] = deployment_details

   if(deployment_status == 'Success'):
      deployed_components[row['Backlog_Item__r.Name']]['Components'] = get_successfully_deployed_components(result_dict)
      print_info('Successfully deployed')
   else:
      print_info(deployment_status)
   
   #subprocess.check_output(retrieve_cmd, shell=True)

def get_error(result):
   if "Errors" in result:
      for error in result['Errors']:
         if(error != '0'):
            return True
   return False

def get_error_message(result):
   error_message = ''
   error_message_counter = 0
   for key in result:
      if key != "Errors" and ("Error" in key or "error" in key):
         error_message_counter = error_message_counter + 1
         if(error_message_counter <= 0):
            error_message = error_message + key + ': ' + result[key]
         else:
            error_message = error_message + '\n' + key + ': ' + result[key]

def get_successfully_deployed_components(result):
   #deployed_components = []
   #for key in result:
   #   if key == "Deploy Success":
   #      deployed_components.append(result['Deploy Success'])
   if 'Deploy Success' in result:
      return result['Deploy Success']
   else:
      return []

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
def main():
   parser = argparse.ArgumentParser(description='Exports vlocity components from a source SF environment.\n' +
                                                'Example:\n' +
                                                '\tretrieve_vlocity_components.py -d',
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
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   args = parser.parse_args()
   this.DEBUG = args.debug
   this.IGNORE_ERRORS = args.ignore_errors
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2
   environments = args.environments.split(',')

   # remotes
   orgs_json_file_path = Path(ORGS_JSON_PATH + '/' + ORGS_JSON_FILENAME)
   remotes = get_remote_org_configuration(orgs_json_file_path)

   # TODO check whether is force-dev-tool installed
   #if(platform.system() != 'Windows' and not is_tool("force-dev-tool")):
   if(platform.system() != 'Windows' and not is_tool("force-dev-tool")):
      raise SystemExit('Please install force-dev-tool first!\nFor more information look at\n"https://github.com/amtrack/force-dev-tool"')

   # TODO check whether is force-dev-tool installed
   if(platform.system() != 'Windows' and not is_tool("vlocity")):
      raise SystemExit('Please install vlocity_build first!\nFor more information look at\n"https://github.com/vlocityinc/vlocity_build"')

   # loop through input (stdin)
   counter = 0
   #csv_reader = csv.DictReader(fileinput.input(mode='rb'), delimiter=',')
   csv_reader = csv.DictReader(iter(sys.stdin.readline, ''))

   deployed_components = {}
   for row in csv_reader:
      counter = counter + 1
      
      # print new line
      if(counter > 1):
         print_info('\n')
      output_folder = ''

      print_info(color_string('Component #' + str(counter) + ' (' + row['Backlog_Item__r.Name'] + ')', Color.GREEN))
      #print(row)

      # get_vlocity_yaml_file
      #vlocity_template_path = SCRIPT_FOLDER_PATH + '/' + CONFIG + '/' + TEMPLATES_FOLDER + '/' + VLOCITY_YAML_TEMPLATE
      #vlocity_yaml_file_string = get_vlocity_yaml_file(vlocity_template_path, other_conditions, object_map_by_vlocity_type, row, output_folder)
      
      # write temporary yaml file
      #vlocity_yaml_file_path = TEMP + '/' + row['Backlog_Item__r.Name'] + '.yaml'
      #write_temporary_yaml_file(vlocity_yaml_file_path, vlocity_yaml_file_string)
      
      for target_env in environments:
         # retrieve vlocity metadata for the current row
         deploy_vlocity_metadata(row, target_env, remotes, deployed_components)
      
   write_csv_output(deployed_components)
 
if __name__ == "__main__":
   main()
