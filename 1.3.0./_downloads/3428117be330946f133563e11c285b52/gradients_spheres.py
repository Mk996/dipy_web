"""
=====================
Gradients and Spheres
=====================

This example shows how you can create gradient tables and sphere objects using
DIPY_.

Usually, as we saw in :ref:`example_quick_start`, you load your b-values and
b-vectors from disk and then you can create your own gradient table. But
this time let's say that you are an MR physicist and you want to design a new
gradient scheme or you are a scientist who wants to simulate many different
gradient schemes.

Now let's assume that you are interested in creating a multi-shell
acquisition with 2-shells, one at b=1000 $s/mm^2$ and one at b=2500 $s/mm^2$.
For both shells let's say that we want a specific number of gradients (64) and
we want to have the points on the sphere evenly distributed.

This is possible using the ``disperse_charges`` which is an implementation of
electrostatic repulsion [Jones1999]_.
"""

import numpy as np
from dipy.core.sphere import disperse_charges, Sphere, HemiSphere

###############################################################################
# We can first create some random points on a ``HemiSphere`` using spherical
# polar coordinates.

n_pts = 64
theta = np.pi * np.random.rand(n_pts)
phi = 2 * np.pi * np.random.rand(n_pts)
hsph_initial = HemiSphere(theta=theta, phi=phi)

###############################################################################
# Next, we call ``disperse_charges`` which will iteratively move the points so
# that the electrostatic potential energy is minimized.

hsph_updated, potential = disperse_charges(hsph_initial, 5000)

###############################################################################
# In ``hsph_updated`` we have the updated ``HemiSphere`` with the points nicely
# distributed on the hemisphere. Let's visualize them.

from dipy.viz import window, actor

# Enables/disables interactive visualization
interactive = False

scene = window.Scene()
scene.SetBackground(1, 1, 1)

scene.add(actor.point(hsph_initial.vertices, window.colors.red,
                      point_radius=0.05))
scene.add(actor.point(hsph_updated.vertices, window.colors.green,
                      point_radius=0.05))

print('Saving illustration as initial_vs_updated.png')
window.record(scene, out_path='initial_vs_updated.png', size=(300, 300))
if interactive:
    window.show(scene)

###############################################################################
# .. figure:: initial_vs_updated.png
#    :align: center
#
#    Illustration of electrostatic repulsion of red points which become
#    green points.
#
# We can also create a sphere from the hemisphere and show it in the
# following way.

sph = Sphere(xyz=np.vstack((hsph_updated.vertices, -hsph_updated.vertices)))

scene.clear()
scene.add(actor.point(sph.vertices, window.colors.green, point_radius=0.05))

print('Saving illustration as full_sphere.png')
window.record(scene, out_path='full_sphere.png', size=(300, 300))
if interactive:
    window.show(scene)

###############################################################################
# .. figure:: full_sphere.png
#    :align: center
#
#    Full sphere.
#
# It is time to create the Gradients. For this purpose we will use the
# function ``gradient_table`` and fill it with the ``hsph_updated`` vectors
# that we created above.

from dipy.core.gradients import gradient_table

vertices = hsph_updated.vertices
values = np.ones(vertices.shape[0])

###############################################################################
# We need two stacks of ``vertices``, one for every shell, and we need two sets
# of b-values, one at 1000 $s/mm^2$, and one at 2500 $s/mm^2$, as we discussed
# previously.

bvecs = np.vstack((vertices, vertices))
bvals = np.hstack((1000 * values, 2500 * values))

###############################################################################
# We can also add some b0s. Let's add one at the beginning and one at the end.

bvecs = np.insert(bvecs, (0, bvecs.shape[0]), np.array([0, 0, 0]), axis=0)
bvals = np.insert(bvals, (0, bvals.shape[0]), 0)

print(bvals)

print(bvecs)

###############################################################################
# Both b-values and b-vectors look correct. Let's now create the
# ``GradientTable``.

gtab = gradient_table(bvals, bvecs)

scene.clear()

###############################################################################
# We can also visualize the gradients. Let's color the first shell blue and
# the second shell cyan.

colors_b1000 = window.colors.blue * np.ones(vertices.shape)
colors_b2500 = window.colors.cyan * np.ones(vertices.shape)
colors = np.vstack((colors_b1000, colors_b2500))
colors = np.insert(colors, (0, colors.shape[0]), np.array([0, 0, 0]), axis=0)
colors = np.ascontiguousarray(colors)

scene.add(actor.point(gtab.gradients, colors, point_radius=100))

print('Saving illustration as gradients.png')
window.record(scene, out_path='gradients.png', size=(300, 300))
if interactive:
    window.show(scene)

###############################################################################
# .. figure:: gradients.png
#    :align: center
#
#    Diffusion gradients.
#
# References
# ----------
#
# .. [Jones1999] Jones, DK. et al. Optimal strategies for measuring diffusion
#    in anisotropic systems by magnetic resonance imaging, Magnetic Resonance
#    in Medicine, vol 42, no 3, 515-525, 1999.
#
# .. include:: ../links_names.inc
