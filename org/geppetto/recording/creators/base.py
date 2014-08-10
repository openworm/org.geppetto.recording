import h5py
import numpy as np
import os
import string
from enum import Enum

# TODO: Make clear in the docs what these mean and especially what the difference between PARAMETER and PROPERTY is
import time

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


def make_iterable(object):
    """Return a list that holds the object, or the object itself if it is already iterable."""
    if hasattr(object, '__iter__'):
        return object
    else:
        return [object]


class RecordingCreator:
    """
    This class allows to create a recording for Geppetto.

    There should be one instance of this class per recording created.
    In order to create a recording instantiate this class specifying the filename of the recording you wish to create
     and the simulator used to produce the recording.
    The method add_values allows to add a recording for a given variable by specifying its path.
    It is possible to call add_values multiple times for the same path (values will be appended) or call it once
     specifying a list of values.
    Once all the values have been appended call either add_fixed_time_step_vector or  add_variable_time_step_vector
     to generate a vector with values for time.
    The values provided with the method add_values will be associated with the corresponding time step at the same index
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
    creator.add_values('a', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_values('a', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_values('a.b', 1, 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_values('a.b.param1', 1, 'float_', 'mV', MetaType.PARAMETER)
    creator.add_values('a.b.prop1', 1, 'float_', 'mV', MetaType.PROPERTY)
    creator.add_values('a.b.c.d', [1, 2, 3, 4, 5, 6], 'float_', 'mV', MetaType.STATE_VARIABLE)
    creator.add_values('a.b', 2, 'float_', 'mV', MetaType.STATE_VARIABLE)
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

    def add_values(self, label, values, unit, meta_type, is_single_value=False):
        """Add one or multiple values to the variable `label`."""
        if not label:
            raise ValueError("Label is empty")
        if meta_type not in MetaType:
            raise TypeError("Meta type is not a member of enum MetaType: " + str(meta_type))
        if unit is None:  # dimensionless
            unit = ''

        if label not in self.values:
            # TODO: Use numpy arrays instead? -> Check performance of extending numpy arrays vs python lists
            self.values[label] = []
        if hasattr(values, '__iter__') and not is_single_value:
            # TODO: This can cause a MemoryError for many steps and 32-bit versions of Python (depending on the OS, there are only 1 to 4 GB of memory available).
            # TODO: Possible solution: Flush values to hdf5 file if they extend a certain size.
            self.values[label].extend(values)
        else:
            self.values[label].append(values)
        self.units[label] = unit
        self.meta_types[label] = meta_type

    def add_time(self, time_step_or_vector, unit):
        if self.time is not None:
            raise RuntimeError("Time has already been defined")
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

        max_num_steps = 0
        for label in self.values.keys():
            if self.meta_types[label] == MetaType.STATE_VARIABLE:
                max_num_steps = max(max_num_steps, len(self.values[label]))

        is_time_vector = hasattr(self.time, '__iter__')
        if max_num_steps or is_time_vector:  # do not write time for a fixed time step and no state variables
            if self.time is None:
                raise RuntimeError("There are state variables but no time is defined, call add_time")
            if is_time_vector:
                if len(self.time) < max_num_steps:
                    raise IndexError("The number of steps in the time vector is smaller than the number of values in the state variables")
            else:  # fixed time step
                self.time = np.linspace(0, max_num_steps * self.time, max_num_steps, endpoint=False)
            f['time'] = self.time
            f['time'].attrs['unit'] = self.time_unit

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
        # TODO: Have the logic from _process_added_values in here?
        print 'Writing file...'
        start_time = time.time()
        self._process_added_values(f)
        print 'Time to write file:', time.time() - start_time
        f.close()

    def exists(self, variable_label):
        return variable_label in self.values

    def next_free_index(self, label):
        """Return the next index for which the variable `label + str(index)` does not exist yet."""
        i = 0
        while self.exists(label + str(i)):
            i += 1
        return 1