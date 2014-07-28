Work in progress, bear with me.
===============================

Python project allowing to create a recording for Geppetto.

Import one of the following recording creators from `org.geppetto.recording.creators`:

* `RecordingCreator` The base class to write a recording for Geppetto. You can add variables and values, define a time step vector (fixed or variable) and add metadata for the recording. Call the `create` method to write everything to an HDF5 file.

* `NeuronRecordingCreator`

* `BrianRecordingCreator`

To represent the meta type of variables, please make also sure to import the enum `MetaType`.