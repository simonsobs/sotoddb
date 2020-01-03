import sqlite3
import os
from collections import OrderedDict
import numpy as np

TABLE_DEFS = {
    'detsets': [
        "`name`    varchar(16)",
        "`det`     varchar(32) unique",
    ],
    'files': [
        "`name`    varchar(256) unique",
        "`detset`  varchar(16)",
        "`obs_id`  varchar(256)",
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
    can be faster to suppress commit ops when a running a batch of
    updates, and commit manually at the end).

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
    def from_file(cls, filename, must_exist=False, readonly=False,
                  prefix=None):
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
        if prefix is None:
            prefix = os.path.split(filename)[0]
        self.prefix = prefix
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

    def copy(self, map_file=None, overwrite=False):
        """
        Duplicate the current database into a new database object, and
        return it.  If map_file is specified, the new database will be
        connected to that sqlite file on disk.  Note that a quick way
        of writing a DB to disk to call copy(map_file=...).
        """
        if map_file is None:
            map_file = ':memory:'
        script = ' '.join(self.conn.iterdump())
        if map_file != ':memory:' and os.path.exists(map_file):
            if not overwrite:
                raise RuntimeError("Output database '%s' exists -- remove or "
                                   "pass overwrite=True to copy." % map_file)
            os.remove(map_file)
        new_db = ObsFileDB(map_file)
        new_db.conn.executescript(script)
        new_db.prefix = self.prefix
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
        c = self.conn.execute('select distinct detset from files '
                              'where obs_id=?', (obs_id,))
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

    def verify(self):
        # Check for the presence of each listed file.
        c = self.conn.execute('select name, obs_id, detset, sample_start '
                              'from files')
        rows = []
        for r in c:
            fp = self.prefix + r[0]
            rows.append((os.path.exists(fp), fp) + tuple(r))

        obs = OrderedDict()
        for r in rows:
            present, fullpath, name, obs_id, detset, sample_start = r
            if obs_id not in obs:
                obs[obs_id] = {'present': [],
                               'absent': []}
            if present:
                obs[obs_id]['present'].append((detset, sample_start))
            else:
                obs[obs_id]['absent'].append((detset, sample_start))

        # Make a detset, sample_start grid for each observation.
        grids = OrderedDict()
        for k, v in obs.items():
            items = v['present']
            detsets = list(set([a for a, b in items]))
            sample_starts = list(set([b for a, b in items]))
            grid = np.zeros((len(detsets), len(sample_starts)), bool)
            for a, b in items:
                grid[detsets.index(a), sample_starts.index(b)] = True
            grids[k] = {'detset': detsets,
                        'sample_start': sample_starts,
                        'grid': grid}

        return {'raw': rows,
                'obs_id': obs,
                'grids': grids}

    def drop_obs(self, obs_id):
        """Delete the specified obs_id from the database.  Returns a list of
        files that are no longer covered by the databse (with prefix).

        """
        # What files does this affect?
        c = self.conn.execute('select name from files where obs_id=?',
                              (obs_id,))
        affected_files = [self.prefix + r[0] for r in c]
        # Drop them.
        self.conn.execute('delete from frame_offsets where file_name in '
                          '(select name from files where obs_id=?)',
                          (obs_id,))
        self.conn.execute('delete from files where obs_id=?',
                          (obs_id,))
        self.conn.commit()
        return affected_files

    def drop_detset(self, detset):
        """Delete the specified detset from the database.  Returns a list of
        files that are no longer covered by the database (with
        prefix).

        """
        # What files does this affect?
        c = self.conn.execute('select name from files where detset=?',
                              (detset,))
        affected_files = [self.prefix + r[0] for r in c]
        # Drop them.
        self.conn.execute('delete from frame_offsets where file_name in '
                          '(select name from files where detset=?)',
                          (detset,))
        self.conn.execute('delete from files where detset=?',
                          (detset,))
        self.conn.commit()
        return affected_files

    def drop_incomplete(self):
        """Compare the files actually present on the system to the ones listed
        in this database.  Drop detsets from each observation, as
        necessary, such that the database is consistent with the file
        system.

        Returns a list of files that are on the system but are no
        longer included in the database.

        """
        affected_files = []
        scan = self.verify()
        for obs_id, info in scan['grids'].items():
            # Drop any detset that does not have complete sample
            # coverage.
            detset_to_drop = np.any(~info['grid'], axis=1)
            for i in detset_to_drop.nonzero()[0]:
                affected_files.extend(
                    [r[0] for r in self.conn.execute(
                        'select name from files where obs_id=? and detset=?',
                        (obs_id, info['detset'][i]))])
                self.conn.execute(
                    'delete from files where obs_id=? and detset=?',
                    (obs_id, info['detset'][i]))
        # Drop any detset that no longer appear in any files.
        self.conn.execute('delete from detsets where name not in '
                            '(select distinct detset from files)')
        self.conn.commit()
        self.conn.execute('vacuum')

        # Return the full paths of only the existing files that have
        # been dropped from the DB.
        path_map = {r[2]: r[1] for r in scan['raw'] if r[0]}
        return [r[1] for r in scan['raw'] if r[2] in affected_files]

    def get_file_list(self, fout=None):
        """Returns a list of all files in the database, without the file
        prefix, sorted by observation / detset / sample_start.  This
        is the sort of list one might use with rsync --files-from.

        If you pass an open file or filename to fout, the names will
        be written there, too.

        """
        c = self.conn.execute('select name from files order by '
                              'obs_id, detset, sample_start')
        output = [r[0] for r in c]
        if fout is not None:
            if isinstance(fout, str):
                assert(not os.path.exists(fout))
                fout = open(fout, 'w')
            for line in output:
                fout.write(line+'\n')
        return output
