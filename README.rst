org.geppetto.recording
======================

Note: This is work in progress, mind your step!

This Python project creates recordings for `Geppetto <www.geppetto.org>`_. A recording is a file that contains all the raw data processed during a simulation run.
The recording files are based on the popular binary file format `HDF5 <http://www.hdfgroup.org/HDF5/>`_ (more information to come).

Requirements
------------

* Python 2.7: `Download <https://www.python.org/download>`_ and install (Tip: Using a 32bit version of Python will save you a lot of trouble, especially if you install NEURON and Brian below). Make sure that the `Python27` and `Python27/Scripts` directories are in your PATH environment variable or append them.
* Python packages: The simplest way to install additional Python packages is through pip (`Install information <http://pip.readthedocs.org/en/latest/installing.html>`_). If you have it, go to the command line and type::

pip install h5py
pip install numpy
pip install enum

* NEURON (optional): Required to record NEURON simulations and read binary recordings from NEURON. You need a NEURON version that you can import from Python - unfortunately, the standard installer for NEURON won't do. For OSX and Linux, there are some (unofficial) `installers <http://neuralensemble.org/people/eilifmuller/software.html>`_ from Eilif Muller that enable this. For Windows, there is the `pyNEURON <https://bitbucket.org/uric/pyneuron/wiki/Home>`_ package (only works for 32bit version of Python). If you have pip (see above), simply run ``pip install pyNEURON`` (some things may only work with a 32bit version of Python). If your model loads any of the built-in NEURON hoc files (for example nrngui, NEURON's graphical user interface), set the NEURONHOME environment variable to the directory of your (standard) NEURON installation. pyNEURON can then execute your model file, however, it will not actually show you the user interface! Hence, make sure that your simulation run starts without it. At the last resort you can build NEURON from source (on all operating systems), see the `instructions <http://www.neuron.yale.edu/neuron/download/getstd>`_. To check if it works, open the Python console and type ``import neuron``.
* Brian (optional): Required to record Brian simulations and read binary recordings from Brian. If you have `pip` (see above), simply run ``pip install brian`` (can give problems with 64bit versions of Python), or have a look at the `installation instructions <http://www.briansimulator.org/docs/installation.html>_`. To check if it works, open the Python console and type ``import brian``.

Installation
------------
If you installed all requirements, download or clone the source code from this repository. Fire up the command line, navigate into the org.geppetto.recording folder (the one containing this README) and type::

    python setup.py install

Basic Use
---------
Now, you can import the contents of this repository in Python, for example::

    from org.geppetto.recording.creators import RecordingCreator

Create a recording
------------------

There are several options to create a recording file: You can do the handwork (supplying values, units, etc) on your own, or you can use one of our super-handy functions to create a Geppetto recording right from recordings or models from the NEURON or Brian simulator.
In every case, you need to import some of these from ``org.geppetto.recording.creators``:

* ``RecordingCreator`` The base class to write a recording for Geppetto. You can add variables and values, define a time step vector (fixed or variable) and add metadata for the recording.

* ``NeuronRecordingCreator`` Add recordings from the NEURON simulator or run and record a NEURON model (hoc file).

* ``BrianRecordingCreator`` Add recordings from the Brian simulator or run and record a Brian model (py file).

To represent the meta type of variables, please make also sure to import the enum ``MetaType``.

Once you have that, the basic routine to create a recording is::

    c = RecordingCreator('filename.h5')
    # add whatever you want to add here
    c.create()

More information will come soon...
