#!/bin/bash

sed -i 's/^Listen.*/Listen 8080/g' /etc/httpd/conf/httpd.conf
chkconfig --level 2345 nginx on
chkconfig --level 2345 httpd on
service httpd restart
service nginx restart
