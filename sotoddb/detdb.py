import sqlite3
import os
import numpy as np

class SchemaError(Exception):
    """
    This is raised in cases where the code detects a schema violation,
    such as tables not having the required named columns.
    """
    pass

class IntervalError(Exception):
    """
    This is raised in cases where the code detects that time intervals
    in a property table are of negative size or overlap with other
    intervals for the same det_id.
    """
    pass

TABLE_DEFS = {
    'dets': [
        "`id` integer primary key autoincrement",
        "`name` varchar(256) unique",
        ],
    'template': [
        "`det_id` integer",
        "`time0` integer",
        "`time1` integer",
    ],
}


class DetDB:
    """
    Detector database.  The database stores data about a set of
    detectors.

    The ``dets`` table lists all valid detectors, associating a
    (time-invariant) name to each ``id``.

    The other tables in the database are user configurable "property
    tables" that must obey certain rules:

    1. They have at least the following columns:
  
       - ``det_id`` integer
       - ``time0`` integer (unix timestamp)
       - ``time1`` integer (unix timestamp)
    
    2. The values time0 and time1 define an interval ``[time0,time1)``
       over which the data in the row is valid.  Every row shall
       respect the constraint that ``time0 <= time1``.
  
    3. No two rows in a property table shall have the same ``det_id``
       and overlapping time intervals.  Note that since the intervals
       are half-open, the intervals [t0, t1) and [t1, t2) do not
       overlap.
    """

    @classmethod
    def from_file(cls, filename):
        """
        Instantiate a DetDB and return it, with the data copied in from
        the specified sqlite file.  Note that if you want a
        `persistent` connection to the file, you should instead pass
        the filename to the DetDB constructor map_file argument.
        """
        db0 = cls(map_file=filename)
        return db0.copy(map_file=None)
        
    def __init__(self, *args, map_file=None, init_db=True):
        """
        Instantiate a detector database.  If map_file is provided, the
        database will be connected to the indicated sqlite file on
        disk, and any changes made to this object be written back to
        the file.
        """
        assert(len(args)) == 0  # If you want map_file, specify by name.

        if map_file == None:
            map_file = ':memory:'
        self.conn = sqlite3.connect(map_file)
        self.conn.row_factory = sqlite3.Row  # access columns by name

        if init_db:
            # Create dets table if not found.
            c = self.conn.cursor()
            c.execute("SELECT name FROM sqlite_master "
                      "WHERE type='table' and name not like 'sqlite_%';")
            tables = [r[0] for r in c]
            if not 'dets' in tables:
                self.create_table('dets', TABLE_DEFS['dets'])

    def validate(self):
        """
        Checks that the database is following internal rules.
        Specifically we check that a ``dets`` table exists and has the
        necessary columns; then we check that all other tables do not
        have overlapping property intervals.  Raises SchemaError in
        the first case, IntervalError in the second.
        """
        c = self.conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' and name not like 'sqlite_%';")
        tables = [r[0] for r in c]
        if not 'dets' in tables:
            raise SchemaError("Database does not contain a `dets` table.")
        tables.remove('dets')
        for t in tables:
            try:
                c.execute("SELECT det_id,time0,time1 from `%s` order by det_id,time0" % t)
            except sqlite3.OperationalError as e:
                raise SchemaError("Key columns not found in table `%s`" % t)
            last_id, last_t1 = None, None
            for r in c:
                _id, _t0, _t1 = r
                if (_t1 < _t0):
                    raise IntervalError("Negative size time interval for table %s, "
                                        "det_id=%i" % (t, _id))
                if _id == last_id:
                    if _t0 < last_t1:
                        raise IntervalError("Overlapping interval for table %s, "
                                            "det_id=%i" % (t, _id))
                    last_t1 = t1
                else:
                    last_id, last_t1 = _id, _t1

    def create_table(self, table_name, column_defs):
        """
        Add a property table to the database.

        Args:
          table_name (str): The name of the new table.
          column_defs (list): A list of sqlite column definition
            strings.
            
        And example of column_defs (note it must have the det_id,
        time0, time1 columns)::

          column_defs=[
            "`det_id` integer",
            "`time0` integer",
            "`time1` integer",
            "`x_pos` float",
            "`y_pos` float",
          ]
        """
        c = self.conn.cursor()
        q = ('create table if not exists `%s` (' % table_name  +
                 ','.join(column_defs) + ')')
        c.execute(q)
        self.conn.commit()
        return self
        

    def drop_table(self, name):
        c = self.conn.cursor()
        c.execute('drop table %s' % name)

    def copy(self, *args, map_file=None, clobber=False):
        """
        Duplicate the current database into a new database object, and
        return it.  If map_file is specified, the new database will be
        connected to that sqlite file on disk.  Note that a quick way
        of writing a DB to disk to call copy(map_file=...) and then
        simply discard the returned object.
        """
        assert(len(args) == 0) # User must use map_file=... keyword for filename.
        if map_file is not None and os.path.exists(map_file):
            if clobber:
                os.remove(map_file)
            else:
                raise RuntimeError("Output file %s exists (clobber=True "
                                   "to overwrite)." % map_file)
        new_db = DetDB(map_file=map_file, init_db=False)
        script = ' '.join(self.conn.iterdump())
        new_db.conn.executescript(script)
        return new_db

    def to_file(self, filename, clobber=True):
        """
        Write the present database, as an sqlite3 file, to the indicated
        filename.  (This does not create a persistent connection to
        the file.)
        """
        self.copy(map_file=filename, clobber=clobber)

    def reduce(self, det_list=None, time0=None, time1=None):
        """
        Discard information from the database unless it is relevant.
        Data is relevant if:

        - det_list is None, or det_id is in det_list.
        - time0 is None, or time1 is None and time0 is within a
          property's validity range.

        ``time0`` and ``time1`` are both not None, and (``time0``,
        ``time1``) overlaps with the property's validity range.
        """
        c = self.conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' and "
                  "name not like 'sqlite_%';")
        tables = [r[0] for r in c]
        time_clause = '1'
        if time0 is not None:
            if time1 is None:
                time_clause = '(%i < time0) or (time1 <= %i)' % (time0, time0)
            else:
                assert(time1 >= time0)
                time_clause = '(%i > time1) or (time0 >= %i)' % (time0, time1)
        else:
            assert(time1 is None)

        if det_list is not None:
            # Create a temporary table to hold the dets we're keeping.
            # Make sure it has the full index definitions, or the
            # iterdump -> executescript in .copy() might not work.
            self.create_table('_dets', TABLE_DEFS['dets'])
            batch = 2000
            # The list might be tuples from a get_dets()... convert to just ids.
            if hasattr(det_list[0], '__getitem__'):
                det_list = [r[0] for r in det_list]
            # Copy rows, in batches.
            while len(det_list):
                c.execute('insert into _dets select * from dets where id in (%s)' % 
                          ','.join(['%i' % _x for _x in det_list[:batch]]))
                det_list=det_list[batch:]
            # Install this as the new dets table.
            c.execute('drop table dets')
            c.execute('alter table _dets rename to dets')
            det_clause = 'det_id not in (select id from dets)'
        else:
            det_clause = '1'

        # Cull rows from other tables.
        for t in tables:
            if t == 'dets': continue
            c.execute('delete from %s where %s or %s' % (t, det_clause, time_clause))
            
        self.conn.commit()
        c.execute('vacuum') # compact the db.
        self.conn.commit()

        return self

    def __len__(self):
        return self.conn.execute('select count(id) from dets').fetchone()[0]


    # Forward lookup.
    def get_dets(self, timestamp=None, props={}):
        """
        Get a list of detectors matching the conditions listed in the
        "props" dict.  If timestamp is not provided, then time range
        restriction is not applied.

        Returns a list of tuples of the form (det_id, det_name,
        valid).  The "valid" flag is not currently implemented in any
        useful way.
        """
        q = 'select dets.id as id, dets.name as name, count(id)=1 as valid from dets'
        r, args = [], []
        other_tables = []
        for m, v in props.items():
            if '.' in m:
                t,f = m.split('.', 1)
            else:
                t, f = 'base', m
            if not t in other_tables:
                other_tables.append(t)
            r.append('%s=?' % m)
            args.append(v)
        if timestamp is not None:
            r.extend(['(%s.time0 <= ? and ? < %s.time1)' % (m,m)
                      for m in other_tables])
            [args.extend([timestamp, timestamp]) for m in other_tables]
        q = q + ' ' + ' '.join(['join %s as %s on %s.det_id=dets.id' % (m,m,m) for m in other_tables])
        if len(r):
            q = q + ' where ' + ' and '.join(r)
        q = q + ' group by id'
        c = self.conn.cursor()
        c.execute(q, tuple(args))
        return ResultSet.from_cursor(c)
        #return c.fetchall()
            

    # Reverse lookup.
    def get_props(self, dets, timestamp=None, props=[]):
        """
        Get the value of the properties listed in props, for each detector
        identified in dets (a list of strings, or a ResultSet with a
        column called 'name').
        """
        # Create temporary table
        c = self.conn.cursor()
        #c.execute('begin transaction')
        c.execute('drop table if exists _dets')
        c.execute('create temp table _dets (`name` varchar(32))')
        q = 'insert into _dets (name) values (?)'
        if isinstance(dets, ResultSet):
            dets = dets.asarray()['name']
        for a in dets:
            c.execute(q, (a,))
        #c.execute('end transaction')
        # Now look stuff up in it.
        r, args = [], []
        other_tables = []
        fields, keys = [], []
        for i, m in enumerate(props):
            if '.' in m:
                t, f = m.split('.', 1)
            else:
                t, f = 'base', m
            if not t in other_tables:
                other_tables.append(t)
            fields.append('%s.%s as result%i' % (t, f, i))
            keys.append(m)
        q = 'select ' + ','.join(fields) + ' from _dets join dets on _dets.name=dets.name '
        q = q + ' ' + ' '.join(['join %s as %s on %s.det_id=dets.id' % (m,m,m,)
                                for m in other_tables])
        print(q)
        c.execute(q)
        results = ResultSet.from_cursor(c, keys=keys)
        c.execute('drop table if exists _dets')
        return results

