#!/bin/bash

config=config
deploymentsVlocity=deploymentsVlocity

if [ $# -ne 1 ]; 
    then echo "Example:"
	 echo "  git diff dev01 Item-01031 --name-status | ./create_vlocity_package.sh Item-01031"
    exit 0
else
    feature=$1

    if [ ! -d "$config" ]; then
         mkdir "$config"
    fi
    
    if [ ! -d "$config/$deploymentsVlocity" ]; then
         mkdir "$config/$deploymentsVlocity"
    fi

    if [ ! -d "$config/$deploymentsVlocity/$feature" ]; then
         echo "Creating package $config/$deploymentsVlocity/$feature"
         mkdir "$config/$deploymentsVlocity/$feature"
    fi
fi

#copiedComponents=""
while read input; do 
    item=`echo $input | egrep "^(A|M)(\s)vlocity/.+" | cut -d" " -f2`
    if [ ! -z $item ]; then
        # get array of the subfolders
        IFS='/' read -ra subdirs <<< "$item"

        # remove the file itself from the array
        unset 'subdirs[${#subdirs[@]}-1]'

        # init
        partialPath="$config/$deploymentsVlocity/$feature"
        originalPath=""
        for i in "${subdirs[@]}"; do
            partialPath="$partialPath/$i"
            if [ -z $originalPath ]; then
               originalPath="$i"
            else
               originalPath="$originalPath/$i"
            fi

            if [ ! -d "$partialPath" ]; then
               mkdir "$partialPath"
            fi
        done
       
        #if [[ *":$partialPath:"* != "$copiedComponents" ]]; then
        
        if [ ! -z "$partialPath" ]; then
           copiedComponents=$copiedComponents":$partialPath:"
           #echo "$copiedComponents"
           echo "Copying item $partialPath"
           for i in "$originalPath"/*; do
              #echo "Copying item $i"
              cp "$i" "$partialPath"
           done
        fi
        #fi
    fi
done
