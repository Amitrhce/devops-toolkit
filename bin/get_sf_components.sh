#!/bin/bash

# author	: Stepan Ruzicka
# date  	: 2017.08.17

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
    echo "	-o	output file"
    echo "	-d	debug mode"
    echo "	-f	filter environment"
    echo "	-i	input file"
    echo 
    echo "Example"
    echo "	$(basename $0) Item-01234 Item-43210"
    echo "	$(basename $0) -f Dev02 -o backlog_components_dev02.csv Item-01234 Item-43210"
    echo "	$(basename $0) -d -f Dev01 -o backlog_components_dev01.csv Item-01234 Item-43210"
    echo "	$(basename $0) -i items.txt"
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

check_and_print_missing_components(){
   lineCount=`echo "$@" | wc -l`
   if [ "$lineCount" -gt 1 ]; then
      # for each item
      for((i=0; i<${#items[@]}; ++i)); do
         resultString=`echo $@ | grep "${items[i]}"`
         # result for the given component wasn't found
         if [ -z "$resultString" ]; then
            #printMissingComponent "${items[i]}"
            #print_error "$outputLine"
            printf -v missingBacklogItems "%s\n" "${items[i]} is missing in the result!"
         fi
      done
      printf "%s" "$missingBacklogItems"
   fi
}

filter_output_csv(){
   tempResult=$1
   tempFilter=$2
   tempHeader=$(echo "$tempResult" | head -1)
   tempBody=$(echo "$tempResult" | tail -n +2 | egrep "\"$tempFilter\"")
   if [[ ! -z $tempBody  ]]; then
      printf "%s\n%s\n" "$tempHeader" "$tempBody"
   else
      printf "%s\n" "$tempHeader"
   fi
}

#===================================== Parse Parameters =====================================#

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

while getopts "hi:o:df:" opt; do
    case "$opt" in
    h|\?)
        print_help
        exit 0
        ;;
    d)  VERBOSE=1
        ;;
    i)  inputFile=$OPTARG
        ;;
    o)  outputFile=$OPTARG
        ;;
    f)  filter=$OPTARG
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
   query="select alm_pm2__Source_Instance__r.alm_pm2__Instance_Name__c, alm_pm2__Backlog__r.Name, alm_pm2__Component__r.Name, alm_pm2__Component__r.alm_pm2__Type__c, alm_pm2__Component__r.alm_pm2__Parent_Component__r.Name, alm_pm2__Component__r.alm_pm2__Parent_Component__r.alm_pm2__Type__c from alm_pm2__Backlog_Component__c where alm_pm2__Backlog__r.Name in($componentList)"

   log "Running query:"
   log "$query"
   result=$(force-dev-tool bulk export "$query" "$sourceEnv")

   # if outputFile set then return the result to the outputFile otherwise print it to stdout
   if [[ ! -z $outputFile ]]; then
      dir=$(dirname "${outputFile}")
      [ ! -f $dir ] && mkdir -p $dir
      log "Printing the result to outputfile $outputFile"
      if [[ ! -z $filter ]]; then
         log "Output is filtered using \"$filter\" value"
         filter_output_csv "$result" "$filter" > $outputFile
      else
         echo -e "$result" > $outputFile 
      fi
   else
      # if outputFile set then return the result to the outputFile otherwise print it to stdout
      log "Result is:"
    
      if [[ ! -z $filter ]]; then
         missingComponents="`check_and_print_missing_components "$result"`" 
         log "Output is filtered using \"$filter\" value"
         filter_output_csv "$result" "$filter" 
         log `print_error "$missingComponents"`
      else
         missingComponents="`check_and_print_missing_components "$result"`"
         echo -e "$result"
         log `print_error "$missingComponents"`
      fi
   fi    
fi
