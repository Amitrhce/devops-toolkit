#!/usr/bin/env python

# author        : Stepan Ruzicka
# date          : 2018.03.02

import json
import subprocess
import io
import argparse
from pathlib import Path
from argparse import RawTextHelpFormatter
import re
import sys
from distutils.spawn import find_executable
import os
import xml.etree.ElementTree as ElementTree
from io import BytesIO

SCRIPT_FOLDER_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = '../etc'
MERGE_CONFIGURATION = 'merge_config.json'
DEFAULT_NAMESPACE = "http://soap.sforce.com/2006/04/metadata"

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

#def load_xml():

#def print_xml():
def get_root_namespace(element_tree):
   root = element_tree.getroot()
   match = re.search('\{(.*)\}', root.tag)
   return match.group(1) if match else ''

def get_element_local_name(element):
   match = re.search('\{.*\}(.*)', element.tag)
   return match.group(1) if match else ''

def write_xml(element_tree, file_path, namespaces):
   element_tree.write(file_path, xml_declaration=True, encoding="utf-8", method="xml", default_namespace=namespaces['default'])

def build_element_unique_key(element, config, namespace, unmatched_element_count = None):
   # default value
   element_local_name = get_element_local_name(element)
   key = None
   if element_local_name in config:
      element_config = config[element_local_name]
      if('uniqueKeys' in element_config):
         for uniqueKey in element_config['uniqueKeys']:
            key_element = element.find('{' + namespace  + '}' + uniqueKey)
            if(key_element is not None and key_element.text):
               if key is None:
                  key = ''
               key = key + '#' + element_local_name + '#' + key_element.text
      elif('exclusiveUniqueKeys' in  element_config):
         for exclusiveUniqueKeyList in element_config['exclusiveUniqueKeys']:
            for exlusiveUniqueKey in exclusiveUniqueKeyList:
               key_element = element.find('{' + namespace  + '}' +exlusiveUniqueKey)
               if(key_element is not None and key_element.text):
                  if key is None:
                     key = ''
                  key = key + '#' + element_local_name + '#' + key_element.text
            # we already have a unique key we can return
            if(key != None):
               break;
      else:
         # key == element name itself - e.g. userLicense, custom
         key = element_local_name
   
   if(key is None and unmatched_element_count is not None):
     unmatched_element_count = unmatched_element_count + 1
     key = element_local_name + "#" + str(unmatched_element_count)
  
   if key == None:
      print "Not configured: " + element_local_name
   return key

def load_base_xml_file(element_tree, config, namespace, unmatched_element_count):
   xml_dict = {}
   root = element_tree.getroot()
   for child in root:
      child_key = build_element_unique_key(child, config, namespace, unmatched_element_count)

      # if child_key is None then ignore the element
      if(child_key is not None):
         xml_dict[child_key] = {'element-type': get_element_local_name(child), 'element': child}

   return xml_dict

def update_base_xml(base_xml, base_xml_dict, element_tree, config, namespace, unmatched_element_count):
   xml_dict = {}
   root = element_tree.getroot()
   for child in root:
      child_key = build_element_unique_key(child, config, namespace, unmatched_element_count)
      exists_in_base = key_exists_in_dict(base_xml_dict, child_key)
      if(exists_in_base):
         # check whether key exists and if yes and not equal then update
         is_equal_to_base = elements_are_equal(child, base_xml_dict[child_key]['element'], config, namespace)
         if not is_equal_to_base:
            print('Updating element with key: ' + child_key)
      else:
         # default value
         # add new value if doesn't exist
         print('Appending new element ' + child_key)
         base_xml.getroot().append(child)
         is_equal_to_base = False

      xml_dict[child_key] = {'element-type': get_element_local_name(child), 'element': child, 'existsInBase': exists_in_base, 'isEqualToBase': is_equal_to_base}
   return xml_dict

