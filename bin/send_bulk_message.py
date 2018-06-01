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
DEFAULT_ENV = "prod"

# configuration folders and files
CONFIG = '../etc'

def is_tool(name):
   return find_executable(name) is not None   

def load_remotes(orgs_json_file_path):
   with open(orgs_json_file_path, 'r') as orgs_json:
      orgs_json_data = json.load(orgs_json)

   if 'remotes' not in orgs_json_data:
      raise ValueError(orgs_json_file_path + " is invalid")
   else:
      return orgs_json_data['remotes']

def getApexSendBulkChatterCommentAnonymousApex(message, items):
      if len(items) == 0:
         raise RuntimeError("At least one backlog item has to be provided.")

      counter = 0
      cmd = "DevOpsUtils.sendBulkChatterComment('" + message.encode('string_escape') + "', new Set<String>{"
      for item in items:
         if counter == 0:
            cmd += "'" + item + "'"
         else:
            cmd += ",'" + item + "'"
         counter = counter + 1

      cmd += '});'
      return cmd

def runAnonymousApex(apex, environment):
   cmd = 'echo "' + apex + '" | force-dev-tool execute "' + environment + '"'
   try:
      result = subprocess.check_output(cmd, shell=True)
   except subprocess.CalledProcessError as e:
      if(not IGNORE_ERRORS):
         raise RuntimeError("Anonymous apex failed (Command: '{}' returned error (code {}). If you want to ignore errors during the processing you can run it with --ignore-errors parameter. Please, also use -d parameter for more details".format(e.cmd, e.returncode))
      result = e.output
   return result

def main():
   parser = argparse.ArgumentParser(description='Send bulk chatter comment to all assignees from the list on backlog item.\n' +
                                                'Example:\n' +
                                                '\t.py -d',
						formatter_class=RawTextHelpFormatter)
   parser.add_argument(
        "-d", "--debug", dest="debug",
        help="Debug mode", action="store_true")

   parser.add_argument(
        "-t", "--target", dest="target",
        help="Target environment", action="store_true")

   parser.add_argument(
        "--ignore-errors", dest="ignore_errors",
        help="Will keep on processing despite errors", action="store_true")

   parser.add_argument(
        "-m", "--message", dest="message",
        help="Source folder", required=True)

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

   apex = getApexSendBulkChatterCommentAnonymousApex(args.message, args.items)
   if(args.target):
      print runAnonymousApex(apex, args.target)
   else:
      print runAnonymousApex(apex, DEFAULT_ENV)

if __name__ == "__main__":
   main()
