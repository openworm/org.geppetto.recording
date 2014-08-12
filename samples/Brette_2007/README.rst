This network simulation is derived from the paper by Brette et al., 2007 [1]_. For faster processing, the number of
neurons was decreased to 200 and the runtime to 200 ms.
The original and complete simulation files (for various simulators) are accessible on ModelDB [2]_.
The recording was created using `BrianRecordingCreator.record_from_brian()`.

* COBAHH.py: Brian model and simulation, 200 neuron, 200 ms runtime, contains random elements.
* temp_model.py: The temporary, modified model that is created by `BrianRecordingCreator`.
Contains the contents of COBAHH.py with some additions and changes in order to record all variables.
* recording.h5: The recording file for Geppetto.

.. [1] Brette R, Rudolph M, Carnevale T, Hines M, Beeman D, Bower JM, Diesmann M, Morrison A, et al. (2007):
Simulation of networks of spiking neurons: A review of tools and strategies. J Comp Neurosci 23:349-98

.. [2] http://senselab.med.yale.edu/ModelDB/ShowModel.asp?model=83319