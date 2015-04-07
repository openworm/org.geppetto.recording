import unittest
import os
import sys
from org.geppetto.recording.creators import SPHRecordingCreator
from org.geppetto.recording.creators.tests.abstest import AbstractTestCase


class SPHRecordingCreatorTestCase(AbstractTestCase):
    """Unittests for the SPHRecordingCreator class."""

    def test_text_recording(self):
        c = SPHRecordingCreator('test_sph_recording.h5')
        self.register_recording_creator(c)

        c.add_recording(os.path.abspath('sph_recordings/transformations/matrix_anchored_31S_'),
                        os.path.abspath('sph_recordings/muscle_signal_evo.txt'),
                        65, 6381, 1, 4)

        # TODO: test values etc

        c.create()


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
