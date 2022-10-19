#!/bin/bash
# Setup and run extension tests. This script should be run in a _clean_ CKAN
# environment. e.g.:
#
#     $ docker-compose run --rm app ./test.sh
#

set -o errexit
set -o pipefail

test_ini=/srv/app/test.ini

# Database is listening, but still unavailable. Just keep trying...
while ! ckan -c $test_ini db init; do
  echo Retrying in 5 seconds...
  sleep 5
done

HOST=db
DB_NAME=ckan
DB_USER=ckan
PASS=ckan

# Uncomment if you would like to rapid-prototype with the spatial extension
# Note: make sure the correct brance is referenced in either requirements.py file
# cd /srv/app/src/ckanext-spatial/
# git pull
# cd -

ckan -c $test_ini harvester initdb
ckan -c $test_ini spatial initdb

pytest --ckan-ini=test.ini --cov=ckanext.geodatagov --disable-warnings ckanext/geodatagov/tests/

# Run this this pytest command if only testing a single test
# pytest --ckan-ini=$test_ini --cov=ckanext.geodatagov --disable-warnings ckanext/geodatagov/tests/test_category_tags.py ckanext/geodatagov/tests/test_db_solr_sync.py
