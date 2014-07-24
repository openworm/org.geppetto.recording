__author__ = 'matteocantarelli, Johannes Rieke'

import h5py
import numpy as np
from enum import Enum


MetaType = Enum("STATE_VARIABLE", "PARAMETER", "PROPERTY")


class GeppettoRecordingCreator:
    """
    This class allows to create a recording for Geppetto.

    There should be one instance of this class per recording created.
    In order to create a recording instantiate this class specifying the filename of the recording you wish to create
     and the simulator used to produce the recording.
    The method add_value allows to add a recording for a given variable by specifying its path.
    It is possible to call add_value multiple times for the same path (values will be appended) or call it once
     specifying a list of values.
    Once all the values have been appended call either add_fixed_time_step_vector or  add_variable_time_step_vector
     to generate a vector with values for time.
    The values provided with the method add_value will be associated with the corresponding time step at the same index
     in the time vector.
    Additionally, global metadata of various types can be added through add_metadata.
    Once all the values have been added and the time vector generated it is possible to create the recording
     by calling create().

    Example:
    time [0.1, 0.2, 0.3, 0.4, 0.5]
    cell
        v1 [0.65, 0.66, 0.67, 0.68, 0.69]
        v2 [0.20, 0.20, 0.21, 0.22, 0.23]
    0.67 will be the value of cell.v1 at 0.3ms
    0.22 will be the value of cell.v2 at 0.4ms

    Snippet:
    creator = GeppettoRecordingCreator('example1.h5')
    creator.add_value('a', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_value('a', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_value('a.b', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_value('a.b.param1', 1, 'float_', 'mV', MetaType.PARAMETER)
    creator.add_value('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
    creator.add_value('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_value('a.b', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_fixed_time_step_vector(1, 'ms')
    creator.add_metadata('string_metadata', 'description or link')
    creator.add_metadata('float_metadata', 1.0)
    creator.add_metadata('boolean_metadata', True)
    creator.create()
    """
    def __init__(self, filename, simulator='Not specified'):
        self.f = h5py.File(filename, 'a')
        self.values = {}
        self.units = {}
        self.data_types = {}
        self.meta_types = {}
        self.time = None
        self.time_unit = None
        self.simulator = simulator
        self.metadata = {}

    def add_value(self, path_string, value, data_type, unit, meta_type):
        if not unit:
            raise Exception('Supply a unit and be a good boy')
        if not meta_type:
            raise Exception('Supply the meta type and be a good boy')
        if not data_type:
            raise Exception('Supply the numpy data type and be a good boy')
        if not data_type:
            raise Exception('Supply the value and be a good boy')
        if path_string not in self.values.keys():
            self.values[path_string] = []
        if isinstance(value, list):
            self.values.get(path_string).extend(value)
        else:
            self.values.get(path_string).append(value)
        self.units[path_string] = unit
        self.data_types[path_string] = data_type
        self.meta_types[path_string] = meta_type

    def __get_max_length(self):
        max_length = 0
        for v in self.values.values():
            max_length = max(max_length, len(v))
        return max_length

    def add_fixed_time_step_vector(self, time_step, unit):
        if not unit:
            raise Exception('Supply a unit and be a good boy')
        if not time_step:
            raise Exception('Supply the time step and be a good boy')
        length = self.__get_max_length()
        self.time = [None] * length
        for i in range(0, length):
            self.time[i] = [i * time_step]
        self.time_unit = unit

    def add_variable_time_step_vector(self, time_step, unit):
        if len(time_step) < self.__get_max_length():
            raise Exception('There are not enough time steps defined in the passed vector to cover all the values')
        else:
            self.time = time_step
            self.time_unit = unit

    def __process_added_values(self):
        self.f.attrs['simulator'] = self.simulator
        for name, value in self.metadata.iteritems():
            self.f.attrs[name] = value
        time_data_set = self.f.create_dataset('time', (len(self.time),), dtype='float_', data=self.time)
        time_data_set.attrs['unit'] = self.time_unit
        for path_string in self.values.keys():
            path = path_string.split(".")
            node = self.f
            for path_node in path:
                #if the group already exists get it
                if path_node in node:
                    node = node.get(path_node)
                #else create it
                else:
                    if path_node == path[-1]:
                        #this is the leaf create a dataset to store the values
                        values_array = np.array(self.values.get(path_string))
                        dataset = node.create_dataset(path_node, (values_array.size,),
                                                      dtype=self.data_types[path_string], data=values_array)
                        dataset.attrs['unit'] = self.units.get(path_string)
                        dataset.attrs['meta_type'] = self.meta_types.get(path_string).key
                    else:
                        if type(node) is h5py.Dataset:
                            raise Exception('A previous leaf is now referred to as a type')
                        else:
                            node = node.create_group(path_node)
            #at this stage node will have the leaf for our path, we can go ahead and add the data
            print node

    def add_metadata(self, name, value):
        if not name:
            raise Exception('Supply a name and be a good boy')
        if not value:
            raise Exception('Supply a value and be a good boy')
        self.metadata[name] = value

    def create(self):
        if self.time is None:  # can be a numpy array, in this case `if not self.time` will raise an error
            raise Exception('Time step vector is not defined, '
                            'call add_fixed_time_step_vector or add_variable_time_step_vector')
        self.__process_added_values()
        self.f.close()

    def add_recording_from_neuron(self, recording_file, variable_unit='mV', path_string=None):
        """
        Read a file that contains a recording from the NEURON simulator and add its contents to the current recording.
        The file can be created using NEURON's Graph and Vector GUI.

        Keyword arguments:
        recording_file -- path to the file that should be added
        """
        with open(recording_file, 'r') as r:
            lines = r.read().splitlines()
            r.close()

            # Extract label
            if path_string is None:

                path_string = lines[0][6:]
                # Replace NEURON's location indices like v(.5) by segmentAt0_5.v
                left_bracket = path_string.rfind('(')
                if left_bracket != -1:
                    right_bracket = path_string.find(')', left_bracket)
                    location = path_string[left_bracket+1:right_bracket]
                    if location.startswith('.'):
                        location = '0' + location
                    point_before_left_bracket = max(0, path_string.rfind('.', 0, left_bracket)+1)
                    # TODO: Think about alternatives for the segment name
                    path_string = path_string[:point_before_left_bracket] + 'segmentAt' + location.replace('.', '_') + '.' + path_string[point_before_left_bracket:left_bracket] + path_string[right_bracket+1:]

            # Extract time and variable data points
            num_steps = int(lines[1])
            times = np.empty(num_steps)
            values = np.empty(num_steps)
            for i, line in enumerate(lines[2:]):
                next_time, next_value = line.split()
                times[i] = next_time
                values[i] = next_value

            # Add everything to HDF5
            # TODO: Extract unit depending on variable name or at least give warning if they don't match
            self.add_value(path_string, values, 'float_', variable_unit, MetaType.STATE_VARIABLE)
            if self.time is None:
                self.add_variable_time_step_vector(times, 'ms')
            else:
                if not np.all(self.time == times):
                    raise ValueError('The file \"{0}\" contains a different time step vector than the one already definded'.format(recording_file))


    def add_recording_from_brian(self, recording_file, path_string_prefix=''):
        """
        Read a file that contains a recording from the brian simulator and add its contents to the current recording.
        The file can be created using brian's FileSpikeMonitor or AERSpikeMonitor.

        Keyword arguments:
        recording_file -- path to the file that should be added
        """
        with open(recording_file, 'r') as r:
            file_content = r.read()
            r.close()

            # TODO: Add exceptions if file can not be parsed
            if file_content.find('AER-DAT') == -1:  # txt format (recorded with brian.FileSpikeMonitor)
                lines = file_content.splitlines()
                # Extract indices and spike times similar to brian.load_aer() below
                indices = np.empty(len(lines), dtype='int')
                times = np.empty(len(lines))
                for i, line in enumerate(lines):
                    colon = line.find(',')
                    indices[i] = int(line[:colon])
                    times[i] = float(line[colon+2:])
            else:  # AER format (recorded with brian.AERSpikeMonitor)
                import brian
                try:
                    indices, times = brian.load_aer(recording_file)
                except Exception:
                    raise ValueError('The file \"{0}\" looks like an AER file but cannot be read'.format(recording_file))

            spikes = {}
            for index, time in zip(indices, times):
                str_index = str(index)
                if not str_index in spikes:
                    spikes[str_index] = []
                spikes[str_index].append(time)

            for index, spike_list in spikes.items():
                # TODO: Think about alternative naming for neuron
                path_string = path_string_prefix + 'neuron' + str(index) + '.spikes'
                # TODO: Alter current format to support events (that do not need a timestep)
                # TODO: Store spike_list under path_string

