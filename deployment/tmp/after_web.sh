#!/bin/bash

chkconfig --level 2345 httpd on
chkconfig --level 2345 memcached on
setsebool -P httpd_can_network_connect 1
setsebool -P httpd_tmp_exec on
initctl reload-configuration
rm -f /etc/httpd/conf.d/welcome.conf

if [ ! -f /usr/lib64/libxmlsec1-openssl.so ];
then
     ln -s /usr/lib64/libxmlsec1-openssl.so.1.2.16 /usr/lib64/libxmlsec1-openssl.so
fi

# no spiders on dev servers
if [ -f /etc/ckan/robots.txt ];
then
    cp -f /etc/ckan/robots.txt /usr/lib/ckan/src/ckan/ckan/public/robots.txt
fi

service memcached start
service httpd restart

if [ ! -f /usr/lib/ckan/src/ckan/ckan/public/usasearch-custom-feed.xml ];
then
    ln -s /usr/lib/ckan/src/ckanext-geodatagov/ckanext/geodatagov/dynamic_menu/usasearch-custom-feed.xml /usr/lib/ckan/src/ckan/ckan/public/usasearch-custom-feed.xml
fi

chown apache:apache -R /usr/lib/ckan/src/ckanext-geodatagov/ckanext/geodatagov/dynamic_menu
chmod -R a+r /usr/lib/ckan
