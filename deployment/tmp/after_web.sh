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

service memcached start
service httpd restart
