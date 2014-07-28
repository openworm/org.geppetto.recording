import h5py
import numpy as np
import os
from enum import Enum
import string


MetaType = Enum('STATE_VARIABLE', 'PARAMETER', 'PROPERTY', 'EVENT')


def is_text_file(filepath):
    """Return True if the file is text, False if it is binary."""
    with open(filepath, 'r') as f:
        test_string = f.read(512)
        text_characters = ''.join(map(chr, range(32, 127)) + ['\n', '\r', '\t', '\b'])
        null_translation = string.maketrans('', '')
        if not test_string:  # empty file -> text
            return True
        if '\0' in test_string:  # file with null byte -> binary
            return False
        non_text_characters = test_string.translate(null_translation, text_characters)
        if float(len(non_text_characters)) / float(len(test_string)) > 0.30:  # more than 30% non-text characters -> binary
            return False
        else:
            return True


class RecordingCreator:
    # TODO: Adapt docstring
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
    creator = RecordingCreator('example1.h5')
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
    def __init__(self, filename, simulator='Not specified', overwrite=False,):
        # TODO: Add support for file to be reopened
        # TODO: Test
        self.remove_previous_file = False
        if os.path.exists(filename):
            if os.path.isfile(filename):  # file
                if overwrite:
                    self.remove_previous_file = True
                else:
                    raise IOError("File already exists, set the overwrite flag to remove it before writing: " + filename)
            else:  # directory
                raise IOError("Filename points to a directory: " + filename)

        self.filename = filename
        self.values = {}
        self.units = {}
        self.data_types = {}
        self.meta_types = {}
        self.time = None
        self.time_unit = None
        self.simulator = simulator
        self.metadata = {}

    def add_value(self, label, value, unit, meta_type):
        if not label:
            raise ValueError("Label is empty")
        if meta_type not in MetaType:
            raise TypeError("Meta type is not a member of enum MetaType: " + str(meta_type))
        if unit is None:  # dimensionless
            unit = ''

        if label not in self.values:
            # TODO: Use numpy arrays instead? -> Check performance of extending numpy arrays vs python lists
            self.values[label] = []
        if hasattr(value, '__iter__'):
            self.values.get(label).extend(value)
        else:
            self.values.get(label).append(value)
        self.units[label] = unit
        self.meta_types[label] = meta_type

    def add_time(self, time_step_or_vector, unit):
        print time_step_or_vector
        if self.time is not None:
            raise RuntimeError("Time has already been defined previously")
        if not unit:
            raise ValueError("The time unit cannot be empty")
        if time_step_or_vector is None:
            raise ValueError("Supply a time step or vector and be a good boy")
        elif not hasattr(time_step_or_vector, '__iter__') and time_step_or_vector == 0:
            raise ValueError("The time step cannot be 0")
        elif hasattr(time_step_or_vector, '__iter__') and len(time_step_or_vector) == 0:
            raise ValueError("The time vector cannot be empty")
        self.time = time_step_or_vector  # will be parsed in _process_added_values
        self.time_unit = unit

    def _process_added_values(self, f):
        f.attrs['simulator'] = self.simulator
        for name, value in self.metadata.iteritems():
            f.attrs[name] = value

        # TODO: Should the number of steps in the state variables match (with each other and with the time vector) or should it only be smaller than the time vector?
        # num_steps = None
        # for label in self.values.keys():
        #     if self.meta_types[label] == MetaType.STATE_VARIABLE:
        #         if num_steps is None:
        #             num_steps = len(self.values[label])
        #         else:
        #             if len(self.values[label]) != num_steps:
        #                 raise IndexError("The number of steps in the state variables do not match")

        max_num_steps = 0
        for label in self.values.keys():
            if self.meta_types[label] == MetaType.STATE_VARIABLE:
                max_num_steps = max(max_num_steps, len(self.values[label]))

        is_time_vector = hasattr(self.time, '__iter__')
        if max_num_steps or is_time_vector:  # do not write time for a fixed time step and no state variables
            if self.time is None:
                raise RuntimeError("There are state variables but no time is defined, call add_time")
            if is_time_vector:
                if len(self.time) != max_num_steps:
                    raise IndexError("The number of steps in the time vector and in the state variables do not match")
            else:  # fixed time step
                self.time = np.linspace(0, max_num_steps * self.time, max_num_steps, endpoint=False)
            f['time'] = self.time
            f['time'].attrs['unit'] = self.time_unit

        #time_data_set = self.f.create_dataset('time', (len(self.time),), dtype='float_', data=self.time)
        #time_data_set.attrs['unit'] = self.time_unit

        for label in self.values.keys():
            path = label.replace('.', '/')
            try:
                f[path] = self.values[label]
                f[path].attrs['unit'] = self.units[label]
                f[path].attrs['meta_type'] = str(self.meta_types[label])
            except RuntimeError:
                # TODO: What are ALL the reasons that raise this exception?
                # TODO: Should the case 'A previous leaf is now referred to as a type' be explicitly mentioned in the error message?
                raise ValueError("Cannot write dataset for variable " + label)

        # for path_string in self.values.keys():
        #     path = path_string.split('.')
        #     node = self.f
        #     for path_node in path:
        #         #if the group already exists get it
        #         if path_node in node:
        #             node = node.get(path_node)
        #         #else create it
        #         else:
        #             if path_node == path[-1]:
        #                 #this is the leaf create a dataset to store the values
        #                 values_array = np.array(self.values.get(path_string))
        #                 dataset = node.create_dataset(path_node, (values_array.size,),
        #                                               dtype=self.data_types[path_string], data=values_array)
        #                 dataset.attrs['unit'] = self.units.get(path_string)
        #                 dataset.attrs['meta_type'] = self.meta_types.get(path_string).key
        #             else:
        #                 if type(node) is h5py.Dataset:
        #                     raise Exception('A previous leaf is now referred to as a type')
        #                 else:
        #                     node = node.create_group(path_node)
        #     #at this stage node will have the leaf for our path, we can go ahead and add the data
        #     print node

    def add_metadata(self, name, value):
        if not name:
            raise Exception('Supply a name and be a good boy')
        if value is None:  # empty metadata, for example to set a flag
            value = ''
        self.metadata[name] = value

    def create(self):
        if self.remove_previous_file:
            os.remove(self.filename)
        f = h5py.File(self.filename, 'w-')  # create file here to avoid an empty file if an error occurs
        # TODO: Include _process_added_values here?
        self._process_added_values(f)
        f.close()