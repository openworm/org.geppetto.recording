__author__ = 'matteocantarelli'

from org.geppetto.recording.ARecordingCreator import ARecordingCreator


class NESTRecordingCreator(ARecordingCreator):
    def __init__(self):
        ARecordingCreator.__init__(self, 'NEST')

    def create_recording(self, model_to_record, recording_output):
        return ARecordingCreator.create_recording(self, model_to_record, recording_output)
