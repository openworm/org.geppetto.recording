import sys
import os
sys.path.insert(0, os.path.abspath('..'))
from org.geppetto.recording.creators import NeuronRecordingCreator, BrianRecordingCreator

help_msg = """
Usage:
------

record -neuron modelfile.hoc [recordingfile.h5]
    Execute a NEURON model (experimental, only hoc!) and
    store the simulation data in a Geppetto recording.

record -brian modelfile.py [recordingfile.h5]
    Execute a Brian model and
    store the simulation data in a Geppetto recording.

record help
    Show this help message.
"""


def main(argv):
    if not argv:
        print help_msg
    elif argv[0] == help_msg:
        print help_msg
    elif argv[0] == '-neuron' or argv[0] == '-brian':
        try:
            model_filename = argv[1]
        except IndexError:
            print 'Please give me a model file.'
            sys.exit()

        try:
            output_filename = argv[2]
        except IndexError:
            output_filename = model_filename.rstrip('.py').rstrip('.hoc') + '.h5'

        if argv[0] == '-neuron':
            print 'Recording NEURON model... (close all upcoming windows!)'
            c = NeuronRecordingCreator(output_filename)
            c.record_neuron_model(model_filename)
        elif argv[0] == '-brian':
            print 'Recording Brian model...'
            c = BrianRecordingCreator(output_filename)
            c.record_brian_model(model_filename)

        c.create()
        print '---'
        print 'Finished! Your recording is in', output_filename
    else:
        print 'I do not understand that...'
        print help_msg


if __name__ == '__main__':
    main(sys.argv[1:])