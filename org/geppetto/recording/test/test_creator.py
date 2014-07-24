__author__ = 'matteocantarelli'

from org.geppetto.recording import GeppettoRecordingCreator, MetaType
import unittest

class CreateTestGeppettoRecording(unittest.TestCase):
    """This class demonstrates how to create a recording for Geppetto."""

    def test_fixed_timestep(self):
        creator = GeppettoRecordingCreator('example1.h5')
        creator.add_value('a.w', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b.c.param', 1, 'float_', 'mV', MetaType.PARAMETER)
        creator.add_value('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
        creator.add_value('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_fixed_time_step_vector(1, 'ms')
        creator.add_metadata('string_metadata', 'description or link')
        creator.add_metadata('float_metadata', 1.0)
        creator.add_metadata('boolean_metadata', True)
        creator.create()

    def test_variable_timestep(self):
        creator = GeppettoRecordingCreator('example2.h5')
        creator.add_value('a.w', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b.c.param', 1, 'float_', 'mV', MetaType.PARAMETER)
        creator.add_value('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
        creator.add_value('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_variable_time_step_vector([0.1, 0.2, 0.5, 0.51, 0.52, 0.6, 0.7], 'ms')
        creator.add_metadata('string_metadata', 'description or link')
        creator.create()


if __name__ == '__main__':
    unittest.main()  # automatically executes all methods above that start with 'test'
