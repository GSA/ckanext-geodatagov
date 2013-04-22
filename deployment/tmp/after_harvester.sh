#!/bin/bash

chkconfig --level 2345 rabbitmq-server on
chkconfig --level 2345 tomcat6 on
chkconfig --level 2345 crond on
initctl reload-configuration

if [ ! -f /usr/lib64/libxmlsec1-openssl.so ];
then
     ln -s /usr/lib64/libxmlsec1-openssl.so.1.2.16 /usr/lib64/libxmlsec1-openssl.so
fi

initctl start supervisor
service rabbitmq-server restart
service tomcat6 restart
service crond restart
supervisorctl restart all
