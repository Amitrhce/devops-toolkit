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

def load_vlocity_object_map(vlocity_object_map_path):
   vlocity_object_map_file = Path(vlocity_object_map_path)
   object_map_by_vlocity_type = {}
   if(not vlocity_object_map_file):
      raise SystemExit('Vlocity object map file: ' + vlocity_object_map_file + 'not found!')
   else:
      with open(vlocity_object_map_path, 'r') as object_map_by_vlocity_type_file:
         csv_reader = csv.DictReader(object_map_by_vlocity_type_file)
         for vlocity_object_map_row in csv_reader:
            object_map_by_vlocity_type[vlocity_object_map_row['VlocityType']] = vlocity_object_map_row['sObject']
   return object_map_by_vlocity_type

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

def get_vlocity_yaml_file(vlocity_template_path, other_conditions, object_map_by_vlocity_type, row, output_folder):
   vlocity_yaml = ''
   template_file = Path(vlocity_template_path)
   if(not template_file.is_file()):
      raise SystemExit('Vlocity template file: ' + vlocity_template_path + ' not found!')
   else:
      print_info('Using vlocity yaml template: ' + color_string(vlocity_template_path, Color.BLUE))
      # replace all keywords
      with open(vlocity_template_path, 'r') as vlocity_template:
         query = QUERY_TEMPLATE_STRING.replace('%sobject%', object_map_by_vlocity_type[row['Vlocity_Type__c']]).replace('%name%', row['Name']).replace('%otherConditions%', other_conditions)
         #vlocity_yaml = vlocity_template.read().replace('%vlocityType%', row['Vlocity_Type__c']).replace('%Name%', row['Name']).replace('%otherConditions%', other_conditions).replace('%sobject%', object_map_by_vlocity_type[row['Vlocity_Type__c']]).replace('%feature%', DEPLOYMENT_PATH + '/' + DEPLOYMENT_FOLDER + '/' + row['Backlog_Item__r.Name'])
         
         vlocity_yaml = vlocity_template.read().replace('%vlocityType%', row['Vlocity_Type__c']).replace('%feature%', output_folder).replace('%query%', query)
         print_info('Query: ' + color_string(query.replace('%vlocity_namespace%', VLOCITY_NAMESPACE), Color.GREEN))

   return vlocity_yaml

def get_other_conditions(row):
   other_conditions = ''
   if(row['OmniScript_Type__c']):
      other_conditions = " and %vlocity_namespace%__Type__c = '" + row['OmniScript_Type__c'] + "'"
   if(row['OmniScript_SubType__c']):
      other_conditions = " and %vlocity_namespace%__SubType__c = '" + row['OmniScript_SubType__c'] + "'"
   if(row['Version__c']):
      other_conditions = " and %vlocity_namespace%__Version__c = " + row['Version__c']
   return other_conditions

def write_temporary_yaml_file(vlocity_yaml_file_path, vlocity_yaml_file_string):
   print_info('Creating temporary yaml file: ' + color_string(vlocity_yaml_file_path, Color.BLUE))
   folder = os.path.dirname(vlocity_yaml_file_path)
   if not os.path.exists(folder):
      os.makedirs(folder)

   with open(vlocity_yaml_file_path, "w") as vlocity_yaml_file:
      vlocity_yaml_file.write("%s" % vlocity_yaml_file_string)

