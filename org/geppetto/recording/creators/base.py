import h5py
import numpy as np
import os
from enum import Enum
import time


class MetaType(Enum):
    """Enum of the possible meta types of a variable. Use like `MetaType.STATE_VARIABLE`.

    STATE_VARIABLE
        A variable that changes its value during a simulation or experiment.
        The values are associated with successive time points.

    PARAMETER
        A variable that was chosen by the user as an input for a simulation or experiment.

    PROPERTY
        A static variable that is inherent to a simulation or experiment.

    EVENT
        A variable that describes time points at which a certain condition was satisfied.

    """
    STATE_VARIABLE = 1
    PARAMETER = 2
    PROPERTY = 3
    EVENT = 4


class RecordingCreator:
    """
    Basic class to create a recording for Geppetto.

    Create one instance of this class per recording file.
    Add values for different types of variables with `add_values`. Successive values for one variable can be provided
    as an iterable or by calling `add_values` multiple times. If you store state variables that are associated with
    time, create a time definition with either `set_time_step` or `add_time_points`. Add global metadata for the
    recording with `add_metadata`. All these methods will return the `RecordingCreator` itself, so the method calls
    can be chained.
    If finished, call `create` to write all data to an HDF5 file.

    Parameters
    ----------
    filename : string
        The path to the recording file that will be created.
    simulator : string, optional
        The name of the simulator that was used to create the data in this recording.
    overwrite : boolean, optional
        If `False` (default), raise an error if `filename` exists. If `True`, overwrite it.

    Examples
    --------
    >>> c = RecordingCreator('recording_file.h5')
    >>> c.add_values('cell.voltage', [-60.0, -59.9, -59.8], 'mV', MetaType.STATE_VARIABLE)
    >>> c.add_values('cell.voltage', -59.7)
    >>> c.set_time_step(0.1, 'ms')
    >>> c.add_metadata('date', '2014-08-17')
    >>> c.create()

    Adds a state variable *voltage* for the entity *cell*.
    Its values are *-59.9 mV* at *0.1 ms*, *-59.7 mV* at *0.3 ms* etc.

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
        self.meta_types = {}
        self.time_points = None
        self.time_step = None
        self.time_unit = None
        self.simulator = simulator
        self.metadata = {}
        self.created = False

    def __repr__(self):
        r = 'Recording creator for ' + self.filename + ' (simulator: ' + self.simulator + ', variables: ' + str(len(self.values))
        if self.time_points is not None:
            r += ', time points:' + str(len(self.time_points))
        elif self.time_step is not None:
            r += ', fixed time step'
        else:
            r += ', no time'
        r += ', metadata: ' + str(len(self.metadata)) + ')'
        return r

    def __nonzero__(self):
        return not self.created

    def _assert_not_created(self):
        """Assert that the create method was not called yet."""
        if self.created:
            raise IOError("The recording file has already been created")

    def _variable_exists(self, name):
        """Return `True` if the recording contains values for the variable `name`."""
        return name in self.values

    def _next_free_index(self, name):
        """Return the next index for which the variable `name + str(index)` does not exist yet."""
        i = 0
        while self._variable_exists(name + str(i)):
            i += 1
        return 1

    def add_values(self, name, values, unit=None, meta_type=None, is_single_value=False):
        """Add one or multiple values for a variable to the recording.

        If values for this variable were added before, the new values will be appended. In this case, you can
        omit the `unit` and `meta_type` parameters.

        Parameters
        ----------
        name : string
            The name of the variable.
            A dot separated name creates a hierarchy in the file (for example `poolroom.table.ball.x`).
        values : number or any iterable of numbers
            One or multiple values of the variable. Will be appended to existing values. If `meta_type` is
            STATE_VARIABLE and `values` is iterable, its elements will be associated with successive time points.
        unit : string, optional
            The unit of the variable. If `None` (default), the unit from a previous definition of this variable
            will be used.
        meta_type : {MetaType.STATE_VARIABLE, MetaType.PARAMETER, MetaType.PROPERTY, MetaType.EVENT}, optional
            The type of the variable. If `None` (default), the meta type from a previous definition of this variable
            will be used.
        is_single_value : boolean, optional
            If set to `True`, `values` will be stored as a single value for a single time point, even if it is iterable.

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
        """Add global metadata to the recording.

        Parameters
        ----------
        name : string
            The name of the metadata field.
        value : string, number or iterable
            The value of the metadata field.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.

        """
        self._assert_not_created()
        if not name:
            raise Exception('Supply a name and be a good boy')
        self.metadata[name] = value
        return self

    def set_time_step(self, time_step, unit):
        """Set a fixed time step for all state variables in the recording.

        Call only one of `set_time_step` and `add_time_points`.

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

        See also
        --------
        add_time_points

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
        """Add one or multiple time points for all state variables in the recording.

        If other time points were added before, the new ones will be appended. In this case, you can
        omit the `unit` and `meta_type` parameters. Call only one of `set_time_step` and `add_time_points`.

        Parameters
        ----------
        time_points : number or iterable of numbers
            One or multiple time points to add. Will be appended to existing time points.
        unit : string, optional
            The unit of the time points. If `None` (default), the unit from a previous definition of time points
            will be used.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.

        See also
        --------
        set_time_step

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
        """Create the recording file and write all data to it.

        This has to be the last call to the `RecordingCreator`. Any further method calls will raise errors.

        Parameters
        ----------
        verbose : boolean, optional
            If set to True, will print additional information.

        """
        self._assert_not_created()
        with h5py.File(self.filename, 'w') as f:  # overwrite a previous file
            # TODO: Do this with logging?
            if verbose:
                print 'Writing file...'
                start_time = time.time()
            self._process_added_data(f)
            if verbose:
                print 'Time to write file:', time.time() - start_time
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
