__author__ = 'matteocantarelli'

from lems.run import main
from org.geppetto.recording.ARecordingCreator import ARecordingCreator


class LEMSRecordingCreator(ARecordingCreator):
    def __init__(self):
        ARecordingCreator.__init__(self, 'LEMS')
