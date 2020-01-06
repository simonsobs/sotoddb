Observation File Database (ObsFileDB)
=====================================

The purpose of ObsFileDB is to provide a map into a large set of TOD
files, giving the names of the files and a compressed expression of
what time indices and detectors are present in each file.

Location of Files
-----------------

The ObsFileDB is represented on disk by an sqlite database file.  The
sqlite database contains information about data files, and the
*partial paths* of the data files.  By *partial paths*, we mean that
only the part of the filenames relative to some root node of the data
set should be stored in the database.  In order for the code to find
the data files easily, it is most natural to place the
obsfiledb.sqlite file in that same root node of the data set.
Consider the following file listing as an example::

  /
   data/
        planet_obs/
                   obsfiledb.sqlite     # the database
                   observation0/        # directory for an obs
                                data0_0 # one data file
                                data0_1
                   observation1/
                                data1_0
                                data1_1
                   observation2/
                   ...

On this particular file system, our "root node of the data set" is
located at ``/data/planet_obs``.  All data files are located in
subdirectories of that one root node directory.  The ObsFileDB
database file is also located in that directory, and called
``obsfiledb.sqlite``.  The filenames in obsfiledb.sqlite are written
relative to that root node directory; for example
``observation0/data0_1``.  This means that we can copy or move the
contents of the ``planet_obs`` directory to some other path and the
ObsFileDB will not need to be updated.

There are functions in ObsFileDB that return the full path to the
files, rather than the partial path.  This is achieved by combining
the partial file names in the database with the ObsFileDB instance's
"prefix".  By default, "prefix" is set equal to the directory where
the source sqlite datafile is located.  But it can be overridden, if
needed, when the ObsFileDB is instantiated (or afterwards).


Data Model
----------

We assume the following organization of the data:

- The data are divided into contiguous segments of time called
  "Observations".  An observation is identified by an ``obs_id``,
  which is a string.
- An Observation involves a certain set of co-sampled detectors.  The
  files associated with the Observation must contain data for all the
  Observation's detectors at all times covered by the Observation.
- The detectors involved in a particular Observation are divided into
  groups called detsets.  The purpose of detset grouping is to map
  cleanly onto files, thus each file in the Observation should contain
  the data for exactly one detset.

Here's some ascii art showing an example of how the data in an
observation must be split between files::

     sample index
   X-------------------------------------------------->
 d |
 e |   +-------------------------+------------------+
 t |   | obs0_waf0_00000         | obs0_waf0_01000  |
 e |   +-------------------------+------------------+
 c |   | obs0_waf1_00000         | obs0_waf1_01000  |
 t |   +-------------------------+------------------+
 o |   | obs0_waf2_00000         | obs0_waf2_01000  |
 r |   +-------------------------+------------------+
   V


In this example the data for the observation has been distributed into
6 files.  There are three detsets, probably called ``waf0``, ``waf1``,
and ``waf2``.  In the sample index (or time) direction, each detset is
associated with two files; apparently the observation has been split
at sample index 1000.

Notes:

- Normally detsets will be coherent across a large set of observations
  -- i.e. because we will probably always group the detectors into
  files in the same way.  But this is not required.
- In the case of non-cosampled arrays that are observing at the same
  time on the same telescope: these qualify as different observations
  and should be given different obs_ids.
- It is currently assumed that in a single observation the files for
  each detset will be divided at the same sample index.  The database
  structure doesn't have this baked in, but some internal verification
  code assumes this behavior.  So this requirement can likely be
  loosened, if need be.


The database consists of two main tables.  The first is called
``detsets`` and associates detectors (string ``detsets.det``) with a
particular detset (string ``detset.name``).  The second is called
``files`` and associates files (``files.name`` to each Observation
(string ``files.obs_id``), detset (string ``files.detset``), and
sample range (integers ``sample_start`` and ``sample_stop``).

The ObsFileDB is intended to be portable with the TOD data.  It should
thus be placed near the data (such as in the base directory of the
data), and use relative filenames.

Constructing the ObsFileDB involves building the detsets and files
tables, using functions ``add_detset`` and ``add_obsfile``.  Using the
ObsFileDB is accomplished through the functions ``get_dets``,
``get_detsets``, ``get_obs``, and through custom SQL queries on
``conn``.


Example Usage
-------------

Suppose we have a coherent archive of TOD data files living at
``/mnt/so1/shared/todsims/pipe-s0001/v2/``.  And suppose there's a
database file, ``obsfiledb.sqlite``, in that directory.  We can load
the observation database like this::

  import sotoddb
  db = sotoddb.ObsFileDB.from_file('/mnt/so1/shared/todsims/pip-s0001/v2/')

Note we've given it a directory, not a filename... in such cases the
code will read ``obsfiledb.sqlite`` in the stated directory.

Now we get the list of all observations, and choose one::

  all_obs = db.get_obs()
  print(all_obs[0])   # -> 'CES-Atacama-LAT-Tier1DEC-035..-045_RA+040..+050-0-0_LF'

We can list the detsets present in this observation; then get all the
file info (paths and sample indices) for one of the detsets::

  all_detsets = db.get_detsets(all_obs[0])
  print(all_detsets)  # -> ['LF1_tube_LT6', 'LF2_tube_LT6']
  
  files = db.get_files(all_obs[0], detsets=[all_detsets[0]])
  print(files['LF1_tube_LT6'])
                      # -> [('/mnt/so1/shared/todsims/pipe-s0001/v2/datadump_LAT_LF1/CES-Atacama-LAT-Tier1DEC-035..-045_RA+040..+050-0-0/LF1_tube_LT6_00000000.g3', 0, None)]


Class Documentation
-------------------

*The class documentation of ObsFileDB should appear below.*

.. autoclass:: sotoddb.ObsFileDB
   :members:

   .. automethod:: __init__
