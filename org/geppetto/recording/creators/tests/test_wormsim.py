import unittest
import os
import sys
from org.geppetto.recording.creators import WormSimRecordingCreator
from org.geppetto.recording.creators.tests.abstest import AbstractTestCase


class WormSimRecordingCreatorTestCase(AbstractTestCase):
    """Unittests for the WormSimRecordingCreator class."""

    def test_text_recording(self):
        c = WormSimRecordingCreator('test_wormsim_recording.h5')
        self.register_recording_creator(c)

        c.add_recording(os.path.abspath('wormsim_recordings/transformations/matrix_anchored_31S_'),
                        os.path.abspath('wormsim_recordings/muscle_signal_evo.txt'),
                        65, 6381, 1, 4)

        # Test times tep and unit
        self.assertEquals(c.time_step, 0.000005)
        self.assertEquals(c.time_unit, 's')

        # Test some values
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][0], 0.575365)
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][1], 0.57586)
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][2], 0.576354)
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][3], 0.576848)

        # TODO: test transformations

        c.create()

    def test_text_recording_with_downsampling(self):
        c = WormSimRecordingCreator('test_wormsim_recording.h5')
        self.register_recording_creator(c)

        c.add_recording(os.path.abspath('wormsim_recordings/transformations/matrix_anchored_31S_'),
                        os.path.abspath('wormsim_recordings/muscle_signal_evo.txt'),
                        65, 6381, 10, 4)

        # Test times tep and unit
        self.assertEquals(c.time_step, 0.000005*10)
        self.assertEquals(c.time_unit, 's')

        # Test some values
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][0], 0.575365)
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][1], 0.580304)
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][2], 0.585235)
        self.assertEquals(c.values['wormsim.muscle_0.mechanical.SIMULATION_TREE.activation'][3], 0.590158)

        # TODO: test transformations

        c.create()

if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
