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
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import OrderedDict
import shutil

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

def print_info(info):
   if(DEBUG):
      print(info)

def print_error(message):
   print color_string(message, Color.RED)

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
         # create package xml

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

def translate_output(rows):
   for item in rows:
      item['alm_pm2__Source_Instance__r.alm_pm2__Instance_Name__c'] = item.pop('Instance')
      item['alm_pm2__Backlog__r.Name'] = item.pop('Item')
      item['alm_pm2__Component__r.Name'] = item.pop('Component API Name')
      item['alm_pm2__Component__r.alm_pm2__Type__c'] = item.pop('Component Type')
      item['alm_pm2__Component__r.alm_pm2__Parent_Component__r.Name'] = item.pop('Parent Component API Name')
      item['alm_pm2__Component__r.alm_pm2__Parent_Component__r.alm_pm2__Type__c'] = item.pop('Parent Component Type')
      
      # remove the rest
      item.pop('Item Type')
      item.pop('E-mail')
      item.pop('Branch Name')

   return rows

def write_csv_output(rows, output = sys.stdout):
   rows = translate_output(rows)
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

def filter_blank_lines(text_block):
    ret_value = ""
    for line in text_block.split("\n"):
        if line.strip() != '':
            ret_value += line.strip() + '\n'
    return ret_value

def get_spreadsheet_records(client, workbook_name, sheet_name):
   # Find a workbook by name and open the first sheet
   try:
      # sheet = client.open(workbook_name).sheet1
      workbook = client.open(workbook_name)
   except Exception as e:
      error_message = "Unable to load workbook " + workbook_name
      if(not IGNORE_ERRORS):
         raise RuntimeError(error_message)
      else:
         print_error(error_message)

   try:
      sheet = workbook.worksheet(sheet_name)
   except Exception as e:
      error_message = "Unable to load sheet " + sheet_name
      if(not IGNORE_ERRORS):
         raise RuntimeError(error_message)
      else:
         print_error(error_message)

   # Extract and print all of the values
   rows = sheet.get_all_records()
   return rows

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
        "-c", "--credentials", dest="credentials_json", required=True,
        help="Sheet name")

   parser.add_argument(
        "-w", "--workbook", dest="workbook", required=True,
        help="Workbook name")

   parser.add_argument(
        "-s", "--sheet", dest="sheet", required=True,
        help="Sheet name")

   parser.add_argument(
        "--source", dest="source",
        help="Source environment")

   parser.add_argument(
        "-o", "--output", dest="output",
        help="Output folder")

   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   parser.add_argument(
        "-t", "--target", dest="target",
        help="Target environment")

   parser.add_argument(
        "items", nargs="*",
        help="User story list")

   args = parser.parse_args()

   items = args.items

   # arguments assignment to global variables
   this.DEBUG = args.debug
   this.IGNORE_ERRORS = args.ignore_errors
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2

   #if(len(args.items) == 0):
      #raise ValueError("Backlog item list is empty, please specify at least one backlog item which you want to update!")

   if not is_tool('force-dev-tool'):
      print 'force-dev-tool not installed!'
      sys.exit(1);

   remotes = load_remotes(CURRENT_WORKING_PATH + '/' + ORGS_JSON_FILE_PATH)

   # use creds to create a client to interact with the Google Drive API
   scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
   try:
      creds = ServiceAccountCredentials.from_json_keyfile_name(args.credentials_json, scope)
      client = gspread.authorize(creds)
   except Exception as e:
      error_message = "Unable to open file with credentials " + args.credentials_json
      if(not IGNORE_ERRORS):
         raise RuntimeError(error_message)
      else:
         print_error(error_message)

   rows = get_spreadsheet_records(client, args.workbook, args.sheet)
   columns = []
   columns.append('Branch Name')
   columns.append('Instance')
   records_per_items_and_instances = group_by_columns(rows, columns)
   for item in records_per_items_and_instances:
      item_name = item.replace("feature/", "").replace("defect/", "")
      
      # if items to be retrieved not particularly defined (take all) or defined then proceed for those which are defined
      if not items or item_name in items:
         for instance in records_per_items_and_instances[item]:
            # create package xml
            csv_output = get_csv_output(records_per_items_and_instances[item][instance])

            # create package xml
            if args.output:
               #package_xml_path = args.output + '_' + instance + '/src'
               package_xml_path = args.output + '/' + '/src'
            else:
               #package_xml_path = PACKAGES + '/' + item + '_' + instance + '/src'
               package_xml_path = PACKAGES +  '/' + item + '/src'

            if os.path.isdir(package_xml_path):
               shutil.rmtree(package_xml_path)

            p = Popen([SCRIPT_FOLDER_PATH + '/create_package_xml.sh', '-o', package_xml_path + '/package.xml'], stdout=PIPE, stdin=PIPE, stderr=STDOUT) 
            create_package_stdout = p.communicate(input = csv_output)[0]  

            # retrieve the package
            if args.source:
               p = Popen(['force-dev-tool', 'retrieve',  '-d', package_xml_path, args.source], stderr=PIPE)
            else:
               p = Popen(['force-dev-tool', 'retrieve',  '-d', package_xml_path, instance], stderr=PIPE)
 
            error = p.communicate()[1]
            if error:
               print_error(item + ' ' + error.strip())
               break

            print "Running cleanup of directory " + package_xml_path
            p = Popen([SCRIPT_FOLDER_PATH + '/clean_sf_metadata.py', '-s', package_xml_path])
            p.communicate()

            if args.target:
               p = Popen(['force-dev-tool', 'deploy', '-c',  '-d', package_xml_path, args.target])
               p.communicate()

            '''
            if args.test:
               p = Popen(['get_code_coverage.py', '-t',  instance, '-p', package_xml_path + '/package.xml', '-d'], stderr=PIPE, stdout=PIPE)
               output,error_output = p.communicate()
               if output:
                  print output.strip()
               if error_output:
                  if args.send_message:
                     print error_output.strip()
                     p = Popen(['send_bulk_message.py', '-m', "Test results:\n" + error_output])
                     p = Popen(['force-dev-tool', 'deploy', '-c',  '-d', package_xml_path, args.target])
            '''

if __name__ == "__main__":
   main()
