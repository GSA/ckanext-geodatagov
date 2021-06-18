#!/bin/bash
# Setup and run extension tests. This script should be run in a _clean_ CKAN
# environment. e.g.:
#
#     $ docker-compose run --rm app ./test.sh
#

set -o errexit
set -o pipefail

# Wrapper for paster/ckan.
# CKAN 2.9 replaces paster with ckan CLI. This wrapper abstracts which comand
# is called.
#
# In order to keep the parsing simple, the first argument MUST be
# --plugin=plugin-name. The config option -c is assumed to be
# test.ini because the argument ordering matters to paster and
# ckan, and again, we want to keep the parsing simple.
function ckan_wrapper () {
  if command -v paster > /dev/null; then
    paster "$@" -c test.ini
  else
    shift  # drop the --plugin= argument
    ckan -c test.ini "$@"
  fi
}

# Database is listening, but still unavailable. Just keep trying...
while ! ckan_wrapper --plugin=ckan db init; do 
  echo Retrying in 5 seconds...
  sleep 5
done

ckan_wrapper --plugin=ckanext-harvest harvester initdb
ckan_wrapper --plugin=ckanext-spatial spatial initdb

## Depreciated, but may be relevant
# 
# echo "-----------------------------------------------------------------"
# echo "Installing locations table"
# DEST_FOLDER=/tmp
# HOST=db
# DB_NAME=ckan_test
# DB_USER=ckan
# PASS=ckan
# 
# echo "Downloading locations table"
# wget https://github.com/GSA/datagov-deploy/raw/71936f004be1882a506362670b82c710c64ef796/ansible/roles/software/ec2/ansible/files/locations.sql.gz -O $DEST_FOLDER/locations.sql.gz
# 
# echo "Creating locations table"
# PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION postgis;"
# gunzip -c ${DEST_FOLDER}/locations.sql.gz | PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1
# 
# echo "Cleaning"
# rm -f $DEST_FOLDER/locations.sql.gz

pytest -s --ckan-ini=test.ini --cov=ckanext.datajson --disable-warnings ckanext/geodatagov/tests/test_export_csv.py
