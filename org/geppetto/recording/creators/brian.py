from __future__ import absolute_import
import numpy as np
from org.geppetto.recording.creators import utils
from org.geppetto.recording.creators.base import RecordingCreator, MetaType
from org.geppetto.recording.creators.utils import *

try:
    import brian
    brian_imported = True
except ImportError:
    brian_imported = False


def _assert_brian_imported():
    """Raise an `ImportError` if the brian package could not be imported."""
    if not brian_imported:
        raise ImportError("Could not import brian, install it to proceed (see README for instructions)")


class BrianRecordingCreator(RecordingCreator):
    """
    A RecordingCreator which interfaces to the Brian spiking neural network simulator (www.briansimulator.org).

    Basically, there are three ways to add simulation data from Brian:

    1. Provide a model file for Brian: The creator will execute the simulation, monitor all variables while running
       and add their values to the recording (see `record_brian_model`).
    2. Provide a recording file from Brian (created through `brian.FileSpikeMonitor` or `brian.AERSpikeMonitor`):
       The creator will read it and add all values to the recording (see `add_brian_recording`).
    3. Use the creator inside a Brian simulation and provide a monitor from Brian: The creator will add all the values
       in this monitor to the recording (see `add_spike_monitor`, `add_state_monitor` and
       `add_multi_state_monitor`).

    Some methods need to import the brian package (see README for install instructions).

    Parameters
    ----------
    filename : string
        The path of the recording file that will be created.
    overwrite : boolean, optional
        If `False` (default), raise an error if `filename` exists. If `True`, overwrite it.

    """

    def __init__(self, filename, overwrite=False):
        RecordingCreator.__init__(self, filename, 'Brian', overwrite)

    def add_recording(self, recording_filename, neuron_group_name=None):
        """Read a recording file from the Brian simulator and add its contents to the current recording.

        The recording file may be created using `brian.FileSpikeMonitor` (text format) or `brian.AERSpikeMonitor`
        (binary format).

        Parameters
        ----------
        recording_filename : string
            Path to the recording file from Brian.
        neuron_group_name : string, optional
            Name of the NeuronGroup the recording file belongs to. If supplied, the values will be stored as
            *neuron_group_name.neuron123.variable*, otherwise as *neuron123.variable*.

        Returns
        -------
        BrianRecordingCreator
            The creator itself, to allow chained method calls.

        """
        self._assert_not_created()

        unformatted_variable_name = 'neuron{0}.spikes'
        if neuron_group_name:
            unformatted_variable_name = neuron_group_name + '.' + unformatted_variable_name

        if is_text_file(recording_filename):  # text format from FileSpikeMonitor
            with open(recording_filename, 'r') as r:
                file_content = r.read()
            for i, line in enumerate(file_content.splitlines()):
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
                raise RuntimeError("Could not parse AER file or is empty: " + recording_filename)
            for index, time in zip(indices, times):
                self.add_values(unformatted_variable_name.format(index), time, 'ms', MetaType.EVENT)
        return self

    def add_spike_monitor(self, spike_monitor, neuron_group_name=None):
        """Add all spike times in a SpikeMonitor from Brian to the recording.

        Parameters
        ----------
        spike_monitor : brian.SpikeMonitor
            Monitor whose values to add.
        neuron_group_name : string, optional
            Name of the NeuronGroup the monitor belongs to. If supplied, the values will be stored as
            neuron_group_name.neuron123.variable, otherwise as neuron123.variable.

        Returns
        -------
        BrianRecordingCreator
            The creator itself, to allow chained method calls.

        See also
        --------
        add_state_monitor, add_multi_state_monitor

        """
        self._assert_not_created()
        unformatted_name = 'Neuron{0}.spikes'
        if neuron_group_name:
            unformatted_name = neuron_group_name + '.' + unformatted_name
        for neuron_index, spike_times in spike_monitor.spiketimes.iteritems():
            self.add_values(unformatted_name.format(neuron_index), spike_times, 'ms', MetaType.EVENT)
        return self

    def add_state_monitor(self, state_monitor, neuron_group_name=None):
        """Add all values and time points in a StateMonitor from Brian to the recording.

        Parameters
        ----------
        state_monitor : brian.StateMonitor
            Monitor whose values to add.
        neuron_group_name : string, optional
            Name of the NeuronGroup the monitor belongs to. If supplied, the values will be stored as
            neuron_group_name.neuron123.variable, otherwise as neuron123.variable.

        Returns
        -------
        BrianRecordingCreator
            The creator itself, to allow chained method calls.

        See also
        --------
        add_multi_state_monitor, add_spike_monitor

        """
        self._assert_not_created()
        _assert_brian_imported()

        try:
            times = state_monitor.times
        except IndexError:
            # print '\tNot successful (this is normal for some groups like SpikeGeneratorGroup)'
            # print 'Could not get times'
            pass  # this is normal for some groups like SpikeGeneratorGroup
        else:
            if times is not None and len(times) > 0:
                if self.time_points is None:
                    self.add_time_points(times, 'ms')
                else:
                    if not np.all(times == self.time_points):
                        raise ValueError("StateMonitor has different time points than already defined (maybe you were adding a group after running?)")

        unit = str(state_monitor.unit)[4:]  # state_monitor.unit is something like 1 * V
        unformatted_name = 'Neuron{0}.' + state_monitor.varname
        if neuron_group_name:
            unformatted_name = neuron_group_name + '.' + unformatted_name
        for neuron_index, values in enumerate(state_monitor):
            self.add_values(unformatted_name.format(neuron_index), values, unit, MetaType.STATE_VARIABLE)
        return self

    def add_multi_state_monitor(self, multi_state_monitor, neuron_group_name=None):
        """Add all values and time points in a MultiStateMonitor from Brian to the recording.

        Parameters
        ----------
        multi_state_monitor : brian.MultiStateMonitor
            Monitor whose values to add.
        neuron_group_name : string, optional
            Name of the NeuronGroup the monitor belongs to. If supplied, the values will be stored as
            neuron_group_name.neuron123.variable, otherwise as neuron123.variable.

        Returns
        -------
        BrianRecordingCreator
            The creator itself, to allow chained method calls.

        See also
        --------
        add_state_monitor, add_spike_monitor

        """
        self._assert_not_created()
        for state_monitor in multi_state_monitor.monitors.values():
            # TODO: Can cause memory errors if the state_monitor has many values.
            # Iterating over state_monitor._values solves this, but does not give the correct number of values.
            self.add_state_monitor(state_monitor, neuron_group_name)
        return self

    def record_model(self, model_filename):
        """Execute a Brian simulation, record all variables and add their values to the recording.

        The model file is responsible for running the simulation (by calling Brian's `run` or `Network.run` methods
        at least once). All neuron groups, that are affected by the simulation, will be monitored. For these,
        all state variables and spike times will be recorded. Where possible, the variable names from the the model file
        will be used to store the values.

        Parameters
        ----------
        model_filename : string
            The path to the Python file for the Brian simulation.

        Notes
        -----
        Known limitations:

        - May conflict with debuggers because it uses `sys.settrace`.
        - May not work with exotic Python distributions, use the official CPython version.
        - May not work with custom update algorithms, call Brian's `run` or `Network.run` methods somewhere.
        - Cannot recognize simulation runs that are invoked in external Python scripts, which are executed from the
          model file via the `runpy` module (use `execfile` or `import` instead).

        """
        self._assert_not_created()
        _assert_brian_imported()

        model_abspath = os.path.abspath(model_filename)

        # All these use the same indices. The elements are sorted in creation order of the NeuronGroups
        # (this is needed to handle duplicates).
        neuron_groups = []
        neuron_group_names = []
        spike_monitors = []
        multi_state_monitors = []

        def append_neuron_group(group, name):
            """Append a neuron group, its name and None for its monitors to the lists above."""
            neuron_groups.append(group)
            neuron_group_names.append(name)
            spike_monitors.append(None)
            multi_state_monitors.append(None)

        # TODO: Tracing is also active during the update function in brian. Find out how this can be disabled.
        def trace_model(frame, event, arg):
            if frame.f_code.co_name == 'run' and event == 'call':  # possible call to Brian's `run` or `Network.run`
                # print '\n-------------- Run ----------------'
                # print 'File:', frame.f_code.co_filename
                # print 'Reached run function'
                if 'self' in frame.f_locals:
                    possible_network = frame.f_locals['self']
                    # print '\tFound self:', possible_network
                    try:
                        groups = possible_network.groups
                    except AttributeError:
                        # print '\tIs no network'
                        pass  # not a Network
                    else:
                        # print '\tIs network'
                        for group in groups:
                            try:
                                index = neuron_groups.index(group)
                            except ValueError:  # `group` is not in `neuron_groups`
                                name = 'NeuronGroup' + str(id(group))
                                append_neuron_group(group, name)
                                index = -1

                            # print '\tRecognized neuron group:', neuron_group_names[index]
                            if not spike_monitors[index]:
                                spike_monitors[index] = brian.SpikeMonitor(neuron_groups[index], record=True)
                            if not multi_state_monitors[index]:
                                multi_state_monitors[index] = brian.MultiStateMonitor(neuron_groups[index], record=True)
                            possible_network.add(spike_monitors[index])
                            possible_network.add(multi_state_monitors[index])
                            # print '\tAdded its monitors'
                        return  # do not trace during simulation run
            elif os.path.abspath(frame.f_code.co_filename) == model_abspath:
                # print '\n-------------- In Model ----------------'
                # print 'File:', frame.f_code.co_filename
                # Recognize all NeuronGroup's created in the model file or in a file that is run from the model file
                # via execfile or import (not via runpy!).
                for name, possible_neuron_group in frame.f_locals.iteritems():
                    if isinstance(possible_neuron_group, brian.NeuronGroup) and possible_neuron_group not in neuron_groups:
                        try:
                            index = neuron_group_names.index(name)
                        except ValueError:
                            pass
                        else:  # name is already occupied by another neuron group
                            neuron_group_names[index] += id(neuron_group)
                            name += id(possible_neuron_group)
                        append_neuron_group(possible_neuron_group, name)
                return trace_model
            # elif event == 'call' and frame.f_code.co_filename == 'update':
            #     print '\n-------------- Update ----------------'
            #     print frame.f_code.co_filename
            else:
                # print '\n-------------- End Tracing ----------------'
                # print frame.f_code.co_filename
                return  # do not trace outside the scope of the model file

        sys.settrace(trace_model)
        utils.run_as_script(model_abspath)
        sys.settrace(None)

        # Process all created monitors.
        for neuron_group_name, neuron_group, spike_monitor, multi_state_monitor in zip(neuron_group_names, neuron_groups, spike_monitors, multi_state_monitors):
            if spike_monitor:
                self.add_spike_monitor(spike_monitor, neuron_group_name)
            if multi_state_monitor:
                self.add_multi_state_monitor(multi_state_monitor, neuron_group_name)
