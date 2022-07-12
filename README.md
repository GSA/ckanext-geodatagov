[![Github Actions](https://github.com/GSA/ckanext-geodatagov/actions/workflows/test.yml/badge.svg)](https://github.com/GSA/ckanext-geodatagov/actions)
[![PyPI version](https://badge.fury.io/py/ckanext-geodatagov.svg)](https://badge.fury.io/py/ckanext-geodatagov)

# Data.gov  

[Data.gov](http://data.gov) is an open data website created by the [U.S. General Services Administration](https://github.com/GSA/) that is based on two robust open source projects: [CKAN](http://ckan.org) and [WordPress](http://wordpress.org). The data catalog at [catalog.data.gov](catalog.data.gov) is powered by CKAN, while the content seen at [Data.gov](Data.gov) is powered by WordPress.  
        
**For all code, bugs, and feature requests related to Data.gov, see the project wide Data.gov [issue tracker](https://github.com/GSA/data.gov/issues).** 

Currently this repository is only used for source version control on the code for the CKAN extension for geospatial data, but you can see all of the Data.gov relevant repos listed in the [GSA Data.gov README file](https://github.com/GSA/data.gov/blob/master/README.md). 

## CKAN Extension for Geospatial Data

Most Data.gov specific CKAN customizations are contained within this extension, but the extension also provides additional geospatial capabilities.

### Customization

The migration process from CKAN 2.3 (forked version) to CKAN 2.8 includes a significant reduction in custom code (and a large reduction in the time required to maintain this code).
This new version of the catalog (called _Catalog-Next_) begins to use the official versions of:
  - CKAN
  - ckanext-harvest
  - ckanext-spatial

In this way of reducing custom code this extension should be reviewed. Some features should be removed or moved to the official community versions:
  - [Stop rolling up the extras](https://github.com/GSA/ckanext-geodatagov/issues/178)
  - [Move to the official search by geolocation](https://github.com/GSA/datagov-deploy/issues/2440) (probably sharing our version that has improvements)
  - Do a general analysis of this extension to detect other personalized functionalities that should be discontinued.

### Requirements

Package                                                                | Notes
---------------------------------------------------------------------- | -------------
[ckanext-harvest](https://github.com/ckan/ckanext-harvest/)            | Commit: [9d1f647](https://github.com/nickumia-reisys/ckanext-harvest.git@9d1f647d247c16b6c3acba26e321e9500cafb18c) on [nickumia-reisys fork](https://github.com/nickumia-reisys/ckanext-harvest) until merged upstream
[ckanext-datagovtheme](https://github.com/GSA/ckanext-datagovtheme)    | --
[ckanext-datajson](https://github.com/GSA/ckanext-datajson)            | Commit: [a3dfe6b](https://github.com/GSA/ckanext-datajson.git@a3dfe6bc183022572092ee572e557270701950a4) on [GSA branch](https://github.com/GSA/ckanext-datajson) until merged to main
[ckanext-spatial](https://github.com/ckan/ckanext-spatial)             | Commit: [93c430f](https://github.com/GSA/ckanext-spatial.git@93c430ffc36ba7e306652fd511efd0d1e7081381) on [GSA fork](https://github.com/GSA/ckanext-spatial) until merged upstream
[PyZ3950](https://github.com/danizen/PyZ3950)                          | --
[werkzeug](https://github.com/nickumia-reisys/werkzeug)                | This only effects the tests.  For all intents and purposes, this should be tracking [upstream](https://github.com/pallets/werkzeug)

This extension is compatible with these versions of CKAN.

CKAN version | Compatibility
------------ | -------------
<=2.7        | no
2.8          | yes
2.9          | [complete](https://github.com/GSA/datagov-ckan-multi/issues/570)

## Tests

All the tests live in the [/ckanext/geodatagov/tests](/ckanext/geodatagov/tests) folder. After each commit, via the [CircleCI config](https://github.com/GSA/ckanext-geodatagov/blob/master/.circleci/config.yml), this tests will [run in CircleCI](https://circleci.com/gh/GSA/ckanext-geodatagov) with CKAN 2.3 (custom GSA fork) and CKAN 2.8.  The CircleCI tests were not retained, but may be revisited in the future.

## Using the Docker Dev Environment

### Build Environment

To start environment, run:
```docker-compose build```
```docker-compose up```

CKAN will start at localhost:5000

To shut down environment, run:

```docker-compose down```

To docker exec into the CKAN image, run:

```docker-compose exec app /bin/bash```

### Testing

They follow the guidelines for [testing CKAN
extensions](https://docs.ckan.org/en/2.8/extensions/testing-extensions.html#testing-extensions).

To run the extension tests, start the containers with `make up`, then:

    $ make test

Lint the code.

    $ make lint
    
### Matrix builds

The existing development environment assumes a full catalog.data.gov test setup. This makes
it difficult to develop and test against new versions of CKAN (or really any
dependency) because everything is tightly coupled and would require us to
upgrade everything at once which doesn't really work. A new make target
`test-new` is introduced with a new docker-compose file.

The "new" development environment drops as many dependencies as possible. It is
not meant to have feature parity with
[GSA/catalog.data.gov](https://github.com/GSA/catalog.data.gov/). Tests should
mock external dependencies where possible.

In order to support multiple versions of CKAN, or even upgrade to new versions
of CKAN, we support development and testing through the `CKAN_VERSION`
environment variable.

    $ make CKAN_VERSION=2.8 test
    $ make CKAN_VERSION=2.9 test

## Credit / Copying

Original work written by the HealthData.gov team. It has been modified in support of Data.gov.

As a work of the United States Government, this package is in the public
domain within the United States. Additionally, we waive copyright and
related rights in the work worldwide through the CC0 1.0 Universal
public domain dedication (which can be found at http://creativecommons.org/publicdomain/zero/1.0/).

## Ways to Contribute
We're so glad you're thinking about contributing to ckanext-datajson!

Before contributing to ckanext-datajson we encourage you to read our
[CONTRIBUTING](CONTRIBUTING.md) guide, our [LICENSE](LICENSE.md), and our README
(you are here), all of which should be in this repository. If you have any
questions, you can email the Data.gov team at
[datagov@gsa.gov](mailto:datagov@gsa.gov).
