#!/usr/bin/env python

# author        : Stepan Ruzicka
# date          : 2018.05.24

import sys
import os
import argparse
from argparse import RawTextHelpFormatter
import json
import subprocess
from git import *

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
SCRIPT_NAME = os.path.basename(__file__)

# default config values
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1
DEFAULT_REPOSITORY = 'bluewolfcorm'
DEFAULT_BRANCH = 'dev'

# configuration folders and files
CONFIG = '../etc'
DEFAULT_OUPTUT_PATH = '../temp'

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

def get_commits(repo, branch):
    commits = []
    for commit in repo.iter_commits(rev=branch):
        commits.append(commit)
    return commits

def main():
   parser = argparse.ArgumentParser(description='Deploys branch to sf environment.\n' +
                                                'Example:\n' +
                                                '\t' + SCRIPT_NAME + ' -d',
						formatter_class=RawTextHelpFormatter)
   parser.add_argument(
        "-d", "--debug", dest="debug",
        help="Debug mode", action="store_true")

   '''
   parser.add_argument(
        "--ignore-errors", dest="ignore_errors",
        help="Will keep on processing despite errors", action="store_true")
   '''

   parser.add_argument(
        "--pull", dest="pull",
        help="Will pull the latest code from repository before it creates the package.", action="store_true")

   parser.add_argument(
        "-b", "--branch", dest="branch",
        help="Source folder")

   parser.add_argument(
        "-r", "--repository", dest="repository",
        help="Repository")

   parser.add_argument(
        "-o", "--output", dest="output",
        help="Output folder")

   '''
   parser.add_argument(
        "-t", "--target", dest="target",
        help="Target environment", required=True)
   '''

   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   args = parser.parse_args()

   # arguments assignment to global variables
   this.DEBUG = args.debug
   #this.IGNORE_ERRORS = args.ignore_errors
   if(args.debug_level == 2):
      this.DEBUG_LEVEL = 2

   repository_name = ''
   if args.repository:
      repository_name = args.repository
   else:
      repository_name = DEFAULT_REPOSITORY

   try:
      repo = Repo(repository_name)
   except:
      print_error('Please, make sure ' + CURRENT_WORKING_PATH + '/' + repository_name + ' exists!')
      sys.exit(1)

   o = repo.remotes.origin
   if(args.pull):
      print_info(color_string('Pulling the latest code from repository ', Color.BLUE) + color_string(repository_name, Color.MAGENTA))
      o.pull()

   #dev_branch = repo.branches.dev.commits()
   #repo.git.checkout(args.branch)
   #print dev_branch.log()
   branch_name = ''
   if args.branch:
      branch_name = args.branch
   else:
      branch_name = DEFAULT_BRANCH

   print_info(color_string('Retrieving a list of commits for repository ' + repository_name + ' and branch ' + branch_name, Color.GREEN)) 
   try: 
      commits = get_commits(repo, branch_name)
   except:
      print_error('Please, make sure branch ' + branch_name  + ' exists!')
      sys.exit(1)
   
   last_commit_id = commits[0]
   first_commit_id = commits[len(commits)-1]

   print_info('First commit id: ' + color_string(str(first_commit_id), Color.MAGENTA))
   print_info('Last commit id: ' + color_string(str(last_commit_id), Color.MAGENTA))

   #print repo.git.diff(first_commit_id, last_commit_id)
   if(args.output):
      output_path = args.output
   else:
      output_path = DEFAULT_OUPTUT_PATH
      
   cmd = 'git diff ' + str(first_commit_id) + ' ' + str(last_commit_id) + ' | force-dev-tool changeset create ' + branch_name + ' -f -d ' + output_path
   print_info('Running command:\n' + color_string(cmd, Color.BLUE))
   os.chdir(repository_name)
   try:
      result = subprocess.check_output(cmd, shell=True)
   except subprocess.CalledProcessError as e:
      raise RuntimeError("(Command: '{}' returned error (code {}).".format(e.cmd, e.returncode))
      result = e.output
   os.chdir('..')   

   print result

if __name__ == "__main__":
   main()
