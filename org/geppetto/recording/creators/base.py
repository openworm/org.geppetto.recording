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
    THIS IS OUTDATED!

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
    """
    def __init__(self, filename, simulator='Not specified', overwrite=False):
        # TODO: Add support for file to be reopened
        if os.path.isfile(filename) and not overwrite:
            raise IOError("File already exists, delete it or set the overwrite flag to proceed: " + filename)
        elif os.path.isdir(filename):
            raise IOError("Filename points to a directory: " + filename)

        self.filename = filename
        self.values = {}
        self.units = {}
        self.data_types = {}
        self.meta_types = {}
        self.time_points = None
        self.time_step = None
        self.time_unit = None
        self.simulator = simulator
        self.metadata = {}
        self.created = False

    def _assert_not_created(self):
        """Assert that the create method was not called yet."""
        if self.created:
            raise IOError("The recording file has already been created")

    def _variable_exists(self, name):
        """Return True if the variable `name` exists in this recording."""
        return name in self.values

    def _next_free_index(self, name):
        """Return the next index for which the variable `name + str(index)` does not exist yet."""
        i = 0
        while self._variable_exists(name + str(i)):
            i += 1
        return 1

    def add_values(self, name, values, unit=None, meta_type=None, is_single_value=False):
        """
        Add one or multiple values of a variable to the recording.

        If the variable was never defined before, it will be created. Otherwise, the values will be appended.

        Parameters
        ----------
        name : string
            The name of the variable.
            A dot separated name creates a hierarchy in the file (for example `poolroom.table.ball.x`).
        values : number or any iterable of numbers
            One or multiple values of the variable. Will be appended to existing values.
            If `meta_type` is STATE_VARIABLE and `values` is iterable, its elements will be stored for successive time points.
        unit : string, optional
            The unit of the variable. Leave `None` to use the value from a previous definition of this variable.
        meta_type : {MetaType.STATE_VARIABLE, MetaType.PARAMETER, MetaType.PROPERTY, MetaType.Event}, optional
            The type of the variable. Leave `None` to use the value from a previous definition of this variable.
        is_single_value : boolean, optional
            If set to True, `values` will be stored as a single value for a single time point even if it is iterable.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.
        """
        self._assert_not_created()
        if not name:
            raise ValueError("Name must not be empty")
        if meta_type is not None and meta_type not in MetaType:
            raise TypeError("Meta type is not a member of enum MetaType: " + str(meta_type))

        if not self._variable_exists(name):  # variable does not exist yet
            # TODO: Use numpy arrays instead? -> Check performance of extending numpy arrays vs python lists
            self.values[name] = []
            self.units[name] = unit
            self.meta_types[name] = meta_type
        else:
            if meta_type is not None and meta_type != self.meta_types[name]:
                raise ValueError("The meta type does not match with a previous definition of this variable")
            if unit is not None and unit != self.units[name]:
                raise ValueError("The unit does not match with a previous definition of this variable")

        if hasattr(values, '__iter__') and not is_single_value:
            # TODO: This can cause a MemoryError for many steps and 32-bit versions of Python (depending on the OS, there are only 1 to 4 GB of memory available).
            # TODO: Possible solution: Flush values to hdf5 file if they extend a certain size or if a MemoryError is raised.
            self.values[name].extend(values)
        else:
            self.values[name].append(values)

        return self

    def add_metadata(self, name, value):
        """
        Add global metadata to the recording.

        Parameters
        ----------
        name : string
            The name of the metadata field.
        value : anything
            The value of the metadata field.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.
        """
        self._assert_not_created()
        if not name:
            raise Exception('Supply a name and be a good boy')
        # TODO: Can h5py also take None itself as a value?
        if value is None:  # empty metadata, for example to set a flag
            value = ''
        self.metadata[name] = value
        return self

    def set_time_step(self, time_step, unit):
        """
        Set a fixed time step for all state variables in the recording.

        Call only one of set_time_step and add_time_points.

        Parameters
        ----------
        time_step : number
            The (fixed) duration between successive time points.
        unit : string
            The unit of `time_step`.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.
        """
        self._assert_not_created()
        if hasattr(time_step, '__iter__'):
            raise TypeError("Time step must be a single number, use add_time_points to add successive time points")
        if not time_step > 0:
            raise ValueError("Time step must be larger than 0, is: " + str(time_step))
        if self.time_points is not None:
            raise RuntimeError("Time points were already added, use either a fixed time step OR time points")
        self.time_step = time_step
        self.time_unit = unit
        return self

    def add_time_points(self, time_points, unit=None):
        """
        Add one or multiple time points for all state variables in the recording.

        If other time points were added previously, the new ones will be appended.
        Call only one of set_time_step and add_time_points.

        Parameters
        ----------
        time_points : number of any iterable of numbers
            One or multiple time points to add. Will be appended to existing time points.
        unit : string, optional
            The unit of the values in `time_points`. Leave `None` to use the value from a previous definition of time points.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.
        """
        self._assert_not_created()
        if self.time_step is not None:
            raise RuntimeError("A fixed time step was already set, use either a fixed time step OR time points")
        if self.time_points is None:
            self.time_points = []
            self.time_unit = unit
        else:
            if unit is not None and unit != self.time_unit:
                raise ValueError("The unit does not match with a previous definition of time points")
        if hasattr(time_points, '__iter__'):
            self.time_points.extend(time_points)
        else:
            self.time_points.append(time_points)
        return self

    # def set_time(self, time_step_or_vector, unit):
    #     self._assert_not_created()
    #     if self.time is not None:
    #         raise RuntimeError("Time has already been defined")
    #     if time_step_or_vector is None:
    #         raise ValueError("Supply a time step or vector and be a good boy")
    #     elif not hasattr(time_step_or_vector, '__iter__') and time_step_or_vector == 0:
    #         raise ValueError("The time step cannot be 0")
    #     elif hasattr(time_step_or_vector, '__iter__') and len(time_step_or_vector) == 0:
    #         raise ValueError("The time vector cannot be empty")
    #     self.time = time_step_or_vector  # will be parsed in _process_added_data
    #     self.time_unit = unit
    #     return self

    def create(self, verbose=False):
        """
        Create the recording file and write all added data to it.

        After calling this method, the `RecordingCreator` is useless. Any further method calls will raise errors.

        Parameters
        ----------
        verbose : boolean, optional
            If set to True, will print additional information.
        """
        self._assert_not_created()
        f = h5py.File(self.filename, 'w')  # overwrite a previous file
        if verbose:
            print 'Writing file...'
            start_time = time.time()
        self._process_added_data(f)
        if verbose:
            print 'Time to write file:', time.time() - start_time
        f.close()
        self.created = True

    def _process_added_data(self, f):
        """Check all added data for consistency and write it to file."""
        f.attrs['simulator'] = self.simulator
        for name, value in self.metadata.iteritems():
            f.attrs[name] = value

        max_num_steps = 0
        for name in self.values:
            if self.meta_types[name] == MetaType.STATE_VARIABLE:
                max_num_steps = max(max_num_steps, len(self.values[name]))

        if self.time_points is not None and self.time_step is not None:  # this should normally not happen
            raise RuntimeError("You added both time points and a time step, use only one")
        if self.time_points is None and self.time_step is None and max_num_steps:
            raise RuntimeError("You added state variables, please also add time points or set a time step")
        if self.time_points is not None:
            if len(self.time_points) < max_num_steps:
                raise IndexError("There are not enough time points to cover the values of all state variables")
            f['time'] = self.time_points
            f['time'].attrs['unit'] = self.time_unit
        elif self.time_step is not None:
            f['time'] = np.linspace(0, max_num_steps * self.time_step, max_num_steps, endpoint=False)
            f['time'].attrs['unit'] = self.time_unit

        # is_time_vector = hasattr(self.time, '__iter__')
        # if max_num_steps or is_time_vector:  # do not write time for a fixed time step and no state variables
        #     if self.time is None:
        #         raise RuntimeError("There are state variables but no time is defined, call set_time")
        #     if is_time_vector:
        #         if len(self.time) < max_num_steps:
        #             raise IndexError("The number of steps in the time vector is smaller than the number of values in the state variables")
        #     else:  # fixed time step
        #         self.time = np.linspace(0, max_num_steps * self.time, max_num_steps, endpoint=False)
        #     f['time'] = self.time
        #     f['time'].attrs['unit'] = self.time_unit

        for name in self.values.keys():
            path = name.replace('.', '/')
            try:
                f[path] = self.values[name]
                f[path].attrs['unit'] = self.units[name]
                f[path].attrs['meta_type'] = str(self.meta_types[name])
            except RuntimeError:
                # TODO: What are ALL the reasons that raise this exception?
                # TODO: Should the case 'A previous leaf is now referred to as a type' be explicitly mentioned in the error message?
                raise ValueError("Cannot write dataset for variable " + name)