def retrieve_vlocity_metadata(vlocity_yaml_file_path, remotes, environment, row, retrieved_components, output_folder):
   remote = get_remote(environment, remotes)
   print_info('Destination folder ' + color_string(output_folder, Color.BLUE))
   retrieve_cmd = 'vlocity packExport -job="' + vlocity_yaml_file_path + '" -sf.username="'  + remote['username'] + '" -sf.password="' + remote['password'] + '" -sf.loginUrl="' + remote['serverUrl'] + '"'
   print_info('Running command: ' + color_string(retrieve_cmd, Color.BLUE))

   #result = os.system(retrieve_cmd)
   result = commands.getoutput(retrieve_cmd)

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
         result_dict[result_array[0].strip()] = result_array[1].strip()
      else:
         result_dict[result_array[0].strip()] = ''
   
   # default values
   retrieval_status = 'Success'
   retrieval_details = ''
   retrieval_error_message = ''

   query = ''
   if('Query' in result_dict):
      query = result_dict['Query']

   retrieval_details = query

   # check errors
   if('Errors' in result_dict and result_dict['Errors'] != '0'):
      retrieval_status = 'Failed'
      retrieval_error_message = 'Errors for item: ' + row['Backlog_Item__r.Name']
      if(IGNORE_ERRORS):
         print_info(color_string(retrieval_error_message, Color.RED))
      else:
         raise SystemExit(color_string(retrieval_error_message, Color.RED))
   elif(('Records' in result_dict and result_dict['Records'] == '0') or ('Query Total' in result_dict and result_dict['Query Total'] == '0')):
      retrieval_status = 'Failed'
      retrieval_error_message = 'Component ' + row['Name']  + ' for item ' + row['Backlog_Item__r.Name'] + ' doesn\'t exist!'
      if(IGNORE_ERRORS):
         print_info(color_string(retrieval_error_message + '\nQuery: ' + query, Color.RED))
      else:
         raise SystemExit(color_string(retrieval_error_message + '\nQuery: ' + query, Color.RED))
  
   # if successfully retrieved add component to retrieved_components dictionary
   if(row['Backlog_Item__r.Name'] in retrieved_components):
      if('Components' in retrieved_components[row['Backlog_Item__r.Name']] and row['Vlocity_Type__c'] in retrieved_components[row['Backlog_Item__r.Name']]['Components']):
         retrieved_components[row['Backlog_Item__r.Name']]['Components'][row['Vlocity_Type__c']].append({'Name': row['Name'], 'Type': row['OmniScript_Type__c'], 'SubType': row['OmniScript_SubType__c'], 'Version': row['Version__c'], 'Item': row['Backlog_Item__r.Name']})
      else:
         retrieved_components[row['Backlog_Item__r.Name']]['Components'][row['Vlocity_Type__c']] = [{'Name': row['Name'], 'Type': row['OmniScript_Type__c'], 'SubType': row['OmniScript_SubType__c'], 'Version': row['Version__c'],'Item': row['Backlog_Item__r.Name']}]
   else:
      retrieved_components[row['Backlog_Item__r.Name']] = {'Components': {row['Vlocity_Type__c']: [{'Name': row['Name'], 'Type': row['OmniScript_Type__c'], 'SubType': row['OmniScript_SubType__c'], 'Version': row['Version__c'],'Item': row['Backlog_Item__r.Name']}]}}

   # update retrieval status, retrieval error message if any
   if('Retrieval_Status' not in retrieved_components[row['Backlog_Item__r.Name']] or (retrieved_components[row['Backlog_Item__r.Name']]['Retrieval_Status'] != 'Failed' and retrieval_status == 'Failed')):
      retrieved_components[row['Backlog_Item__r.Name']]['Retrieval_Status'] = retrieval_status
      retrieved_components[row['Backlog_Item__r.Name']]['Retrieval_Error_Message'] = retrieval_error_message
   else:
      retrieved_components[row['Backlog_Item__r.Name']]['Retrieval_Status'] = 'Success'
      retrieved_components[row['Backlog_Item__r.Name']]['Retrieval_Error_Message'] = ''

   # update retrieval details
   retrieved_components[row['Backlog_Item__r.Name']]['Retrieval_Details'] = retrieval_details

   # update output folder
   if('Output_Folder' not in retrieved_components[row['Backlog_Item__r.Name']]):
      retrieved_components[row['Backlog_Item__r.Name']]['Output_Folder'] = output_folder

   # update job file path
   if('Job_File_Path' not in retrieved_components[row['Backlog_Item__r.Name']]):
      retrieved_components[row['Backlog_Item__r.Name']]['Job_File_Path'] = vlocity_yaml_file_path

   if(retrieval_status == 'Success'):
      print_info('Successfully retrieved')
   else:
      print_info('Failed')
  
   #subprocess.check_output(retrieve_cmd, shell=True)

def check_omniscript_conflicts(retrieved_components, processed_omniscripts):
   conflict = False
   for item in retrieved_components:
      for vlocity_type in retrieved_components[item]:
         if(vlocity_type == 'OmniScript'):
            for component in retrieved_components[item][vlocity_type]:
               if(component['Type'] in processed_omniscripts):
                  if(component['SubType'] in processed_omniscripts[component['Type']]):
                     # conflict
                     conflict = True
                     processed_omniscripts[component['Type']][component['SubType']].append(component)
                  else:
                     processed_omniscripts[component['Type']][component['SubType']] = [component]
               else:
                  processed_omniscripts[component['Type']] = {component['SubType']: [component]}
   return conflict

def print_conflicted_omniscripts(processed_omniscripts):
   message = ''
   print_info(color_string('Conflicted OmniScripts: ', Color.RED))
   for omnitype in processed_omniscripts:
      for subtype in processed_omniscripts[omnitype]:
         if(len(processed_omniscripts[omnitype][subtype]) > 0):
            for item in processed_omniscripts[omnitype][subtype]:
               if(len(message) > 0):
                  message = message + '\n'
               message = message + color_string(item['Item'] + ', ' + item['Type'] + ', ' + item['SubType'] + ', ' + item['Version'], Color.RED)
   raise SystemExit(message)

def is_tool(name):
    return find_executable(name) is not None

