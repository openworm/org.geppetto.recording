from __future__ import absolute_import
import os
import numpy as np
from org.geppetto.recording.creators.base import RecordingCreator, MetaType
from org.geppetto.recording.creators import utils


try:
    import neuron
    from neuron import h
    neuron_imported = True
except ImportError:
    neuron_imported = False


def _assert_neuron_imported():
    """Raise an `ImportError` if the neuron package could not be imported."""
    if not neuron_imported:
        raise ImportError("Could not import neuron, install it to proceed (see README for instructions)")


class NeuronRecordingCreator(RecordingCreator):
    """
    A RecordingCreator which interfaces to the NEURON simulator (www.neuron.yale.edu).

    Basically, there are three ways to add simulation data from NEURON:

    1. Provide a model file for NEURON (hoc or py): The creator will execute the simulation, monitor all variables
       while running and add their values to the recording (see `record_model`).
    2. Provide a recording file from NEURON (various text formats or binary):
       The creator will read it and add all values to the recording (see `add_text_recording` and
       `add_binary_recording`).
    3. Use the creator inside a NEURON simulation (in Python) and add values from a NEURON vector with
       *Vector.to_python()* and `add_values` or `add_time_points`.

    Some methods need to import the neuron package (see README for install instructions).

    Parameters
    ----------
    filename : string
        The path of the recording file that will be created.
    overwrite : boolean, optional
        If `False` (default), raise an error if `filename` exists. If `True`, overwrite it.

    """

    def __init__(self, filename, overwrite=False):
        RecordingCreator.__init__(self, filename, 'NEURON', overwrite)

    @staticmethod
    def _replace_location_indices(s):
        """Return the string with all of NEURON's location indices like v(.5) replaced by SegmentAt0_5.v."""
        while '(' in s:
            left_bracket = s.rfind('(')
            right_bracket = s.find(')', left_bracket)
            location_string = s[left_bracket+1:right_bracket]
            if location_string.startswith('.'):
                location_string = '0' + location_string
            point_before_left_bracket = max(0, s.rfind('.', 0, left_bracket)+1)
            s = s[:point_before_left_bracket] + 'segmentAt' + location_string.replace('.', '_') + '.' + s[point_before_left_bracket:left_bracket] + s[right_bracket+1:]
        return s

    def add_text_recording(self, recording_file, variable_names=None, variable_units=None, time_column=True):
        """Read a text recording file from the NEURON simulator and add its contents to the recording.

        The recording file has to be in text format. A range of file structures can be parsed. The data and variable
        names will be extracted automatically from the file contents.
        Particularly, the most common ways to create a recording in NEURON are covered:

        1) In the GUI, picking a vector from a *Graph* and choosing *Vector* -> *Save File*.
        2) In the GUI, going to *Window* -> *Print & File Window Manager*, selecting a *Graph* window and then doing
           *Print* -> *ASCII*.
        3) In NEURON code, calling *Vector.printf(file)*.
        4) In NEURON code, using *File.printf(string)* to create a CSV-like text file for different variables.
           Make one line with the variable names and one line with the values per time point. Different value
           separators or additional commentary lines will be handled automatically. If you are unsure, structure your
           file contents like this:

           time    soma.v    dendrite.v
           0       -60       -60
           1       -59       -58

        Parameters
        ----------
        recording_filename : string
            Path of the NEURON recording file that should be added.
        variable_names : iterable of strings, optional
            The names of the variables in the recording file. If `None` (default), the names will be searched within
            the recording.
        variable_units : iterable of strings, optional
            The units of the variables in the recording file. If `None`, empty strings will be used.
            The number of units has to match the number of variables in the recording.
        time_column : int or boolean
            The zero-count index of the data column in the recording file that contains time points.
            If `True` (default), the first variable whose name contains *time* is the time column.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.

        See also
        --------
        add_binary_recording

        """
        with open(recording_file, 'r') as r:
            lines = [line for line in r.read().splitlines() if line != '']

        # Analyze the file structure.
        current_line = 0
        first_data_line = 0
        num_data_columns = -1
        num_data_lines = 0
        text_lines = []

        # Search for three successive data lines (which contain an equal amount of numbers).
        while num_data_lines < 3:
            try:
                line = lines[current_line]
            except IndexError:
                if num_data_lines:  # at least one data line was found, go ahead and parse
                    break
                else:
                    raise EOFError("Reached end of file while analyzing file contents: " + recording_file)

            elements = utils.split_by_separators(line)
            try:
                elements = map(float, elements)
            except ValueError:  # this is not a data line, it could contain labels
                num_data_lines = 0
                num_data_columns = -1
                text_lines.append(line)
            else:  # this is a data line
                if len(elements) == num_data_columns:  # this is the next data line
                    num_data_lines += 1
                else:  # this is the first data line
                    num_data_columns = len(elements)
                    num_data_lines = 1
                    first_data_line = current_line
            current_line += 1

        if num_data_columns == 1 and time_column == 0:  # only time column
            variable_names = ['time']
            variable_units = ['ms']

        if variable_units is None:
            # TODO: Extract the units from the recording file.
            variable_units = [''] * num_data_columns
        else:
            # Check if the number of data columns and variable units match.
            if len(variable_units) != num_data_columns:
                raise IndexError("Got {0} variable units but found {1} data column(s)".format(len(variable_units), num_data_columns))


        if variable_names is None:
            # Find variable labels in the non-data lines from above.
            if text_lines:
                most_likely_variable_names = text_lines[0]
                likelihood = 0
                for text_items in map(utils.split_by_separators, text_lines):
                    # Check items for different attributes which make them more or less plausible as variable names.
                    if likelihood < 1:
                        # Likelihood 1: One less item than data columns (the missing label is time).
                        if len(text_items) == num_data_columns-1:
                            most_likely_variable_names = ['time'] + text_items
                            likelihood = 1
                    if likelihood < 2:
                        # Likelihood 2: Equally many items and data columns.
                        if len(text_items) == num_data_columns:
                            most_likely_variable_names = text_items
                            likelihood = 2
                    if likelihood < 3:
                        # Likelihood 3: One less item than data columns (no time), one item starts with *label:*.
                        if len(text_items) == num_data_columns-1:
                            for current_line, item in enumerate(text_items):
                                if item.startswith('label:'):
                                    text_items[current_line] = text_items[current_line][6:]
                                    most_likely_variable_names = ['time'] + text_items
                                    time_column = 0
                                    likelihood = 3
                                    break
                    if likelihood < 4:
                        # Likelihood 4: Equally many items and data columns, one item starts with *label:*.
                        if len(text_items) == num_data_columns:
                            for current_line, item in enumerate(text_items):
                                if item.startswith('label:'):
                                    text_items[current_line] = text_items[current_line][6:]
                                    most_likely_variable_names = ['time'] + text_items
                                    time_column = 0
                                    likelihood = 4
                                    break
                if likelihood > 0:
                    variable_names = map(self._replace_location_indices, most_likely_variable_names)
                else:
                    raise RuntimeError("Could not find variable names in the recording file, please set them manually")
            else:
                raise RuntimeError("Could not find variable names in the recording file, please set them manually")

        if len(variable_names) != num_data_columns:
            raise IndexError("Got {0} variable names but found {1} data column(s)".format(len(variable_names), num_data_columns))

        # Search for a label containing 'time' and select it as the time column
        if time_column is True:
            for i, name in enumerate(variable_names):
                if 'time' in name.lower():
                    time_column = i
                    if not variable_units[i]:
                        variable_units[i] = 'ms'
                    break

        # Allocate arrays for data points.
        num_total_data_lines = len(lines) - first_data_line
        data_columns = np.zeros((num_data_columns, num_total_data_lines))

        # Read all data and store it in the arrays.
        for current_line, line in enumerate(lines[first_data_line:]):
            text_items = utils.split_by_separators(line)
            try:
                numbers = map(float, text_items)
            except ValueError:
                raise TypeError("Could not cast to float: " + text_items)
            try:
                data_columns[:, current_line] = numbers
            except ValueError:
                raise IndexError("Encountered line with {0} number(s) for {1} variable(s): ".format(len(numbers), num_data_columns) + line)

        # Add everything to the RecordingCreator.
        for current_line, (name, unit, data) in enumerate(zip(variable_names, variable_units, data_columns)):
            if current_line == time_column:
                if self.time_points is None:
                    self.add_time_points(data, unit)
                else:
                    if not np.all(data == self.time_points):
                        raise ValueError("Recording file has different time points than already defined")
            else:
                self.add_values(name, data, unit, MetaType.STATE_VARIABLE)
        return self

    def add_binary_recording(self, recording_file, variable_name, variable_unit='', is_time=False):
        """Read a binary recording file from the NEURON simulator and add its contents to the recording.

        The recording file has to be created by NEURON's *Vector.vwrite(file)*. Therefore, it contains one vector.

        Parameters
        ----------
        recording_filename : string
            Path of the NEURON recording file that should be added.
        variable_name : string
            The name of the variable in the recording file.
        variable_unit : string, optional
            The unit of the variables in the recording file.
        is_time : boolean, optional
            If `False` (default), the values will be added as a state variable. If `True`, the values will be added
            as time points.

        Returns
        -------
        RecordingCreator
            The creator itself, to allow chained method calls.

        See also
        --------
        add_text_recording

        """
        _assert_neuron_imported()
        f = h.File()
        f.ropen(recording_file)
        vector = h.Vector()
        vector.vread(f)
        if vector:
            if is_time:
                self.add_time_points(vector.to_python(), variable_unit)
            else:
                self.add_values(variable_name, vector.to_python(), variable_unit, MetaType.STATE_VARIABLE)
        else:
            raise IOError("Binary file could not be parsed or is empty: " + recording_file)
        return self

    # TODO: Calling this method multiple times with hoc models could populate allsec with all sections from all models. Investigate this and possibly find a workaround.
    def record_model(self, model_filename, tstop=None, dt=None, format=None):
        """Execute a NEURON simulation, try to record all variables and add their values to the recording.

        The model file can be in Hoc or Python. Set `format` to force one; otherwise the file extension will be
        used. The model file must not start the simulation run. Instead, this method will load the model file
        and then run the simulation for `tstop` milliseconds (using the `neuron.run` command from Python).
        All available variables for all sections, segments and mechanisms will be recorded and added to the recording
        creator in hierarchical order (e. g. as *section.segment.mechanism.variable*).

        Parameters
        ----------
        model_filename : string
            The path of the Hoc or Python file for the NEURON simulation.
        tstop : float, optional
            The time to run the simulation for (in ms). If `None` (default), the value of the tstop variable in your
            Hoc file will be used, or 5 ms if it is not defined.
        dt : float, optional
            The time step to use for the simulation run (in ms). If `None` (default), the value ot the dt variable in
            your Hoc file will be used (this is 0.025 ms by default).
        format : 'hoc', 'py' or None, optional
            The format of the model file. If `None` (default), use the file extension.

        """
        self._assert_not_created()
        _assert_neuron_imported()

        if format is None:
            format = os.path.splitext(model_filename)[1][1:]

        # Execute the model file (hoc or py) and get the neuron.h object.
        if format == 'py':
            vars_dict = utils.run_as_script(model_filename)
            try:
                model_h = vars_dict['h']
            except KeyError:
                raise RuntimeError("Could not find neuron.h in the model file")
        elif format == 'hoc':
            h.load_file(os.path.abspath(model_filename).replace('\\', '/'))  # needs slashes, also on Windows
            model_h = h
        else:
            raise ValueError("Invalid file format, must be hoc or py")

        # Record time.
        time_vector = h.Vector()
        time_vector.record(h._ref_t)
        vectors = {}

        def add_vectors_for_variables(hoc_obj, hoc_obj_name, ignore=None):
            """Add a recording vector to `vectors` for each recordable variable of a NEURON object."""
            if ignore is None:
                ignore = []
            for attr in dir(hoc_obj):
                if not attr.startswith('__') and attr not in ignore:
                    try:
                        ref = getattr(segment, '_ref_' + attr)
                    except (NameError, AttributeError):
                        pass
                    else:
                        vec = model_h.Vector()
                        vec.record(ref)
                        vectors[hoc_obj_name + '.' + attr] = vec
                        # TODO: Get the unit of the attr.

        # TODO: Find out which variables are static, add them as properties and do not record them in vectors.
        for section in model_h.allsec():
            self.add_values(section.name() + '.L', section.L, 'um', MetaType.PARAMETER)
            # TODO: For Python models, section.name() gives ugly names. Instead, extract the name of the variable in the Python file (like in BrianRecordingCreator).
            add_vectors_for_variables(section, section.name())
            unformatted_segment_name = section.name() + '.segment{0}'
            for i, segment in enumerate(section):
                segment_name = unformatted_segment_name.format(i)
                self.add_values(segment_name + '.x', segment.x, '', MetaType.PROPERTY)
                add_vectors_for_variables(segment, segment_name)
                unformatted_mechanism_name = segment_name + '.{0}'
                for mechanism in segment:
                    add_vectors_for_variables(mechanism, unformatted_mechanism_name.format(mechanism.name()))

        # TODO: Look at point processes.

        # Run the simulation
        if tstop is None:
            try:
                tstop = model_h.tstop
            except AttributeError:
                tstop = 5

        if dt is not None:
            model_h.dt = dt

        #print 'Running for', tstop, 'ms with timestep', model_h.dt, 'ms'

        neuron.init()
        neuron.run(tstop)

        for name, vector in vectors.iteritems():
            self.add_values(name, vector.to_python(), '', MetaType.STATE_VARIABLE)

        self.add_time_points(time_vector.to_python(), 'ms')
