import unittest
import os
import sys
from org.geppetto.recording.creators import SPHRecordingCreator
from org.geppetto.recording.creators.tests.abstest import AbstractTestCase


class BrianRecordingCreatorTestCase(AbstractTestCase):
    """Unittests for the SPHRecordingCreator class."""

    def test_text_recording(self):
        c = SPHRecordingCreator('test_sph_recording.h5')
        self.register_recording_creator(c)

        # TODO: test logic

        c.create()


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test_'
