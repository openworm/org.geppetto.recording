from __future__ import absolute_import
import numpy as np
from org.geppetto.recording.creators import utils
from org.geppetto.recording.creators.base import RecordingCreator, MetaType
from org.geppetto.recording.creators.utils import *


class SPHRecordingCreator(RecordingCreator):
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

    def create_recording(self,
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

        # Read activation signals into a list of arrays
        activation_signals = []
        if is_text_file(activations_filename):  # text format for activation signals file
            with open(activations_filename, 'r') as r:
                file_content = r.read()
            for i, line in enumerate(file_content.splitlines()):
                # TODO: convert retrieved values into float
                activation_signals.append(utils.split_by_separators(line))
        else:  # Raise exception
            raise StandardError("Activation signals file is not a text file as expected.")

        # Loop through time steps in range, run one loop every sampling_factor
        for i in range(step_start, step_end+1, sampling_factor):

            # generate suffix for filename (based on arbitrary padding on file names ... )
            transform_file_suffix = utils.pad_number(i, 4)

            transformations = []
            # Read transformation file for the given time step
            if is_text_file(transforms_filename + transform_file_suffix):  # text format for activation signals file
                with open(transforms_filename + transform_file_suffix, 'r') as r:
                    file_content = r.read()

                matrices = []
                line_periodicity_idx = 0
                for j, line in enumerate(file_content.splitlines()):

                    # skip one line every transform_matrix_dimension lines
                    if line_periodicity_idx == (transform_matrix_dimension - 1):
                        line_periodicity_idx = 0
                        continue

                    # Put transformation matrices into appropriate data structures
                    matrix_lines = []
                    for k in range(0, transform_matrix_dimension):
                        # TODO: convert retrieved values into float
                        matrix_lines.append(utils.split_by_separators(line))

                    # create matrix every transform_matrix_dimension lines
                    matrix = np.matrix((transform_matrix_dimension, transform_matrix_dimension))
                    for k in range(0, transform_matrix_dimension):
                        matrix.append(matrix_lines[k])

                    # add matrix to matrices array
                    matrices.append(matrix)

                    # increase periodicity index
                    line_periodicity_idx += 1

                transformations.append(matrices)
            else:  # Raise exception
                raise StandardError("Transformations file " + i + " is not a text file as expected.")

            #TODO Add step to recording with data for given timestep
                #TODO Transformation matrices for given timestep
                #TODO Activation signals for given timestep by muscle name

        return self