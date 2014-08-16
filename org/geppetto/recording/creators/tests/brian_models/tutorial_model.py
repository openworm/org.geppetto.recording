'''
Model inspired by the Brian tutorial at http://www.briansimulator.org/docs/tutorial_1f_recording_spikes.html
'''

from brian import *
import numpy

tau = 20 * msecond        # membrane time constant
Vt = -50 * mvolt          # spike threshold
Vr = -60 * mvolt          # reset value
El = -49 * mvolt          # resting potential (same as the reset)
psp = 0.5 * mvolt         # postsynaptic potential size

num_neurons = 5

G = NeuronGroup(N=num_neurons, model='dV/dt = -(V-El)/tau : volt', threshold=Vt, reset=Vr)
G.V = Vr + numpy.linspace(0., 1., num_neurons) * (Vt - Vr)  # slightly increasing initial potential

G_sub = G.subgroup(2)
#G_link = G
#H = NeuronGroup(N=5, model='dV/dt = -(V-El)/tau : volt', threshold=Vt, reset=Vr)

C = Connection(G, G)
C.connect_random(sparseness=0.1, weight=psp)

#execfile('sub_model.py')

N = Network(G, C)#, sub_group)
#N2 = Network(G, C)

run(0.1 * second)