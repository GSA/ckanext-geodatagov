#!/bin/sh -e

echo "TESTING ckanext-geodatagov"
nosetests --ckan --with-pylons=subdir/test.ini ckanext/geodatagov 