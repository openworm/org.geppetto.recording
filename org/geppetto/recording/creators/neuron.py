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

    More info to come...

    Parameters
    ----------
    filename : string
        The path to the recording file that will be created.
    overwrite : boolean, optional
        If `False` (default), raise an error if `filename` exists. If `True`, overwrite it.

    """

    def __init__(self, filename, overwrite=False):
        RecordingCreator.__init__(self, filename, 'NEURON', overwrite)

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
            variable_units = utils.make_iterable(variable_units)
        if variable_labels:
            variable_labels = utils.make_iterable(variable_labels)

        if utils.is_text_file(recording_file):  # text file
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
                    items = utils.split_by_separators(line)
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
                    items = utils.split_by_separators(line)
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
            _assert_neuron_imported()
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
                raise IOError("Binary file could not be parsed (or is empty): " + recording_file)
        return self

    # TODO: Use STATE_VARIABLE as default meta_type?
    def add_vector(self, name, neuron_vector, unit=None, meta_type=None):
        """Add all the values from a NEURON vector to the recording.

        Parameters
        ----------
        name : string
            The name of the variable.
            A dot separated name creates a hierarchy in the file (for example `poolroom.table.ball.x`).
        neuron_vector : neuron.h.Vector
            Vector whose values to add. Will be appended to existing values. If `meta_type` is
            STATE_VARIABLE, the values will be associated with successive time points.
        unit : string, optional
            The unit of the variable. If `None` (default), the unit from a previous definition of this variable
            will be used.
        meta_type : {MetaType.STATE_VARIABLE, MetaType.PARAMETER, MetaType.PROPERTY, MetaType.EVENT}, optional
            The type of the variable. If `None` (default), the meta type from a previous definition of this variable
            will be used.
        """
        self._assert_not_created()
        _assert_neuron_imported()
        self.add_values(name, neuron_vector.to_python(), unit, meta_type)
        return self

    # TODO: Successive calls of this method could keep populating allsec.
    def record_model(self, model_filename, tstop=None, dt=None, is_py=None):
        # TODO: Update.
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
        _assert_neuron_imported()

        if is_py is None:
            extension = os.path.splitext(model_filename)[1]
            if extension == '.hoc':
                is_py = False
            elif extension == '.py':
                is_py = True
            else:
                raise ValueError("Could not recognize file extension, set `is_py` False for hoc or True for py")

        if is_py:
            vars_dict = utils.run_as_script(model_filename)
            try:
                model_h = vars_dict['h']
            except KeyError:
                raise RuntimeError("Could not find neuron.h from the model file")
        else:
            h.load_file(os.path.abspath(model_filename).replace('\\', '/'))  # needs slashes, also on Windows
            model_h = h

        time_vector = h.Vector()
        time_vector.record(h._ref_t)
        vectors = {}

        def add_vectors_for_variables(obj, obj_name, ignore_variables=None):
            if ignore_variables is None:
                ignore_variables = []
            for attr in dir(obj):
                if not attr.startswith('__') and attr not in ignore_variables:
                    try:
                        ref = getattr(segment, '_ref_' + attr)
                    except NameError:
                        pass
                    except AttributeError:
                        pass  # no state variable
                    else:
                        vec = model_h.Vector()
                        vec.record(ref)
                        vectors[obj_name + '.' + attr] = vec

        # TODO: Add static values as properties and ignore them for vectors.
        for section in model_h.allsec():
            # TODO: Is this always um?
            self.add_values(section.name() + '.L', section.L, 'um', MetaType.PROPERTY)
            add_vectors_for_variables(section, section.name())

            unformatted_segment_name = section.name() + '.segment{0}'
            for i, segment in enumerate(section):
                segment_name = unformatted_segment_name.format(i)
                add_vectors_for_variables(segment, segment_name)
                #self.add_values(segment_label + '.diam', segment.diam, 'um', MetaType.PROPERTY)

                for mechanism in segment:
                    # TODO: Handle mechanism attributes like hh.n_hh.
                    add_vectors_for_variables(mechanism, segment_name + '.' + mechanism.name())

                # TODO: Look at point processes
                # for point_process in segment.point_processes():
                #     print 'found:', point_process

        # access point processes (here: of type IClamp), see http://www.neuron.yale.edu/phpbb/viewtopic.php?f=8&t=186
        # TODO: How to do this in Python natively?
        # TODO: How to dereference to section (see URL above)?
        # TODO: How/where to store this in HDF5?
        # TODO: Synapses
        # h('objref listIClamps')
        # h('listIClamps = new List("IClamp")')
        #
        # # TODO: This terminates Python if there are no iclamps present
        # i_clamps = h.listIClamps
        #
        #
        # for i, i_clamp in enumerate(i_clamps):
        #     label = 'i_clamp_' + str(i)
        #     self.add_values(label + '.dur', i_clamp.dur, 'ms', MetaType.PARAMETER)
        #     self.add_values(label + '.del', i_clamp.delay, 'ms', MetaType.PARAMETER)
        #     self.add_values(label + '.amp', i_clamp.amp, 'mA', MetaType.PARAMETER)
        #     vector_i = h.Vector()
        #     vector_i.record(i_clamp._ref_i)
        #     vectors.append(vector_i)
        #     #print i_clamp.Section
        #     # TODO: Get i_clamp name
        #     labels.append(label + '.i')
        #
        # print 'set up iclamps'

        if tstop is None:
            try:
                tstop = model_h.tstop
            except AttributeError:
                tstop = 5

        if dt is not None:
            model_h.dt = dt

        print 'Running for', tstop, 'ms with timestep', model_h.dt, 'ms'

        neuron.init()
        neuron.run(tstop)

        for name, vector in vectors.iteritems():
            # TODO: Extract unit
            self.add_vector(name, vector, '', MetaType.STATE_VARIABLE)

        self.add_time_points(time_vector.to_python(), 'ms')

        # TODO: Return self?


    # TODO: Old code, look through what's still needed and clean up.
    # def record_neuron_py_model(self, model_filename):
    #     """In development, do not use.
    #     You need to do init() before run(), otherwise state variables can not be recorded."""
    #     self._assert_not_created()
    #
    #     # TODO: Do this in common method: Parse hoc or py model depending on `file_extension`
    #     # try:
    #     #     file_extension = model_filename[model_filename.rindex('.')+1:]
    #     #     if file_extension == 'hoc':
    #     #         pass
    #     #     elif file_extension == 'py':
    #     #         pass
    #     #     else:
    #     #         pass
    #     # except ValueError:
    #     #     pass
    #
    #     _assert_neuron_imported()
    #
    #     model_abspath = os.path.abspath(model_filename)
    #     model_dirname = os.path.dirname(model_abspath)
    #
    #     # TODO: This is a workaround because time_vector cannot be referenced in the inner func trace_model. Fix it!
    #     time_vector = []
    #     objects = []  # sections, segments, mechanisms, point processes, ...
    #     names = []
    #     vector_dicts = []
    #
    #     # def append_object(hoc_obj):
    #     #     objects.append(hoc_obj)
    #     #     for variable in variables:
    #     #         try:
    #     #             ref = getattr(hoc_obj, '_ref_'+variable)
    #     #         except AttributeError:
    #     #             pass  # object does not have this attribute
    #     #         else:
    #     #             vector = h.Vector()
    #     #             vector.record(ref)
    #     #             # TODO: Store vector and object, and possibly name.
    #
    #     def trace_model(frame, event, arg):
    #         # print '----------------------------------'
    #         # filename, lineno, function, code_context, index = inspect.getframeinfo(frame)
    #         # print 'File:', filename
    #         # print 'Code:', code_context
    #
    #         if os.path.abspath(frame.f_code.co_filename) == model_abspath:
    #             try:
    #                 # TODO: Maybe this is not required as h can also be accessed from here.
    #                 model_h = frame.f_locals['h']
    #             except KeyError:
    #                 pass  # `h` not found
    #             else:
    #                 # TODO: Avoid global access
    #                 #global time_vector
    #                 if not time_vector:
    #                     try:
    #                         vec = model_h.Vector()
    #                         vec.record(model_h._ref_t)
    #                     except RuntimeError:
    #                         pass  # time cannot be accessed at the beginning
    #                     else:
    #                         time_vector.append(vec)
    #
    #                 print 'Found h; all sections:'
    #                 for section in model_h.allsec():
    #                     print section.name()
    #                     for i, segment in enumerate(section):
    #                         print '\tSegment', i
    #                         try:
    #                             index = objects.index(segment)
    #                         except ValueError:  # new section
    #                             vector_dict = {}
    #                             for attr in dir(segment):
    #                                 if not attr.startswith('__'):  # ignore magic functions
    #                                     try:
    #                                         ref = getattr(segment, '_ref_' + attr)
    #                                     except NameError:
    #                                         pass
    #                                     except AttributeError:
    #                                         pass  # no state variable
    #                                     except RuntimeError:
    #                                         print 'RuntimeError when accessing variable:', attr
    #                                     else:
    #                                         vector = model_h.Vector()
    #                                         vector.record(ref)
    #                                         vector_dict[attr] = vector
    #                             objects.append(segment)
    #                             name = section.name() + '.Segment' + str(i)
    #                             names.append(name)  # TODO: Search for name in f_locals
    #                             print 'Added name:', name
    #                             vector_dicts.append(vector_dict)
    #                         else:  # known section
    #                             vector_dict = vector_dicts[index]
    #                             for attr in dir(segment):
    #                                 if not attr.startswith('__') and attr not in vector_dict:  # ignore magic functions
    #                                     try:
    #                                         ref = getattr(section, '_ref_' + attr)
    #                                     except NameError:
    #                                         pass
    #                                     except AttributeError:
    #                                         pass  # no state variable
    #                                     except RuntimeError:
    #                                         print 'RuntimeError when accessing variable:', attr
    #                                     else:
    #                                         vector = model_h.Vector()
    #                                         vector.record(ref)
    #                                         vector_dict[attr] = vector
    #
    #
    #                     # TODO: Maybe store `section.name() + '.' + variable` as name.
    #                     # for i, segment in enumerate(section):
    #                     #     check_variables(segment)
    #                     #     # TODO: Store `section.name() + '.' + 'Segment' + str(i) + '.' + variable` as name.
    #                     #     for mechanism in segment:
    #                     #         check_variables()
    #
    #                     # try:
    #                     #     print '\tL:', sec.L
    #                     #     print '\tnseg:', sec.nseg
    #                     #     for seg in sec:
    #                     #         print '\t\tx:', seg.x
    #                     #         print '\t\tmembers:', dir(seg)
    #                     #         for mech in seg:
    #                     #             print '\t\t\tmechanism:', mech.name(), ':', mech
    #                     # except AttributeError:
    #                     #     pass
    #
    #
    #         return trace_model
    #     #
    #     #             for section in model_h.allsec():
    #     #                 if section not in objects:
    #     #                     objects.append(section)
    #     #
    #     #                 self.add_values(section.name() + '.L', section.L, 'um', MetaType.PROPERTY)
    #     #                 for segment in section:
    #     #         segment_label = section.name() + '.segmentAt' + str(segment.x).replace('.', '_')
    #     #         self.add_values(segment_label + '.diam', segment.diam, 'um', MetaType.PROPERTY)
    #     #         vector_v = h.Vector()
    #     #         vector_v.record(segment._ref_v)
    #     #         vectors.append(vector_v)
    #     #         labels.append(segment_label + '.v')
    #     #         #print 'has public attributes: ', [a for a in dir(segment) if not a[:1] == '_']
    #     #         #print dir(segment.point_processes)
    #     #         #for point_process in segment.point_processes():
    #     #             #print 'found:', point_process
    #     #     print section.name() + ' (' + str(section)
    #     #
    #     # print '-> set up ' + str(len(vectors)) + ' vectors'
    #     #
    #     # # access point processes (here: of type IClamp), see http://www.neuron.yale.edu/phpbb/viewtopic.php?f=8&t=186
    #     # # TODO: How to do this in Python natively?
    #     # # TODO: How to dereference to section (see URL above)?
    #     # # TODO: How/where to store this in HDF5?
    #     # # TODO: Synapses
    #     # h('objref listIClamps')
    #     # h('listIClamps = new List("IClamp")')
    #     #
    #     # # TODO: This terminates Python if there are no iclamps present
    #     # i_clamps = h.listIClamps
    #     #
    #     #
    #     # for i, i_clamp in enumerate(i_clamps):
    #     #     label = 'i_clamp_' + str(i)
    #     #     self.add_values(label + '.dur', i_clamp.dur, 'ms', MetaType.PARAMETER)
    #     #     self.add_values(label + '.del', i_clamp.delay, 'ms', MetaType.PARAMETER)
    #     #     self.add_values(label + '.amp', i_clamp.amp, 'mA', MetaType.PARAMETER)
    #     #     vector_i = h.Vector()
    #     #     vector_i.record(i_clamp._ref_i)
    #     #     vectors.append(vector_i)
    #     #     #print i_clamp.Section
    #     #     # TODO: Get i_clamp name
    #     #     labels.append(label + '.i')
    #     #
    #     # print 'set up iclamps'
    #     #
    #     #
    #     #     # if event == 'call'and frame.f_code.co_name == 'run':
    #     #     #     # TODO: What other run commands are there?
    #     #     #     print 'Reached run...'
    #     #     #     # Has access to h and hence to everything in the model file here (probably due to h being a global object in neuron).
    #     #     #     # TODO: This actually means I only have to listen for run commands and then process the sections etc.
    #     #     #     print 'Accessing sections from outside:'
    #     #     #     for sec in h.allsec():
    #     #     #         print sec.name(), sec.L
    #     #     #     # TODO: Set up vectors.
    #     #     #     return None
    #     #     print '----------------------------------\n'
    #
    #     '''
    #     for seg in sec :   # iterates over the section compartments
    #         for mech in seg : # iterates over the segment mechanisms
    #             print sec.name(), seg.x, mech.name()
    #     '''
    #
    #
    #
    #     # Append directory of the model file to system path (enables the model file to import local modules)
    #     # and change Python's working directory to this directory (enables the model file to execute local files).
    #     sys.path.append(model_dirname)
    #     old_cwd = os.getcwd()
    #     os.chdir(model_dirname)
    #
    #     sys.settrace(trace_model)
    #     #h.load_file(model_abspath.replace('\\', '/'))
    #     runpy.run_path(model_abspath, run_name='__main__', )
    #     sys.settrace(None)
    #
    #     # Revert the changes affecting the system path and working directory (see above).
    #     os.chdir(old_cwd)
    #     sys.path.remove(model_dirname)
    #
    #     print 'Simulation finished, processing vectors...'
    #     for name, vector_dict in zip(names, vector_dicts):
    #         print '\tObject:', name
    #         for variable, vector in vector_dict.iteritems():
    #             print '\t\tVariable:', variable
    #             # TODO: Get unit, maybe by looking at variable name?
    #             self.add_vector(name + '.' + variable, vector, '', MetaType.STATE_VARIABLE)
    #     print 'Finished processing'
    #
    #     # TODO: Add recorded time.
    #     self.set_time_step(0.1, 'ms')

