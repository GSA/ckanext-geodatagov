ARG CKAN_VERSION=2.11
FROM ckan/ckan-dev:${CKAN_VERSION}
ARG CKAN_VERSION

USER root

RUN apt-get update && apt-get install -y postgresql-client openjdk-17-jre

# Download Saxon jar for FGDC2ISO transform (geodatagov)
ARG saxon_ver=9.9.1-7
ADD \
  https://repo1.maven.org/maven2/net/sf/saxon/Saxon-HE/${saxon_ver}/Saxon-HE-${saxon_ver}.jar \
  /usr/lib/jvm/java-11-openjdk/saxon/saxon.jar

ENV CLASSPATH=${CLASSPATH}:/usr/lib/jvm/java-11-openjdk/saxon/saxon.jar

# Pinned for build issue: https://github.com/pyproj4/pyproj/issues/1321
RUN pip install --upgrade pip
# RUN python3 -m pip install 'cython<3'
# RUN python3 -m pip install --no-use-pep517 pyproj==3.4.1
RUN python3 -m pip install pyproj

COPY . $APP_DIR/

RUN pip install -r $APP_DIR/requirements.txt -r $APP_DIR/dev-requirements.txt -e $APP_DIR/.
