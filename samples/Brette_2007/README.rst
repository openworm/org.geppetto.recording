Brette et al. 2007: Simulation of networks of spiking neurons
=============================================================

This network simulation is derived from the paper by Brette et al., 2007 [1]_. For faster processing, the number of
neurons and the runtime was decreased.
The original simulation files (for various simulators) are accessible on `ModelDB <http://senselab.med.yale.edu/ModelDB/ShowModel.asp?model=83319>`_.
The recording was created using ``BrianRecordingCreator.record_from_brian()``.

* **COBAHH.py**: Brian model and simulation, 200 neurons for 200 ms, contains random elements.
* **temp_model.py**: Temporary model that is created by ``BrianRecordingCreator``. Contains the contents of COBAHH.py with some additions and changes for recording.
* **recording.h5**: Recording file for Geppetto, simulation runtime was 200 ms.
* **recording_small.h5**: Recording file for Geppetto, simulation runtime was 10 ms (Note: Because the model contains random elements, the recordings are not the same!)

.. [1] Brette R, Rudolph M, Carnevale T, Hines M, Beeman D, Bower JM, Diesmann M, Morrison A, et al. (2007): Simulation of networks of spiking neurons: A review of tools and strategies. J Comp Neurosci 23:349-98
