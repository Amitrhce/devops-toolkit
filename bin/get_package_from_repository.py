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

# default config values
DEBUG = False
IGNORE_ERRORS = False
DEBUG_LEVEL = 1
DEFAULT_REPOSITORY = 'bluewolfcorm'

# configuration folders and files
CONFIG = '../etc'

def get_commits(repo, branch):
    commits = []
    for commit in repo.iter_commits(rev=branch):
        commits.append(commit)
    return commits

def main():
   parser = argparse.ArgumentParser(description='Deploys branch to sf environment.\n' +
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
        "-b", "--branch", dest="branch",
        help="Source folder", required=True)

   parser.add_argument(
        "-r", "--repository", dest="repository",
        help="Repository")

   parser.add_argument(
        "-t", "--target", dest="target",
        help="Target environment", required=True)

   parser.add_argument(
        "--debug-level", dest="debug_level",type=int,
        help="Debug level from {1, 2}")

   args = parser.parse_args()

   # arguments assignment to global variables
   this.DEBUG = args.debug
   this.IGNORE_ERRORS = args.ignore_errors
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
      print 'Please, make sure ' + CURRENT_WORKING_PATH + '/' + repository_name + ' exists!'
      sys.exit(1)

   o = repo.remotes.origin
   o.pull()

   #dev_branch = repo.branches.dev.commits()
   #repo.git.checkout(args.branch)
   #print dev_branch.log()
   try: 
      commits = get_commits(repo, args.branch)
   except:
      print 'Please, make sure branch ' + args.branch  + ' exists!'
      sys.exit(1)
   
   last_commit_id = commits[len(commits)-1]
   first_commit_id = commits[0]

   #print repo.git.diff(first_commit_id, last_commit_id)
   cmd = 'git diff ' + str(first_commit_id) + ' ' + str(last_commit_id) + ' | force-dev-tool changeset create ' + args.branch + ' -d ../temp'
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
