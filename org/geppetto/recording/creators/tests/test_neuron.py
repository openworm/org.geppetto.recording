import unittest
import os
from org.geppetto.recording.creators import NeuronRecordingCreator
from org.geppetto.recording.creators.tests.abstest import AbstractRecordingCreatorTestCase


class NeuronRecordingCreatorTestCase(AbstractRecordingCreatorTestCase):

    def test_text_recording_1(self):
        c = NeuronRecordingCreator('test_text_recording_1.h5')
        self.register_recording_creator(c)
        c.add_neuron_recording(os.path.abspath('neuron_recordings/text_from_gui.dat'), variable_units=['ms', 'mV'])#text_time.dat')#
        self.assertAlmostEquals(c.values['soma.segmentAt0_5.v'], [-65, -65.0156, -65.0244, -65.0285])
        self.assertEqual(c.units['soma.segmentAt0_5.v'], 'mV')
        self.assertAlmostEquals(c.time_points, [0, 0.025, 0.05, 0.075])
        self.assertEqual(c.time_unit, 'ms')
        c.create()

    def test_text_recording_2(self):
        c = NeuronRecordingCreator('test_text_recording_2.h5')
        self.register_recording_creator(c)
        c.add_neuron_recording(os.path.abspath('neuron_recordings/text_multiple_variables.dat'), variable_labels_prefix='segment.')
        self.assertAlmostEquals(c.values['segment.ica'], [-0.000422814, -0.000422814])
        self.assertAlmostEquals(c.values['segment.ica_nacax'], [-0.00028025, -0.00028025])
        self.assertAlmostEquals(c.values['segment.ica_capump'], [0, 0])
        self.assertAlmostEquals(c.values['segment.ica_cachan'], [-0.000142564, -0.000142564])
        self.assertAlmostEquals(c.values['segment.ica_pmp_cadifpmp'], [0, 0.00083607])
        self.assertAlmostEquals(c.time_points, [0, 0.025])
        c.create()

    def test_text_recording_3(self):
        # TODO: Test txt file with single vector
        pass

    def test_binary_recording(self):
        c = NeuronRecordingCreator('test_binary_recording.h5')
        self.register_recording_creator(c)
        c.add_neuron_recording(os.path.abspath('neuron_recordings/binary_voltage.dat'), variable_labels='v', variable_units='mV')
        c.add_neuron_recording(os.path.abspath('neuron_recordings/binary_time.dat'), variable_labels='t', variable_units='ms', time_column=0)
        # TODO: Make tests recording shorter and run assertEquals checks
        c.create()

    def test_corrupted_binary_recording(self):
        c = NeuronRecordingCreator('test_corrupted_binary_recording.h5')
        self.register_recording_creator(c)
        self.assertRaises(IOError, c.add_neuron_recording, (os.path.join('neuron_recordings', 'binary_corrupted.dat')))

    # TODO: Add test for add_vector

    def test_hoc_model(self):
        c = NeuronRecordingCreator('test_hoc_model.h5')
        self.register_recording_creator(c)
        c.record_model(os.path.abspath('neuron_models/sthB.hoc'))
        c.create()

    def test_py_model(self):
        c = NeuronRecordingCreator('test_py_model.h5')
        self.register_recording_creator(c)
        c.record_model(os.path.abspath('neuron_models/sthB.py'))
        c.create()


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
