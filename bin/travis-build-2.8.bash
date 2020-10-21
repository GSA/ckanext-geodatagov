#!/bin/bash
set -e

echo "Updating script ..."

wget https://raw.githubusercontent.com/GSA/catalog.data.gov/master/tools/ci-scripts/circleci-build-catalog-next.bash
wget https://raw.githubusercontent.com/GSA/catalog.data.gov/master/tools/ci-scripts/test-catalog-next.ini

sudo chmod +x circleci-build-catalog-next.bash
source circleci-build-catalog-next.bash

echo "Update ckanext-geodatagov"
python setup.py develop

echo "TESTING ckanext-geodatagov"
nosetests --ckan --with-pylons=test-catalog-next.ini ckanext/geodatagov --debug=ckanext
