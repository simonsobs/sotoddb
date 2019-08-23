Observation File Database (ObsFileDB)
=====================================

The purpose of ObsFileDB is to provide a map into a large set of TOD
files, giving the names of the files and a compressed expression of
what time indices and detectors are present in each file.

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

Notes:

- Normally detsets will be coherent across a large set of observations
  -- i.e. because we will probably always group the detectors into
  files in the same way.  But this is not required.
- In the case of non-cosampled arrays that are observing at the same
  time on the same telescope: these qualify as different observations
  and should be given different obs_ids.
- Some work will be easier if all of the files in the data set are
  divided along the same lines in time.  But this is not strictly
  required, at present, by the database structure.

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

Suppose we have a coherent archive of TOD data files living at path
MY_TOD_FILES/.  Suppose someone was generated the database file
MY_TOD_FILES/obsfiledb.sqlite.  Then to find things in the data set we
instantiate access to the database (this will open the DB as read-only
by default)::

  db = ObsFileDB.for_dir('MY_TOD_FILES')

And then find an observation::

  all_obs = db.get_obs()
  print(all_obs[0])   # -> 'CES-Atacama-LAT-Tier1DEC-035..-045_RA+040..+050-0-0_LF'

We can list the detsets present in this observation; then get all the
file info (paths and sample indices) for one of the detsets::

  all_detsets = db.get_detsets(all_obs[0])
  print(all_detsets)  # -> ['LF1_tube_LT6', 'LF2_tube_LT6']
  
  files = db.get_files(all_obs[0], detsets=[all_detsets[0]])
  print(files['LF1_tube_LT6'])
                      # -> ('MY_TOD_FILES/datadump_LAT_LF1/CES-Atacama-LAT-Tier1DEC-035..-045_RA+040..+050-0-0/LF1_tube_LT6_00000000.g3', 0, None)



Class Documentation
-------------------

*The class documentation of ObsFileDB should appear below.*

.. autoclass:: sotoddb.ObsFileDB
   :members:

   .. automethod:: __init__
