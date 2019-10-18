====================================
DetDB: Detector Information Database
====================================

The purpose of the ``DetDB`` class is to give analysts access to
quasi-static detector metadata.  Some good example of quasi-static
detector metadata are: the name of telescope the detector lives in,
the approximate central frequency of its passband, the approximate
position of the detector in the focal plane.  This database is not
intended to carry precision results needed for mapping, such as
calibration information or precise pointing and polarization angle
data.

Certain properties may change with time, for example if wiring or
optics tube arrangements are adjusted from one season of observations
to the next.  The ``DetDB`` is intended to support values that change
with time.  **The timestamp support is still under development.**


.. contents:: Jump to:
   :local:


Using a DetDB (Tutorial)
========================

Loading a database into memory
------------------------------

To load an existing :py:obj:`DetDB<sotoddb.DetDB>` into memory, use
the :py:obj:`DetDB.from_file<sotoddb.DetDB.from_file>` class method::

  >>> import sotoddb
  >>> my_db = sotoddb.DetDB.from_file('path/to/database.sqlite')

.. _DetDB : :py:obj:`blech<sotoddb.DetDB.from_file>`

This function understands a few different formats; see the method
documentation.

If you want an example database to play with, run this::

  >>> import sotoddb
  >>> my_db = sotoddb.get_example('DetDB')
  Creating table base
  Creating table geometry
  Creating LF-type arrays...
  Creating MF-type arrays...
  Creating HF-type arrays...
  Committing 17094 detectors...
  Checking the work...
  >>> my_db
  <sotoddb.detdb.DetDB object at 0x7f691ccb4080>

The usage examples below are based on this example database.


Detectors and Properties
------------------------

The typical use of DetDB involves alternating use of the ``dets`` and
``props`` functions.  The ``dets`` function returns a list of
detectors with certain indicated properties; the ``props`` function
returns the properties of certain indicated detectors.

We can start by getting a list of *all* detectors in the database::

  >>> det_list = my_db.dets()
  >>> det_list
  ResultSet<[name], 17094 rows>

The :py:obj:`ResultSet<sotoddb.ResultSet>` is a simple container for
tabular data.  Follow the link to the class documentation for the
detailed interface.  Here we have a single column, giving the detector
name::

  >>> det_list['name']
  array(['LF1_00000', 'LF1_00001', 'LF1_00002', ..., 'HF2_06501',
         'HF2_06502', 'HF2_06503'], dtype='<U9')

Similarly, we can retrieve all of the properties for all of the
detectors in the database::

  >>> props = my_db.props()
  >>> props
  ResultSet<[base.instrument,base.camera,base.array_code,
  base.array_class,base.wafer_code,base.freq_code,base.det_type,
  geometry.wafer_x,geometry.wafer_y,geometry.wafer_pol], 17094 rows>

The output of ``props()`` is also a ``ResultSet``; but it has many
columns.  The property values for the first detector are:

  >>> props[0]
  {'base.instrument': 'simonsobs', 'base.camera': 'latr',
   'base.array_code': 'LF1', 'base.array_class': 'LF',
   'base.wafer_code': 'W1', 'base.freq_code': 'f027',
   'base.det_type': 'bolo', 'geometry.wafer_x': 0.0,
   'geometry.wafer_y': 0.0, 'geometry.wafer_pol': 0.0}

We can also inspect the data by column, e.g. ``props['base.camera']``.
Note that `name` isn't a column here... each row corresponds to a
single detector, in the order returned by my_db.dets().


Querying detectors based on properties
--------------------------------------

Suppose we want to get the names of the detectors in the (nominal) 93
GHz band.  These are signified, in this example, by having the value
``'f093'`` for the ``base.freq_code`` property.  We call ``dets()``
with this specfied::

  >>> f093_dets = my_db.dets(props={'base.freq_code': 'f093'})
  >>> f093_dets
  ResultSet<[name], 5184 rows>

The argument passed to the ``props=`` keyword, here, is a dictionary
containing certain values that must be matched in order for a detector
to be included in the output ResultSet.  One can also pass a *list* of
such dictionaries (in which case a detector is included if it fully
matches any of the dicts in the list).  One can, to similar effect,
pass a ResultSet, which results in detectors being checked against
each row of the ResultSet.

Similarly, we can request the properties of some sub-set of the
detectors; let's use the ``f093_dets`` list to confirm that these
detectors are all in ``MF`` arrays::

  >>> f093_props = my_db.props(f093_dets, props=['base.array_class'])
  >>> list(f093_props.distinct())
  [{'base.array_class': 'MF'}]

Note we've used the
:py:obj:`ResultSet.distinct()<sotoddb.ResultSet.distinct>` method to
eliminate duplicate entries in the output from ``props()``.  If you
prefer to work with unkeyed data, you can work with ``.rows`` instead
of converting to a list::

  >>> f093_props.distinct().rows
  [('MF',)]


Grouping detectors by property
------------------------------

