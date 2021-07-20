
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

