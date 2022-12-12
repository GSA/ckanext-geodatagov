
ADRs for CKANEXT_GEODATAGOV
==============================================

# 1. Fix encoding issue for waf harvester

Date: 2021-07-16

## Status

Accepted

## Context

We are using the upstream ckan version of ckanext-spatial.  They upgraded the extension to PY3; however, their harvester tests were removed.  The waf harvester was not being encoded properly to support PY2 and PY3 so our tests were failing.

## Decision

We decided to fix the bug and submit a PR [upstream](https://github.com/ckan/ckanext-spatial/pull/252).

## Consequences

- Until the fix is merged upstream, the ckanext-geodatagov repo will be tracking a pinned version of ckanext-spatial fork which adds complexity.
- All of the customization of the GSA fork of ckanext-spatial is disregarded.  The GSA fork was messy already.



# 2. Fix JSON Serialization of dictionary

Date: 2021-07-19

## Status

Accepted

## Context

We are using the upstream ckan version of ckanext-harvest.  They upgraded the extension to PY3; however, there is a PY3-compatibility issue that causes our tests were failing.

## Decision

We decided to fix the bug and submit a PR [upstream](https://github.com/ckan/ckanext-harvest/pull/450).

## Consequences

- Until the fix is merged upstream, the ckanext-geodatagov repo will be tracking a pinned version of ckanext-spatial fork
which adds complexity.
- All of the customization of the GSA fork of ckanext-spatial is disregarded.  The GSA fork was messy already.


# 3. Use catalog.data.gov Solr Image

Date: 2021-06-21

## Status

Accepted

## Context

The Solr dev image that ckanext-datajson uses was incompatible with ckanext-geodatagov.  There was a 'solrsearch issue' that popped up with no clear resolution.

## Decision

Using the catalog.data.gov stopped solr from throwing exceptions.

## Consequences

- Consequences unknown.
- All of the ckanext repos shouldn't be using varying versions of solr/postgres/etc..


# 4. Fix CKAN Test Suite, specifically reset_db()

Date: 2021-06-24

## Status

Accepted

## Context

If all of the tables are not initialized, the 'reset_db' function attempts to delete all of the tables and reinitialize everything.  Becaues geodatagov requires the postgis tables which has a complicated initialized, the ckan function doesn't support it's maintenance (the current code doesn't support it, it doesn't mean they can't or won't).  This is the [logic](https://github.com/ckan/ckan/blob/e2d9d1610e63d2256739a09ba2a18e59a29a45db/ckan/model/__init__.py#L225-L236) that breaks it.  Either way, if reset_db() is called to early, the postgis tables will be deleted and will break the code.  If reset_db() is called too late, the db can't initialize and the code breaks.  

## Decision

Implement two customizations.
- https://github.com/GSA/ckanext-geodatagov/pull/190/commits/627a8ad689d50b446527ea39ff4b9290203929a9
- https://github.com/GSA/ckanext-geodatagov/pull/190/commits/8e34ee0164ac1ce454d4c8944ee5fbc5d025b2ed

## Consequences

- Consequences unknown.
- If the commands called in the test_category_tags.py is called anywhere else, the tests fail.
- If the commands are repeated in multiple files, the tests fail.
- If any test needs to be run in isolation, the test_category_tags.py test needs to precede it, otherwise the independent test will fail..


# 5. Track PY2 pip requirements separately from PY3

Date: 2021-07-08

## Status

Accepted

## Context

There are a few libraries that either operate differently in py2 and py3 or have different support for py2 and py3 needed to use two separate version.

PY2:
- https://github.com/asl2/PyZ3950.git#egg=PyZ3950
- OWSLib == 0.8.6
- pyproj 1.9.6
- factory-boy==2.1.1
- werkzeug (no customization; it installed based on other dependencies)

PY3:
- https://github.com/danizen/PyZ3950.git#egg=PyZ3950
- OWSLib >= 0.18.0 
- pyproj 2.6.1
- factory-boy==2.12.0
- https://github.com/nickumia-reisys/werkzeug@e1f6527604ab30e4b46b5430a5fb97e7a7055cd7#egg=werkzeug

The PY3 upgrade for ckanext-harvest and ckanext-spatial had small bugs that were submitted as PRs upstream, until they are accepted, the local change needs to be tracked.
- https://github.com/nickumia-reisys/ckanext-harvest.git@9d1f647d247c16b6c3acba26e321e9500cafb18c#egg=ckanext-harvest
- https://github.com/GSA/ckanext-spatial.git@93c430ffc36ba7e306652fd511efd0d1e7081381#egg=ckanext-spatial

## Decision

See [commit](https://github.com/GSA/ckanext-geodatagov/pull/190/commits/0cbd146d286fc1467fd2f3fba4800f7ba66b76ce)

## Consequences

- A lot of specificity


# 6. Remove csw harvester tests

Date: 2021-07-16

## Status

Accepted

## Context

We don't have any customizations to the csw harvesting capability, so we no longer need to test our unique cases.

## Decision

Remove [tests](https://github.com/GSA/ckanext-geodatagov/pull/190/commits/18927273785a8b2f06939c259f909c0d1ae36faf).

## Consequences

- ckanext-spatial or ckanext-harvester are not testing csw harvesting, so there are missing tests overall.


# 6. Rewrite source form test

Date: 2021-07-19

## Status

Unreviewed

## Context

The CKAN test suite no longer supports forms in web pages; so custom parsing needs to be done to extract form options and data.  The new tests leverage [this](https://docs.python.org/3/library/html.parser.html).  The CKAN test suite changed the return type of the test app from [2.8](https://github.com/ckan/ckan/blob/2.8/ckan/tests/helpers.py#L147-L159) to [2.9](https://github.com/ckan/ckan/blob/2.9/ckan/tests/helpers.py#L194-L240).

## Decision

Write [custom test functions](https://github.com/GSA/ckanext-geodatagov/pull/190/commits/18927273785a8b2f06939c259f909c0d1ae36faf).

## Consequences

- ckanext-spatial or ckanext-harvester are not testing csw harvesting, so there are missing tests overall.


# 7. Remove test_source_form test

Date: 2022-12-12

## Status

Unreviewed

## Context

The test was trying to create a harvest source with a post request to `/harvest/new`; however, we suspect something in ckanext-harvest changed and broke this functionality.  Since we are doing harvest tests in catalog.data.gov, we thought it was acceptable to remove this test altogether.

## Decision

Remove test

## Consequences

- Less tests?
