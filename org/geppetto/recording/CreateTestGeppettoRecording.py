__author__ = 'matteocantarelli'

from org.geppetto.recording.GeppettoRecordingCreator import GeppettoRecordingCreator
from org.geppetto.recording.GeppettoRecordingCreator import MetaType


class CreateTestGeppettoRecording:
    """
    This class demonstrates how to create a recording for Geppetto.

    """
    def __init__(self):
        pass

    @staticmethod
    def example1():
        creator = GeppettoRecordingCreator('example1.h5')
        creator.add_value('a', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b[4].param1', 1, 'float_', 'mV', MetaType.PARAMETER)
        creator.add_value('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
        creator.add_value('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_fixed_time_step_vector(1, 'ms')
        creator.create()

    @staticmethod
    def example2():
        creator = GeppettoRecordingCreator('example2.h5')
        creator.add_value('a', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b.param1', 1, 'float_', 'mV', MetaType.PARAMETER)
        creator.add_value('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
        creator.add_value('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_value('a.b', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
        creator.add_variable_time_step_vector([0.1, 0.2, 0.5, 0.51, 0.52, 0.6, 0.7], 'ms')
        creator.create()
