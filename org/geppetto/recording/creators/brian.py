from __future__ import absolute_import
import numpy as np
import os
import time
import re
import runpy
from org.geppetto.recording.creators.base import RecordingCreator, MetaType, is_text_file


_brian_not_installed_error = ImportError("You have to install the brian package to use this method")


class BrianRecordingCreator(RecordingCreator):
    """
    A RecordingCreator which interfaces to the Brian spiking neural network simulator (www.briansimulator.org).

    More info to come...

    Parameters
    ----------
    filename : string
        The path to the recording file that will be created.
    overwrite : boolean, optional
        Set True to overwrite an existing file.

    """

    def __init__(self, filename, overwrite=False):
        RecordingCreator.__init__(self, filename, 'Brian', overwrite)

    def add_brian_recording(self, recording_filename, neuron_group_name=None):
        # TODO: Use variable_labels_prefix instead of neuron_group_name?
        """Read a recording file from the Brian simulator and add its contents to the current recording.

        Recording files from Brian contain the spike times for all neurons in one NeuronGroup.
        They can be created using Brian's FileSpikeMonitor (text format) or AERSpikeMonitor (binary format).
        If `neuron_group_name` is supplied, the spike times will be stored as neuron_group_name.neuron123.spikes,
        otherwise simply as neuron123.spikes.

        Parameters
        ----------
        recording_filename : string
            Path to the file that holds the Brian recording.
        neuron_group_name : string
            Name of the NeuronGroup this recording belongs to. If supplied, the spike times will be stored under
            neuron_group_name.neuron123.spikes.

        """
        self._assert_not_created()

        unformatted_variable_name = 'neuron{0}.spikes'
        if neuron_group_name:
            unformatted_variable_name = neuron_group_name + '.' + unformatted_variable_name

        if is_text_file(recording_filename):  # text format from FileSpikeMonitor
            with open(recording_filename, 'r') as r:
                file_content = r.read()
            lines = file_content.splitlines()

            for i, line in enumerate(lines):
                colon = line.find(',')
                index = int(line[:colon])
                time = float(line[colon+2:])
                self.add_values(unformatted_variable_name.format(index), time, 'ms', MetaType.EVENT)
        else:  # binary format from AERSpikeMonitor
            try:
                import brian
            except ImportError:
                raise _brian_not_installed_error

            try:
                indices, times = brian.load_aer(recording_filename)
            except Exception as e:
                raise IOError("Could not parse AER file: " + e.message)
            if len(indices) == 0 or len(times) == 0:
                raise ValueError("Could not parse file or file is empty: " + recording_filename)

            for index, time in zip(indices, times):
                self.add_values(unformatted_variable_name.format(index), time, 'ms', MetaType.EVENT)
        return self

    def record_brian_model(self, model_filename, temp_filename=None, overwrite_temp_file=True, remove_temp_file=True):
        """Simulate a Brian model, record all variables and add their values to the recording.

        More info to come...

        Parameters
        ----------
        model_filename : string
            The path to the Python file for the Brian simulation.
        temp_filename : string, optional
            The path to the temporary file where the modified model information is written. If None (default), the file
            will be stored alongside your model file (may be necessary if you access other files from you model).
        overwrite_temp_file : boolean, optional
            If True, overwrite a previous version of the temporary file (default).
        remove_temp_file : boolean, optional
            If True, remove the temporary file after the simulation was run (default).

        """
        self._assert_not_created()
        # TODO: Include runtime and timestep to run the model from outside.

        try:
            import brian
            from brian import Network, NeuronGroup, SpikeMonitor, MultiStateMonitor
        except ImportError:
            raise _brian_not_installed_error

        # TODO: Rename variables so that there are no name conflicts with variables in the model file
        # TODO: Access brian classes via brian. to avoid name conflicts?
        text_to_prepend = '''
from brian import Network, MagicNetwork, NeuronGroup, SpikeMonitor, MultiStateMonitor


monitored_groups = {}
spike_monitors = {}
multi_state_monitors = {}


def get_variable_name(object, variables_dict):
    for name, var_object in variables_dict.iteritems():
        if var_object is object:
            # TODO: What if the object is stored under multiple variables?
            return name
    raise IndexError("The object \\"{0}\\" could not be found in the variables dictionary".format(object))


def get_key(dict, value):
    for key, val in dict.iteritems():
        if val is value:
            return key
    raise IndexError("The value \\"{0}\\" could not be found in the dictionary".format(value))


def add_monitors_to_all_networks(variables_dict):
    for network_name, network in variables_dict.iteritems():
        if isinstance(network, Network):
            print 'Processing network:', network_name
            for group in network.groups:
                if group in monitored_groups.values():
                    group_name = get_key(monitored_groups, group)
                    print '    Group is already monitored, its name is:', group_name
                else:
                    try:
                        group_name = get_variable_name(group, variables_dict)  # TODO: Maybe get outer_locals right here.
                    except IndexError:
                        group_name = 'NeuronGroup' + str(id(group))
                    print '    Group is not monitored yet, its name was found to be:', group_name
                    monitored_groups[group_name] = group
                    spike_monitors[group_name] = SpikeMonitor(group, record=True)
                    multi_state_monitors[group_name] = MultiStateMonitor(group, record=True)

                network.add(spike_monitors[group_name])  # `add` automatically filters out duplicates
                network.add(multi_state_monitors[group_name])

'''

        # TODO: Find out subgroups and store their neurons under different labels

        if temp_filename is None:
            dirname, filename = os.path.split(os.path.abspath(model_filename))
            temp_filename = os.path.join(dirname, 'RECORD_' + filename.rsplit('.', 1)[0] + '.py')
        if os.path.exists(temp_filename) and not overwrite_temp_file:
            raise IOError("Temporary file already exists, set the overwrite flag to proceed")
        # Create a temporary file that contains the model and some additions to set up the monitors for recording.
        # TODO: Maybe try to make this without a temporary file, using exec
        with open(temp_filename, 'w') as temp_file:
            temp_file.write(text_to_prepend)
            with open(model_filename, 'r') as model_file:
                for line in model_file:
                    # TODO: Maybe omit lines with # or ''' or """ before run or where run is in a string (although it doesn't do any harm functionally)
                    # TODO: Refactor this
                    # TODO: What if additional model files are being called?
                    # TODO: Instead of searching for run commands, use sys.settrace (or sth equivalent) to check at each execution step if the monitors are set up. This could also be done from here, without the need to create a temporary model file.
                    if 'run' in line:
                        stripped_line = line
                        indentation = ''
                        while stripped_line.startswith((' ', '\t')):
                            indentation += stripped_line[:1]
                            stripped_line = stripped_line[1:]

                        # TODO: How to handle multiline commands?
                        if re.match(r'run[ \t]*\(', stripped_line):  # simple run (line starts with something like 'run (' )
                            temp_file.write(indentation + "default_magic_network = MagicNetwork(verbose=False, level=2)\n")
                            temp_file.write(indentation + "add_monitors_to_all_networks(locals())\n")
                            temp_file.write(indentation + "default_magic_network." + stripped_line)
                        elif re.search(r'\.[ \t]*run[ \t]*\(', stripped_line):  # maybe Network.run (line starts with something like 'net. run (' )
                            temp_file.write(indentation + "add_monitors_to_all_networks(locals())\n")
                            temp_file.write(line)
                    else:
                        temp_file.write(line)

        # Execute the temporary file and retrieve the dictionaries that store the neuron groups and monitors.
        #vars = {'__name__': '__main__', '__file__': os.path.abspath(temp_filename)}
        #execfile(temp_filename, vars)
        vars = runpy.run_path(os.path.abspath(temp_filename), run_name='__main__')
        monitored_groups = vars['monitored_groups']
        spike_monitors = vars['spike_monitors']
        multi_state_monitors = vars['multi_state_monitors']

        if remove_temp_file:
            try:
                os.remove(temp_filename)
            except:
                print 'Could not remove temporary file:', os.path.abspath(temp_filename)

        # print 'Found {0} neuron group(s) in total'.format(len(monitored_groups))
        # for name_neuron_group, group in monitored_groups.items():
        #     print '    {0} with {1} neurons'.format(name_neuron_group, len(group))

        start_time = time.time()
        print 'Populating file...'
        for neuron_group_name, spike_monitor in spike_monitors.iteritems():
            print 'Adding spikes for neuron group', neuron_group_name
            unformatted_name = neuron_group_name + '.Neuron{0}.spikes'
            for neuron_index, spike_times in spike_monitor.spiketimes.iteritems():
                self.add_values(unformatted_name.format(neuron_index), spike_times, 'ms', MetaType.EVENT)

        times = None
        for neuron_group_name, multi_state_monitor in multi_state_monitors.iteritems():
            print 'Processing neuron group', neuron_group_name
            print '\tGetting time points'
            try:
                current_times = multi_state_monitor.times / brian.ms
            except IndexError:
                print '\tNot successful (this is normal for some groups like SpikeGeneratorGroup)'
            else:
                if times is None:
                    times = current_times
                elif any(times != current_times):
                    raise ValueError("Your neuron groups operate with different times (maybe you were adding a group after running?), this is not supported by Geppetto.")
            for variable_name, state_monitor in multi_state_monitor.iteritems():
                # TODO: Iterating over the state monitor can cause a MemoryError for many steps and 32-bit versions of Python. Iterating over state_monitor._values solves this, but does not give the correct number of values.
                # TODO: Try to find a workaround for this, or at least except the MemoryError and show a warning to use 64-bit version of Python (and Brian! -> Is this possible?).
                print '\tAdding variable', variable_name
                unit = str(state_monitor.unit)[4:]
                unformatted_name = neuron_group_name + '.neuron{0}.' + variable_name
                for neuron_index, variable_values in enumerate(state_monitor):
                    self.add_values(unformatted_name.format(neuron_index), variable_values, unit, MetaType.STATE_VARIABLE)

        if times is not None:
            self.add_time_points(times, 'ms')
            print 'Added time points'
        else:
            print 'No time points found'

        print 'Time to populate file:', time.time() - start_time
        return self

