from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(
	name='ckanext-geogovdemo',
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
	namespace_packages=['ckanext', 'ckanext.geogovdemo'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
        [ckan.plugins]
	# Add plugins here, eg
	geogovdemo=ckanext.geogovdemo.plugins:Demo
    iso_csw_harvester=ckanext.geogovdemo.harvesters:IsoCswHarvester
    iso_doc_harvester=ckanext.geogovdemo.harvesters:IsoDocHarvester
    iso_waf_harvester=ckanext.geogovdemo.harvesters:IsoWafHarvester
	""",
)
