from __future__ import absolute_import
import os
import numpy as np
from org.geppetto.recording.creators.base import RecordingCreator, MetaType, is_text_file, make_iterable


_neuron_not_installed_error = ImportError("You have to install the pyNEURON package to use this method")


def split_by_separators(s, separators=(' ', ',', ';', '\t')):
    """Split a string by various separators (or any combination of them) and return the non-empty substrings as a list."""
    if not hasattr(separators, '__iter__'):
        separators = make_iterable(separators)

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


class NeuronRecordingCreator(RecordingCreator):
    """
    A RecordingCreator which interfaces to the NEURON simulator (www.neuron.yale.edu).

    More info to come...

    Parameters
    ----------
    filename : string
        The path to the recording file that will be created.

    """

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
        """Read a recording file from the NEURON simulator and add its contents to the current recording.

        More info to come...

        Parameters
        ----------
        recording_file : string
            Path to the file that should be added
        variable_labels : string or iterable of strings
            The label(s) of the variable(s) in the recording. If None or empty, the labels are searched within the recording. The number of labels has to match the number of data columns in the recording.
        variable_labels_prefix : string
            A string to prepend to all variable labels. For example, `neuron0.` makes the variable `v` to `neuron0.v`.
        variable_units : string or iterable of strings
            The unit(s) of the variable(s) in the recording. If None or empty, `unknown_unit` is used. The number of units has to match the number of data columns in the recording.
        time_column : int
            The index of the data column in the recording that contains the time. If None, the time column is searched within the recording.

        """
        self._assert_not_created()

        if variable_units:
            variable_units = make_iterable(variable_units)
        if variable_labels:
            variable_labels = make_iterable(variable_labels)

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
                        items = map(float, items)
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


                if variable_units:
                    # Check if the number of data columns and variable units match
                    if len(variable_units) != num_data_columns:
                        raise IndexError("Got {0} variable units but found {1} data column(s)".format(len(variable_units), num_data_columns))
                else:
                    # Make list of placeholder variable units
                    variable_units = ['unknownUnit'] * num_data_columns

                if variable_labels:
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
                        variable_labels = []
                        for i in range(num_data_columns):
                            variable_labels.append('unknownVariable' + str(self._next_free_index('unknownVariable')))
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
                        numbers = map(float, items)
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
                            self.add_time_points(data, unit)
                        except RuntimeError:
                            # TODO: Reconcile error messages
                            raise ValueError('The file \"{0}\" contains a different time step vector than the one already defined'.format(recording_file))
                    else:
                        self.add_values(variable_labels_prefix + label, data, unit, MetaType.STATE_VARIABLE)

        else:  # binary file
            try:
                import neuron
                from neuron import h
            except ImportError:
                raise _neuron_not_installed_error
            f = h.File()
            f.ropen(recording_file)
            vector = h.Vector()
            vector.vread(f)
            if vector:
                # Check if the number of data columns and variable units match
                if variable_units:
                    if len(variable_units) != 1:
                        raise IndexError("Got {0} variable units but found 1 data column(s)".format(len(variable_labels)))
                else:
                    variable_units = ['unknownUnit']

                if time_column == 0:
                    self.add_time_points(vector.to_python(), variable_units[0])
                else:
                    # TODO: Do these sanity checks and add_values calls together with the ones for a text file
                    # Check if the number of data columns and variable labels match
                    if variable_labels:
                        if len(variable_labels) != 1:
                            raise IndexError("Got {0} variable labels but found 1 data column(s)".format(len(variable_labels)))
                    else:
                        variable_labels = ['unknownVariable' + str(self._next_free_index('unknownVariable'))]

                    self.add_values(variable_labels[0], vector.to_python(), variable_units[0], MetaType.STATE_VARIABLE)
            else:
                raise ValueError("Binary file is empty or could not be parsed: " + recording_file)
        return self


    def record_neuron_hoc_model(self, model_filename, temp_filename='temp_model.hoc', overwrite_temp_file=True, remove_temp_file=True):
        self._assert_not_created()

        # TODO: Do this in common method: Parse hoc or py model depending on `file_extension`
        try:
            file_extension = model_filename[model_filename.rindex('.')+1:]
            if file_extension == 'hoc':
                pass
            elif file_extension == 'py':
                pass
            else:
                pass
        except ValueError:
            pass

        try:
            import neuron
            from neuron import h
        except ImportError:
            raise _neuron_not_installed_error

        if os.path.exists(temp_filename) and not overwrite_temp_file:
            raise IOError("Temporary file already _variable_exists, set the overwrite flag to proceed")

        text_to_prepend="""
proc

"""


        # Create a temporary file that contains the model and some additions to set up the monitors for recording.
        with open(temp_filename, 'w') as temp_file:
            temp_file.write(text_to_prepend)
            with open(model_filename, 'r') as model_filename:
                for line in model_filename:
                    pass


    def record_neuron_model(self, model_file, tstop=None, dt=None):
        """Simulate a NEURON model, record some variables and add their values to the recording.

        More info to come...

        Parameters
        ----------
        model_file : string
            The path to the Hoc file for the NEURON simulation.
        tstop : number
            The time to run the simulation for.
        dt : number
            The time step to use for the simulation run.

        """
        self._assert_not_created()
        try:
            import neuron
            from neuron import h
        except ImportError:
            raise _neuron_not_installed_error

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

        # TODO: This terminates Python if there are no iclamps present
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

        print 'set up iclamps'

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
        self.add_time_points(time_vector.to_python(), 'ms')
        return self
