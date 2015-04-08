from __future__ import absolute_import
import numpy as np
from org.geppetto.recording.creators import utils
from org.geppetto.recording.creators.base import RecordingCreator, MetaType
from org.geppetto.recording.creators.utils import *


class WormSimRecordingCreator(RecordingCreator):
    """
    A RecordingCreator that builds a recording file given SPH derived visual transformations and activation signals.

    Visual transformations are derived from a particle based simulation using the pipeline stored in this git repo:
    - https://github.com/openworm/skeletonExtraction

    Parameters
    ----------
    filename : string
        The path of the recording file that will be created.
    overwrite : boolean, optional
        If `False` (default), raise an error if `filename` exists. If `True`, overwrite it.

    """

    def __init__(self, filename, overwrite=False):
        RecordingCreator.__init__(self, filename, 'SPH', overwrite)

    def add_recording(self,
                      transforms_filename,
                      activations_filename,
                      step_start, step_end,
                      sampling_factor,
                      transform_matrix_dimension):
        """

        Parameters
        ----------
        transform_filename : string
            Path to the file + filename base for the files with visual transformations.
        activations_filename : string
            Path to the activation signals file.
        step_start : integer
            Starting timestep index.
        step_end : integer
            Ending timestep index.
        sampling_factor : integer
            Sampling factor for original source (i.e. 1 = all the steps, 10 = 1 steps every 10, etc.).
        transform_matrix_dimension : integer
            Dimension of the transformation matrix.

        Returns
        -------
        SPHRecordingCreator
            The creator itself, to allow chained method calls.

        """
        self._assert_not_created()

        self.set_time_step(0.000005*sampling_factor, 's')

        # Read activation signals into a list of arrays
        activation_signals = []
        if is_text_file(activations_filename):  # text format for activation signals file
            with open(activations_filename, 'r') as r:
                file_content = r.read()
            for i, line in enumerate(file_content.splitlines()):
                # convert retrieved values into float and append
                activation_signals.append([float(numeric_string) for numeric_string in utils.split_by_separators(line)])
        else:  # Raise exception
            raise StandardError("Activation signals file is not a text file as expected.")

        # Loop through time steps (one per file) in range, run one loop every sampling_factor
        for i in range(step_start, step_end+1, sampling_factor):

            step_transformations = []

            # generate suffix for filename (based on arbitrary padding on file names ... )
            transform_file_suffix = utils.pad_number(i, 3) + '.mat'

            # Read transformation file for the given time step
            if is_text_file(transforms_filename + transform_file_suffix):  # text format for activation signals file
                with open(transforms_filename + transform_file_suffix, 'r') as r:
                    file_content = r.read()

                line_periodicity_idx = 0
                for j, line in enumerate(file_content.splitlines()):

                    # skip one line every transform_matrix_dimension lines
                    if line_periodicity_idx == (transform_matrix_dimension):
                        line_periodicity_idx = 0
                        continue

                    # convert to float and append
                    step_transformations.append([float(numeric_string) for numeric_string in utils.split_by_separators(line)])

                    # increase periodicity index
                    line_periodicity_idx += 1
            else:  # Raise exception
                raise StandardError("Transformations file " + i + " is not a text file as expected.")

            # Add step values to recording with data for given timestep

            # 1. Transformation matrices for given timestep
            self.add_values('wormsim.mechanical.VISUALIZATION_TREE.transformation', step_transformations, 'DimensionlessUnit', MetaType.VISUAL_TRANSFORMATION)
            # 2. Activation signals for given timestep by muscle name
            for m in range(0, len(activation_signals[i])):
                self.add_values('wormsim.muscle_' + str(m) + '.mechanical.SIMULATION_TREE.activation', activation_signals[i][m], 'DimensionlessUnit', MetaType.STATE_VARIABLE)

        return self