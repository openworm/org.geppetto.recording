org.geppetto.recording
======================

Note: This is work in progress, mind your step!

This Python project creates recordings for `Geppetto <www.geppetto.org>`_. A recording is a file that contains all the raw data processed during a simulation run.
The recording files are based on the popular binary file format `HDF5 <http://www.hdfgroup.org/HDF5/>`_ (more information to come).

Installation
------------
First, make sure that you have Python 2.7 installed. On Windows, you may have to append the path of the bin folder in your Python directory to the PATH environment variable.
Then, download or clone the source code from this repository. Fire up the command line, navigate into the org.geppetto.recording folder and type::

    python setup.py install

Basic Use
---------
Now, you can import the contents of this repository in Python, for example::

    from org.geppetto.recording.creators import RecordingCreator

Create a recording
------------------

There are several options to create a recording file: You can do the handwork (supplying values, units, etc) on your own, or you can use one of our super-handy functions to create a Geppetto recording right from recordings or models from the NEURON or Brian simulator.
In every case, you need to import some of these from ``org.geppetto.recording.creators``:

* ``RecordingCreator`` The base class to write a recording for Geppetto. You can add variables and values, define a time step vector (fixed or variable) and add metadata for the recording. Call the ``create`` method to write everything to an HDF5 file.

* ``NeuronRecordingCreator`` Add recordings from the NEURON simulator or run and record a NEURON model (hoc file).

* ``BrianRecordingCreator`` Add recordings from the Brian simulator or run and record a Brian model (py file).

To represent the meta type of variables, please make also sure to import the enum ``MetaType``.

Once you have that, the basic routine to create a recording is::

    c = RecordingCreator('filename.h5')
    # add whatever you want to add here
    c.create()

More information will come soon...
