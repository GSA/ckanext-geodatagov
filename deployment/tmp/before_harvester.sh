#!/bin/bash

service crond stop

if [ $(ps -ef | grep "supervisord" | grep -v "grep" | wc -l) > 0 ];
then
    /usr/bin/supervisorctl stop all
fi

rm -rf /usr/lib/ckan/bin /usr/lib/ckan/include /usr/lib/ckan/lib /usr/lib/ckan/lib64 /usr/lib/ckan/man