from distutils.core import setup

setup(
    name='org.geppetto.recording',
    version='0.0.1',
    packages=['org', 'org.geppetto', 'org.geppetto.recording', 'org.geppetto.recording.creators', 'org.geppetto.recording.creators.tests'],
    requires=['h5py', 'numpy', 'enum'],
    url='http://github.com/openworm/org.geppetto.recording',
    license='MIT',
    author='Johannes Rieke, Matteo Cantarelli',
    author_email='matteo@geppetto.org',
    description='Package to create a recording for Geppetto'
)
