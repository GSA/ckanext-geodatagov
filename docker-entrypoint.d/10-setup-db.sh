#!/bin/bash

echo "Installing updated cryptography.."
pip install cryptography==37.0.4
pip list

echo "Init Harvest database tables"
ckan harvester initdb

echo "Init Spatial database tables"
ckan spatial initdb

