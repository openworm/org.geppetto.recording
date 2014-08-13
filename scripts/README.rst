Scripts
=======

Don't want to delve into the code? Use the **record.py** script!

It's so easy: 4 words on your command line and you can replay your NEURON and Brian simulations in Geppetto.
The script takes a model file (.hoc for NEURON - *experimental*, .py for Brian), executes it and stores all simulation data in a
Geppetto recording. Load this into Geppetto and watch your nerves lighting up!

Usage
-----

You need Python 2.7 to run the script. Furthermore, you have to have NEURON and/or Brian installed (more info soon) and
configured to work with your Python version (so, ``import neuron`` and ``import brian`` on the Python console should give
no errors).

If .py files are associated with the Python interpreter, you can run the script from the command line with::

record -neuron modelfile.hoc [recordingfile.h5]
    Execute a NEURON model (only hoc at the moment and not quite finished!) and store the simulation data to a Geppetto recording.
record -brian modelfile.py [recordingfile.h5]
    Execute a Brian model and store the simulation data to a Geppetto recording.
record help
    Show this help message.

Otherwise, replace ``record`` with ``python record.py``.
While the script is running, please close all upcoming windows that block the execution (for example plots from your model file).
