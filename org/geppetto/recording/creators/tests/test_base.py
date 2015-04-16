import unittest
from org.geppetto.recording.creators import RecordingCreator, MetaType
from org.geppetto.recording.creators.tests.abstest import AbstractTestCase


class RecordingCreatorTestCase(AbstractTestCase):
    """Unittests for the basic RecordingCreator class."""

    def test_values(self):
        c = RecordingCreator('test_values.h5')
        self.register_recording_creator(c)
        c.add_values('a.var', [1, 2], 'mV', MetaType.STATE_VARIABLE)
        c.add_values('a.var', 3, 'mV', MetaType.STATE_VARIABLE)
        c.add_values('a.var', 4)
        self.assertRaises(ValueError, c.add_values, 'a.var', [5], 'another_unit', MetaType.PROPERTY)
        self.assertEquals(c.values['a.var'], [1, 2, 3, 4])
        self.assertEquals(c.units['a.var'], 'mV')
        self.assertEqual(c.meta_types['a.var'], MetaType.STATE_VARIABLE)
        self.assertRaises(RuntimeError, c.create)  # no time defined

    def test_time_step(self):
        c = RecordingCreator('test_time_step.h5')
        self.register_recording_creator(c)
        c.add_values('a.var', [1, 2, 3], 'mV', MetaType.STATE_VARIABLE)
        c.set_time_step(0.1, 's')
        self.assertRaises(RuntimeError, c.add_time_points, [0.1, 0.2, 0.3], 's')
        c.set_time_step(0.2, 's')
        self.assertEquals(c.time_step, 0.2)
        self.assertEquals(c.time_unit, 's')
        c.create()

    def test_time_points(self):
        c = RecordingCreator('test_time_points.h5')
        self.register_recording_creator(c)
        c.add_values('a.var', [1, 2, 3], 'mV', MetaType.STATE_VARIABLE)
        c.add_time_points([0.1, 0.2], 's')
        c.add_time_points(0.3)
        self.assertRaises(RuntimeError, c.set_time_step, 0.1, 's')
        self.assertEquals(c.time_points, [0.1, 0.2, 0.3])
        self.assertEquals(c.time_unit, 's')
        c.create()

    def test_metadata(self):
        c = RecordingCreator('test_metadata.h5')
        self.register_recording_creator(c)
        c.add_metadata('version', 1)
        c.add_metadata('meta', 'data')
        self.assertEqual(c.metadata['version'], 1)
        self.assertEqual(c.metadata['meta'], 'data')
        c.create()

    def test_add_after_create(self):
        c = RecordingCreator('test_add_after_create.h5')
        self.register_recording_creator(c)
        c.create()
        self.assertRaises(RuntimeError, c.add_metadata, 'meta', 'data')

    def test_matrix(self):
        c = RecordingCreator('test_matrix.h5', '', True)
        self.register_recording_creator(c)
        c.set_time_step(1, 's')
        c.add_values('a.var', [[1, 2, 3], [4, 5, 6], [7, 8, 9]], 'DimensionlessUnit', MetaType.STATE_VARIABLE, True)
        c.add_values('a.var', [[10, 11, 12], [13, 14, 15], [16, 17, 18]], 'DimensionlessUnit', MetaType.STATE_VARIABLE, True)
        self.assertEquals(c.values['a.var'], [[[1, 2, 3], [4, 5, 6], [7, 8, 9]], [[10, 11, 12], [13, 14, 15], [16, 17, 18]]])
        self.assertEquals(c.units['a.var'], 'DimensionlessUnit')
        c.create()

    def test_vectors(self):
        c = RecordingCreator('test_vectors.h5', '', True)
        self.register_recording_creator(c)
        c.set_time_step(1, 's')
        c.add_values('a.var', [1, 2, 3, 4, 5, 6, 7, 8, 9], 'DimensionlessUnit', MetaType.STATE_VARIABLE, True)
        c.add_values('a.var', [10, 11, 12, 13, 14, 15, 16, 17, 18], 'DimensionlessUnit', MetaType.STATE_VARIABLE, True)
        self.assertEquals(c.values['a.var'], [[1, 2, 3, 4, 5, 6, 7, 8, 9], [10, 11, 12, 13, 14, 15, 16, 17, 18]])
        self.assertEquals(c.units['a.var'], 'DimensionlessUnit')
        c.create()


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
