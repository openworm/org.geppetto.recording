from distutils.core import setup

setup(
    name='org.geppetto.recording',
    version='0.0.1',
    packages=['org', 'org.geppetto', 'org.geppetto.recording', 'org.geppetto.recording.lems',
              'org.geppetto.recording.nest', 'org.geppetto.recording.brian', 'org.geppetto.recording.neuron',
              'org.geppetto.recording.sibernetic'],
    requires=['h5py', 'numpy'],
    url='http:\\geppetto.org',
    license='MIT',
    author='matteocantarelli',
    author_email='matteo@geppetto.org',
    description='Package to create a Geppetto recording '
)
