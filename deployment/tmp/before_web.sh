#!/bin/bash

rm -rf /usr/lib/ckan/bin /usr/lib/ckan/include /usr/lib/ckan/lib /usr/lib/ckan/lib64 /usr/lib/ckan/man

if [ $(ps -ef | grep "httpd" | grep -v "grep" | wc -l) > 0 ];
then
    service httpd stop
fi

