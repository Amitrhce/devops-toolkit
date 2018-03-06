#!/bin/bash

# author	: Stepan Ruzicka
# date  	: 2017.08.17

# default setting
VERBOSE=0
inputFile="/dev/stdin"

#======================================== Help ==============================================#
print_help(){
    echo "Synopsis"
    echo "	$(basename $0) [-h] [-d] [string ...]"
    echo "Description"
    echo ""
    echo "	The options are as follows:"
    echo "	-h	help"
    echo "	-d	debug mode"
    echo "	-t	target environment"
    echo 
    echo "Example"
    echo "	$(basename $0) -t cita,citc Item-01234 Item-43210"
    echo "	$(basename $0) -h"
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

prepare_item_list(){
   tempArray=($@)
   # for each item
   for((i=0; i<${#tempArray[@]}; ++i)); do
      if [ $i -eq 0 ]; then
         tempComponentList="${tempArray[i]}"
      else
         tempComponentList="$tempComponentList ${tempArray[i]}"
      fi
   done
   echo "$tempComponentList"
}

#===================================== Parse Parameters =====================================#

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

while getopts "ht:i:o:df:" opt; do
    case "$opt" in
    h|\?)
        print_help
        exit 0
        ;;
    d)  VERBOSE=1
        ;;
    i)  inputFile=$OPTARG
        ;;
    o)  outputFolder=$OPTARG
        ;;
    f)  filter=$OPTARG
        ;;
    t)	target=$OPTARG
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

  # for each item
  for((i=0; i<${#items[@]}; ++i)); do
      OFS=$IFS
      IFS=',' read -r -a target_array <<< "$target"
      IFS=$OFS
     
      if [ ! -z "$target" ];then
        for((j=0; j<${#target_array[@]}; ++j)); do
          if [ -d "packages/${items[i]}" ]; then 
             log "deploying ${items[i]} components to ${target_array[j]}"
             force-dev-tool deploy -d "packages/${items[i]}" "${target_array[j]}"

          elif [ -d "packages/${items[i]}_dev01" ] && [ -d "packages/${items[i]}_dev02" ]; then
             log "deploying ${items[i]} dev01 components to ${target_array[j]}"
             force-dev-tool deploy -d "packages/${items[i]}_dev01" "${target_array[j]}"

             log "deploying ${items[i]} dev02 components to ${target_array[j]}"
             force-dev-tool deploy -d "packages/${items[i]}_dev02" "${target_array[j]}"
          else
             print_error "Package "packages/${items[i]}" not found!" 
          fi
        done
      else
        log "No target environment specified, nothing will be deployed, if you want to deploy the package later on, please run"
        log "force-dev-tool deploy -d packages/${items[i]}_dev01 [TARGET]"
        log "force-dev-tool deploy -d packages/${items[i]}_dev02 [TARGET]"
      fi
 done