def write_csv_output(retrieved_components):
   # write csv output if debug mode is not turned on
   if(not this.DEBUG):
      #fieldnames_output = list(csv_reader.fieldnames)
      #fieldnames_output.append("Retrieval_Status")
      fieldnames_output = {'Backlog_Item__r.Name', 'Retrieval_Status', 'Retrieval_Error_Message', 'Retrieval_Details', 'Job_File_Path', 'Output_Folder'}
      csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames_output, quoting=csv.QUOTE_ALL)
      csv_writer.writeheader()   

   #print(retrieved_components)
   if(this.DEBUG):
      print_info('\nSummary:')
   for item in retrieved_components:
      # write csv output if debug mode is not turned on
      if(not this.DEBUG):
         row_out = {'Backlog_Item__r.Name': item, 'Retrieval_Status': retrieved_components[item]['Retrieval_Status'], 'Retrieval_Error_Message': retrieved_components[item]['Retrieval_Error_Message'], 'Retrieval_Details': retrieved_components[item]['Retrieval_Details'], 'Job_File_Path': retrieved_components[item]['Job_File_Path']}
         csv_writer.writerow(row_out)
      if(retrieved_components[item]['Retrieval_Status'] != 'Success'):
         print_info('For item ' + color_string(item, Color.BLUE) + ' retrieval failed! Error message is: ' + color_string(retrieved_components[item]['Retrieval_Error_Message'], Color.RED))
         print_info('  Details: ' + color_string(retrieved_components[item]['Retrieval_Details'], Color.GREEN))
      elif(retrieved_components[item]['Retrieval_Status'] == 'Success' and  'Components' in retrieved_components[item]):   
         print_info('For item ' + color_string(item, Color.BLUE) + ' retrieved components are:')
         for vloc_type in retrieved_components[item]['Components']:
            print_info('\t' + vloc_type + ':')
            for vloc_component in retrieved_components[item]['Components'][vloc_type]:
               print_info('\t\t' + vloc_component['Name'])
      else:
         print_info('For item ' + color_string(item, Color.BLUE) + ' no components retrieved')
  
def main():
   parser = argparse.ArgumentParser(description='Deploys vlocity components from a source SF environment.\n' +
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
        "-o", "--output-folder", dest="output",
        help="Output folder")

   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   args = parser.parse_args()
   this.DEBUG = args.debug
   this.IGNORE_ERRORS = args.ignore_errors
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2

   # remotes
   orgs_json_file_path = Path(ORGS_JSON_PATH + '/' + ORGS_JSON_FILENAME)
   remotes = get_remote_org_configuration(orgs_json_file_path)

   # vlocity object map
   vlocity_object_map_path = SCRIPT_FOLDER_PATH + '/../' + CONFIG + '/' + VLOCITY_OBJECT_MAP_FILENAME
   object_map_by_vlocity_type = load_vlocity_object_map(vlocity_object_map_path)

   # check whether is force-dev-tool installed
   if(platform.system() != 'Windows' and not is_tool("force-dev-tool")):
      raise SystemExit('Please install force-dev-tool first!\nFor more information look at\n"https://github.com/amtrack/force-dev-tool"')

   # check whether is force-dev-tool installed
   if(platform.system() != 'Windows' and not is_tool("vlocity")):
      raise SystemExit('Please install vlocity_build first!\nFor more information look at\n"https://github.com/vlocityinc/vlocity_build"')

   # loop through input (stdin)
   counter = 0
   #csv_reader = csv.DictReader(fileinput.input(mode='rb'), delimiter=',')
   csv_reader = csv.DictReader(iter(sys.stdin.readline, ''))

   retrieved_components = {}
   for row in csv_reader:
      counter = counter + 1
      
      # print new line
      if(counter > 1):
         print_info('')
      output_folder = ''
      # set-up ouput folder
      if(not args.output):
         if(DEPLOYMENT_PATH):
            output_folder = output_folder + DEPLOYMENT_PATH + '/'
         if(DEPLOYMENT_FOLDER):
            output_folder = output_folder + DEPLOYMENT_FOLDER + '/'
         output_folder = output_folder + row['Backlog_Item__r.Name']
      else:
         output_folder = args.output
      print_info(color_string('Component #' + str(counter) + ' (' + row['Backlog_Item__r.Name'] + ')', Color.GREEN))
      #print(row)
      print_info('Exporting ' + color_string(row['Vlocity_Type__c'], Color.GREEN) + ': ' + color_string(row['Name'], Color.YELLOW) + ' from ' + color_string(row['Environment__c'], Color.MAGENTA))
      # get other conditions
      other_conditions = get_other_conditions(row)

      # get_vlocity_yaml_file
      vlocity_template_path = SCRIPT_FOLDER_PATH + '/../' + CONFIG + '/' + TEMPLATES_FOLDER + '/' + VLOCITY_YAML_TEMPLATE
      vlocity_yaml_file_string = get_vlocity_yaml_file(vlocity_template_path, other_conditions, object_map_by_vlocity_type, row, output_folder)
      
      # write temporary yaml file
      vlocity_yaml_file_path = TEMP + '/' + row['Backlog_Item__r.Name'] + '.yaml'
      write_temporary_yaml_file(vlocity_yaml_file_path, vlocity_yaml_file_string)

      # retrieve vlocity metadata for the current row
      retrieve_vlocity_metadata(vlocity_yaml_file_path, remotes, row['Environment__c'], row, retrieved_components, output_folder)
      
   processed_omniscripts = {}
   if(check_omniscript_conflicts(retrieved_components, processed_omniscripts)):
      print_conflicted_omniscripts(processed_omniscripts)

   write_csv_output(retrieved_components)
 
if __name__ == "__main__":
   main()
