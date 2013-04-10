#!/bin/bash

chkconfig --level 2345 rabbitmq-server on
chkconfig --level 2345 tomcat6 on
chkconfig --level 2345 crond on
initctl reload-configuration

initctl start supervisor
service rabbitmq-server restart
service tomcat6 restart
service crond restart
supervisorctl restart all
