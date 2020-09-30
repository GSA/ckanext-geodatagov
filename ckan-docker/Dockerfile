FROM openknowledge/ckan-dev:2.8

RUN apk add py-cryptography libressl-dev musl-dev libffi-dev vim

ADD http://download.osgeo.org/geos/geos-3.7.0.tar.bz2 /geos/geos.tar.bz2
RUN tar xf /geos/geos.tar.bz2 -C /geos --strip-components=1
RUN cd /geos && \
    ./configure && \
    make -j 1 && \
    make install

RUN cd ${SRC_DIR}/ckan && \
    git remote add gsa https://github.com/GSA/ckan.git && \
    git fetch gsa && \
    git checkout gsa/datagov-newcatalog

# Use reqs from catalog-next repo (and skip GSA/CKAN instalation)
ADD https://raw.githubusercontent.com/GSA/catalog.data.gov/master/ckan/requirements.txt ${APP_DIR}/requirements.txt
RUN sed -i '/GSA\/ckan\.git/d' ${APP_DIR}/requirements.txt

RUN pip install --upgrade pip && \
    pip install -r ${APP_DIR}/requirements.txt
