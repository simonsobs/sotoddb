from .detdb import DetDB
from .loader import SuperLoader
from .obsfiledb import ObsFileDB
from .proddb import ManifestDB, ManifestScheme
from .resultset import ResultSet

from . import simple

def get_example(db_type, *args, **kwargs):
    if db_type == 'DetDB':
        return detdb.get_example(*args, **kwargs)

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
