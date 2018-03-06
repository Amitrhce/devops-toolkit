#!/bin/bash

# author	: Stepan Ruzicka
# date  	: 2018.01.05

# default setting
VERBOSE=0
sourceEnv=prod
inputFile="/dev/stdin"

#======================================== Help ==============================================#
print_help(){
    echo "Synopsis"
    echo "	$(basename $0) [-h] [-d] [-i file] [-o file] [string ...]"
    echo "Description"
    echo ""
    echo "	The options are as follows:"
    echo "	-h	help"
    echo "	-d	debug mode"
    echo "	-i	input file"
    echo "	-m	message"
    echo 
    echo "Example"
    echo "	$(basename $0) "Deployment finished, if this has been smoke tested can you please modify the status to \'QA Ready\'" Item-01234 Item-43210"
    echo "	$(basename $0) -h"
    echo "	echo "Item-01234" | $(basename $0) -d"
    echo "	cat item_list.txt | $(basename $0)"
}

function log () {
    if [[ $VERBOSE -eq 1 ]]; then
        if [[ ! -z "$@" ]]; then
           echo "$@"
        fi
    fi
}

function print_error(){
    if [[ ! -z "$@" ]]; then
       echo -e "\033[31m$@\033[0m"
    fi
}

print_install_force_dev_tool(){
    print_error "Install force-dev-tool first"
    echo "For more information look at"
    echo "https://github.com/amtrack/force-dev-tool"
}

check_force_dev_tool_installed(){
    path=`command -v force-dev-tool`
    if [ -z "$path" ]; then
       print_install_force_dev_tool;
       exit 1;
    else
       log "force-dev-tool found - $path"
    fi
}

print_create_environment_command(){
    print_error "Environment $@ configuration missing! Please use the command below to add it or manually edit .orgs.json"
    echo "force-dev-tool remote add $@ <username> <password> [-u <url>]"
}

check_environment_exists(){
    temp_env=`force-dev-tool remote -v | cut -d: -f1 | grep "$@"`
    if [ -z "$temp_env" ]; then
       print_create_environment_command $@;
       exit 1;
    else
       if [ ! -z "$@" ]; then
          log "Environment $@ found"
       fi
    fi
}

prepare_component_list(){
   tempArray=($@)
   # for each item
   for((i=0; i<${#tempArray[@]}; ++i)); do
      if [ $i -eq 0 ]; then
         tempComponentList="'${tempArray[i]}'"
      else
         tempComponentList="$tempComponentList,'${tempArray[i]}'"
      fi
   done
   echo "$tempComponentList"
}

#===================================== Parse Parameters =====================================#

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

while getopts "hi:dm:" opt; do
    case "$opt" in
    h|\?)
        print_help
        exit 0
        ;;
    d)  VERBOSE=1
        ;;
    i)  inputFile=$OPTARG
        ;;
    m)	message=$OPTARG
	;;
    esac
done
#============================================ MAIN =============================================#

# process the remaining parameters - items - if there are no items then try to read from stdin
shift $(expr $OPTIND - 1)

if [ ! $# -eq 0 ]; then
   for item in "$@"
   do
       items+=($item)
   done
else
   if [ -z "$inputFile" ]; then
      print_error "$inputFile doesn't exist!"
   fi
   while read item; do
      items+=($item)
   done < $inputFile
fi

# check whether force-dev-tool is installed
check_force_dev_tool_installed;

# check whether .orgs.json and environment exists - if not return an error with instructions what to do
check_environment_exists "$sourceEnv";


# if the array is not empty then perform the query
if [ ! -z "$items" ]; then
   log "Adding items ${items[@]} to the query"
   componentList=`prepare_component_list "${items[@]}"`;
   query="DevOpsUtils.sendBulkChatterComment('$message', new Set<String>{$componentList});"

   log "Running query:"
   log "$query"
   echo "$query" | force-dev-tool execute "$sourceEnv"
fi
