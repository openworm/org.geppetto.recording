__author__ = 'matteocantarelli'

from org.geppetto.recording.GeppettoRecordingCreator import GeppettoRecordingCreator


class ARecordingCreator():
    """
    This abstract class is meant to be extended by the different recording creators.
    The method create_recording is the main entry point, allowing to specify a path to the model which needs to
     be executed and the output file for the Geppetto recording.

    """
    def __init__(self, simulator):
        self.simulator = simulator

    def create_recording(self, model_to_record, recording_output):
        raise NotImplementedError('You should have implemented this')

    def new_creator(self, filename):
        return GeppettoRecordingCreator(filename,self.simulator)