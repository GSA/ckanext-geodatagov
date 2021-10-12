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
  if command -v ckan > /dev/null; then
    shift  # drop the --plugin= argument
    ckan -c test.ini "$@"
  else
    paster "$@" -c test.ini
  fi
}

# Database is listening, but still unavailable. Just keep trying...
while ! ckan_wrapper --plugin=ckan db init; do 
  echo Retrying in 5 seconds...
  sleep 5
done


HOST=db
DB_NAME=ckan
DB_USER=ckan
PASS=ckan

#PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -c "create EXTENSION postgis;"
#PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -f ./postgis.sql
#PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -f ./spatial_ref_sys.sql
#PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -c "drop extension IF EXISTS postgis cascade;"
#PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -c "DROP TABLE spatial_ref_sys CASCADE;"
#PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -c "drop EXTENSION PostGIS;"
#PGPASSWORD=${PASS} psql -h $HOST -U $DB_USER -d $DB_NAME -f /usr/local/share/postgresql/contrib/postgis-2.5/postgis.sql

#ckan_wrapper --plugin=ckan db clean

# Uncomment if you would like to rapid-prototype with the spatial extension
# Note: make sure the correct brance is referenced in either requirements.py file
# cd /srv/app/src/ckanext-spatial/
# git pull
# cd -

ckan_wrapper --plugin=ckanext-harvest harvester initdb
ckan_wrapper --plugin=ckanext-spatial spatial initdb

pytest --ckan-ini=test.ini --cov=ckanext.geodatagov --disable-warnings ckanext/geodatagov/tests/

# Run this this pytest command if only testing a single test
# pytest --ckan-ini=test.ini --cov=ckanext.geodatagov --disable-warnings ckanext/geodatagov/tests/test_category_tags.py ckanext/geodatagov/tests/test_waf.py
