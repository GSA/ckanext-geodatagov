-------------
Install
-------------

To install this webapp install tomcat.

sudo apt-get install tomcat6

Copy this directory (fgdc2iso) to the webapps folder /var/lib/tomcat6/webapps/

Copy the saxon licence file to /var/lib/tomcat6/webapps/fgdc2iso/WEB-INF/lib/

sudo service tomcat6 restart


------
USAGE
------

POST FGDC file to http://0.0.0.0:8080/fgdc2iso/ and you should recieve ISO document back if valid.
A 409 will be raised with errors if conversion failes.


-------
Example
-------

tl_2009_us_uac00_url.shp.xml FGDC file is included as sample.


Run 

curl http://0.0.0.0:8080/fgdc2iso/ -d @tl_2009_us_uac00_url.shp.xml

and the ISO document should be returned.



