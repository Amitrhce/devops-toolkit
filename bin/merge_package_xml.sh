#!/bin/bash

# author	: Stepan Ruzicka
# date  	: 2017.08.17

# default setting
VERBOSE=0
inputFile="/dev/stdin"
version=40

#======================================== Help ==============================================#
print_help(){
    echo "Synopsis"
    echo "	$(basename $0) [-h] [-d] [-i file] [-o file] [string ...]"
    echo "Description"
    echo ""
    echo "	The options are as follows:"
    echo "	-h	help"
    echo "	-d	debug mode"
    echo "	-o	output folder name"
    echo "	-v	output version"
    echo 
    echo "Example"
    echo "	$(basename $0) -t packages/Item-1234_dev01/package.xml Item-1234_dev02/package.xml"
    echo "	$(basename $0) -t packages/Item-1234_dev01/package.xml Item-4321_dev02/package.xml -o packages/Item-1234/package.xml"
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

merge_files(){
   tempArray=($@)
   if [[ ! -z "$@" ]]; then
     printf -v packageXmlFile "%s\n%s" "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" "<Package xmlns=\"http://soap.sforce.com/2006/04/metadata\">"
     # for each item
     for((i=0; i<${#tempArray[@]}; ++i)); do
        if [ -f "${tempArray[i]}" ]; then
          # remove first two and last two lines
          printf -v packageXmlFile "%s\n%s" "$packageXmlFile" "`cat "${tempArray[i]}" | tail -n +3 | tail -r | tail -n +3 | tail -r`"
        else
          print_error "File ${tempArray[i]} doesn't exist"
          exit 1;
        fi
     done
     printf "%s\n%s\n%s\n" "$packageXmlFile" "<version>$version</version>" "</Package>"
   fi
}

#===================================== Parse Parameters =====================================#

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

while getopts "ho:dv:" opt; do
    case "$opt" in
    h|\?)
        print_help
        exit 0
        ;;
    d)  VERBOSE=1
        ;;
    o)  outputFile=$OPTARG
        ;;
    v)	version=$OPTARG
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
fi

# if outputFile set then return the result to the outputFile otherwise print it to stdout
if [[ ! -z $outputFile ]]; then
   dir=$(dirname "${outputFile}")
   [ ! -f $dir ] && mkdir -p $dir
   log "Printing the result to outputfile $outputFile"
   merge_files "${items[@]}" > $outputFile
else
   merge_files "${items[@]}"
fi

