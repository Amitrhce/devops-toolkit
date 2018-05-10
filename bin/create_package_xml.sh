#!/bin/bash

# Script configuration
SCRIPTPATH=$(dirname "$0")
#SCRIPTPATH=`pwd -P`
#SCRIPTPATH=/Users/stepan/Workspace/bin/deployUtils
CONFIG=$SCRIPTPATH/../etc
TEMPLATES="$CONFIG/jobTemplates"
SFMETADATAMAP="salesforce_metadata_map.csv"
FETCHRESULTSTEMPLATE="FetchResultTemplate.json"

# CSV fields we are interested in
ITEM_CSV="\"alm_pm2__Backlog__r.Name\""
COMPONENT_CSV="\"alm_pm2__Component__r.Name\""
COMPONENT_TYPE_CSV="\"alm_pm2__Component__r.alm_pm2__Type__c\""
PARENT_COMPONENT_CSV="\"alm_pm2__Component__r.alm_pm2__Parent_Component__r.Name\""
PARENT_COMPONENT_TYPE="\"alm_pm2__Component__r.alm_pm2__Parent_Component__r.alm_pm2__Type__c\""

# Default components which should be automaticaally added to the output JSON
version=41.0

DEFAULT_COMPONENTS[0]="Custom Admin","Profile","",""
DEFAULT_COMPONENTS[1]="Omniscript Tester","Profile","",""
DEFAULT_COMPONENTS[2]="Customer Community User Vlocity","Profile","",""
DEFAULT_COMPONENTS[3]="Account Receivables Team","Profile","",""
DEFAULT_COMPONENTS[4]="Admin","Profile","",""
DEFAULT_COMPONENTS[5]="Advisor","Profile","",""
DEFAULT_COMPONENTS[6]="Channel Manager","Profile","",""
DEFAULT_COMPONENTS[7]="Collections Agent","Profile","",""
DEFAULT_COMPONENTS[8]="Collections Agent","Profile","",""
DEFAULT_COMPONENTS[9]="Collections Back Office Agent","Profile","",""
DEFAULT_COMPONENTS[10]="Commercial Manager","Profile","",""
DEFAULT_COMPONENTS[11]="Content Manager","Profile","",""
DEFAULT_COMPONENTS[12]="Content Team Member","Profile","",""
DEFAULT_COMPONENTS[13]="Distribution Partner","Profile","",""
DEFAULT_COMPONENTS[14]="Finance Manager","Profile","",""
DEFAULT_COMPONENTS[15]="In-Direct Administrator","Profile","",""
DEFAULT_COMPONENTS[16]="In-Direct Advisor","Profile","",""
DEFAULT_COMPONENTS[17]="In-Direct Agent","Profile","",""
DEFAULT_COMPONENTS[18]="In-Direct Retailer","Profile","",""
DEFAULT_COMPONENTS[19]="Insurance Advisor","Profile","",""
DEFAULT_COMPONENTS[20]="Legal and Regulatory Manager","Profile","",""
DEFAULT_COMPONENTS[21]="MVNO Manager","Profile","",""
DEFAULT_COMPONENTS[22]="Marketing Manager","Profile","",""
DEFAULT_COMPONENTS[23]="Network Manager","Profile","",""
DEFAULT_COMPONENTS[24]="Operations Manager","Profile","",""
DEFAULT_COMPONENTS[25]="Performance Manager","Profile","",""
DEFAULT_COMPONENTS[26]="Product Manager","Profile","",""
DEFAULT_COMPONENTS[27]="Revenue Analyst","Profile","",""
DEFAULT_COMPONENTS[28]="SEO Manager","Profile","",""
DEFAULT_COMPONENTS[29]="Supply Change Manager","Profile","",""
DEFAULT_COMPONENTS[30]="Warehouse Manager","Profile","",""
DEFAULT_COMPONENTS[31]="Workforce Manager","Profile","",""
DEFAULT_COMPONENTS[32]="Admin","Profile","",""

