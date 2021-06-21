# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

from ckanext.geodatagov.harvesters.base import GeoDataGovHarvester
from ckanext.geodatagov.harvesters.base import GeoDataGovCSWHarvester
from ckanext.geodatagov.harvesters.base import GeoDataGovWAFHarvester
from ckanext.geodatagov.harvesters.base import GeoDataGovDocHarvester
from ckanext.geodatagov.harvesters.base import GeoDataGovGeoportalHarvester
from ckanext.geodatagov.harvesters.waf_collection import WAFCollectionHarvester
from ckanext.geodatagov.harvesters.z3950 import Z3950Harvester
from ckanext.geodatagov.harvesters.arcgis import ArcGISHarvester
