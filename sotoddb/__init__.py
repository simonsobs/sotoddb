from . import detdb
from .detdb import DetDB
from .detdb import ResultSet


def get_example(db_type, *args, **kwargs):
    if db_type == 'DetDB':
        return detdb.get_example(*args, **kwargs)
