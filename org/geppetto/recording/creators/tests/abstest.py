import unittest
import os
from org.geppetto.recording.creators import RecordingCreator, NeuronRecordingCreator, BrianRecordingCreator, MetaType


class AbstractRecordingCreatorTestCase(unittest.TestCase):
    """This class demonstrates how to create a recording for Geppetto."""

    REMOVE_FILES_AFTER_TEST = True

    def setUp(self):
        self.filenames = []

    def register_recording_creator(self, creator):
        """Register a tests recording creator whose file will be removed after the tests if REMOVE_FILES_AFTER_TEST is set"""
        self.filenames.append(creator.filename)

    def assertAlmostEquals(self, first, second, places=None, msg=None, delta=None):
        """Extended assertAlmostEqual method that works with iterables"""
        if hasattr(first, '__iter__') and hasattr(second, '__iter__'):
            for f, s in zip(first, second):
                unittest.TestCase.assertAlmostEquals(self, f, s, places, msg, delta)
        elif hasattr(first, '__iter__') or hasattr(second, '__iter__'):
            raise TypeError('One of first and second is iterable, the other not')
        else:
            unittest.TestCase.assertAlmostEquals(self, first, second, places, msg, delta)

    def tearDown(self):
        if self.REMOVE_FILES_AFTER_TEST:
            for filename in self.filenames:
                try:
                    os.remove(filename)
                except WindowsError:
                    pass