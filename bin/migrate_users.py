#!/usr/bin/env python

import subprocess
import io
import csv
import argparse
from argparse import RawTextHelpFormatter
import sys

DEBUG = False
this = sys.modules[__name__]

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

def get_profile_name_by_id_map(environment):
   print_info('Exporting profiles from ' + color_string(environment, Color.BLUE))
   profiles_csv = subprocess.check_output("force-dev-tool bulk export 'select Id, Name from Profile' " + environment, shell=True)
   csv_reader = csv.DictReader(io.StringIO(profiles_csv.decode("unicode-escape")))
   
   profile_name_by_id = {}
   for row in csv_reader:
      profile_name_by_id[row['Id']] = row['Name']
   return profile_name_by_id

def get_profile_id_by_name_map(environment):
   print_info('Exporting profiles from ' + color_string(environment, Color.BLUE))
   profiles_csv = subprocess.check_output("force-dev-tool bulk export 'select Id, Name from Profile' " + environment, shell=True)
   csv_reader = csv.DictReader(io.StringIO(profiles_csv.decode("unicode-escape")))
   
   profile_id_by_name = {}
   for row in csv_reader:
      profile_id_by_name[row['Name']] = row['Id']
   return profile_id_by_name

def get_role_name_by_id_map(environment):
   print_info('Exporting roles from ' + color_string(environment, Color.BLUE))
   profiles_csv = subprocess.check_output("force-dev-tool bulk export 'select Id, Name from UserRole' " + environment, shell=True)
   csv_reader = csv.DictReader(io.StringIO(profiles_csv.decode("unicode-escape")))
   
   profile_name_by_id = {}
   for row in csv_reader:
      profile_name_by_id[row['Id']] = row['Name']
   return profile_name_by_id

def get_role_id_by_name_map(environment):
   print_info('Exporting roles from ' + color_string(environment, Color.BLUE))
   profiles_csv = subprocess.check_output("force-dev-tool bulk export 'select Id, Name from UserRole' " + environment, shell=True)
   csv_reader = csv.DictReader(io.StringIO(profiles_csv.decode("unicode-escape")))
   
   profile_id_by_name = {}
   for row in csv_reader:
      profile_id_by_name[row['Name']] = row['Id']
   return profile_id_by_name

def get_users(environment, query_filter):
   print_info('Exporting users from ' + color_string(environment, Color.BLUE) + ' based on the following filter: ' + color_string(query_filter, Color.YELLOW))
   users_csv = subprocess.check_output('force-dev-tool bulk export "select UserRoleId, Email, Username, LastName, FirstName, Department, Latitude, TimeZoneSidKey, LocaleSidKey, EmailEncodingKey, ProfileId, LanguageLocaleKey, Alias from User where ' + query_filter + '" ' + environment, shell=True)
   csv_reader = csv.DictReader(io.StringIO(users_csv.decode("unicode-escape")))
   dict_list = []
   for row in csv_reader:
      print_info(row)
      dict_list.append(row) 
   return dict_list

def update_profile_and_role_ids(users, source_profile_name_by_id_map, target_profile_id_by_name_map, source_role_name_by_id_map, target_role_id_by_name_map):
   users_with_new_ids = []
   print_info('Updating profile and role ids for target environment.')
   for row in users:
      #print(target_profile_id_by_name_map[source_profile_name_by_id_map[row['ProfileId']]])
      if('ProfileId' not in row):
         raise SystemExit('You have to query ProfileId in order to migrate user!')
 
      if(row['ProfileId'] not in source_profile_name_by_id_map):
         raise SystemExit('Profile id: ' + row['ProfileId'] + ' not found in destination environment!')

      if(source_profile_name_by_id_map[row['ProfileId']] not in target_profile_id_by_name_map):
         raise SystemExit('Profile name: ' + source_profile_name_by_id_map[row['ProfileId']] + ' not found in destination environment!')

      if('UserRoleId' not in row):
         raise SystemExit('You have to query UserRoleId in order to migrate user!')

      if(row['UserRoleId'] not in source_role_name_by_id_map):
         raise SystemExit('UserRole id: ' + row['UserRoleId'] + ' not found in destination environment!')
         # Profile id: row['ProfileId'] not found in source environment
 
      if(source_role_name_by_id_map[row['UserRoleId']] not in target_role_id_by_name_map):
         raise SystemExit('UserRole name: ' + source_role_name_by_id_map[row['UserRoleId']] + ' not found in destination environment!')
         
      row['ProfileId'] = target_profile_id_by_name_map[source_profile_name_by_id_map[row['ProfileId']]]
      row['UserRoleId'] = target_role_id_by_name_map[source_role_name_by_id_map[row['UserRoleId']]]
      users_with_new_ids.append(row)
   return users_with_new_ids