class ResultSet(list):
    """
    ResultSet is a list intended to hold the results of database
    queries, i.e. tables of numbers.  Each entry in the list
    corresponds to a row of results.  The names of the columns are
    stored in self.keys.

    The .from_cursor(cursor) method can be used to construct this
    object after executing a query on the cursor.  The .asarray()
    method can be used to return the results in a numpy "structured
    array", which may be convenient for further grouping and usage of
    the results.
    """
    @classmethod
    def from_cursor(cls, cursor, keys=None):
        self = cls()
        if keys is None:
            keys = [c[0] for c in cursor.description]
        self.keys = keys
        x = cursor.fetchall()
        self.x = x
        for _x in x:
            self.append(tuple(_x))
        return self

    def asarray(self, simplify_keys=False):
        """
        Returns a numpy structured array containing a copy of this
        ResultSet.  The names of the fields are taken from self.keys.
        If simplify_keys=True, then the keys are stripped of any
        prefix; an error is thrown if this yields duplicate key names.
        """
        keys = [k for k in self.keys]
        if simplify_keys: # remove prefixes
            keys = [k.split('.')[-1] for k in keys]
            assert(len(set(keys)) == len(keys))  # distinct.
        columns = tuple(map(np.array, zip(*self)))
        dtype = [(k,c.dtype) for k,c in zip(keys, columns)]
        output = np.ndarray(shape=len(columns[0]), dtype=dtype)
        for k,c in zip(keys, columns):
            output[k] = c
        return output

    def distinct(self):
        """
        Returns a ResultSet that is a copy of the present one, with
        duplicates removed.  The rows are sorted (according to python
        sort).
        """
        output = ResultSet(set(self))
        output.sort()
        return output
    

