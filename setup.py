from setuptools import setup, find_packages

version = '0.1'

setup(
	name='ckanext-geodatagov',
	version=version,
	description="",
	long_description="""\
	""",
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='',
	author_email='',
	url='',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.geodatagov'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
        [ckan.plugins]
	# Add plugins here, eg
	geodatagov=ckanext.geodatagov.plugins:Demo
	datagov_harvest=ckanext.geodatagov.plugins:DataGovHarvest

    geodatagov_csw_harvester=ckanext.geodatagov.harvesters:GeoDataGovCSWHarvester
    geodatagov_waf_harvester=ckanext.geodatagov.harvesters:GeoDataGovWAFHarvester
    geodatagov_doc_harvester=ckanext.geodatagov.harvesters:GeoDataGovDocHarvester
    geodatagov_geoportal_harvester=ckanext.geodatagov.harvesters:GeoDataGovGeoportalHarvester
    waf_harvester_collection=ckanext.geodatagov.harvesters:WAFCollectionHarvester
    arcgis_harvester=ckanext.geodatagov.harvesters:ArcGISHarvester
    z3950_harvester=ckanext.geodatagov.harvesters:Z3950Harvester
    geodatagov_miscs=ckanext.geodatagov.plugins:Miscs

    [paste.paster_command]
    geodatagov=ckanext.geodatagov.commands:GeoGovCommand
	""",
)
