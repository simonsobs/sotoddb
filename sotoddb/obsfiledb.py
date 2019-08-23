import sqlite3
import os
from collections import OrderedDict

TABLE_DEFS = {
    'detsets': [
        "`name`    varchar(16)",
        "`det`     varchar(32) unique",
    ],
    'files': [
        "`name`    varchar(256) unique",
        "`detset`  varchar(16)",
        "`obs_id`  int",
        "`sample_start` int",
        "`sample_stop`  int",
    ],
    'frame_offsets': [
        "`file_name` varchar(256)",
        "`frame_index` int",
        "`byte_offset` int",
        "`frame_type` varchar(16)",
        "`sample_start` int",
        "`sample_stop` int",
    ],
    'meta': [
        "`param` varchar(32)",
        "`value` varchar"
    ],
}


class ObsFileDB:
    """sqlite3-based database for managing large archives of files.

    The data model here is that each distinct "Observation" comprises
    co-sampled detector data for a large number of detectors.  Each
    detector belongs to a single "detset", and there is a set of files
    containing the data for each detset.  Finding the file that
    contains data for a particular detector is a matter of looking up
    what detset the detector is in, and looking up what file covers
    that detset.

    Note that many functions have a "commit" option, which simply
    affects whether the .commit is called on the database or not (it
    can be faster to suppress such commit ops when

    """

    #: The sqlite3 database connection.
    conn = None

    #: The filename prefix to apply to all filename results returned
    #: from this database.
    prefix = ''

    def __init__(self, map_file, readonly=False):
        """Instantiate a database.  Users should normally get a database
        through one of the classmethods, "new" or "from_file".

        """
        if readonly:
            map_file, uri = 'file:%s?mode=ro' % map_file, True
        else:
            uri = False
        self.conn = sqlite3.connect(map_file, uri=uri)
        self.conn.row_factory = sqlite3.Row  # access columns by name

    @classmethod
    def from_file(cls, filename, must_exist=False, readonly=False):
        """
        Returns an ObsFileDB mapped onto the specified sqlite file.
        """
        do_create = False
        if not os.path.exists(filename):
            if must_exist:
                raise RuntimeError('Insisted that ObsFileDB at {} must exist, '
                                   'but it does not.'.format(filename))
            do_create = True
        self = cls(filename, readonly)
        if do_create:
            self._create()
        return self

    @classmethod
    def for_dir(cls, path, filename='obsfiledb.sqlite', readonly=True):
        """Returns an ObsFileDB located at the specified directory.  The DB is
        assumed to describe the data files based in that directory.

        """
        db_file = os.path.join(path, filename)
        self = cls(db_file, readonly)
        self.prefix = path
        return self

    @classmethod
    def new(cls, filename=':memory:'):
        """Returns a new ObsFileDB.  It will be mapped to RAM unless a
        database file is specified, in which case that file should not exist.

        """
        if filename is None:
            self = cls(':memory:')
        else:
            assert(not os.path.exists(filename))
            self = cls(filename)
        self._create()
        return self

    def copy(self, map_file=None, clobber=False):
        """
        Duplicate the current database into a new database object, and
        return it.  If map_file is specified, the new database will be
        connected to that sqlite file on disk.  Note that a quick way
        of writing a DB to disk to call copy(map_file=...).
        """
        if map_file is None:
            map_file = ':memory:'
        script = ' '.join(self.conn.iterdump())
        new_db = ObsFileDB(map_file)
        new_db.conn.executescript(script)
        return new_db

    def _create(self):
        """
        Create the database tables.
        """
        # Create the tables:
        table_defs = TABLE_DEFS.items()
        c = self.conn.cursor()
        for table_name, column_defs in table_defs:
            q = ('create table if not exists `%s` (' % table_name  +
                 ','.join(column_defs) + ')')
            c.execute(q)

        # Forward looking...
        c.execute('insert into meta (param,value) values (?,?)',
                  ('obsfiledb_version', 1))
        self.conn.commit()

    def add_detset(self, detset_name, detector_names, commit=True):
        """Add a detset to the detsets table.

        Arguments:
          detset_name (str): The (unique) name of this detset.
          detector_names (list of str): The detectors belonging to
            this detset.

        """
        for d in detector_names:
            q = 'insert into detsets (name,det) values (?,?)'
            self.conn.execute(q, (detset_name, d))
        if commit:
            self.conn.commit()

    def add_obsfile(self, filename, obs_id, detset, sample_start=None, sample_stop=None,
                    commit=True):
        """Add an observation file to the files table.

        Arguments:
          filename (str): The filename, relative to the data base
            directory and without a leading /.
          obs_id (str): The observation id.
          detset (str): The detset name.
          sample_start (int): The observation sample index at the
            start of this file.
          sample_stop (int): sample_start + n_samples.

        """
        self.conn.execute(
            'insert into files (name,detset,obs_id,sample_start,sample_stop) '
            'values (?,?,?,?,?)',
            (filename,detset,obs_id,sample_start,sample_stop))
        if commit:
            self.conn.commit()

    # Retrieval

    def get_obs(self):
        """Returns all a list of all obs_id present in this database.

        """
        c = self.conn.execute('select distinct obs_id from files')
        return [r[0] for r in c]

    def get_detsets(self, obs_id):
        """Returns a list of all detsets represented in the observation
        specified by obs_id.

        """
        c = self.conn.execute('select detset from files where obs_id=?', (obs_id,))
        return [r[0] for r in c]

    def get_dets(self, detset):
        """Returns a list of all detectors in the specified detset.

        """
        c = self.conn.execute('select det from detsets where name=?', (detset,))
        return [r[0] for r in c]

    def get_files(self, obs_id, detsets=None, prefix=None):
        """Get the file names associated with a particular obs_id and detsets.

        Returns:

          OrderedDict where the key is the detset name and the value
          is a list of tuples of the form (full_filename,
          sample_start, sample_stop).

        """
        if prefix is None:
            self.prefix

        if detsets is None:
            detsets = self.get_detsets(obs_id)

        c = self.conn.execute('select detset, name, sample_start, sample_stop '
                              'from files where obs_id=? and detset in (%s) '
                              'order by detset, sample_start' %
                              ','.join(['?' for _ in detsets]),
                              (obs_id,) + tuple(detsets))
        output = OrderedDict()
        for r in c:
            output[r[0]] = (self.prefix + r[1], r[2], r[3])
        return output
