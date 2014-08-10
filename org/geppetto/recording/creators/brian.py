from __future__ import absolute_import
import numpy as np
import os
import time
from org.geppetto.recording.creators.base import RecordingCreator, MetaType, is_text_file


_brian_not_installed_error = ImportError("You have to install the brian package to use this method")


class BrianRecordingCreator(RecordingCreator):
    """
    Work in progress...
    """

    def __init__(self, filename):
        RecordingCreator.__init__(self, filename, 'Brian')

    def add_brian_recording(self, recording_file, neuron_group_label=None):
        # TODO: Use variable_labels_prefix instead of neuron_group_label?
        """
        Read a file that contains a recording from the brian simulator and add its contents to the current recording.
        The file can be created using brian's FileSpikeMonitor or AERSpikeMonitor.

        Parameters
        ----------
        recording_file : string
            Path to the file that should be added
        neuron_group_label : string
            Label for the neuron group of these values. If supplied, the values will be stored as `neuron_group_label.neuron123.spikes`, otherwise as `neuron123.spikes`, for example.
        """

        # TODO: Add exceptions if file can not be parsed
        if is_text_file(recording_file):
            with open(recording_file, 'r') as r:
                file_content = r.read()
                r.close()

                lines = file_content.splitlines()
                # Extract indices and spike times in a similar manner to brian.load_aer() below
                indices = np.empty(len(lines), dtype='int')
                times = np.empty(len(lines))
                for i, line in enumerate(lines):
                    colon = line.find(',')
                    indices[i] = int(line[:colon])
                    times[i] = float(line[colon+2:])
        else:  # binary format
            try:
                import brian
            except ImportError:
                raise _brian_not_installed_error
            try:
                indices, times = brian.load_aer(recording_file)
            except Exception:
                raise ValueError("Could not parse AER file: " + recording_file)

        # TODO: Should empty files be neglected or should an error be raised?
        if len(indices) == 0 or len(times) == 0:
            raise ValueError("Could not parse file or file is empty: " + recording_file)

        spikes = {}
        for index, time in zip(indices, times):
            str_index = str(index)
            if not str_index in spikes:
                spikes[str_index] = []
            spikes[str_index].append(time)

        for index, spike_list in spikes.items():
            # TODO: Think about alternative naming for neuron
            neuron_label = 'neuron' + str(index) + '.spikes'
            if neuron_group_label:
                neuron_label = neuron_group_label + '.' + neuron_label
            self.add_values(neuron_label, spike_list, 'ms', MetaType.EVENT)

    def record_brian_model(self, model_file, temp_file='temp_model.py', overwrite_temp_file=True, remove_temp_file=False):
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
                        group_name = 'UnknownNeuronGroup'  # TODO: format
                    print '    Group is not monitored yet, its name was found to be:', group_name
                    monitored_groups[group_name] = group
                    spike_monitors[group_name] = SpikeMonitor(group, record=True)
                    multi_state_monitors[group_name] = MultiStateMonitor(group, record=True)

                network.add(spike_monitors[group_name])  # `add` automatically filters out duplicates
                network.add(multi_state_monitors[group_name])

'''

        # TODO: Find out subgroups and store their neurons under different labels

        if os.path.exists(temp_file) and not overwrite_temp_file:
            raise IOError("Temporary file already exists, set the overwrite flag to proceed")

        # Create a temporary file that contains the model and some additions to set up the monitors for recording.
        with open(temp_file, 'w') as temp:
            temp.write(text_to_prepend)
            with open(model_file, 'r') as model:
                for line in model:
                    # TODO: Maybe omit lines with # or ''' or """ before run or where run is in a string (although it doesn't do any harm functionally)
                    if 'run' in line:
                        stripped_line = line
                        indentation = ''
                        while stripped_line.startswith((' ', '\t')):
                            indentation += stripped_line[:1]
                            stripped_line = stripped_line[1:]

                        if stripped_line.startswith('run'):  # simple run()
                            temp.write(indentation + "default_magic_network = MagicNetwork(verbose=False, level=2)\n")
                            temp.write(indentation + "add_monitors_to_all_networks(locals())\n")
                            temp.write(indentation + "default_magic_network." + stripped_line)
                        else:  # may be Network.run()
                            temp.write(indentation + "add_monitors_to_all_networks(locals())\n")
                            temp.write(line)
                    else:
                        temp.write(line)

        # Execute the temporary file and retrieve the dictionaries that store the neuron groups and monitors.
        vars = {}
        execfile(temp_file, vars)
        monitored_groups = vars['monitored_groups']
        spike_monitors = vars['spike_monitors']
        multi_state_monitors = vars['multi_state_monitors']

        # print 'Found {0} neuron group(s) in total'.format(len(monitored_groups))
        # for name_neuron_group, group in monitored_groups.items():
        #     print '    {0} with {1} neurons'.format(name_neuron_group, len(group))

        start_time = time.time()
        print 'Populating file...'
        for name_neuron_group, spike_monitor in spike_monitors.iteritems():
            for neuron_index, spike_times in spike_monitor.spiketimes.iteritems():
                self.add_values(name_neuron_group + '.neuron' + str(neuron_index) + '.spikes', spike_times, 'ms', MetaType.EVENT)

        for name_neuron_group, multi_state_monitor in multi_state_monitors.iteritems():
            if self.time is None:
                self.add_time(multi_state_monitor.times / brian.ms, 'ms')
            elif any(self.time != state_monitor.times):
                raise ValueError("Your model contains multiple time vectors, this is not supported yet by the Geppetto recording format.")
            for variable_name, state_monitor in multi_state_monitor.iteritems():
                # TODO: Iterating over the state monitor can cause a MemoryError for many steps and 32-bit versions of Python. Iterating over state_monitor._values solves this, but does not give the correct number of values.
                # TODO: Try to find a workaround for this, or at least except the MemoryError and show a warning to use 64-bit version of Python (and Brian! -> Is this possible?).
                unit = str(state_monitor.unit)[4:]
                unformatted_name = name_neuron_group + '.neuron{0}.' + variable_name
                for neuron_index, variable_values in enumerate(state_monitor):
                    self.add_values(unformatted_name.format(neuron_index), variable_values, unit, MetaType.STATE_VARIABLE)
                print 'Added variable:', variable_name

        print 'Time to populate file:', time.time() - start_time
