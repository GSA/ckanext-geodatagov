ARG CKAN_VERSION=2.8
FROM openknowledge/ckan-dev:${CKAN_VERSION}

COPY . /app
WORKDIR /app

# python cryptography takes a while to build
RUN pip install -r requirements.txt -r dev-requirements.txt -e .