def get_example():
    """
    Returns an example DetDB, mapped to RAM, for the SO LAT-like
    array.  The two property tables are called "base" and "geometry".
    The geometry table is not currently populated.
    """
    import sotoddb
    db = sotoddb.DetDB()

    TABLES = [
        ('base', [
            "`det_id` integer",
            "`time0` integer",
            "`time1` integer",
            "`instrument` varchar(32)",
            "`camera` varchar(32)",
            "`array_code` varchar(16)",
            "`array_class` varchar(16)",
            "`wafer_code` varchar(32)",
            "`freq_code` varchar(16)",
            "`det_type` varchar(32)",
        ]),
        ('geometry', [
            "`det_id` integer",
            "`time0` integer",
            "`time1` integer",
            "`wafer_x` float",
            "`wafer_y` float",
            "`wafer_pol` float",
        ]),
    ]

    for n, d in TABLES:
        print('Creating table %s' % n)
        db.create_table(n, d)

    rows = []
    for ar_type, bands, n_ar, n_wa, n_det in [
            ('LF', [27, 39], 1, 3, 37),
            ('MF', [93, 145], 4, 3, 432),
            ('HF', [225, 278], 2, 3, 542)
    ]:
        print('Creating %s-type arrays...' % ar_type)
        arc = 1 
        for fi,f in enumerate(bands):
            for ar in range(n_ar):
                for wa in range(n_wa):
                    iofs = (fi*n_ar*n_wa + n_wa * ar + wa) * n_det
                    rows.extend([(
                        '%s%i_%05i' % (ar_type, arc, i),
                        'f%03i' % f,
                        ar_type,
                        '%s%i' % (ar_type, arc),
                        'W%i' % (wa+1),
                    )
                                 for i in range(iofs, iofs + n_det)])

    print('Adding %i detectors...' % len(rows))
    t0, t1 = 0, 2e9
    q0 = 'insert into dets (name) values (?)'
    q1 = ('insert into base ' 
          '(time0, time1, det_id, freq_code, array_class, array_code, wafer_code) '
          'values (?,?,?,?,?,?,?)')
    c = db.conn.cursor()

    det_ids = []
    for r in rows:
        c.execute(q0, (r[0],))
        det_ids.append(c.lastrowid)
        args = (t0, t1, det_ids[-1]) + r[1:]
        c.execute(q1, args)

    c.execute('update base set instrument="simonsobs",camera="latr",'\
              'det_type="bolo" where 1')

    # Organize these dets in a big square.  This is not the plan.
    n_row = int(len(rows)**.5)
    for i in range(n_row):
        for j in range(n_row):
            d = i*n_row+j
            if d >= len(rows):
                break
            x, y, ang = i * .02, j * .02, (i+j) % 12. * 15
            c.execute('insert into geometry '
                      '(det_id,time0,time1,wafer_x,wafer_y,wafer_pol) '
                      'values (?,?,?,?,?,?)',
                      (det_ids[d], 0, 2e9, x, y, ang))

    db.conn.commit()

    print('Checking the work...')
    db.validate()

    return db
