#!/usr/bin/env python

# author        : Stepan Ruzicka
# date          : 2018.05.24

import sys
import os
import argparse
from argparse import RawTextHelpFormatter
import json
import subprocess
from subprocess import Popen, PIPE, STDOUT
import re
from distutils.spawn import find_executable
import csv
import io
from cStringIO import StringIO

# script context variables
SCRIPT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
CURRENT_WORKING_PATH = os.getcwd()
this = sys.modules[__name__]

# default config values
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1
DEFAULT_ENV = "prod"

# configuration folders and files
CONFIG = '../etc'
PACKAGES = 'packages'
ORGS_JSON_FILE_PATH = 'config/.orgs.json'

def is_tool(name):
   return find_executable(name) is not None   

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

def get_bulk_export_query(items):
   query = ''
   if len(items) > 0:
      query += 'select alm_pm2__Source_Instance__r.alm_pm2__Instance_Name__c, alm_pm2__Backlog__r.Name, alm_pm2__Component__r.Name, alm_pm2__Component__r.alm_pm2__Type__c, alm_pm2__Component__r.alm_pm2__Parent_Component__r.Name, alm_pm2__Component__r.alm_pm2__Parent_Component__r.alm_pm2__Type__c from alm_pm2__Backlog_Component__c where alm_pm2__Backlog__r.Name in('
      counter = 0
      for item in items:
         if counter == 0:
            query += "'" + item + "'"
         else:
            query += ",'" + item + "'"
         counter += 1
      query += ')'
   return query

def get_bulk_export_cmd(query, environment = 'prod'):
   cmd = 'force-dev-tool bulk export "' + query  + '" ' + environment
   return cmd

def group_by_column(csv_dict, column):
   result_dict = {} 
   for row in csv_dict:
     instance = row[column]
     if instance in result_dict:
        result_dict[instance].append(row)
     else:
        result_dict[instance] = [row]
   return result_dict

def group_by_columns(csv_dict, columns):
   result_dict = {} 
   for row in csv_dict:
     columns_size = len(columns)
     counter = 0
     current_parent = result_dict
     for column in columns:
        counter += 1
        # it's not a list
        if counter != columns_size:
           if row[column] not in current_parent:
              result_dict[row[column]] = {}
           current_parent = result_dict[row[column]]
        # if list then create/append row as a list member
        else:
           if row[column] in current_parent:
              current_parent[row[column]].append(row)
           else:
              current_parent[row[column]] = [row]
   return result_dict

def write_csv_output(rows, output = sys.stdout):
   fieldnames_output = {"alm_pm2__Source_Instance__r.alm_pm2__Instance_Name__c","alm_pm2__Backlog__r.Name","alm_pm2__Component__r.Name","alm_pm2__Component__r.alm_pm2__Type__c","alm_pm2__Component__r.alm_pm2__Parent_Component__r.Name","alm_pm2__Component__r.alm_pm2__Parent_Component__r.alm_pm2__Type__c"}
   #csv_writer = csv.DictWriter(sys.stdout, fieldnames = fieldnames_output, quoting = csv.QUOTE_ALL)
   csv_writer = csv.DictWriter(output, fieldnames = fieldnames_output, quoting = csv.QUOTE_ALL)
   csv_writer.writeheader()

   for row in rows:
      csv_writer.writerow(row)

def get_csv_output(rows):
   csv_temp_variable  = StringIO()
   write_csv_output(rows, csv_temp_variable)
   return csv_temp_variable.getvalue()

def main():
   parser = argparse.ArgumentParser(description='Get all SF metadata for given backlog items\n' +
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
        help="Source environment")

   parser.add_argument(
        "-o", "--output", dest="output",
        help="Output folder")

   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   parser.add_argument(
        "items", nargs="*",
        help="Backlog item list")

   args = parser.parse_args()

   # arguments assignment to global variables
   this.DEBUG = args.debug
   this.IGNORE_ERRORS = args.ignore_errors
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2

   if(len(args.items) == 0):
      raise ValueError("Backlog item list is empty, please specify at least one backlog item which you want to update!")

   if not is_tool('force-dev-tool'):
      print 'force-dev-tool not installed!'
      sys.exit(1);

   remotes = load_remotes(CURRENT_WORKING_PATH + '/' + ORGS_JSON_FILE_PATH)
   default_remote = get_remote(DEFAULT_ENV, remotes)
   query = get_bulk_export_query(args.items)
 
   cmd = get_bulk_export_cmd(query)

   try:
      result = subprocess.check_output(cmd, shell=True)
   except subprocess.CalledProcessError as e:
      if(not IGNORE_ERRORS):
         raise RuntimeError("Command execution failed (Command: '{}' returned error (code {}). If you want to ignore errors during the synchronization you can run it with --ignore-errors parameter. Please, also use -d parameter for more details".format(e.cmd, e.returncode))
      result = e.output
      sys.exit(1)

   csv_reader = csv.DictReader(io.StringIO(result.decode("unicode-escape")))
   records_per_items_and_instances = group_by_columns(csv_reader, {'alm_pm2__Backlog__r.Name', 'alm_pm2__Source_Instance__r.alm_pm2__Instance_Name__c'})

   for item in records_per_items_and_instances:
      for instance in records_per_items_and_instances[item]:
         # create package xml
         csv_output = get_csv_output(records_per_items_and_instances[item][instance])
         if args.output:
            package_xml_path = args.output + '/src'
         else:
            package_xml_path = PACKAGES + '/' + item + '_' + instance + '/src'

         p = Popen(['create_package_xml.sh', '-o', package_xml_path + '/package.xml'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)    
         create_package_stdout = p.communicate(input = csv_output)[0]
         
         # retrieve the package
         cmd = 'force-dev-tool retrieve -d ' + package_xml_path + ' ' + instance
         p = Popen(['force-dev-tool', 'retrieve',  '-d', package_xml_path, instance])
         #retrieve_stdout = p.communicate(input = csv_output)[0]
         p.communicate()

'''      
   #for row in csv_reader:
   #   print row
   #print row['alm_pm2__Source_Instance__r.alm_pm2__Instance_Name__c']
   p = Popen(['create_package_xml.sh', '-o', ''], stdout=PIPE, stdin=PIPE, stderr=STDOUT)    
   grep_stdout = p.communicate(input=result)[0]
   print(grep_stdout.decode())
'''

if __name__ == "__main__":
   main()
