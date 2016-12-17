/usr/lib/ckan/bin/paster --plugin=ckanext-spatial ckan-pycsw load -p /etc/ckan/pycsw-all.cfg;

/usr/lib/ckan/bin/python /usr/lib/ckan/bin/pycsw-db-admin.py vacuumdb /etc/ckan/pycsw-all.cfg;
