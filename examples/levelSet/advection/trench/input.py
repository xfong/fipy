#!/usr/bin/env python

## 
 # ###################################################################
 #  FiPy - Python-based finite volume PDE solver
 # 
 #  FILE: "input.py"
 #                                    created: 11/17/03 {10:29:10 AM} 
 #                                last update: 3/7/05 {1:37:51 PM} { 1:23:41 PM}
 #  Author: Jonathan Guyer <guyer@nist.gov>
 #  Author: Daniel Wheeler <daniel.wheeler@nist.gov>
 #  Author: James Warren   <jwarren@nist.gov>
 #    mail: NIST
 #     www: http://www.ctcms.nist.gov/fipy/
 #  
 # ========================================================================
 # This software was developed at the National Institute of Standards
 # and Technology by employees of the Federal Government in the course
 # of their official duties.  Pursuant to title 17 Section 105 of the
 # United States Code this software is not subject to copyright
 # protection and is in the public domain.  FiPy is an experimental
 # system.  NIST assumes no responsibility whatsoever for its use by
 # other parties, and makes no guarantees, expressed or implied, about
 # its quality, reliability, or any other characteristic.  We would
 # appreciate acknowledgement if the software is used.
 # 
 # This software can be redistributed and/or modified freely
 # provided that any derivative works bear some notice that they are
 # derived from it, and any modified versions bear some notice that
 # they have been modified.
 # ========================================================================
 #  
 #  Description: 
 # 
 #  History
 # 
 #  modified   by  rev reason
 #  ---------- --- --- -----------
 #  2003-11-17 JEG 1.0 original
 # ###################################################################
 ##

"""

This example creates a trench with the following zero level set:

.. raw:: latex

    $$ \\phi \\left( x, y \\right) = 0 \;\; \\text{when} \;\; y = L_y / 5 \\text{and} x \ge L_x / 2 $$
    $$ \\phi \\left( x, y \\right) = 0 \;\; \\text{when} \;\; L_y / 5 \le y \le 3 Ly / 5  \\text{and} x = L_x / 2 $$
    $$ \\phi \\left( x, y \\right) = 0 \;\; \\text{when} \;\; y = 3 Ly / 5  \\text{and} x \le L_x / 2 $$

The trench is then advected with a unit velocity. The following test can be made
for the initial position of the interface:

   >>> x = mesh.getCellCenters()[:,0]
   >>> y = mesh.getCellCenters()[:,1]
   >>> r1 =  -Numeric.sqrt((x - Lx / 2)**2 + (y - Ly / 5)**2)
   >>> r2 =  Numeric.sqrt((x - Lx / 2)**2 + (y - 3 * Ly / 5)**2)
   >>> d = Numeric.zeros((len(x),3), 'd')
   >>> d[:,0] = Numeric.where(x >= Lx / 2, y - Ly / 5, r1)
   >>> d[:,1] = Numeric.where(x <= Lx / 2, y - 3 * Ly / 5, r2)
   >>> d[:,2] = Numeric.where(Numeric.logical_and(Ly / 5 <= y, y <= 3 * Ly / 5), x - Lx / 2, d[:,0])
   >>> argmins = Numeric.argmin(Numeric.absolute(d), axis = 1)
   >>> answer = Numeric.take(d.flat, Numeric.arange(len(argmins))*3 + argmins)
   >>> solution = Numeric.array(var)
   >>> Numeric.allclose(answer, solution, atol = 1e-1)
   1

Advect the interface and check the position.

   >>> for step in range(steps):
   ...     var.updateOld()
   ...     advEqn.solve(var, dt = timeStepDuration)

   >>> distanceMoved = timeStepDuration * steps * velocity
   >>> answer = answer - distanceMoved
   >>> solution = Numeric.array(var)
   >>> answer = Numeric.where(answer < 0., 0., answer)
   >>> solution = Numeric.where(solution < 0., 0., solution)
   >>> Numeric.allclose(answer, solution, atol = 1e-1)
   1
 
"""
__docformat__ = 'restructuredtext'

import Numeric
   
from fipy.meshes.grid2D import Grid2D
from fipy.models.levelSet.distanceFunction.distanceVariable import DistanceVariable
from fipy.models.levelSet.advection.advectionEquation import buildAdvectionEquation

height = 0.5
Lx = 0.4
Ly = 1.
dx = 0.01
velocity = 1.
cfl = 0.1

nx = int(Lx / dx)
ny = int(Ly / dx)
timeStepDuration = cfl * dx / velocity
steps = 200

mesh = Grid2D(dx = dx, dy = dx, nx = nx, ny = ny)

values = -Numeric.ones(nx * ny, 'd')

positiveCells = mesh.getCells(lambda cell: (cell.getCenter()[1] > 0.6 * Ly) or (cell.getCenter()[1] > 0.2 * Ly and cell.getCenter()[0] > 0.5 * Lx))
for cell in positiveCells:
    values[cell.getID()] = 1.

var = DistanceVariable(
    name = 'level set variable',
    mesh = mesh,
    value = values
    )

var.calcDistanceFunction()

advEqn = buildAdvectionEquation(velocity)
                        
if __name__ == '__main__':
    import fipy.viewers
    viewer = fipy.viewers.make(vars = var, limits = {'datamin': -0.1, 'datamax': 0.1})

    viewer.plot()

    for step in range(steps):
        var.updateOld()
        advEqn.solve(var, dt = timeStepDuration)
        viewer.plot()

    raw_input('finished')
