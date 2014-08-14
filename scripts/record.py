import sys
import os

# add the directory to the python code to system path, so it can also be used without installation
sys.path.insert(0, os.path.abspath(__file__ + '/../..'))
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
            output_filename = model_filename.rsplit('.', 1)[0] + '.h5'

        overwrite = False
        while os.path.exists(output_filename) and not overwrite:
            cmd_in = raw_input("Recording file exists. Overwrite? (y/n) ").lower()
            if cmd_in == 'y' or cmd_in == 'yes':
                overwrite = True
            elif cmd_in == 'n' or cmd_in == 'no':
                output_filename = raw_input("New filename: ")
            else:
                pass  # Show input message again

        if argv[0] == '-neuron':
            print ''
            print '-------------------------------------------------------'
            print 'Recording NEURON model... (close all upcoming windows!)'
            print '-------------------------------------------------------'
            print ''
            c = NeuronRecordingCreator(output_filename, overwrite=True)
            c.record_neuron_model(model_filename)
        elif argv[0] == '-brian':
            print ''
            print '------------------------------------------------------'
            print 'Recording Brian model... (close all upcoming windows!)'
            print '------------------------------------------------------'
            print ''
            c = BrianRecordingCreator(output_filename, overwrite=True)
            c.record_brian_model(model_filename)

        c.create()
        print ''
        print '-----------------------------------------------------------------'
        print 'Finished!\nYour recording is in', os.path.abspath(output_filename)
        print '-----------------------------------------------------------------'
        print ''

        cmd_in = raw_input("Open in live.geppetto.org? (y/n) ").lower()
        if cmd_in == 'y' or cmd_in == 'yes':
            print "This feature is coming soon, stay tuned!"
        elif cmd_in == 'n' or cmd_in == 'no':
            print "Ok, try it next time, it's really awesome!"
    else:
        print 'I do not understand that...'
        print help_msg


if __name__ == '__main__':
    main(sys.argv[1:])