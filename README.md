[![CircleCI](https://circleci.com/gh/GSA/ckanext-geodatagov.svg?style=svg)](https://circleci.com/gh/GSA/ckanext-geodatagov)

# Data.gov  

[Data.gov](http://data.gov) is an open data website created by the [U.S. General Services Administration](https://github.com/GSA/) that is based on two robust open source projects: [CKAN](http://ckan.org) and [WordPress](http://wordpress.org). The data catalog at [catalog.data.gov](catalog.data.gov) is powered by CKAN, while the content seen at [Data.gov](Data.gov) is powered by WordPress.  
        
**For all code, bugs, and feature requests related to Data.gov, see the project wide Data.gov [issue tracker](https://github.com/GSA/data.gov/issues).** 

Currently this repository is only used for source version control on the code for the CKAN extension for geospatial data, but you can see all of the Data.gov relevant repos listed in the [GSA Data.gov README file](https://github.com/GSA/data.gov/blob/master/README.md). 

## CKAN Extension for Geospatial Data

Most Data.gov specific CKAN customizations are contained within this extension, but the extension also provides additional geospatial capabilities.

## Ways to Contribute
We're so glad you're thinking about contributing to Data.gov!

Before contributing to this extension we encourage you to read our [CONTRIBUTING](https://github.com/GSA/ckanext-geodatagov/blob/master/CONTRIBUTING.md) guide, our [LICENSE](https://github.com/GSA/ckanext-geodatagov/blob/master/LICENSE.md), and our README (you are here), all of which should be in this repository. If you have any questions, you can email the Data.gov team at [datagov@gsa.gov](mailto:datagov@gsa.gov).

## Tests

All the tests lives in the [/ckanext/geodatagov/tests](/ckanext/geodatagov/tests) folder. After each commit, via the [CircleCI config](https://github.com/GSA/ckanext-geodatagov/blob/master/.circleci/config.yml), this tests will [run in CircleCI](https://circleci.com/gh/GSA/ckanext-geodatagov) with CKAN 2.3 (custom GSA fork) and CKAN 2.8.

### Run Tests with Docker

```docker-compose exec ckan /bin/bash -c "nosetests --ckan --with-pylons=src_extensions/geodatagov/docker_test.ini src_extensions/geodatagov/"```

## Using the Docker Dev Environment

### Build Environment

To start environment, run:
```docker-compose build```
```docker-compose up```

CKAN will start at localhost:5000

To shut down environment, run:

```docker-compose down```

To docker exec into the CKAN image, run:

```docker-compose exec ckan /bin/bash```
