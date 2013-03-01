'''
Quick script for tansfering the properties defined in ESRI Geoportal's
properties file to the iso-details.xslt XSLT file.

Oringinal files:

[1] https://github.com/Esri/geoportal-server/blob/master/geoportal/src/gpt/metadata/iso/iso-details.xslt
[2] https://github.com/Esri/geoportal-server/blob/master/geoportal/src/gpt/resources/gpt.properties

Esri Geoportal Server is an open source project released under the Apache
License, version 2.0.

'''

import ConfigParser

ORIGINAL_FILE = 'gpt.properties'
XSLT_FILE = 'iso-details.xslt'


with open(ORIGINAL_FILE, 'r') as f:
    content = f.read()

content = '[main]' + content
content = content.replace('%', '\\%').replace('\\\n', '')

new_file_name = '{0}_mod'.format(ORIGINAL_FILE)

with open(new_file_name, 'w') as f2:
    f2.write(content)

config = ConfigParser.SafeConfigParser()
config.optionxform = str    # Keep keys case
config.read(new_file_name)

with open(XSLT_FILE, 'r') as f3:
    xslt = f3.read()

for key, value in config.items('main'):
    xslt = xslt.replace('>i18n.{0}<'.format(key), '>{0}<'.format(value))

with open('{0}_mod'.format(XSLT_FILE), 'w') as f4:
    f4.write(xslt)

print 'Done'
