#!/usr/bin/env python

## -*-Pyth-*-
 # ###################################################################
 #  FiPy - Python-based finite volume PDE solver
 # 
 #  FILE: "boundaryCondition.py"
 #                                    created: 11/15/03 {9:47:59 PM} 
 #                                last update: 12/15/04 {4:53:56 PM} 
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
 #  2003-11-15 JEG 1.0 original
 # ###################################################################
 ##

"""Generic boundary condition base class
"""
__docformat__ = 'restructuredtext'

import Numeric

from fipy.tools.dimensions.physicalField import PhysicalField

class BoundaryCondition:
    def __init__(self,faces,value):
	"""Generic boundary condition base class.
	
	:Parameters:
	    
	    - `faces`: `list` or `tuple` of `Face` objects to which this condition applies
	    - `value`: the value to impose
	"""
        self.faces = faces
        self.value = PhysicalField(value)
	
	self.faceIds = Numeric.array([face.getID() for face in self.faces])
	self.adjacentCellIds = Numeric.array([face.getCellID() for face in self.faces])

    def buildMatrix(self, Ncells, MaxFaces, coeff):
	"""Return the effect of this boundary condition on the equation
	solution matrices.
    
	`buildMatrix()` is called by each `Term` of each `Equation`.
	
	:Parameters:
	    
	  - `Ncells`:     Number of cells (to build **L** and **b**)
	  - `MaxFaces`:   Maximum number of faces per cell (to build **L**)
	  - `coeff`:      Contribution due to this face
	
	A `tuple` of (`LL`, `bb`) is calculated, to be added to the Term's 
	(**L**, **b**) matrices.
	""" 
	pass
    
    def getFaces(self):
	"""Return the faces this boundary condition applies to.
	"""
        return self.faces
        
    def getDerivative(self, order):
	"""Return a tuple of the boundary conditions to apply
	to the term and to the derivative of the term
	"""
	if order == 0:
	    return self
	else:
	    return None


