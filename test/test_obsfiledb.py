import unittest
import os

from sotoddb import ObsFileDB

class TestObsFileDB(unittest.TestCase):
    test_filename = 'test_obsfiledb.sqlite'

    def setUp(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)

    def testBasic(self):
        # Create database in RAM
        db = ObsFileDB.new()
        obs_ids = ['obs1', 'obs2']
        detsets = ['group1', 'group2']
        db.add_detset('group1', ['det1a', 'det1b', 'det1c'])
        db.add_detset('group2', ['det2a', 'det2b', 'det2c'])
        for obs_id in obs_ids:
            for detset in detsets:
                for file_index, sample_index in enumerate([0, 1000, 2000]):
                    filename = '{}_{}_{:04d}.g3'.format(obs_id, detset, sample_index)
                db.add_obsfile(filename, obs_id, detset, sample_index)

        # Write database to disk.
        db.copy(self.test_filename)
        del db

        # Load it up again.
        db = ObsFileDB.from_file(self.test_filename)

        # Check.
        assert (sorted(db.get_obs()) == sorted(obs_ids))
        assert (sorted(db.get_detsets(obs_ids[0])) == sorted(detsets))
        assert (len(db.get_dets(detsets[0])) == 3)
        assert (db.get_detsets('not an obs') == [])

if __name__ == '__main__':
    unittest.main()

