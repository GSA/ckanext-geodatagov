#!/bin/sh
wget http://www.saxonica.com/download/SaxonPE9-4-0-4J.zip
unzip SaxonPE9-4-0-4J.zip
mv saxon9pe.jar lib/
rm saxon*.jar
rm SaxonPE9-4-0-4J.zip

wget http://jdbc.postgresql.org/download/postgresql-9.1-902.jdbc4.jar
mv postgresql-9.1-902.jdbc4.jar lib/postgresql-9.1-902.jdbc4.jar