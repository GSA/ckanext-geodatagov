#!/bin/bash

echo "Init Harvest database tables"
ckan harvester initdb

echo "Init Spatial database tables"
ckan spatial initdb

