#!/bin/bash

RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_PATH=`dirname $0`

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

while getopts "hr:d" opt; do
    case "$opt" in
    #h|\?)
    #    print_help
    #    exit 0
    #    ;;
    d)  VERBOSE=1
        ;;
    r)	repository_path=$OPTARG
	;;
    esac
done

# first check whether this is a git repostiroy
if [ ! -d "$repository_path/.git" ]; then
   printf "${RED}This folder is not a git repository!${NC}\n"
   exit 1;
fi

# first check whether this is a git repostiroy
if [ ! -d "packages" ]; then
   printf "${RED}The folder packages is missing!${NC}\n"
   exit 1;
fi

deployment_path=$PWD

for i in `find packages -type d | egrep -e "packages\/(defect|feature)\/SFCRM-[0-9]+$"`;do
  echo "$i found."
  folder=`echo "$i" | cut -d"/" -f1`;
  branch_type=`echo "$i" | cut -d"/" -f2`;
  branch_name=`echo "$i" | cut -d"/" -f3`;
  
  cd $repository_path
  echo "Checking out crm branch."
  git checkout crm
  git reset --hard origin/crm

  existing_local_branch=""
  existing_remote_branch=""
  
  existing_remote_branch=`git branch -r | grep "$branch_type/$branch_name"`
  existing_local_branch=`git branch -l | grep "$branch_type/$branch_name"`
  
  commit_message=""

  if [ ! -z $existing_local_branch ]; then
     git branch -D $branch_type/$branch_name
  fi

  git checkout -B $branch_type/$branch_name
  commit_message="Initial commit"

#  if [ ! -z $existing_local_branch ] && [ ! -z $existing_remote_branch ]; then
#     echo "$branch_type/$branch_name exists on local and remote as well, checking out the branch."
#     git checkout $existing_local_branch
#     git pull
#     commit_message="Another commit"
#  elif [ ! $existing_local_branch ]; then
#     echo "$branch_type/$branch_name exists on local only, checking out the branch and setting up the upstream."
#     git checkout $existing_local_branch
#     git branch --set-upstream-to=origin/$branch_type/$branch_name $branch_type/$branch_name
#  elif [ ! -z $existing_remote_branch ]; then
#     echo "$branch_type/$branch_name exists on the remote only."
#     git checkout $existing_remote_branch
#     commit_message="Another commit"
#  else
#     echo "$branch_type/$branch_name doesn't exist, creating a new one."
#     git checkout -b $branch_type/$branch_name
#     commit_message="Initial commit"
#  fi

  cd $deployment_path
  $SCRIPT_PATH/synchronize_sf_metadata.py -s $i/src -t $repository_path/src

  cd $repository_path
  added_changes=`git status | egrep "(modified|deleted|new)" | egrep "src/"`

  echo "$added_changes"
  git add src

  if [ ! -z "$added_changes" ]; then
    if [ ! -z $existing_remote_branch ]; then
       git push origin --delete $branch_type/$branch_name
    fi

    echo "Commiting changes to $branch_type/$branch_name"
    git commit -m "$commit_message to $branch_name"
    echo "Pushing $branch_type/$branch_name"
    #if [ -z $existing_local_branch ] && [ -z $existing_remote_branch ]; then
    #   git push --set-upstream origin $branch_type/$branch_name
    #else
    #   git push
    #fi
    git push --set-upstream origin $branch_type/$branch_name
  fi

  cd $deployment_path
  echo
done
