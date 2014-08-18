"""Implementation of the NEURON model in sthB.hoc for Python."""

import neuron
from neuron import h

h.load_file("nrngui.hoc")

num_dendrites = 2
soma = h.Section()
dendrites = [h.Section() for i in range(num_dendrites)]
soma.push()

soma.nseg = 1
soma.diam = 18.8
soma.L = 18.8
soma.Ra = 123.0
soma.insert('hh')
soma.gnabar_hh = 0.25
soma.gl_hh = 0.0001666
soma.el_hh = -60.0

dendrites[0].nseg = 5
dendrites[0].diam = 3.18
dendrites[0].L = 701.9
dendrites[0].Ra = 123

dendrites[1].nseg = 5
dendrites[1].diam = 2.0
dendrites[1].L = 549.1
dendrites[1].Ra = 123

for dendrite in dendrites:
    dendrite.insert('pas')
    dendrite.g_pas = .0001667
    dendrite.e_pas = -60.0

dendrites[0].connect(soma, 0, 0)
dendrites[1].connect(soma, 0, 1)

stimulus = h.IClamp(dendrites[0](0.5))
stimulus.delay = 100
stimulus.dur = 100
stimulus.amp = 0.1

# neuron.init()
# neuron.run(300)
# print "Final soma voltage:", soma.v