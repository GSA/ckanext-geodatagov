import logging
from html.parser import HTMLParser

import six
from ckan.tests import factories, helpers

import ckanext.harvest.model as harvest_model

log = logging.getLogger(__name__)


class SourceFormParser(HTMLParser):
    results = {
        "url": None,
        "source_type": None,
        "title": None,
        "name": None,
        "collection_metadata_url": None,
        "validator_profiles": None,
        "database": None,
        "port": None,
    }

    def handle_starttag(self, tag, attrs):
        if tag == "input":
            attr_dict = {}
            for attr in attrs:
                attr_dict[attr[0]] = attr[1]
            if attr_dict["name"] == "url":
                self.results["url"] = attr_dict["value"]
            if attr_dict["name"] == "title":
                self.results["title"] = attr_dict["value"]
            if attr_dict["name"] == "name":
                self.results["name"] = attr_dict["value"]
            if attr_dict["name"] == "collection_metadata_url":
                self.results["collection_metadata_url"] = attr_dict["value"]
            if attr_dict["name"] == "database":
                self.results["database"] = attr_dict["value"]
            if attr_dict["name"] == "port":
                self.results["port"] = attr_dict["value"]
            if "checked" in attr_dict:
                if attr_dict["name"] == "source_type":
                    if attr_dict["value"] != "":
                        self.results["source_type"] = attr_dict["value"]
                if attr_dict["name"] == "validator_profiles":
                    if attr_dict["value"] != "":
                        self.results["validator_profiles"] = attr_dict["value"]

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        pass


class TestHarvestSourceForm(helpers.FunctionalTestBase):
    @classmethod
    def setup(cls):
        helpers.reset_db()

    @classmethod
    def setup_class(cls):
        super(TestHarvestSourceForm, cls).setup_class()
        harvest_model.setup()
        sysadmin = factories.Sysadmin()
        if six.PY2:
            cls.extra_environ = {"REMOTE_USER": sysadmin["name"].encode("ascii")}
        else:
            cls.extra_environ = {"REMOTE_USER": sysadmin["name"]}

    def test_create_waf_collection_harvest_source_form(self):
        WAF_HARVEST_SOURCE_URL = "https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/concity/"
        COLLECTION_METADATA_URL = "https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/\
                                    SeriesInfo/SeriesCollection_tl_2018_concity.shp.iso.xml"
        self.app = self._get_test_app()

        # Create
        harvest_source_name = "test-waf-collection-harvest-source"

        if six.PY2:
            res = self.app.get("/harvest/new", extra_environ=self.extra_environ)
            fv = res.forms["source-new"]
            fv["url"] = WAF_HARVEST_SOURCE_URL
            fv["source_type"] = "waf-collection"
            fv["title"] = "Test WAF colelction harvest source"
            fv["name"] = harvest_source_name
            fv["collection_metadata_url"] = COLLECTION_METADATA_URL
            fv["validator_profiles"] = "iso19139ngdc"

            # Save
            res = fv.submit("save", extra_environ=self.extra_environ)
            assert "Error" not in res
            assert "Missing value" not in res

            # Go to the edit form
            res_redirect = self.app.get(
                "/harvest/edit/{}".format(harvest_source_name),
                extra_environ=self.extra_environ,
            )

            # ensure we have the expected values
            fv = res_redirect.forms["source-new"]
            assert fv["collection_metadata_url"].value == COLLECTION_METADATA_URL
            assert fv["url"].value == WAF_HARVEST_SOURCE_URL
            assert fv["source_type"].value == "waf-collection"
            assert fv["validator_profiles"].value == "iso19139ngdc"
        else:
            parser = SourceFormParser()
            form_data = {
                "url": WAF_HARVEST_SOURCE_URL,
                "source_type": "waf-collection",
                "title": "Test WAF colelction harvest source",
                "name": harvest_source_name,
                "collection_metadata_url": COLLECTION_METADATA_URL,
                "validator_profiles": "iso19139ngdc",
            }
            res = self.app.post(
                "/harvest/new", params=form_data, extra_environ=self.extra_environ
            )

            assert "Error" not in res.body
            assert "Missing value" not in res.body

            res_redirect = self.app.get(
                "/harvest/edit/{}".format(harvest_source_name),
                extra_environ=self.extra_environ,
            )
            parser.feed(res_redirect.body)

            assert parser.results["collection_metadata_url"] == COLLECTION_METADATA_URL
            assert parser.results["url"] == WAF_HARVEST_SOURCE_URL
            assert parser.results["source_type"] == "waf-collection"
            assert parser.results["validator_profiles"] == "iso19139ngdc"

    def test_create_z3950_harvest_source_form(self):

        self.app = self._get_test_app()

        # Create
        harvest_source_name = "test-harvest-source"

        if six.PY2:
            res = self.app.get("/harvest/new", extra_environ=self.extra_environ)

            fv = res.forms["source-new"]
            fv["url"] = "https://test.z3950.com/"
            fv["source_type"] = "z3950"
            fv["title"] = "Test Z3950 harvest source"
            fv["name"] = harvest_source_name
            fv["database"] = "test-database"
            fv["port"] = "9999"

            # Save
            res = fv.submit("save", extra_environ=self.extra_environ)
            assert "Error" not in res
            assert "Missing value" not in res

            # Go to the edit form
            res_redirect = self.app.get(
                "/harvest/edit/{}".format(harvest_source_name),
                extra_environ=self.extra_environ,
            )

            # ensure we have the expected values
            fv = res_redirect.forms["source-new"]
            assert fv["url"].value == "https://test.z3950.com/"
            assert fv["source_type"].value == "z3950"
            assert fv["database"].value == "test-database"
            assert fv["port"].value == "9999"
        else:

            parser = SourceFormParser()
            form_data = {
                "url": "https://test.z3950.com/",
                "source_type": "z3950",
                "title": "Test Z3950 harvest source",
                "name": harvest_source_name,
                "database": "test-database",
                "port": "9999",
            }

            res = self.app.post(
                "/harvest/new", params=form_data, extra_environ=self.extra_environ
            )
            assert "Error" not in res.body
            assert "Missing value" not in res.body

            res_redirect = self.app.get(
                "/harvest/edit/{}".format(harvest_source_name),
                extra_environ=self.extra_environ,
            )
            parser.feed(res_redirect.body)

            assert parser.results["url"] == "https://test.z3950.com/"
            assert parser.results["source_type"] == "z3950"
            assert parser.results["database"] == "test-database"
            assert parser.results["port"] == "9999"