def key_exists_in_dict(xml_dict, key):
   if key in xml_dict:
      return True
   else:
      return False

def elements_are_equal(element1, element2, config, namespace):
   if(element1 is None or element2 is None):
      return False

   element_local_name = get_element_local_name(element1)
   if element_local_name in config:
      config = config[element_local_name]

   if 'equalKeys' in config and config['equalKeys'] is not None:
      for key in config['equalKeys']:
         #print('--> ' + key + ', ' + element2.find('{' + namespace + '}' + key).text + ', ' + element1.find('{' + namespace + '}' + key).text)
         #print "--->" + key
         element2_key = element2.find('{' + namespace + '}' + key)
         element1_key = element1.find('{' + namespace + '}' + key)
         if(element2_key is not None and element1_key is not None and element2_key.text != element1_key.text):
            print('Updating value: ' + element2_key.text + ' with ' + element1_key.text + ' for element: ' + element_local_name)
            element2_key.text = element1_key.text
            return False
      return True
   else:
      # leaves
      element1_text_temp = element1.text
      element1.text = element2.text
      return element1_text_temp == element2.text

def get_tag(element):
   return element.tag

def sort_xml(tree):
   root = tree.getroot()
   root[:] = sorted(root, key=get_tag)       

def main():
   parser = argparse.ArgumentParser(description='Merges Salesforce XML files. Currently profiles and custom objects are supported.\n' +
                                                'Example:\n' +
                                                '\t' + os.path.basename(__file__),
						formatter_class=RawTextHelpFormatter)

   parser.add_argument(
        "base",
        help="Original XML")

   parser.add_argument(
        "update",
        help="Update XML")

   parser.add_argument(
        "-d", "--debug", dest="debug",
        help="Debug mode", action="store_true")

   parser.add_argument(
        "-o", "--output", dest="output",
        help="Output file")

   parser.add_argument(
        "-m", "--mode", dest="mode",
        help="Mode", default='profiles')

   args = parser.parse_args()

   # check if the xml files provided exist
   if not os.path.isfile(args.base):
      raise SystemExit(('Base XML ' + color_string('{}', Color.RED) + ' doesn\'t exist!').format(args.base))

   if not os.path.isfile(args.update):
      raise SystemExit(('Update XML ' + color_string('{}', Color.RED) + ' doesn\'t exist!').format(args.update))

   merge_config_path = SCRIPT_FOLDER_PATH + '/' + CONFIG_PATH + '/' + MERGE_CONFIGURATION
   with open(merge_config_path) as json_merge_config_file:
      merge_config = json.load(json_merge_config_file)

   if(args.mode in merge_config):
      merge_type_config = merge_config[args.mode]
   else:
      raise SystemExit(args.mode + ' configuration not found in ' + merge_config_path)

   # default namespace
   ElementTree.register_namespace('', DEFAULT_NAMESPACE)
  
   # base xml
   base_xml = ElementTree.parse(args.base)
   #base_namespaces = {'default': get_root_namespace(base_xml)}
      
   unmatched_base_element_count = 0
   base_xml_dict = load_base_xml_file(base_xml, merge_type_config, DEFAULT_NAMESPACE, unmatched_base_element_count)
   # print(load_base_xml_file(base_xml, profile_config, base_namespaces))
      
   # update xml
   update_xml = ElementTree.parse(args.update)
   #update_xml_namespaces = {'default': get_root_namespace(update_xml)}
   unmatched_update_element_count = 0
   update_base_xml(base_xml, base_xml_dict, update_xml, merge_type_config, DEFAULT_NAMESPACE, unmatched_update_element_count)

   if args.output:
      output_file = args.output
   else:
      output_file = args.base

   sort_xml(base_xml)
   base_xml.write(output_file, encoding="UTF-8", xml_declaration = True)
   #print(ElementTree.tostring(base_xml.getroot(), encoding='UTF-8'))     

if __name__ == "__main__":
   main()
