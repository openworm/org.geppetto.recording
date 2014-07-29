from __future__ import absolute_import
import numpy as np
import neuron

from org.geppetto.recording.creators.base import RecordingCreator, MetaType, is_text_file


def split_by_separators(s, separators=(' ', ',', ';', '\t')):
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


def func_on_iterable(iterable, func):
    """Invoke a function on every item in an iterable and return it."""
    for i in range(len(iterable)):
        iterable[i] = func(iterable[i])
    return iterable


class NeuronRecordingCreator(RecordingCreator):

    def __init__(self, filename):
        RecordingCreator.__init__(self, filename, 'NEURON')

    @staticmethod
    def _replace_location_indices(s):
        """Replace all of NEURON's location indices in a string like v(.5) by segmentAt0_5.v and return the string."""
        left_bracket = s.rfind('(')
        while left_bracket != -1:
            right_bracket = s.find(')', left_bracket)
            location_string = s[left_bracket+1:right_bracket]
            if location_string.startswith('.'):
                location_string = '0' + location_string
            point_before_left_bracket = max(0, s.rfind('.', 0, left_bracket)+1)
            # TODO: Think about alternatives for the segment name
            s = s[:point_before_left_bracket] + 'segmentAt' + location_string.replace('.', '_') + '.' + s[point_before_left_bracket:left_bracket] + s[right_bracket+1:]
            left_bracket = s.rfind('(')
        return s

    def add_neuron_recording(self, recording_file, variable_labels=None, variable_labels_prefix='', variable_units=None, time_column=None):
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

        if is_text_file(recording_file):  # text file
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
                    items = split_by_separators(line)
                    #print 'items:', items
                    try:
                        items = func_on_iterable(items, float)
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
                        for i in range(len(variable_labels)):
                            variable_labels[i] = self._replace_location_indices(variable_labels[i])
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
                    items = split_by_separators(line)
                    try:
                        numbers = func_on_iterable(items, float)
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
                        try:
                            self.add_time(data, unit)
                        except RuntimeError:
                            # TODO: Reconcile error messages
                            raise ValueError('The file \"{0}\" contains a different time step vector than the one already defined'.format(recording_file))
                    else:
                        self.add_values(variable_labels_prefix + label, data, unit, MetaType.STATE_VARIABLE)

        else:  # binary file
            # TODO: Handle import somewhere else
            from neuron import h
            f = h.File()
            f.ropen(recording_file)
            vector = h.Vector()
            vector.vread(f)
            if vector:
                # Check if the number of data columns and variable units match
                if variable_units is not None:
                    if len(variable_units) != 1:
                        raise IndexError("Got {0} variable units but found 1 data column(s)".format(len(variable_labels)))
                else:
                    variable_units = ['unknown_unit']

                if time_column == 0:
                    self.add_time(vector.to_python(), variable_units[0])
                else:
                    # TODO: Do these sanity checks and add_values calls together with the ones for a text file
                    # Check if the number of data columns and variable labels match
                    if variable_labels is not None:
                        if len(variable_labels) != 1:
                            raise IndexError("Got {0} variable labels but found 1 data column(s)".format(len(variable_labels)))
                    else:
                        variable_labels = ['unknown_variable_0']

                    self.add_values(variable_labels[0], vector.to_python(), variable_units[0], MetaType.STATE_VARIABLE)
            else:
                raise ValueError("Binary file is empty or could not be parsed: " + recording_file)

    def record_neuron_model(self, model_file, tstop=None, dt=None):
        import neuron
        from neuron import h
        # TODO: Currently, model_file must not contain sth like load_file("nrngui.hoc") because this hoc file cannot be found
        h.load_file(model_file.replace('\\', '/'))  # load_file needs slashes, also on Windows

        time_vector = h.Vector()
        time_vector.record(h._ref_t)
        vectors = []
        labels = []

        for section in h.allsec():
            self.add_values(section.name() + '.L', section.L, 'um', MetaType.PROPERTY)
            for segment in section:
                segment_label = section.name() + '.segmentAt' + str(segment.x).replace('.', '_')
                self.add_values(segment_label + '.diam', segment.diam, 'um', MetaType.PROPERTY)
                vector_v = h.Vector()
                vector_v.record(segment._ref_v)
                vectors.append(vector_v)
                labels.append(segment_label + '.v')
                #print 'has public attributes: ', [a for a in dir(segment) if not a[:1] == '_']
                #print dir(segment.point_processes)
                #for point_process in segment.point_processes():
                    #print 'found:', point_process
            print section.name() + ' (' + str(section)

        print '-> set up ' + str(len(vectors)) + ' vectors'

        # access point processes (here: of type IClamp), see http://www.neuron.yale.edu/phpbb/viewtopic.php?f=8&t=186
        # TODO: How to do this in Python natively?
        # TODO: How to dereference to section (see URL above)?
        # TODO: How/where to store this in HDF5?
        # TODO: Synapses
        h('objref listIClamps')
        h('listIClamps = new List("IClamp")')
        i_clamps = h.listIClamps

        for i, i_clamp in enumerate(i_clamps):
            label = 'i_clamp_' + str(i)
            self.add_values(label + '.dur', i_clamp.dur, 'ms', MetaType.PARAMETER)
            self.add_values(label + '.del', i_clamp.delay, 'ms', MetaType.PARAMETER)
            self.add_values(label + '.amp', i_clamp.amp, 'mA', MetaType.PARAMETER)
            vector_i = h.Vector()
            vector_i.record(i_clamp._ref_i)
            vectors.append(vector_i)
            #print i_clamp.Section
            # TODO: Get i_clamp name
            labels.append(label + '.i')

        # TODO: Search for  run command in model file? -> execute the code before it, then attach vectors and execute the rest
        # TODO: Describe this behaviour in the docstring
        if tstop is not None:
            h.tstop = tstop
        else:
            if not hasattr(h, 'tstop'):
                h.tstop = 5

        if dt is not None:
            h.dt = dt
        else:
            if not hasattr(h, 'dt'):
                h.dt = 0.025

        print 'running for', h.tstop, 'ms with timestep', h.dt, 'ms'

        neuron.init()
        neuron.run(h.tstop)

        for label, vector_v in zip(labels, vectors):
            # TODO: Extract unit
            self.add_values(label, vector_v.to_python(), 'unknown_unit', MetaType.STATE_VARIABLE)

        # TODO: Is time in NEURON always in ms?
        self.add_time(time_vector.to_python(), 'ms')