def update_usernames(users, source_env, target_env):
   users_with_changed_usernames = []
   print_info('Modifying usernames for ' + color_string(target_env, Color.BLUE))
   for row in users:
      row['Username'] = row['Username'].replace('.' + source_env, '.' + target_env)
      users_with_changed_usernames.append(row)
   return users_with_changed_usernames

def write_csv_file(filename, users):
   with open(filename, 'w') as csvfile:
    fieldnames = users[0].keys()
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames,quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(users)

def upload_users(users, source_env, target_env):
   temp_file = 'temp/import' + '_' + source_env + '_' + 'to' + '_'+ target_env + '_' + 'users' + '.csv'
   print_info('Writing temporary file: ' + color_string(temp_file, Color.BLUE))
   write_csv_file(temp_file, users)
   print_info('Uploading ' + color_string(temp_file, Color.BLUE) + ' to ' + color_string(target_env, Color.BLUE))
   print(subprocess.check_output('force-dev-tool bulk upsert User --in ' + temp_file +  ' --extIdField="Username"' + ' ' + target_env, shell=True))

def save_users(users, source_env):
   temp_file = 'temp/export' + '_' + source_env + '_' + 'users' + '.csv'
   print_info('Writing file: ' + color_string(source_env, Color.BLUE))
   write_csv_file(temp_file, users)

def print_info(info):
   if(DEBUG):
      print(info)

def main():
   parser = argparse.ArgumentParser(description='Exports user records from a source SF environment, modifies the data appropriately and loads them to a target environment.\n' +
                                                'Example:\n' + 
                                                '\tmigrate_users.py -s dev01 -t cita -q "Lastname = \'Test\' and Username like \'%three.cita\'"',
						formatter_class=RawTextHelpFormatter)
   required_group = parser.add_argument_group('required arguments')

   required_group.add_argument(
        "-s", "--source", dest="source_env",
        help="Source environment", required=True)

   required_group.add_argument(
        "-t", "--target", dest="target_env",
        help="Target environment")

   # optional arguments
   parser.add_argument(
        "-d", "--debug", dest="debug",
        help="Debug mode", action="store_true")

   parser.add_argument(
        "-q", "--query", dest="query",
        help="Where clause of the query")

   args = parser.parse_args() 

   this.DEBUG = args.debug
   export_only = not args.target_env
   
   users = get_users(args.source_env, args.query)
   if(not export_only and len(users) > 0):
      source_profile_name_by_id_map = get_profile_name_by_id_map(args.source_env)
      target_profile_id_by_name_map = get_profile_id_by_name_map(args.target_env)
      source_role_name_by_id_map = get_role_name_by_id_map(args.source_env)
      target_role_id_by_name_map = get_role_id_by_name_map(args.target_env)

   if(not export_only and len(users) > 0 and args.target_env):
      users = update_profile_and_role_ids(users, source_profile_name_by_id_map, target_profile_id_by_name_map, source_role_name_by_id_map, target_role_id_by_name_map)
      users = update_usernames(users, args.source_env, args.target_env)
      #write_csv_file('temp/import' + '_' + 'devb' + '_' + 'users' + '.csv', users)   
      upload_users(users, args.source_env, args.target_env)
      #print(users) 
   elif(export_only):
      save_users(users, args.source_env)
   else:
      print('No users found for a given query!')
if __name__ == "__main__":
    main()
