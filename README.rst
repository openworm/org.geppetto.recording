org.geppetto.recording
======================

This Python project creates recordings for `Geppetto <http://www.geppetto.org/>`_.
A recording is a file that contains all the raw data processed during a simulation run.
The recording files are based on the popular binary file format `HDF5 <http://www.hdfgroup.org/HDF5/>`_
(more information to come).

Requirements
------------

- **Python 2.7**: `Download <https://www.python.org/download>`_ and install
  (Tip: Use the 32bit version, it will save you a lot of trouble if you want to install NEURON and Brian later).
  Make sure that the *Python27* and *Python27/Scripts* directories are in your PATH environment variable.

- **Python packages** (h5py, numpy, enum34): If you use pip to install org.geppetto.recording (see below), these
  packages will be installed automatically as needed. If you want to install them manually, use pip
  (`Get it here <http://pip.readthedocs.org/en/latest/installing.html>`_).
  and type on the command line::

    pip install h5py
    pip install numpy
    pip install enum34

- **NEURON and Brian (optional)**: Required to record simulations or read binary recordings
  from `NEURON <http://www.neuron.yale.edu/neuron/>`_ or `Brian <http://briansimulator.org/>`_.
  Note that for NEURON, the standard installer is not enough - you need to be able to run ``import neuron`` or
  ``import brian``, respectively, from the Python console.
  For installation instructions, see the `Appendix: Installing NEURON and Brian`_.

Installation
------------
If you installed all requirements, use pip (`Get it here <http://pip.readthedocs.org/en/latest/installing.html>`_) to
install org.geppetto.recording::

    pip install org.geppetto.recording

Alternatively, download or clone the source code from this repository. Fire up the command line, navigate into
the org.geppetto.recording folder (the one containing this *README*) and type::

    python setup.py install

Usage
-----
Detailed instructions on how to create and replay a recording are in the
`Geppetto documentation <http://docs.geppetto.org/en/latest/recordingandreplaying.html>`_.

If you can't await it, fire up the Python console and type:

>>> from org.geppetto.recording.creators import RecordingCreator, MetaType
>>> c = RecordingCreator('recording_file.h5')
>>> c.add_values('cell.voltage', [-60.0, -59.9, -59.8], 'mV', MetaType.STATE_VARIABLE)
>>> c.set_time_step(0.1, 'ms')
>>> c.create()

This will create a simple recording named *recording_file.h5* in you current directory.
You can look at it with `HDFView <http://www.hdfgroup.org/products/java/hdfview/>`_.

Feedback
--------
Got a great idea for a new feature? Found something you don't like? We are happy to hear from you!
Get in touch through the `OpenWorm mailing list <https://groups.google.com/forum/#!forum/openworm-discuss>`_,
open an issue on `GitHub <https://github.com/openworm/org.geppetto.recording>`_ or create a fork of this repository
and start coding!

Appendix: Installing NEURON and Brian
-------------------------------------

**NEURON**

Unfortunately, the standard installer for NEURON isn't enough, you need to be able to run ``import neuron`` from the
Python console.

For OSX and Linux, there are some (unofficial)
`installers <http://neuralensemble.org/people/eilifmuller/software.html>`_ from Eilif Muller that work.

For Windows, there is the `pyNEURON <https://bitbucket.org/uric/pyneuron/wiki/Home>`_ package.
If you have pip, simply run::

    pip install pyNEURON

Note that pyNEURON only works completely with a 32bit version of Python.
If your NEURON simulation loads any of the built-in hoc files (for example nrngui, NEURON's graphical user interface),
set the NEURONHOME environment variable to the directory of your (standard) NEURON installation.
pyNEURON can then execute your model file, however, it will not actually show you the user interface!
Hence, make sure that your simulation starts without it.

At the very last resort, you can build NEURON from source (on all operating systems),
see the `instructions <http://www.neuron.yale.edu/neuron/download/getstd>`_.
Keep in mind that this is not the easiest thing to do; if possible, use any of the options above.

**Brian**

If you have pip, simply run::

    pip install brian

Note that this may not work with a 64bit version of Python. Alternatively, have a look at Brian's excellent
`installation instructions <http://www.briansimulator.org/docs/installation.html>`_. In the end, you should be able
to run ``import brian`` on the Python console.
