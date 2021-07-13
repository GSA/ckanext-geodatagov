ARG CKAN_VERSION=2.8
FROM openknowledge/ckan-dev:${CKAN_VERSION}
ARG CKAN_VERSION

RUN apk add geos-dev proj proj-util proj-dev
RUN pip install --upgrade pip

COPY . /app
WORKDIR /app

# python cryptography takes a while to build
RUN if [[ "${CKAN_VERSION}" = "2.8" ]] ; then \
        pip install -r requirements-py2.txt -r dev-requirements-py2.txt -e . ; else \
        pip install -r requirements.txt -r dev-requirements.txt -e . ; fi