Suppose we want to loop over all detectors, but with them grouped by
array name and frequency band.  There are many ways to do this, but a
very general approach is to generate a list of tuples representing the
distinct combinations of these properties.  We then loop over that
list, pulling out the names of the matching detectors for each tuple
of property values.

Here's an example, which simply counts the results::

  # Get the two properties, one row per detector.
  >>> props = my_db.props(props=[
  ...   'base.array_code', 'base.freq_code'])
  # Reduce to the distinct combinations (only 14 rows remain).
  >>> combos = props.distinct()
  # Loop over all 14 combos:
  >>> for combo in combos:
  ...   these_dets = my_db.dets(props=combo)
  ...   print('Combo {} includes {} dets.'.format(combo, len(these_dets)))
  ...
  Combo {'base.array_code': 'HF1', 'base.freq_code': 'f225'} includes 1626 dets.
  Combo {'base.array_code': 'HF1', 'base.freq_code': 'f278'} includes 1626 dets.
  Combo {'base.array_code': 'HF2', 'base.freq_code': 'f225'} includes 1626 dets.
  # ...
  Combo {'base.array_code': 'MF4', 'base.freq_code': 'f145'} includes 1296 dets.


Extracting useful detector properties
-------------------------------------

There are a couple of standard recipes for getting data out
efficiently.  SUppose you want to extract two verbosely-named
numerical columns `geometry.wafer_x` and `geometry.wafer_y`.  We want
to be sure to only type those key names out once::

  # Find all 'LF' detectors.
  >>> LF_dets = my_db.dets(props={'base.array_class': 'LF'})
  >>> LF_dets
  ResultSet<[name], 222 rows>
  # Get positions for those detectors.
  >>> positions = my_db.props(LF_dets, props=['geometry.wafer_x',
  ... 'geometry.wafer_y'])
  >>> x, y = numpy.transpose(positions.rows)
  >>> y
  array([0.  , 0.02, 0.04, 0.06, 0.08, 0.1 , 0.12, 0.14, 0.16, 0.18, 0.2 ,
         0.22, 0.24, 0.26, 0.28, 0.3 , 0.32, 0.34, 0.36, 0.38, ...])
  # Now go plot stuff using x and y...
  # ...

  
Note in the last line we've used numpy to transform the tabular data
(in `ResultSet.rows`) into a simple (n,2) float array, which is then
transposed to a (2,n) array, and broadcast to variables x and y.  It
is import to include the `.rows` there -- a direct array conversion on
`positions` will not give you what you want.

Inspecting a database
---------------------

If you want to see a list of the properties defined in the database,
just call ``props`` with an empty list of detectors.  Then access the
``keys`` data member, if you want programmatic access to the list of
properties::

  >>> props = my_db.props([])
  >>> props
  ResultSet<[base.instrument,base.camera,base.array_code,
  base.array_class,base.wafer_code,base.freq_code,base.det_type,
  geometry.wafer_x,geometry.wafer_y,geometry.wafer_pol], 0 rows>
  >>> props.keys
  ['base.instrument', 'base.camera', 'base.array_code',
  'base.array_class', 'base.wafer_code', 'base.freq_code',
  'base.det_type', 'geometry.wafer_x', 'geometry.wafer_y',
  'geometry.wafer_pol']


Creating a DetDB [empty]
========================


Database organization
=====================

**The dets Table**

The database has a primary table, called ``dets``.  The ``dets`` table
has only the following columns:

``name``

    The string name of each detector.

``id``

    The index, used internally, to enumerate detectors.  Do not assume
    that the correspondence between index and name will be static --
    it may change if the underlying inputs are changed, or if a
    database subset is generated.


**The Property Tables**

Every other table in the database is a property table.  Each row of
the property table associates one or more (key,value) pairs with a
detector for a particular range of time.  A property table contains at
least the following 3 columns:

``det_id``

    The detector's internal id, a reference to ``dets.id``.

``time0``

    The timestamp indicating the start of validity of the properties
    in the row.

``time1``

    The timestamp indicating the end of validity of the properties in
    the row.  The pair of timestamps ``time0`` and ``time1`` define a
    semi-open interval, including all times ``t`` such that ``time0 <=
    t < time1``.

All other columns in the property table provide detector metadata.
For a property table to contain valid data, the following criteria
must be satisfied:

1. The range of validity must be non-negative, i.e. ``time0 <=
   time1``.  Note that if ``time0 == time1``, then the interval is
   empty.

2. In any one property table, the time intervals associated with a
   single ``det_id`` must not overlap.  Otherwise, there would be
   ambiguity about the value of a given property.

Internally, query code will assume that above two conditions are
satisfied.  Functions exist, however, to verify compliance of property
tables.


Class auto-documentation
========================

DetDB
-----

Auto-generated documentation should appear here.

.. autoclass:: sotoddb.DetDB
   :members:

ResultSet
---------

Auto-generated documentation should appear here.

.. autoclass:: sotoddb.ResultSet
   :members:
