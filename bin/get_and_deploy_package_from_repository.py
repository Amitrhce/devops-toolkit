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
from distutils.dir_util import copy_tree, remove_tree

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
        "-o", "--output", dest="output",
        help="Output folder")

   parser.add_argument(
        "-t", "--target", dest="target",
        help="Target environment")

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
   #if args.repository:
   #   repository_name = args.repository
   #else:

   repository_name = os.getcwd()

   try:
      repo = Repo(repository_name)
   except:
      print_error('Please, make sure ' + repository_name + ' is a repository!')
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
      #branch_name = DEFAULT_BRANCH
      # active branch
      branch_name = repo.active_branch.name

   print_info(color_string('Retrieving a list of commits for repository ', Color.GREEN) + color_string(repository_name, Color.BLUE) + color_string(' and branch ', Color.GREEN) + color_string(branch_name, Color.BLUE)) 
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
      output_path = DEFAULT_OUPTUT_PATH + '/' + branch_name

   # src folder added by force-dev-tool
   sf_output_path = output_path + "/src"
   vlocity_output_path = output_path + "/vlocity"

   #print_info("Changing folder to " + color_string(repository_name, Color.BLUE))
   #os.chdir(repository_name)
     
   cmd = 'git diff -w --no-renames ' + str(first_commit_id) + ' ' + str(last_commit_id) + ' | force-dev-tool changeset create src -f -d ' + output_path
   print_info('Running command:\n' + color_string(cmd, Color.BLUE))
   try:
      result = subprocess.check_output(cmd, shell=True)
   except subprocess.CalledProcessError as e:
      raise RuntimeError("(Command: '{}' returned error (code {}).".format(e.cmd, e.returncode))
      result = e.output

   print_info("Changing folder to " + color_string("..", Color.BLUE))
   #os.chdir('..')

   # remove destructive changes
   destructive_changes_path = sf_output_path + "/destructiveChanges.xml"
   if os.path.isfile(destructive_changes_path):
      print_info("Removing " + destructive_changes_path)
      os.remove(destructive_changes_path)

   # clean sf package before the installation
   cmd = 'clean_sf_metadata.py -s ' + sf_output_path  + ' -d -c ' + SCRIPT_FOLDER_PATH + "/" + CONFIG + '/full_package_installation_metadata_cleanup_config.json'
   print_info("Cleaning package")
   print_info(color_string(cmd, Color.BLUE))
   try:
      result = subprocess.check_output(cmd, shell=True)
   except subprocess.CalledProcessError as e:
      raise RuntimeError("(Command: '{}' returned error (code {}).".format(e.cmd, e.returncode))
      result = e.output

   print_info(result)

   # vlocity metadata
   vlocity_folder = repository_name + '/vlocity'
   if os.path.isdir(vlocity_folder):
      if os.path.isdir(vlocity_output_path):
         # remove folder
         print_info("Removing existing folder " + color_string(vlocity_output_path, Color.BLUE))
         remove_tree(vlocity_output_path)
      try:
         copy_tree(vlocity_folder, vlocity_output_path)
         print_info("Folder " + color_string(vlocity_folder, Color.BLUE) + " copied successfuly to " + color_string(output_path + "/vlocity", Color.BLUE))
      except Exception as e:
         error_message = "Unable to copy folder " + vlocity_folder + " to the destination folder " + "../" + output_path + ": " + e.message
         if(not IGNORE_ERRORS):
            raise RuntimeError(error_message)
         else:
            print_error(error_message)

   if args.target:
      # deploy sf metadata
      cmd = 'force-dev-tool deploy -d ' + sf_output_path  + ' ' + args.target
      print_info("Deploying sf components")
      print_info(color_string(cmd, Color.BLUE))
      try:
         result = subprocess.check_output(cmd, shell=True)
      except subprocess.CalledProcessError as e:
         raise RuntimeError("(Command: '{}' returned error (code {}).".format(e.cmd, e.returncode))
         result = e.output

      print_info(result)

      # deploy vlocity metadata
      cmd = 'echo ' + output_path  + ' | deploy_vlocity_metadata.py -d -t ' + args.target
      print_info("Deploying vlocity components")
      print_info(color_string(cmd, Color.BLUE))
      try:
         result = subprocess.check_output(cmd, shell=True)
      except subprocess.CalledProcessError as e:
         raise RuntimeError("(Command: '{}' returned error (code {}).".format(e.cmd, e.returncode))
         result = e.output

      print_info(result)

if __name__ == "__main__":
   main()
