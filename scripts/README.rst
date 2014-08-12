Super-handy Scripts
===================

The **record.py** script is an easy way to replay a simulation from NEURON or Brian in Geppetto.
It executes your model file (.hoc for NEURON, .py for Brian), records all variables and stores their values
in a Geppetto recording. This file can then be loaded and replayed in Geppetto.

Use
---

You need Python 2.7 to run the script. Furthermore, you have to have NEURON and/or Brian installed (more info soon) and
configured to work with your Python version (so, ``import neuron`` and ``import brian`` on the Python console should give
no errors).

Then, you can run the script from the command line with::

python record.py -neuron modelfile.hoc [recordingfile.h5]
    Execute a NEURON model (only hoc at the moment!) and store the simulation data to a Geppetto recording.
python record.py -brian modelfile.py [recordingfile.h5]
    Execute a Brian model and store the simulation data to a Geppetto recording.
python record.py help
    Show this help message.


