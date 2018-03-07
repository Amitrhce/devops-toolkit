# devops-toolkit
--------

DevOps-Toolkit is a set of command line scripts to export and deploy Salesforce and Vlocity metadata in a source control friendly format. Its primary goal is to enable Continuous Integration both for Salesforce and Vlocity Metadata through source control. It is written as a Bash and Python and it is build on top of force-dev-tool and Vlocity Build tools.

### Table of Contents
* [Installation Instructions](#installation-instructions)
* [Getting Started](#getting-started)
* [Step by Step Guide](#step-by-step-guide)
    * [Simple Export](#simple-export)
    * [Simple Deploy](#simple-deploy)
    * [Org to Org Migration](#org-to-org-migration)
* [Troubleshooting](#troubleshooting)
* [All Commands](#all-commands)
  * [Example Commands](#example-commands)
  
# Installation Instructions
-----------

## Install force-dev-tool
For more information please refer to
https://github.com/amtrack/force-dev-tool#force-dev-tool

## Install vlocity_build
For more information please refer to
https://github.com/vlocityinc/vlocity_build#installation-instructions

# Getting Started
------------
To begin, you will need to add remotes using force-dev-tool for your source and target (both production and test) Salesforce Orgs:
```java
force-dev-tool remote add prod <username> <password + security token> https://login.salesforce.com --default
force-dev-tool remote add dev01 <username> <password + security token> https://test.salesforce.com
force-dev-tool remote add cita <username> <password + security token> https://test.salesforce.com
force-dev-tool remote add sita <username> <password + security token> https://test.salesforce.com
```

# All Commands
-----------

`get_sf_components.sh`: ...
`get_vlocity_components.sh`: ...
`get_and_deploy_sf_components.sh`: ...  
`deploy_sf_components.sh`: ... 
`create_package_xml.sh`: ... 
`fix_package.sh`: ... 
`retrieve_vlocity_metadata.py`: ... 
`migrate_users.py`: ...

## Examples
-----------

```java
get_sf_components.sh Item-03795 | create_package_xml.sh -o packages/Item-03795
get_and_deploy_sf_components.sh -t deva,cita,citc Item-03795
get_vlocity_components.sh Item-02704 | retrieve_vlocity_metadata.py -d
get_vlocity_components.sh Item-02704 | retrieve_vlocity_metadata.py -d -o config/deploymentsVlocity/CIT-Release-13
```
