#!/bin/bash

# author	: Stepan Ruzicka
# date  	: 2017.08.17

# default setting
VERBOSE=0
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
    echo "	-f	filter environment"
    echo "	-i	input file"
    echo "	-t	target environment"
    echo "	-o	output folder name"
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

print_install_metadata_xml_tool(){
    print_error "Install metadata-xml-tool first"
    echo "For more information look at"
    echo "https://github.com/amtrack/metadata-xml-tool"
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

check_metadata_xml_tool_installed(){
    path=`command -v metadata-xml-tool`
    if [ -z "$path" ]; then
       print_install_metadata_xml_tool;
       exit 1;
    else
       log "metadata-xml-tool found - $path"
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

prepare_component_list(){
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

remove_xml_elements(){
   backlogItem=$1
   # for each item
   if [ -d "$backlogItem" ]; then
      for x in $backlogItem/profiles/*;do metadata-xml-tool remove-element-matching userPermissions "<name>AssignUserToSkill</name>" "$x";done
      for x in $backlogItem/profiles/*;do metadata-xml-tool remove-element-matching userPermissions "<name>ChangeDashboardColors</name>" "$x";done
      for x in $backlogItem/classes/*-meta.xml;do metadata-xml-tool replace-tag-value minorNumber ".*" "96" $x;done
      for x in $backlogItem/pages/*-meta.xml;do metadata-xml-tool replace-tag-value minorNumber ".*" "96" $x;done
      for x in $backlogItem/components/*-meta.xml;do metadata-xml-tool replace-tag-value minorNumber ".*" "96" $x;done
      for x in $backlogItem/connectedApps/*;do metadata-xml-tool remove-element consumerKey "$x";done
   fi
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

# check whether metadata-xml-tool is installed
check_metadata_xml_tool_installed;

# check whether .orgs.json and environment exists - if not return an error with instructions what to do
check_environment_exists "$sourceEnv";

if [ ! -z "$outputFolder"  ];then
  itemList=`prepare_component_list "${items[@]}"`;
  components=`get_sf_components.sh "${itemList}"`
  filter="Dev01"
  dev01_components=`filter_output_csv "$components" "$filter"`
  dev01_components_count=`echo "$dev01_components" | wc -l`
  filter="Dev02"
  dev02_components=`filter_output_csv "$components" "$filter"`
  dev02_components_count=`echo "$dev02_components" | wc -l`

  # don't count the header
  dev01_components_count=$((dev01_components_count - 1))
  dev02_components_count=$((dev02_components_count - 1))

  log "dev01 components count: $dev01_components_count"
  log "dev02 components count: $dev02_components_count"
  if [ "$dev01_components_count" -gt 1 ] && [ "$dev02_components_count" -gt 1 ];then
    #retrieve
    log "retrieving ${itemList} components from dev01"
    echo "$dev01_components" | create_package_xml.sh -o "packages/${outputFolder}_dev01/package.xml"
    force-dev-tool retrieve -d "packages/${outputFolder}_dev01" dev01
    remove_xml_elements "packages/${outputFolder}_dev01"

    log "retrieving ${itemsList} components from dev02"
    echo "$dev02_components" | create_package_xml.sh -o "packages/${outputFolder}_dev02/package.xml"
    force-dev-tool retrieve -d "packages/${outputFolder}_dev02" dev02
    remove_xml_elements "packages/${outputFolder}_dev02"

    if [ ! -z "$target" ];then
      OFS=$IFS
      IFS=',' read -r -a target_array <<< "$target"
      IFS=$OFS

      for((j=0; j<${#target_array[@]}; ++j)); do  
        log "deploying ${itemList} dev01 components to ${target_array[j]}"
        force-dev-tool deploy -d "packages/${outputFolder}_dev01" "$target_array[j]"

        log "deploying ${itemList} dev02 components to $target_array[j]"
        force-dev-tool deploy -d "packages/${outputFolder}_dev02" "$target_array[j]"
      done
    else
      log "No target environment specified, nothing will be deployed, if you want to deploy the package later on, please run"
      log "force-dev-tool deploy -d packages/${outputFolder}_dev01 [TARGET]"
      log "force-dev-tool deploy -d packages/${outputFolder}_dev02 [TARGET]"
    fi
  else
    echo "$components" | create_package_xml.sh -o "packages/${outputFolder}/package.xml"

    if [ "$dev01_components_count" -gt 1 ];then
      log "retrieveing ${itemList} components from dev01"
      force-dev-tool retrieve -d "packages/${outputFolder}" dev01
      remove_xml_elements "packages/${outputFolder}"

      OFS=$IFS
      IFS=',' read -r -a target_array <<< "$target"
      IFS=$OFS

      if [ ! -z "$target" ];then
        for((j=0; j<${#target_array[@]}; ++j)); do  
          log "deploying ${itemList} dev01 components to ${target_array[j]}"
          force-dev-tool deploy -d "packages/${outputFolder}" "${target_array[j]}"
        done
      else
        log "No target environment specified, nothing will be deployed, if you want to deploy the package later on, please run"
        log "force-dev-tool deploy -d packages/${outputFolder} [TARGET]"
      fi
    else
      log "retrieveing ${itemList} components from dev02"
      force-dev-tool retrieve -d "packages/${outputFolder}" dev02
      remove_xml_elements "packages/${outputFolder}"

      OFS=$IFS
      IFS=',' read -r -a target_array <<< "$target"
      IFS=$OFS

      if [ ! -z "$target" ];then
        for((j=0; j<${#target_array[@]}; ++j)); do
          log "deploying ${itemList} dev02 components to ${target_array[j]}"
          force-dev-tool deploy -d "packages/${outputFolder}" "${target_array[j]}"
        done
      else
        log "No target environment specified, nothing will be deployed, if you want to deploy the package later on, please run"
        log "force-dev-tool deploy -d packages/${outputFolder} [TARGET]"
      fi
    fi
  fi
else
  # for each item
  for((i=0; i<${#items[@]}; ++i)); do
    components=`get_sf_components.sh "${items[i]}"`
    filter="Dev01"
    dev01_components=`filter_output_csv "$components" "$filter"`
    dev01_components_count=`echo "$dev01_components" | wc -l`
    filter="Dev02"
    dev02_components=`filter_output_csv "$components" "$filter"`
    dev02_components_count=`echo "$dev02_components" | wc -l`

    # don't count the header
    dev01_components_count=$((dev01_components_count - 1))
    dev02_components_count=$((dev02_components_count - 1))
    
    log "dev01 components count: $dev01_components_count"
    log "dev02 components count: $dev02_components_count"
    if [ "$dev01_components_count" -gt 1 ] && [ "$dev02_components_count" -gt 1 ];then
      #retrieve
      log "retrieving ${items[i]} components from dev01"
      echo "$dev01_components" | create_package_xml.sh -o "packages/${items[i]}_dev01/package.xml"
      force-dev-tool retrieve -d "packages/${items[i]}_dev01" dev01
      remove_xml_elements "packages/${items[i]}_dev01"

      log "retrieving ${items[i]} components from dev02"
      echo "$dev02_components" | create_package_xml.sh -o "packages/${items[i]}_dev02/package.xml"
      force-dev-tool retrieve -d "packages/${items[i]}_dev02" dev02
      remove_xml_elements "packages/${items[i]}_dev02"

      OFS=$IFS
      IFS=',' read -r -a target_array <<< "$target"
      IFS=$OFS
     
      if [ ! -z "$target" ];then
        for((j=0; j<${#target_array[@]}; ++j)); do 
          log "deploying ${items[i]} dev01 components to ${target_array[j]}"
          force-dev-tool deploy -d "packages/${items[i]}_dev01" "${target_array[j]}"

          log "deploying ${items[i]} dev02 components to ${target_array[j]}"
          force-dev-tool deploy -d "packages/${items[i]}_dev02" "${target_array[j]}"
        done
      else
        log "No target environment specified, nothing will be deployed, if you want to deploy the package later on, please run"
        log "force-dev-tool deploy -d packages/${items[i]}_dev01 [TARGET]"
        log "force-dev-tool deploy -d packages/${items[i]}_dev02 [TARGET]"
      fi
    else
      echo "$components" | create_package_xml.sh -o "packages/${items[i]}/package.xml"
      
      if [ "$dev01_components_count" -gt 1 ];then
        log "retrieveing ${items[i]} components from dev01"
        force-dev-tool retrieve -d "packages/${items[i]}" dev01
        remove_xml_elements "packages/${items[i]}"

        OFS=$IFS
        IFS=',' read -r -a target_array <<< "$target"
        IFS=$OFS

        if [ ! -z "$target" ];then
          for((j=0; j<${#target_array[@]}; ++j)); do
            log "deploying ${items[i]} dev01 components to ${target_array[j]}"
            force-dev-tool deploy -d "packages/${items[i]}" "${target_array[j]}"
          done
        else
          log "No target environment specified, nothing will be deployed, if you want to deploy the package later on, please run"
          log "force-dev-tool deploy -d packages/${items[i]} [TARGET]"
        fi
      else
        log "retrieveing ${items[i]} components from dev02"
        force-dev-tool retrieve -d "packages/${items[i]}" dev02
        remove_xml_elements "packages/${items[i]}"
        OFS=$IFS
        IFS=',' read -r -a target_array <<< "$target"
        IFS=$OFS
       
        if [ ! -z "$target" ];then
          for((j=0; j<${#target_array[@]}; ++j)); do
            log "deploying ${items[i]} dev02 components to ${target_array[j]}"
            force-dev-tool deploy -d "packages/${items[i]}" "${target_array[j]}"
          done
        else
          log "No target environment specified, nothing will be deployed, if you want to deploy the package later on, please run"
          log "force-dev-tool deploy -d packages/${items[i]} [TARGET]"
        fi
      fi
    fi
  done
fi
