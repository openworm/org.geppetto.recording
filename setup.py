try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

LONG_DESCRIPTION = """This Python project creates recordings for `Geppetto <http://www.geppetto.org/>`_.
A recording is a file that contains all the raw data processed during a simulation run.
The recording files are based on the popular binary file format `HDF5 <http://www.hdfgroup.org/HDF5/>`_.

For more information on installation and usage visit our
`GitHub repository <http://github.com/openworm/org.geppetto.recording>`_."""

setup(
    name='org.geppetto.recording',
    version='0.0.1',
    packages=['org', 'org.geppetto', 'org.geppetto.recording', 'org.geppetto.recording.creators'],
    scripts=['scripts/record.py'],
    install_requires=['numpy', 'h5py', 'enum34'],
    url='http://github.com/openworm/org.geppetto.recording',
    download_url='http://github.com/openworm/org.geppetto.recording/tarball/0.0.1',
    license='MIT',
    author='Johannes Rieke, Matteo Cantarelli',
    author_email='matteo@geppetto.org',
    description='Package to create a recording for Geppetto',
    long_description=LONG_DESCRIPTION,
    keywords=['simulation', 'neuroscience', 'recording', 'neuron', 'brian']
)
