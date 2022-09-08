#!/bin/bash

echo "Installing updated cryptography.."
pip install cryptopgraphy==37.04

echo "Init Harvest database tables"
ckan harvester initdb

echo "Init Spatial database tables"
ckan spatial initdb

