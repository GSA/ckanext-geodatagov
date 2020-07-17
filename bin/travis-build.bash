#!/bin/bash
set -e
echo "This is travis-build.bash..."

echo "-----------------------------------------------------------------"
echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty libcommons-fileupload-java libpq-dev postgresql postgresql-contrib python-lxml postgresql-9.3-postgis-2.1

echo "-----------------------------------------------------------------"
echo "Installing CKAN and its Python dependencies..."

cd .. # CircleCI starts inside ckanext-geodatagov folder
pwd
ls -la

if [ $CKANVERSION == '2.8' ]
then
	git clone https://github.com/ckan/ckan
	cd ckan
	git checkout ckan-2.8.4
	# apply required patch
	curl -L https://raw.githubusercontent.com/GSA/catalog.data.gov/master/ckan/patches/ckan/unflattern_indexerror.patch > 1.patch
	echo "Applying patch"
	patch -p1 < 1.patch
elif [ $CKANVERSION == '2.3' ]
then
	git clone https://github.com/GSA/ckan
	cd ckan
	git checkout datagov
	echo "Fix debug css"
	cp ckan/public/base/css/main.css ckan/public/base/css/main.debug.css
fi

pip install --upgrade pip
pip install setuptools -U

python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt

cd ..
echo "-----------------------------------------------------------------"
echo "Setting up Solr..."
# solr is multicore for tests on ckan master now, but it's easier to run tests
# on Travis single-core still.
# see https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini
printf "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty restart

echo "-----------------------------------------------------------------"
echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'
sudo -u postgres psql -c 'CREATE DATABASE datastore_test WITH OWNER ckan_default;'

echo "Setting up PostGIS on the database..."
sudo -u postgres psql -d ckan_test -c 'CREATE EXTENSION postgis;'
sudo -u postgres psql -d ckan_test -c 'ALTER VIEW geometry_columns OWNER TO ckan_default;'
sudo -u postgres psql -d ckan_test -c 'ALTER TABLE spatial_ref_sys OWNER TO ckan_default;'

echo "Install other libraries required..."
sudo apt-get install python-dev libxml2-dev libxslt1-dev libgeos-c1

echo "-----------------------------------------------------------------"
echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini

cd ..
echo "-----------------------------------------------------------------"
echo "Installing Harvester"

git clone https://github.com/GSA/ckanext-harvest
cd ckanext-harvest

if [ $CKANVERSION == '2.8' ]
then
	git checkout datagov-catalog
elif [ $CKANVERSION == '2.3' ]
then
	git checkout datagov
fi

python setup.py develop
pip install -r pip-requirements.txt

paster harvester initdb -c ../ckan/test-core.ini

cd ..
echo "-----------------------------------------------------------------"
echo "Installing DCAT-US/Data.json Harvester"

git clone https://github.com/GSA/ckanext-datajson
cd ckanext-datajson

python setup.py develop
pip install -r pip-requirements.txt

cd ..
echo "-----------------------------------------------------------------"
echo "Installing Spatial"
git clone https://github.com/ckan/ckanext-spatial
cd ckanext-spatial
git checkout master

python setup.py develop
pip install -r pip-requirements.txt

paster spatial initdb -c ../ckan/test-core.ini

cd ..
echo "-----------------------------------------------------------------"
echo "Installing DataGovTheme"
git clone https://github.com/GSA/ckanext-datagovtheme
cd ckanext-datagovtheme
git checkout master

python setup.py develop

cd ..
echo "-----------------------------------------------------------------"
echo "Installing ckanext-geodatagov and its requirements..."
cd ckanext-geodatagov
pip install -r pip-requirements.txt
python setup.py develop

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

# paster geodatagov post-install-dbinit -c subdir/test.ini
# Check if we need
# error:
# File "/usr/lib/python2.7/dist-packages/google_compute_engine/boto/compute_auth.py", line 19, in <module>
#     from google_compute_engine import logger
# ImportError: No module named google_compute_engine

echo "travis-build.bash is done."
