__author__ = 'matteocantarelli'

from org.geppetto.recording import GeppettoRecordingCreator, NeuronRecordingCreator, BrianRecordingCreator, MetaType
import unittest
import os


class RecordingCreatorTestCase(unittest.TestCase):
    """This class demonstrates how to create a recording for Geppetto."""

    REMOVE_FILES_AFTER_TEST = True

    def setUp(self):
        self.filenames = []
        self.files = []

    def register_test_recording_creator(self, creator):
        """Register a test recording creator whose file will be removed after the tests if REMOVE_FILES_AFTER_TEST is set"""
        self.filenames.append(creator.f.filename)
        self.files.append(creator.f)

    def assertAlmostEquals(self, first, second, places=None, msg=None, delta=None):
        """Extended assertAlmostEqual method that works with iterables"""
        if hasattr(first, '__iter__') and hasattr(second, '__iter__'):
            for f, s in zip(first, second):
                unittest.TestCase.assertAlmostEquals(self, f, s, places, msg, delta)
        elif hasattr(first, '__iter__') or hasattr(second, '__iter__'):
            raise TypeError('One of first and second is iterable, the other not')
        else:
            unittest.TestCase.assertAlmostEquals(self, first, second, places, msg, delta)


    def test_fixed_timestep(self):
        c = GeppettoRecordingCreator('test_fixed_timestep.h5')
        self.register_test_recording_creator(c)
        c.add_value('a.w', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        c.add_value('a.b.c.param', 1, 'float_', 'mV', MetaType.PARAMETER)
        c.add_value('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
        c.add_value('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
        c.add_fixed_time_step_vector(1, 'ms')
        c.add_metadata('string_metadata', 'description or link')
        c.add_metadata('float_metadata', 1.0)
        c.add_metadata('boolean_metadata', True)
        c.create()

    def test_variable_timestep(self):
        c = GeppettoRecordingCreator('test_variable_timestep.h5')
        self.register_test_recording_creator(c)
        c.add_value('a.w', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        c.add_value('a.b.c.param', 1, 'float_', 'mV', MetaType.PARAMETER)
        c.add_value('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
        c.add_value('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
        c.add_variable_time_step_vector([0.1, 0.2, 0.5, 0.51, 0.52, 0.6, 0.7], 'ms')
        c.add_metadata('string_metadata', 'description or link')
        c.create()

    def test_neuron_recording_text_1(self):
        c = NeuronRecordingCreator('test_neuron_recording_text_1.h5')
        self.register_test_recording_creator(c)
        c.add_recording_from_neuron('neuron_recordings\\text_from_gui.dat', variable_units=['ms', 'mV'])#text_time.dat')#
        self.assertAlmostEquals(c.values['soma.segmentAt0_5.v'], [-65, -65.0156, -65.0244, -65.0285])
        self.assertEqual(c.units['soma.segmentAt0_5.v'], 'mV')
        self.assertAlmostEquals(c.time, [0, 0.025, 0.05, 0.075])
        self.assertEqual(c.time_unit, 'ms')
        # TODO: create does not work yet
        c.f.close()

    def test_neuron_recording_text_2(self):
        c = NeuronRecordingCreator('test_neuron_recording_text_2.h5')
        self.register_test_recording_creator(c)
        c.add_recording_from_neuron('neuron_recordings\\text_multiple_variables.dat', variable_labels_prefix='segment.')
        self.assertAlmostEquals(c.values['segment.ica'], [-0.000422814, -0.000422814])
        self.assertAlmostEquals(c.values['segment.ica_nacax'], [-0.00028025, -0.00028025])
        self.assertAlmostEquals(c.values['segment.ica_capump'], [0, 0])
        self.assertAlmostEquals(c.values['segment.ica_cachan'], [-0.000142564, -0.000142564])
        self.assertAlmostEquals(c.values['segment.ica_pmp_cadifpmp'], [0, 0.00083607])
        self.assertAlmostEquals(c.time, [0, 0.025])
        # TODO: create does not work yet
        c.f.close()

    def test_neuron_recording_binary(self):
        c = NeuronRecordingCreator('test_neuron_recording_binary.h5')
        self.register_test_recording_creator(c)
        c.add_recording_from_neuron('neuron_recordings\\binary_voltage.dat', variable_labels='v')
        # TODO: Make test recording shorter and run assertEquals checks
        # TODO: create does not work yet
        c.f.close()

    def test_neuron_recording_binary_corrupted(self):
        c = NeuronRecordingCreator('test_neuron_recording_binary_corrupted.h5')
        self.register_test_recording_creator(c)
        self.assertRaises(ValueError, c.add_recording_from_neuron, ('neuron_recordings\\binary_corrupted.dat'))
        # TODO: create does not work yet
        c.f.close()

    def test_brian_recording_text(self):
        c = BrianRecordingCreator('test_brian_recording_text.h5')
        self.register_test_recording_creator(c)
        c.add_recording_from_brian('brian_recordings\\filespikemonitor.dat')
        self.assertAlmostEquals(c.values['neuron0.spikes'], [0.0102, 0.0582])
        self.assertAlmostEquals(c.values['neuron1.spikes'], [0.0436])
        self.assertAlmostEquals(c.values['neuron2.spikes'], [0.0201, 0.0681])
        self.assertAlmostEquals(c.values['neuron3.spikes'], [0.0014, 0.0493])
        self.assertAlmostEquals(c.values['neuron4.spikes'], [0.0337])
        # TODO: create does not work yet because events are not implemented
        c.f.close()

    def test_brian_recording_binary(self):
        c = BrianRecordingCreator('test_brian_recording_binary.h5')
        self.register_test_recording_creator(c)
        c.add_recording_from_brian('brian_recordings\\aerspikemonitor.aedat')
        self.assertAlmostEquals(c.values['neuron0.spikes'], [0.0102, 0.0582])
        self.assertAlmostEquals(c.values['neuron1.spikes'], [0.0436])
        self.assertAlmostEquals(c.values['neuron2.spikes'], [0.0201, 0.0681])
        self.assertAlmostEquals(c.values['neuron3.spikes'], [0.0014, 0.0493])
        self.assertAlmostEquals(c.values['neuron4.spikes'], [0.0337])
        # TODO: create does not work yet because events are not implemented
        c.f.close()

    def tearDown(self):
        for f in self.files:
            try:
                f.close()
            except Exception:
                pass  # file is already closed
        if self.REMOVE_FILES_AFTER_TEST:
            for filename in self.filenames:
                os.remove(filename)

    # TODO: Create some tests for NEURON dat, brian dat and brian aedat files


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
