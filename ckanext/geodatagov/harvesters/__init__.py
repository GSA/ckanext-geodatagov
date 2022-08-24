# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

from ckanext.geodatagov.harvesters.base import GeoDataGovHarvester  # NOQA F401
from ckanext.geodatagov.harvesters.base import GeoDataGovCSWHarvester  # NOQA F401
from ckanext.geodatagov.harvesters.base import GeoDataGovWAFHarvester  # NOQA F401
from ckanext.geodatagov.harvesters.base import GeoDataGovDocHarvester  # NOQA F401
from ckanext.geodatagov.harvesters.base import GeoDataGovGeoportalHarvester  # NOQA F401
from ckanext.geodatagov.harvesters.waf_collection import WAFCollectionHarvester  # NOQA F401
from ckanext.geodatagov.harvesters.z3950 import Z3950Harvester  # NOQA F401
from ckanext.geodatagov.harvesters.arcgis import ArcGISHarvester  # NOQA F401
