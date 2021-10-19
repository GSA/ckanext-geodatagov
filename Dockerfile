ARG CKAN_VERSION=2.8
FROM openknowledge/ckan-dev:${CKAN_VERSION}
ARG CKAN_VERSION

RUN apk add geos-dev proj proj-util proj-dev openjdk11-jre

# Download Saxon jar for FGDC2ISO transform (geodatagov)
ARG saxon_ver=9.9.1-7
ADD \
  https://repo1.maven.org/maven2/net/sf/saxon/Saxon-HE/${saxon_ver}/Saxon-HE-${saxon_ver}.jar \
  /usr/lib/jvm/java-11-openjdk/saxon/saxon.jar

ENV CLASSPATH=${CLASSPATH}:/usr/lib/jvm/java-11-openjdk/saxon/saxon.jar

RUN pip install --upgrade pip

COPY . /app
WORKDIR /app

# python cryptography takes a while to build
RUN if [[ "${CKAN_VERSION}" = "2.8" ]] ; then \
        pip install -r requirements-py2.txt -r dev-requirements-py2.txt -e . ; else \
        pip install -r requirements.txt -r dev-requirements.txt -e . ; fi
