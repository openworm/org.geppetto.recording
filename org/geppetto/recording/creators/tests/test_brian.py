import unittest
import os
import sys
from org.geppetto.recording.creators import BrianRecordingCreator
from org.geppetto.recording.creators.tests.abstest import AbstractRecordingCreatorTestCase


class BrianRecordingCreatorTestCase(AbstractRecordingCreatorTestCase):

    def test_text_recording(self):
        c = BrianRecordingCreator('test_text_recording.h5')
        self.register_recording_creator(c)
        c.add_brian_recording(os.path.abspath('brian_recordings/filespikemonitor.dat'))
        self.assertAlmostEquals(c.values['neuron0.spikes'], [0.0102, 0.0582])
        self.assertAlmostEquals(c.values['neuron1.spikes'], [0.0436])
        self.assertAlmostEquals(c.values['neuron2.spikes'], [0.0201, 0.0681])
        self.assertAlmostEquals(c.values['neuron3.spikes'], [0.0014, 0.0493])
        self.assertAlmostEquals(c.values['neuron4.spikes'], [0.0337])
        c.create()

    def test_binary_recording(self):
        c = BrianRecordingCreator('test_binary_recording.h5')
        self.register_recording_creator(c)
        c.add_brian_recording(os.path.abspath('brian_recordings/aerspikemonitor.aedat'))
        self.assertAlmostEquals(c.values['neuron0.spikes'], [0.0102, 0.0582])
        self.assertAlmostEquals(c.values['neuron1.spikes'], [0.0436])
        self.assertAlmostEquals(c.values['neuron2.spikes'], [0.0201, 0.0681])
        self.assertAlmostEquals(c.values['neuron3.spikes'], [0.0014, 0.0493])
        self.assertAlmostEquals(c.values['neuron4.spikes'], [0.0337])
        c.create()

    def test_corrupted_binary_recording(self):
        c = BrianRecordingCreator('test_binary_recording.h5')
        self.register_recording_creator(c)
        self.assertRaises(IOError, c.add_brian_recording, os.path.abspath('brian_recordings/aerspikemonitor_corrupted.aedat'))

    # TODO: Add tests for add_monitor_...

    def test_model(self):
        c = BrianRecordingCreator('test_model.h5')
        self.register_recording_creator(c)
        c.record_model(os.path.abspath('brian_models/tutorial_model.py'))
        # TODO: make short, deterministic model and run assertEquals
        c.create()


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
