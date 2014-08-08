from __future__ import absolute_import
import numpy as np
from org.geppetto.recording.creators.base import RecordingCreator, MetaType, is_text_file


_brian_not_installed_error = ImportError("You have to install the brian package to use this method")


class BrianRecordingCreator(RecordingCreator):
    """
    Work in progress...
    """

    def __init__(self, filename):
        RecordingCreator.__init__(self, filename, 'Brian')

    def add_brian_recording(self, recording_file, neuron_group_label=None):
        # TODO: Use variable_labels_prefix instead of neuron_group_label?
        """
        Read a file that contains a recording from the brian simulator and add its contents to the current recording.
        The file can be created using brian's FileSpikeMonitor or AERSpikeMonitor.

        Parameters
        ----------
        recording_file : string
            Path to the file that should be added
        neuron_group_label : string
            Label for the neuron group of these values. If supplied, the values will be stored as `neuron_group_label.neuron123.spikes`, otherwise as `neuron123.spikes`, for example.
        """

        # TODO: Add exceptions if file can not be parsed
        if is_text_file(recording_file):
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
            try:
                import brian
            except ImportError:
                raise _brian_not_installed_error
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
            neuron_label = 'neuron' + str(index) + '.spikes'
            if neuron_group_label:
                neuron_label = neuron_group_label + '.' + neuron_label
            self.add_values(neuron_label, spike_list, 'ms', MetaType.EVENT)

    def record_brian_model(self):
        try:
            import brian
        except ImportError:
            raise _brian_not_installed_error
        raise NotImplementedError("I'm waiting for someone to implement me")

