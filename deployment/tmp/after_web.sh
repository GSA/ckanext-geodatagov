#!/bin/bash

sed -i 's/^Listen.*/Listen 8080/g' /etc/httpd/conf/httpd.conf
chkconfig --level 2345 nginx on
chkconfig --level 2345 httpd on
setsebool -P httpd_can_network_connect 1
setsebool -P httpd_tmp_exec on
initctl reload-configuration
rm -f /etc/nginx/conf.d/default.conf
rm -f /etc/httpd/conf.d/welcome.conf

if [ ! -f /usr/lib64/libxmlsec1-openssl.so ];
then
     ln -s /usr/lib64/libxmlsec1-openssl.so.1.2.16 /usr/lib64/libxmlsec1-openssl.so
fi

service httpd restart
service nginx restart
