#!/bin/bash

sed -i 's/^Listen.*/Listen 8080/g' /etc/httpd/conf/httpd.conf
chkconfig --level 2345 nginx on
chkconfig --level 2345 httpd on
chkconfig --level 2345 rabbitmq-server on
setsebool -P httpd_can_network_connect 1
initctl reload-configuration

initctl start supervisor
service httpd restart
service nginx restart
service rabbitmq-server restart
