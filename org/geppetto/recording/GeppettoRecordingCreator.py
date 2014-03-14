__author__ = 'matteocantarelli'

import h5py
import numpy as np
from enum import Enum

MetaType = Enum('STATE_VARIABLE', 'PARAMETER', 'PROPERTY')


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
    creator.close()
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
            if meta_type == MetaType.PARAMETER:
                raise Exception('A list has been specified while a parameter should have only one value')
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
                    node = node.create_group(path_node)
            #at this stage node will have the life for our path, we can go ahead and add the data
            print node
            values_array = np.array(self.values.get(path_string))
            dataset = node.create_dataset('values', (values_array.size,), dtype=self.data_types[path_string],
                                          data=values_array)
            dataset.attrs['unit'] = self.units.get(path_string)
            dataset.attrs['meta_type'] = self.meta_types.get(path_string).key

    def create(self):
        if not self.time:
            raise Exception('Time step vector is not defined, '
                            'call add_fixed_time_step_vector or add_variable_time_step_vector')
        self.__process_added_values()
        self.f.close()
