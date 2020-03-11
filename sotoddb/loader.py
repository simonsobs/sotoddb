from sotodlib import core, metadata
from .simple import PerDetectorHdf5

REGISTRY = {
    'PerDetectorHdf5': PerDetectorHdf5.loader_class(),
}

class SuperLoader:
    def __init__(self, context=None, detdb=None, obsdb=None):
        if context is not None:
            if detdb is None:
                detdb = context.detdb
            if obsdb is None:
                obsdb = context.obsdb
        self.detdb = detdb
        self.obsdb = obsdb

    def load_raw(self, spec_list, request,
                 restrict_on_index=True,
                 restrict_on_request=True):
        """Loads metadata objects and returns them in their Natural
        containers.

        """
        items = []
        for spec_dict in spec_list:
            dbfile = spec_dict['db']
            names = spec_dict['name']
            loader = spec_dict.get('loader', None)

            # Load the database, match the request,
            man = metadata.ManifestDB.from_file(dbfile)
            # Provide any extrinsic boosting.
            if not 'obs:timestamp' in request and self.obsdb is not None:
                request['obs:timestamp'] = self.obsdb.something()
                #float(request['obs:obs_id'][:10])
            index_lines = man.match(request, multi=True)

            # Load and reduce each Index line
            results = []
            for index_line in index_lines:
                # Augment the index_line with info from the request.
                skip_this = False
                for k in request:
                    if k in index_line:
                        if request[k] != index_line[k]:
                            skip_this = True
                if skip_this:
                    continue
                index_line.update(request)
                if loader is None:
                    # Pop?
                    loader = index_line.get('loader')
                if loader is None:
                    loader = 'PerDetectorHdf5'
                loader_class = REGISTRY[loader]
                loader_object = loader_class(detdb=self.detdb, obsdb=self.obsdb)
                mi1 = loader_object.from_loadspec(index_line)
                # restrict to index_line...
                mi2 = mi1.restrict_dets(index_line, detdb=self.detdb)
                results.append(mi2)
            # Combine results.
            result = results[0].concatenate(results)

            # Get list of fields and decode name map.
            if isinstance(result, core.AxisManager):
                fields = list(result._fields.keys())
            else:
                fields = result.keys
            unpackers = Unpacker.decode(names, fields)

            items.append((unpackers, result))
        return items

    def unpack(self, packed_items, dest=None):
        """Unpack items from packed_items, and return then in a single
        AxisManager.

        """
        if dest is None:
            dest = core.AxisManager()
        for unpackers, metadata_instance in packed_items:
            # Convert to AxisManager...
            if isinstance(metadata_instance, core.AxisManager):
                child_axes = metadata_instance
            else:
                child_axes = metadata_instance.axismanager(detdb=self.detdb)
            fields_to_delete = list(child_axes._fields.keys())
            # Unpack to requested field names.
            for unpack in unpackers:
                if unpack.src is None:
                    dest.wrap(unpack.dest, child_axes)
                    break
                else:
                    fields_to_delete.remove(unpack.src)
                    if unpack.src != unpack.dest:
                        child_axes.move(unpack.src, unpack.dest)
            else:
                for f in fields_to_delete:
                    child_axes.move(f, None)
                dest.merge(child_axes)
        return dest

    def load(self, spec_list, request, dest=None):
        """Loads metadata objects and processes them into a single
        AxisManager.  This is equivalent to running load_raw and then
        unpack, though the two are intermingled.

        """
        for spec in spec_list:
            item = self.load_raw([spec], request)
            dest = self.unpack(item, dest=dest)
        return dest


class Unpacker:
    @classmethod
    def decode(cls, coded, wildcard=[]):
        if isinstance(coded, str):
            coded = [coded]
        # Make a plan based on the name list.
        unpackers = []
        wrap_name = None
        for name in coded:
            if '&' in name:
                assert(wrap_name is None) # You already initiated a merge...
                dest_name, src_name = name.split('&') # check count...
                if src_name == '':
                    src_name = dest_name
                elif src_name == '*':
                    assert(len(wildcard) == 1)
                    src_name = wildcard[0]
                unpackers.append(cls(dest_name, src_name))
            else:
                assert(len(unpackers) == 0) # You already initiated a wrap...
                assert(wrap_name is None) # Multiple 'merge' names? Use & to multiwrap.
                wrap_name = name
                unpackers.append(cls(wrap_name, None))
        return unpackers

    def __init__(self, dest, src):
        self.dest, self.src = dest, src

    def __repr__(self):
        if self.src is None:
            return f'<Unpacker:{self.dest}>'
        return f'<Unpacker:{self.dest}<-{self.src}>'