#======================================== Help ==============================================#
print_help(){
    echo "Synopsis"
    echo "	./$(basename $0) [-h] [-d] [-v] [-i file] [-o file] [string ...]"
    echo "Description"
    echo ""
    echo "	The options are as follows:"
    echo "	-h	help"
    echo "	-i	input file"
    echo "	-o	output file"
    echo "	-d	debug mode"
    echo "	-v	version of package.xml"
    echo 
    echo "Example"
    echo "	./get_backlog_components.sh | ./$(basename $0)"
    echo "	./$(basename $0) -i input.csv"
    echo "	./$(basename $0) -d -i input.csv -o results.csv"
    echo "	./$(basename $0) -h"
}

#===================================== Parse Parameters =====================================#

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

while getopts "hv:di:o:" opt; do
    case "$opt" in
    h|\?)
        print_help
        exit 0
        ;;
    d )  VERBOSE=1
        ;;
    i )  inputFile=$OPTARG
        ;;
    o )  outputFile=$OPTARG
        ;;
    v )  version=$OPTARG
        ;;
    esac
done

#========================================= FUNCTIONS ========================================#

function log () {
    if [[ $VERBOSE -eq 1 ]]; then
        echo "$@"
    fi
}

function print_error(){
    echo -e "\033[31m$@\033[0m"
}

# Prints output JSON
print_xml(){
  tempComponent=$1
  tempParentComponent=$2
  tempSfComponentType=$3
  
  if [ "$tempSfComponentType" != "Layout [User Profile]" ]; then
    printf "\t%s\n" "<types>"
    if [ ! -z $parentComponent ] && [ "$tempSfComponentType" != "CustomTab" ] && [ "$tempSfComponentType" != "CustomObjectTranslation" ]; then
      if [ "$tempSfComponentType" == "Layout" ];then
        printf "\t\t%s\n" "<members>$tempParentComponent-$tempComponent</members>"
      elif [ "$tempSfComponentType" == "EmailTemplate" ] || [ "$tempSfComponentType" == "Document" ];then
        printf "\t\t%s\n" "<members>$tempParentComponent/$tempComponent</members>"
      elif [ "$tempSfComponentType" == "CustomMetadata" ];then
        adjustedParentComponent=`echo $tempParentComponent | sed 's/__mdt//g'`
        printf "\t\t%s\n" "<members>$adjustedParentComponent.$tempComponent</members>"
      else
        printf "\t\t%s\n" "<members>$tempParentComponent.$tempComponent</members>"
      fi
    else
      printf "\t\t%s\n" "<members>$tempComponent</members>"
    fi

    if [ "$tempSfComponentType" == "CustomObject" ] && [ "$tempComponent" == "CaseStatus" ]; then
      printf "\t\t%s\n" "<name>StandardValueSet</name>"
    else
      printf "\t\t%s\n" "<name>$tempSfComponentType</name>"
    fi
  
    printf "\t%s" "</types>";
  fi
}

findPositions(){
   tempHeader=($@)
   for ((i=0; i<${#tempHeader[@]}; ++i)); do
      if [ "${tempHeader[$i]}" == "$ITEM_CSV" ]; then
         itemPosition=$i;
      elif [ "${tempHeader[$i]}" == "$COMPONENT_CSV" ]; then
          componentPosition=$i;
      elif [ "${tempHeader[$i]}" == "$COMPONENT_TYPE_CSV" ]; then
          componentTypePosition=$i;
      elif [ "${tempHeader[$i]}" == "$PARENT_COMPONENT_CSV" ]; then
          parentComponentPosition=$i;
      elif [ "${tempHeader[$i]}" == "$PARENT_COMPONENT_TYPE_CSV" ]; then
          parentComponentTypePosition=$i;
      fi
   done
}

assignParams(){
   tempBodyLine=($@)
   item=`sed -e 's/^"//' -e 's/"$//' <<< "${tempBodyLine[$itemPosition]}"`
   component=`sed -e 's/^"//' -e 's/"$//' <<< "${tempBodyLine[$componentPosition]}"`
   componentType=`sed -e 's/^"//' -e 's/"$//' <<< "${tempBodyLine[$componentTypePosition]}"`
   parentComponent=`sed -e 's/^"//' -e 's/"$//' <<< "${tempBodyLine[$parentComponentPosition]}"`
   parentComponentType=`sed -e 's/^"//' -e 's/"$//' <<< "${tempBodyLine[$parentComponentTypePosition]}"`
   sfComponentType=`cat $CONFIG/$SFMETADATAMAP | egrep -e "^\"$componentType\"," | awk -F"," '{print $2}' | sed 's/"//g'`
   #sfComponentType=`cat $CONFIG/$SFMETADATAMAP | grep -w "\"$componentType\""  | awk -F"," '{print $2}' | sed 's/"//g'`
   sfParentComponentType=`cat $CONFIG/$SFMETADATAMAP | grep -w "\"$parentComponentType\"" | awk -F"," '{print $2}' | sed 's/"//g'`
}

# prints the input CSV
print(){
   for ((i=0; i<${#header[@]}; ++i)); do
      for ((j=0; j<${#bodyLine[@]}; ++j)); do
          echo "${header[$j]}: ${bodyLine[$j]}";
      done
      echo "";
   done
}


# automatically adds component to the output JSON
addDefaultComponents(){
   OIFS=$IFS;
   IFS=",";
   for ((i=0; i<${#DEFAULT_COMPONENTS[@]}; ++i)); do
      values=(${DEFAULT_COMPONENTS[$i]});
      component=${values[0]}
      sfComponentType=${values[1]}
      parentComponent=${values[2]}
      sfParentComponentType=${values[3]}
      #fileProperties="$fileProperties`echo;print_xml`";
      printf -v fileProperties "%s\n%s" "$fileProperties" `print_xml "$component" "$parentComponent" "$sfComponentType"`
   done
   IFS=$OIFS
}

# processes the input
processInput(){
   log "Processing file $inputFile"
   log ""
   recordCounter=0;
   while read csvLine;do
      OIFS=$IFS;
      IFS=",";
      if [ $recordCounter = "0" ]; then
         header=($csvLine);
         log "Header line is"
         log "$csvLine"
         log ""
         findPositions "${header[@]}";
      else
         bodyLine=($csvLine);
         log "Body line $recordCounter is"
         log "$csvLine"
         log ""
         assignParams ${bodyLine[@]};
         #fileProperties="$fileProperties`echo;print_xml`";
         printf -v fileProperties "%s\n%s" "$fileProperties" `print_xml "$component" "$parentComponent" "$sfComponentType"`
         # for debugging purposes 
         #print
      fi
      recordCounter=$((recordCounter + 1));
      IFS=$OIFS;
   done < $inputFile
}

#============================================ MAIN =============================================#

# print header
printf -v fileProperties "%s" "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
printf -v fileProperties "%s\n%s" "$fileProperties" "<Package xmlns=\"http://soap.sforce.com/2006/04/metadata\">"

# print body
if [[ ! -z $inputFile ]]; then
   if [ -f $inputFile ]; then
      processInput;
   else
      print_error "File $inputFile doesn't exist!"
      exit 1
   fi
else
   inputFile="/dev/stdin";
   processInput;
fi

# add default components like profiles
addDefaultComponents

# print trailor
printf -v fileProperties "%s\n\t%s" "$fileProperties" "<version>$version</version>"
printf -v fileProperties "%s\n%s" "$fileProperties" "</Package>"

# assign XML string to the result
result=$fileProperties;

# if outputFile set then return the result to the outputFile otherwise print it to stdout
if [[ ! -z $outputFile ]]; then
   dir=$(dirname "${outputFile}")
   [ ! -f $dir ] && mkdir -p $dir
   log "Printing the result to outputfile $outputFile"
   echo -e "$result" > $outputFile
else
   echo -e "$result"
fi

