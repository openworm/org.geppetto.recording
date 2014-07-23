from distutils.core import setup

setup(
    name='org.geppetto.recording',
    version='0.0.1',
    packages=['org', 'org.geppetto', 'org.geppetto.recording', 'org.geppetto.recording.test'],
    requires=['h5py', 'numpy', 'enum'],
    url='http:\\geppetto.org',
    license='MIT',
    author='matteocantarelli',
    author_email='matteo@geppetto.org',
    description='Package to create a Geppetto recording '
)
