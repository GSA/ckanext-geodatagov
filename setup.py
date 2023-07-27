from setuptools import setup, find_packages
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="ckanext-geodatagov",
    version="0.2.1",
    description="",
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3'
    ],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Data.gov',
    author_email='datagovhelp@gsa.gov',
    url='https://github.com/GSA/ckanext-geodatagov',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.geodatagov'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
        'ckanext-datajson>=0.1.19',
        'boto3',
        'ply>=3.4',
    ],
    setup_requires=['wheel'],
    entry_points="""
        [ckan.plugins]
    # Add plugins here, eg
    geodatagov=ckanext.geodatagov.plugin:Demo
    s3test=ckanext.geodatagov.plugin:S3Test
    datagov_harvest=ckanext.geodatagov.plugin:DataGovHarvest

    geodatagov_csw_harvester=ckanext.geodatagov.harvesters:GeoDataGovCSWHarvester
    geodatagov_waf_harvester=ckanext.geodatagov.harvesters:GeoDataGovWAFHarvester
    geodatagov_doc_harvester=ckanext.geodatagov.harvesters:GeoDataGovDocHarvester
    geodatagov_geoportal_harvester=ckanext.geodatagov.harvesters:GeoDataGovGeoportalHarvester
    waf_harvester_collection=ckanext.geodatagov.harvesters:WAFCollectionHarvester
    arcgis_harvester=ckanext.geodatagov.harvesters:ArcGISHarvester
    z3950_harvester=ckanext.geodatagov.harvesters:Z3950Harvester
    geodatagov_miscs=ckanext.geodatagov.plugin:Miscs

    [paste.paster_command]
    geodatagov=ckanext.geodatagov.commands:GeoGovCommand
    """,
)
