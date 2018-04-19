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

while read input; do 
    item=`echo $input | egrep "^(A|B)(\s)vlocity/.+" | cut -d" " -f2`
    if [ ! -z $item ]; then
        # get array of the subfolders
        IFS='/' read -ra subdirs <<< "$item"

        # remove the file itself from the array
        unset 'subdirs[${#subdirs[@]}-1]'

        # init
        partialPath="$config/$deploymentsVlocity/$feature"
        for i in "${subdirs[@]}"; do
            partialPath="$partialPath/$i"
            if [ ! -d "$partialPath" ]; then
               mkdir "$partialPath"
            fi
        done
        
        echo "Copying item $item"
        cp $item "$partialPath"
    fi
done
