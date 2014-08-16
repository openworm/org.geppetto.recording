from __future__ import absolute_import
import numpy as np
import os
import time
import re
import runpy
import sys
from org.geppetto.recording.creators.base import RecordingCreator, MetaType, is_text_file

try:
    import brian
    brian_imported = True
except ImportError:
    brian_imported = False


def _assert_brian_imported():
    if not brian_imported:
        raise ImportError("You have to install the brian package to use this method")


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
            _assert_brian_imported()
            try:
                indices, times = brian.load_aer(recording_filename)
            except Exception as e:
                raise IOError("Could not parse AER file: " + e.message)
            if len(indices) == 0 or len(times) == 0:
                raise ValueError("Could not parse file or file is empty: " + recording_filename)

            for index, time in zip(indices, times):
                self.add_values(unformatted_variable_name.format(index), time, 'ms', MetaType.EVENT)
        return self

    # TODO: Maybe change this and the other methods to record_model (without brian)
    def record_brian_model_by_trace(self, model_filename):
        self._assert_not_created()
        _assert_brian_imported()

        # All these use the same indices. The elements are sorted in creation order of the NeuronGroups
        # (this is needed to handle duplicates).
        neuron_groups = []
        neuron_group_names = []
        spike_monitors = []
        multi_state_monitors = []

        def append_neuron_group(group, name):
            neuron_groups.append(group)
            neuron_group_names.append(name)
            spike_monitors.append(None)
            multi_state_monitors.append(None)

        def trace_model(frame, event, arg):
            # Recognize all NeuronGroup's created in the model file or in a file that is run from the model file
            # via execfile or import (not via runpy!).
            if os.path.abspath(frame.f_code.co_filename) == model_abspath:
                for name, var in frame.f_locals.iteritems():
                    if isinstance(var, brian.NeuronGroup) and var not in neuron_groups:
                        try:
                            print 'Found new NeuronGroup:', name, var
                        except:
                            # TODO: Is probably unnecessary
                            print '\tCannot print NeuronGroup'
                        else:
                            append_neuron_group(var, name)

            # Recognize a call to brian's `run` or `Network.run` method.
            if event == 'call' and frame.f_code.co_name == 'run':
                print 'Reached run function'
                if 'self' in frame.f_locals:
                    possible_network = frame.f_locals['self']
                    print '\tFound self:', possible_network
                    try:
                        groups = possible_network.groups
                    except AttributeError:
                        print '\tIs no network'
                        pass  # not a Network
                    else:
                        print '\tIs network'
                        for group in groups:
                            try:
                                index = neuron_groups.index(group)
                            except ValueError:  # `group` is not in `neuron_groups`
                                name = 'UnknownNeuronGroup' + str(id(group))
                                append_neuron_group(group, name)
                                index = -1

                            print '\tRecognized neuron group:', neuron_group_names[index]
                            if not spike_monitors[index]:
                                spike_monitors[index] = brian.SpikeMonitor(neuron_groups[index], record=True)
                            if not multi_state_monitors[index]:
                                multi_state_monitors[index] = brian.MultiStateMonitor(neuron_groups[index], record=True)
                            possible_network.add(spike_monitors[index])
                            possible_network.add(multi_state_monitors[index])
                            print '\tAdded its monitors'
                        return None  # do not trace during simulation run
            return trace_model

        model_abspath = os.path.abspath(model_filename)
        model_dirname = os.path.dirname(model_abspath)

        # Append directory of the model file to system path (enables the model file to import local modules)
        # and change Python's working directory to this directory (enables the model file to execute local files).
        sys.path.append(model_dirname)
        old_cwd = os.getcwd()
        os.chdir(model_dirname)

        sys.settrace(trace_model)
        runpy.run_path(model_abspath, run_name='__main__', )
        sys.settrace(None)

        # Revert the changes affecting the system path and working directory (see above).
        os.chdir(old_cwd)
        sys.path.remove(model_dirname)

        # Process all created monitors.
        for neuron_group_name, neuron_group, spike_monitor, multi_state_monitor in zip(neuron_group_names, neuron_groups, spike_monitors, multi_state_monitors):
            if spike_monitor:
                self.add_spike_monitor(spike_monitor, neuron_group_name)
            if multi_state_monitor:
                self.add_multi_state_monitor(multi_state_monitor, neuron_group_name)

    def add_spike_monitor(self, spike_monitor, neuron_group_name=None):
        """Add all spike times in a SpikeMonitor from Brian to the recording."""
        # TODO: Maybe just store the monitors here and process them during create; this way, they could be added before actually running the simulation.
        self._assert_not_created()
        unformatted_name = 'Neuron{0}.spikes'
        # TODO: spike_monitor.P gives the NeuronGroup -> use its id as name here if neuron_group_name is empty?
        # TODO: Maybe make neuron_group_name is False -> no neuron group, is True -> use id, is string -> use that one
        if neuron_group_name:
            unformatted_name = neuron_group_name + '.' + unformatted_name
        for neuron_index, spike_times in spike_monitor.spiketimes.iteritems():
            # TODO: Are spike times always in ms?
            # TODO: Can spike_times be divided by brian.ms?
            self.add_values(unformatted_name.format(neuron_index), spike_times, 'ms', MetaType.EVENT)
        return self

    def add_state_monitor(self, state_monitor, neuron_group_name=None):
        """Add all values and times in a StateMonitor from Brian to the recording."""
        self._assert_not_created()
        _assert_brian_imported()

        try:
            times = state_monitor.times / brian.ms  # TODO: Can times be None if nothing was added to the monitor yet?
        except IndexError:
            #print '\tNot successful (this is normal for some groups like SpikeGeneratorGroup)'
            print 'Could not get times'
            pass  # this is normal for some groups like SpikeGeneratorGroup
        else:
            if times is not None and len(times) > 0:
                if self.time_points is None:
                    self.add_time_points(times, 'ms')
                else:
                    if not np.all(times == self.time_points):  # TODO: Check that this does not throw errors.
                        raise ValueError("StateMonitor has different time points than already defined (maybe you were adding a group after running?).")

        unit = str(state_monitor.unit)[4:]  # `state_monitor.unit` is something like `1 * V`
        unformatted_name = 'Neuron{0}.' + state_monitor.varname
        if neuron_group_name:
            unformatted_name = neuron_group_name + '.' + unformatted_name
        for neuron_index, values in enumerate(state_monitor):
            self.add_values(unformatted_name.format(neuron_index), values, unit, MetaType.STATE_VARIABLE)
        return self

    def add_multi_state_monitor(self, multi_state_monitor, neuron_group_name=None):
        """Add all values and times in a MultiStateMonitor from Brian to the recording."""
        self._assert_not_created()
        for state_monitor in multi_state_monitor.monitors.values():
            # TODO: Iterating over the state monitor can cause a MemoryError for many steps and 32-bit versions of Python. Iterating over state_monitor._values solves this, but does not give the correct number of values.
            # TODO: Try to find a workaround for this, or at least except the MemoryError and show a warning to use 64-bit version of Python (and Brian! -> Is this possible?).
            self.add_state_monitor(state_monitor, neuron_group_name)
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
            will be stored alongside your model file (recommended if your model uses multiple files).
        overwrite_temp_file : boolean, optional
            If True, overwrite a previous version of the temporary file (default).
        remove_temp_file : boolean, optional
            If True, remove the temporary file after the simulation was run (default).

        """
        # TODO: Maybe include runtime and timestep to run the model from outside.
        self._assert_not_created()
        _assert_brian_imported()

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

        if temp_filename:
            temp_abspath = os.path.abspath(temp_filename)
        else:
            dirname, filename = os.path.split(os.path.abspath(model_filename))
            temp_abspath = os.path.join(dirname, 'RECORD_' + filename.rsplit('.', 1)[0] + '.py')

        if os.path.exists(temp_abspath) and not overwrite_temp_file:
            raise IOError("Temporary file already exists, set the overwrite flag to proceed")
        # Create a temporary file that contains the model and some additions to set up the monitors for recording.
        # TODO: Maybe try to make this without a temporary file, using exec
        with open(temp_abspath, 'w') as temp_file:
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

        #vars = {'__name__': '__main__', '__file__': os.path.abspath(temp_filename)}
        #execfile(temp_filename, vars)

        # Append directory of the model file to system path (enables the model file to import local modules)
        # and change Python's working directory to this directory (enables the model file to execute local files).
        model_abspath = os.path.abspath(model_filename)
        model_dirname = os.path.dirname(model_abspath)
        sys.path.append(model_dirname)
        old_cwd = os.getcwd()
        os.chdir(model_dirname)
        try:
            vars = runpy.run_path(os.path.abspath(temp_filename), run_name='__main__', )
        finally:
            if remove_temp_file:
                try:
                    os.remove(temp_abspath)
                except:
                    print 'Could not remove temporary file:', temp_abspath

        # Revert the changes affecting the system path and working directory (see above).
        os.chdir(old_cwd)
        sys.path.remove(model_dirname)

        monitored_groups = vars['monitored_groups']
        spike_monitors = vars['spike_monitors']
        multi_state_monitors = vars['multi_state_monitors']

        # print 'Found {0} neuron group(s) in total'.format(len(monitored_groups))
        # for name_neuron_group, group in monitored_groups.items():
        #     print '    {0} with {1} neurons'.format(name_neuron_group, len(group))

        start_time = time.time()
        print 'Populating file...'

        # TODO: Maybe refactor to one loop.
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
                else:
                    try:
                        times_differ = any(times != current_times)
                    except TypeError:
                        print times
                        print current_times
                        times_differ = times != current_times
                    if times_differ:
                        raise ValueError("Your neuron groups operate with different times (maybe you were adding a group after running?), this is not supported by Geppetto.")
            for variable_name, state_monitor in multi_state_monitor.iteritems():
                # TODO: Iterating over the state monitor can cause a MemoryError for many steps and 32-bit versions of Python. Iterating over state_monitor._values solves this, but does not give the correct number of values.
                # TODO: Try to find a workaround for this, or at least except the MemoryError and show a warning to use 64-bit version of Python (and Brian! -> Is this possible?).
                print '\tAdding variable', variable_name
                unit = str(state_monitor.unit)[4:]
                unformatted_name = neuron_group_name + '.Neuron{0}.' + variable_name
                for neuron_index, variable_values in enumerate(state_monitor):
                    self.add_values(unformatted_name.format(neuron_index), variable_values, unit, MetaType.STATE_VARIABLE)

        if times is not None:
            self.add_time_points(times, 'ms')
            print 'Added time points'
        else:
            print 'No time points found'

        print 'Time to populate file:', time.time() - start_time
        return self

