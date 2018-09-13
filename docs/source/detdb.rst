Detector Information Database (detdb)
=====================================

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
with time.

Database organization
---------------------

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


Using a DetDB
-------------

Assuming that you already have a populated DetDB, the following
examples show how to extract information from it.  To get an example
database to work, use the ``toddb.get_example`` function::

  >>> import sotoddb
  >>> my_db = sotoddb.get_example('DetDB')

To get a list of all detectors managed by the database, use the
``get_dets()`` method.  Normally this function would be used to
restrict the returned dataset somehow, but without arguments it will
list all detectors::

  >>> det_list = my_db.get_dets()
  >>> det_list[0]
  (1, 'LF1_00000', 1)
  >>> det_list.keys
  ['id', 'name', 'valid']
  >>> det_list.asarray()['name'][0:10]
  array(['LF1_00000', 'LF1_00001', 'LF1_00002', 'LF1_00003', 'LF1_00004',
         'LF1_00005', 'LF1_00006', 'LF1_00007', 'LF1_00008', 'LF1_00009'],
        dtype='<U9')

To look up certain properties of certain detectors, use
``get_props()``.  We will use the detector list returned before, and
see what camera and array is associated with these detectors::

  >>> props = my_db.get_props(det_list, props=['camera', 'array_code'])
  >>> print(len(props))
  17094
  >>> print(set.distinct())
  [('latr', 'HF1'), ('latr', 'LF1'), ('latr', 'MF1')]

The two printed lines indicate that there are 17094 results returned
(one (camera, array_code) pair per detector), but that there only 3
different values for these tuples -- they all have camera "latr" but
have different values for array_code.

The ``det_list`` and ``props`` returned by get_dets and get_props are
actually instances of an sotoddb class called ``ResultSet``.
``ResultSet`` is aware of the column names, and has a few convenience
methods defined for converting the data to more useful structures.
One such structure is the numpy structured array:

  >>> xy = my_db.get_props(det_list, pros=['geometry.wafer_x', 'geometry.wafer_y'])
  >>> xyar = xy.asarray(simplify_keys=True)
  >>> print(xyar.dtype)
  [('wafer_x', '<f8'), ('wafer_y', '<f8')]
  >>> radii = (xyar['wafer_x']**2 + xyar['wafer_y']**2)**0.5
  >>> print(max(radii))
  3.6486709909225854


Class auto-documentation
------------------------

What follows is automatically generated from the docstrings.

.. autoclass:: sotoddb.DetDB
   :members:


.. autoclass:: sotoddb.ResultSet
   :members:
