import unittest
import os
from org.geppetto.recording.creators import NeuronRecordingCreator
from org.geppetto.recording.creators.tests.abstest import AbstractTestCase


class NeuronRecordingCreatorTestCase(AbstractTestCase):
    """Unittests for the NeuronRecordingCreator class."""

    def test_text_recording_1(self):
        c = NeuronRecordingCreator('test_text_recording_1.h5')
        self.register_recording_creator(c)
        c.add_text_recording(os.path.abspath('neuron_recordings/text/graph_gui.dat'), variable_units=['ms', 'mV'])
        self.assertAlmostEquals(c.values['soma.segmentAt0_5.v'], [-65, -65.0156, -65.0244, -65.0285])
        self.assertEqual(c.units['soma.segmentAt0_5.v'], 'mV')
        self.assertAlmostEquals(c.time_points, [0, 0.025, 0.05, 0.075])
        self.assertEqual(c.time_unit, 'ms')
        c.create()

    def test_text_recording_2(self):
        c = NeuronRecordingCreator('test_text_recording_2.h5')
        self.register_recording_creator(c)
        c.add_text_recording(os.path.abspath('neuron_recordings/text/printf.dat'))
        self.assertAlmostEquals(c.values['ica'], [-0.000422814, -0.000422814])
        self.assertAlmostEquals(c.values['ica_nacax'], [-0.00028025, -0.00028025])
        self.assertAlmostEquals(c.values['ica_capump'], [0, 0])
        self.assertAlmostEquals(c.values['ica_cachan'], [-0.000142564, -0.000142564])
        self.assertAlmostEquals(c.values['ica_pmp_cadifpmp'], [0, 0.00083607])
        self.assertAlmostEquals(c.time_points, [0, 0.025])
        c.create()

    def test_text_recording_3(self):
        c = NeuronRecordingCreator('test_text_recording_3.h5')
        self.register_recording_creator(c)
        c.add_text_recording(os.path.abspath('neuron_recordings/text/vector_printf_time.dat'), time_column=0)
        c.add_text_recording(os.path.abspath('neuron_recordings/text/vector_printf_voltage.dat'), variable_names=['soma.segmentAt0_5.v'], variable_units=['mV'])
        self.assertAlmostEquals(c.values['soma.segmentAt0_5.v'], [-65, -65.0156, -65.0244, -65.0285])
        self.assertEqual(c.units['soma.segmentAt0_5.v'], 'mV')
        self.assertAlmostEquals(c.time_points, [0, 0.025, 0.05, 0.075])
        c.create()

    def test_binary_recording(self):
        c = NeuronRecordingCreator('test_binary_recording.h5')
        self.register_recording_creator(c)
        c.add_binary_recording(os.path.abspath('neuron_recordings/binary/voltage.dat'), variable_name='v', variable_unit='mV')
        c.add_binary_recording(os.path.abspath('neuron_recordings/binary/time.dat'), variable_name='t', variable_unit='ms', is_time=True)
        # TODO: Make test recordings shorter and run assertEquals.
        c.create()

    def test_corrupted_binary_recording(self):
        c = NeuronRecordingCreator('test_corrupted_binary_recording.h5')
        self.register_recording_creator(c)
        self.assertRaises(IOError, c.add_binary_recording, os.path.abspath('neuron_recordings/binary/corrupted.dat'), 'name')

    def test_hoc_model(self):
        c = NeuronRecordingCreator('test_hoc_model.h5')
        self.register_recording_creator(c)
        c.record_model(os.path.abspath('neuron_models/sthB.hoc'))
        # TODO: Make test model shorter and run assertEquals.
        c.create()

    def test_py_model(self):
        c = NeuronRecordingCreator('test_py_model.h5')
        self.register_recording_creator(c)
        c.record_model(os.path.abspath('neuron_models/sthB.py'))
        # TODO: Make test model shorter and run assertEquals.
        c.create()


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
