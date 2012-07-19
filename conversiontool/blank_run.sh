#!/bin/sh
export CLASSPATH=./lib/postgresql-9.1-902.jdbc4.jar:./lib/saxon9pe.jar
if [ -f "./errors.log" ]; then
  rm ./errors.log
fi
jython src/translator.py <username> <password> 'jdbc:postgresql://<db_host>/<db_name>' ./data/fgdcrse2iso19115-2.xslt