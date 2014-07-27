__author__ = 'matteocantarelli, Johannes Rieke'

import h5py
import numpy as np
from enum import Enum
import string


def _is_text_file(filepath):
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


def _split_by_separators(s, separators=(' ', ',', ';', '\t')):
    """Split a string by various separators (or any combination of them) and return the non-empty substrings as a list."""
    if not hasattr(separators, '__iter__'):
        separators = (separators, )

    substrings = []

    while s:
        next_separator_start = -1
        next_separator_end = -1

        for separator in separators:
            separator_start = s.find(separator)
            if separator_start != -1 and (next_separator_start == -1 or separator_start < next_separator_start):
                next_separator_start = separator_start
                next_separator_end = separator_start + len(separator)

        if next_separator_start == -1:
            substrings.append(s)
            return substrings
        elif next_separator_start:
            substrings.append(s[:next_separator_start])
        s = s[next_separator_end:]

    return substrings


def _func_on_iterable(iterable, func):
    """Invoke a function on every item in an iterable and return it."""
    for i in range(len(iterable)):
        iterable[i] = func(iterable[i])
    return iterable


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
        if hasattr(value, '__iter__'):
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


class NeuronRecordingCreator(GeppettoRecordingCreator):

    def __init__(self, filename):
        GeppettoRecordingCreator.__init__(self, filename, 'NEURON')

    def add_recording_from_neuron(self, recording_file, variable_labels=None, variable_labels_prefix='', variable_units=None, time_column=None):
        # TODO: Adapt docstring
        """
        Read a file that contains a recording from the NEURON simulator and add its contents to the current recording.
        The file can be created using NEURON's Graph and Vector GUI.

        Keyword arguments:
        recording_file -- path to the file that should be added
        """

        if variable_labels is not None and not hasattr(variable_labels, '__iter__'):
            variable_labels = [variable_labels]
        if variable_units is not None and not hasattr(variable_units, '__iter__'):
            variable_units = [variable_units]

        if _is_text_file(recording_file):  # text file
            with open(recording_file, 'r') as r:
                lines = r.read().splitlines()
                # Omit any blank lines
                for i, line in enumerate(lines):
                    if line == '':
                        lines.pop(i)
                r.close()

                # Analyze the file structure:
                # Search for 3 successive lines that hold an equal amount of numbers, this is the start of the data block
                # On the way, store any non-number lines as possible variable labels
                i = 0
                start_data_lines = 0
                num_data_columns = -1
                num_data_lines = 0
                possible_label_items = []

                while num_data_lines < 3:
                    try:
                        line = lines[i]
                    except IndexError:
                        if num_data_lines:  # at least one data line was found, go ahead and parse
                            break
                        else:
                            raise ValueError("Reached end of file while analyzing file contents: " + recording_file)
                    #print 'line:', line
                    items = _split_by_separators(line)
                    #print 'items:', items
                    try:
                        items = _func_on_iterable(items, float)
                        is_data_line = True
                    except ValueError:  # this is not a data line
                        is_data_line = False

                    if is_data_line:
                        if num_data_columns != len(items):  # this is the first data line
                            num_data_columns = len(items)
                            num_data_lines = 1
                            start_data_lines = i
                        else:  # this is a further data line
                            num_data_lines += 1
                    else:
                        num_data_lines = 0
                        num_data_columns = -1
                        possible_label_items.append(items)

                    i += 1


                if variable_units is not None:
                    # Check if the number of data columns and variable units match
                    if len(variable_units) != num_data_columns:
                        raise IndexError("Got {0} variable units but found {1} data column(s)".format(len(variable_units), num_data_columns))
                else:
                    # Make list of placeholder variable units
                    variable_units = ['unknown_unit'] * num_data_columns

                if variable_labels is not None:
                    # Check if the number of data columns and variable labels match
                    if len(variable_labels) != num_data_columns:
                        raise IndexError("Got {0} variable labels but found {1} data column(s)".format(len(variable_labels), num_data_columns))
                else:
                    # Find variable labels in possible_label_items extracted above
                    labels_found = False
                    # TODO: What if multiple item sets with the same plausibility are found? Currently, the last one is used.
                    # TODO: Find out if an item set contains units.
                    if possible_label_items:
                        variable_labels = possible_label_items[0]
                        current_labels_plausibility = 0
                        for items in possible_label_items:
                            # check items for different attributes which make them more or less plausible to be the variable labels
                            if current_labels_plausibility < 1:
                                # plausibility 1: one less item than data columns (the missing label is time)
                                if len(items) == num_data_columns-1:
                                    variable_labels = ['time'] + items
                                    current_labels_plausibility = 1
                                    print 'found better labels with plausibility 1:', items
                            if current_labels_plausibility < 2:
                                # plausibility 2: equally many items and data columns
                                if len(items) == num_data_columns:
                                    variable_labels = items
                                    current_labels_plausibility = 2
                                    print 'found better labels with plausibility 2:', items
                            if current_labels_plausibility < 3:
                                # plausibility 3: one less item than data columns (the missing label is time) and one item contains 'label:'
                                if len(items) == num_data_columns-1:
                                    for i, item in enumerate(items):
                                        if item.find('label:') != -1:
                                            items[i] = items[i].replace('label:', '')
                                            variable_labels = ['time'] + items
                                            time_column = 0
                                            current_labels_plausibility = 3
                                            print 'found better labels with plausibility 3:', items
                                            break
                            if current_labels_plausibility < 4:
                                # plausibility 4: equally many items and data columns and one item contains 'label:'
                                if len(items) == num_data_columns:
                                    for i, item in enumerate(items):
                                        if item.find('label:') != -1:
                                            items[i] = items[i].replace('label:', '')
                                            variable_labels = ['time'] + items
                                            time_column = 0
                                            current_labels_plausibility = 4
                                            print 'found better labels with plausibility 4:', items
                                            break
                        if current_labels_plausibility > 0:
                            labels_found = True

                    if labels_found:
                        for i, label in enumerate(variable_labels):
                            # Replace NEURON's location indices like v(.5) by segmentAt0_5.v
                            left_bracket = variable_labels[i].rfind('(')
                            while left_bracket != -1:
                                right_bracket = label.find(')', left_bracket)
                                location_string = label[left_bracket+1:right_bracket]
                                if location_string.startswith('.'):
                                    location_string = '0' + location_string
                                point_before_left_bracket = max(0, label.rfind('.', 0, left_bracket)+1)
                                # TODO: Think about alternatives for the segment name
                                variable_labels[i] = label[:point_before_left_bracket] + 'segmentAt' + location_string.replace('.', '_') + '.' + label[point_before_left_bracket:left_bracket] + label[right_bracket+1:]
                                left_bracket = variable_labels[i].rfind('(')
                    else:
                        # TODO: Handle numbers when multiple files with unknown variables are supplied
                        variable_labels = ['unknown_variable_' + str(i) for i in range(num_data_columns)]
                print 'final labels:', variable_labels

                # Search for a label containing 'time' and select it as the time column
                if time_column is None:
                    for i, label in enumerate(variable_labels):
                        if label.lower().find('time') != -1:
                            time_column = i
                            break

                # Allocate arrays for data points
                num_total_data_lines = len(lines) - start_data_lines
                data_columns = np.zeros((num_data_columns, num_total_data_lines))  # first dimension is variable, second dimension is step

                # Read all data and store it in the arrays
                for i, line in enumerate(lines[start_data_lines:]):
                    # TODO: Make option to fill missing data points with zeros
                    # TODO: Use extract_numbers function instead?
                    items = _split_by_separators(line)
                    try:
                        numbers = _func_on_iterable(items, float)
                    except ValueError:
                        # TODO: Raise ValueError that shows both the filename and the specific item that could not be cast (not the complete list)
                        raise TypeError("Could not cast {0} to float: ".format(items) + recording_file)
                    try:
                        data_columns[:, i] = numbers
                    except ValueError:
                        raise IndexError("Found {0} data columns during analysis, now encountered line \"{1}\" with {2} numbers: ".format(num_data_columns, line, len(numbers)) + recording_file)

                print data_columns

                # Add everything to the Geppetto recording file
                for i, (label, unit, data) in enumerate(zip(variable_labels, variable_units, data_columns)):
                    if i == time_column:
                        # TODO: Maybe check this in add_variable_time_step_vector
                        if self.time is None:
                            self.add_variable_time_step_vector(data, unit)
                        else:
                            if not np.all(self.time == data):
                                # TODO: Reconcile error messages
                                raise ValueError('The file \"{0}\" contains a different time step vector than the one already defined'.format(recording_file))
                    else:
                        self.add_value(variable_labels_prefix + label, data, 'float_', unit, MetaType.STATE_VARIABLE)

        else:  # binary file
            # TODO: Handle import somewhere else
            from neuron import h
            f = h.File()
            f.ropen(recording_file)
            vector = h.Vector()
            vector.vread(f)
            if vector:

                # TODO: Do these sanity checks and add_value calls together with the ones for a text file
                # Check if the number of data columns and variable labels match
                if variable_labels is not None:
                    if len(variable_labels) != 1:
                        raise IndexError("Got {0} variable labels but found 1 data column(s)".format(len(variable_labels)))
                else:
                    variable_labels = ['unknown_variable_0']

                # Check if the number of data columns and variable units match
                if variable_units is not None:
                    if len(variable_units) != 1:
                        raise IndexError("Got {0} variable units but found 1 data column(s)".format(len(variable_labels)))
                else:
                    variable_units = ['unknown_unit']

                self.add_value(variable_labels[0], vector.to_python(), 'float_', variable_units[0], MetaType.STATE_VARIABLE)
            else:
                raise ValueError("Binary file is empty or could not be parsed: " + recording_file)


class BrianRecordingCreator(GeppettoRecordingCreator):

    def __init__(self, filename):
        GeppettoRecordingCreator.__init__(self, filename, 'Brian')

    def add_recording_from_brian(self, recording_file, path_string_prefix=''):
        """
        Read a file that contains a recording from the brian simulator and add its contents to the current recording.
        The file can be created using brian's FileSpikeMonitor or AERSpikeMonitor.

        Keyword arguments:
        recording_file -- path to the file that should be added
        """

        # TODO: Add exceptions if file can not be parsed
        if _is_text_file(recording_file):
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
            import brian
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
            path_string = path_string_prefix + 'neuron' + str(index) + '.spikes'
            # TODO: Alter current format to support events (that do not need a timestep)
            # TODO: Make MetaType.EVENT
            self.add_value(path_string, spike_list, 'float_', 'ms', MetaType.STATE_VARIABLE)

