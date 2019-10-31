#!/bin/sh -e

echo "TESTING ckanext-geodatagov"

nosetests --ckan --nologcapture --logging-filter=harvester --with-pylons=subdir/test.ini ckanext/geodatagov 