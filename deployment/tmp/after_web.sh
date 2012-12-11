#!/bin/bash

sed -i 's/^Listen.*/Listen 8080/g' /etc/httpd/conf/httpd.conf
chkconfig --level 2345 nginx on
chkconfig --level 2345 httpd on
setsebool -P httpd_can_network_connect 1
setsebool -P httpd_tmp_exec on
initctl reload-configuration
rm -f /etc/nginx/conf.d/default.conf
rm -f /etc/httpd/conf.d/welcome.conf

service httpd restart
service nginx restart
