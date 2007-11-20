## -*-Pyth-*-
 # #############################################################################
 # FiPy - a finite volume PDE solver in Python
 # 
 # FILE: "operatorVariable.py"
 #                                     created: 5/6/07 {10:53:26 AM}
 #                                 last update: 11/2/07 {3:44:31 PM}
 # Author: Jonathan Guyer <guyer@nist.gov>
 # Author: Daniel Wheeler <daniel.wheeler@nist.gov>
 # Author: James Warren   <jwarren@nist.gov>
 #   mail: NIST
 #    www: <http://www.ctcms.nist.gov/fipy/>
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
 # #############################################################################
 ##

from fipy.variables.variable import Variable

def _OperatorVariableClass(baseClass=None):
    class _OperatorVariable(baseClass):
        def __init__(self, op, var, opShape=(), canInline=True, unit=None, *args, **kwargs):
            self.op = op
            self.var = var
            self.opShape = opShape
            self.unit = unit
            self.canInline = canInline  #allows for certain functions to opt out of --inline
            baseClass.__init__(self, value=None, *args, **kwargs)
            self.name = ''
            for var in self.var:    #C does not accept units
                if not var.getUnit().isDimensionless():
                    self.canInline = False
                    break

            for aVar in self.var:
                self._requires(aVar)
            
            self.dontCacheMe()

        def _calcValue(self):
            if not self.canInline:
                return self._calcValuePy()
            else:
                from fipy.tools.inline import inline
                return inline._optionalInline(self._calcValueIn, self._calcValuePy)

        def _calcValueIn(self):
            return self._execInline()

        def _calcValuePy(self):
            pass

        def _isCached(self):
            return (Variable._isCached(self) 
                    or (len(self.subscribedVariables) > 1 and not self._cacheNever))

        def _getCstring(self, argDict={}, id="", freshen=False):
            if self.canInline: # and not self._isCached():
                s = self._getRepresentation(style="C", argDict=argDict, id=id, freshen=freshen)
            else:
                s = baseClass._getCstring(self, argDict=argDict, id=id)
            if freshen:
                self._markFresh()
              
            return s
                
        def _getRepresentation(self, style="__repr__", argDict={}, id=id, freshen=False):
            """

            :Parameters:
                
              - `style`: one of `'__repr__'`, `'name'`, `'TeX'`, `'C'`

            """
            import opcode
            
            bytecodes = [ord(byte) for byte in self.op.func_code.co_code]
                
            def _popIndex():
                return bytecodes.pop(0) + bytecodes.pop(0) * 256
            
            stack = []
                
            unop = {
                10: "+", 11: "-", 12: "not ", 15: "~"
            }
            
            binop = {
                19: "**", 20: "*", 21: "/", 22: "%", 23: "+", 24: "-", 26: "//", 27: "/",
                        62: "<<", 63: ">>", 64: "&", 65: "^", 66: "|", 106: "=="
            }
            
            while len(bytecodes) > 0:
                bytecode = bytecodes.pop(0)
                if opcode.opname[bytecode] == 'UNARY_CONVERT':
                    stack.append("`" + stack.pop() + "`")
                elif opcode.opname[bytecode] == 'BINARY_SUBSCR':
                    stack.append(stack.pop(-2) + "[" + stack.pop() + "]")
                elif opcode.opname[bytecode] == 'RETURN_VALUE':
                    s = stack.pop()
                    if style == 'C':
                        return s.replace('numerix.', '').replace('arc', 'a')
                    else:
                        return s
                elif opcode.opname[bytecode] == 'LOAD_CONST':
                    stack.append(self.op.func_code.co_consts[_popIndex()])
                elif opcode.opname[bytecode] == 'LOAD_ATTR':
                    stack.append(stack.pop() + "." + self.op.func_code.co_names[_popIndex()])
                elif opcode.opname[bytecode] == 'COMPARE_OP':
                    stack.append(stack.pop(-2) + " " + opcode.cmp_op[_popIndex()] + " " + stack.pop())
                elif opcode.opname[bytecode] == 'LOAD_GLOBAL':
                    counter = _popIndex()
                    stack.append(self.op.func_code.co_names[counter])
                elif opcode.opname[bytecode] == 'LOAD_FAST':
                    if style == "__repr__":
                        stack.append(repr(self.var[_popIndex()]))
                    elif style == "name":
                        v = self.var[_popIndex()]
                        if isinstance(v, Variable):
                            name = v.getName()
                            if len(name) > 0:
                                stack.append(name)
                            else:
                                # The string form of a variable
                                # would probably be too long and messy.
                                # Just give shorthand.
                                stack.append("%s(...)" % v.__class__.__name__)
                        elif type(v) in (type(1), type(1.)):
                            stack.append(repr(v))
                        else:
                            # The string form of anything but a
                            # number would be too long and messy.
                            # Just give shorthand.
                            stack.append("<...>")
                    elif style == "TeX":
                        raise Exception, "TeX style not yet implemented"
                    elif style == "C":
                        counter = _popIndex()
                        if not self.var[counter]._isCached():
                            stack.append(self.var[counter]._getCstring(argDict, id=id + str(counter), freshen=freshen))
                            self.var[counter].value = None
                        else:
                            stack.append(self.var[counter]._getVariableClass()._getCstring(self.var[counter], argDict, \
                                                                                           id=id + str(counter),\
                                                                                           freshen=False))
                    else:
                        raise SyntaxError, "Unknown style: %s" % style
                elif opcode.opname[bytecode] == 'CALL_FUNCTION':    
                    args = []
                    for j in range(bytecodes.pop(1)):
                        # keyword parameters
                        args.insert(0, stack.pop(-2) + " = " + stack.pop())
                    for j in range(bytecodes.pop(0)):
                        # positional parameters
                        args.insert(0, stack.pop())
                    stack.append(stack.pop() + "(" + ", ".join(args) + ")")
                elif opcode.opname[bytecode] == 'LOAD_DEREF':
                    free = self.op.func_code.co_cellvars + self.op.func_code.co_freevars
                    stack.append(free[_popIndex()])
                elif unop.has_key(bytecode):
                    stack.append(unop[bytecode] + '(' + stack.pop() + ')')
                elif binop.has_key(bytecode):
                    stack.append(stack.pop(-2) + " " + binop[bytecode] + " " + stack.pop())
                else:
                    raise SyntaxError, "Unknown bytecode: %s in %s: %s" % (`bytecode`, `[ord(byte) for byte in self.op.func_code.co_code]`,`"FIXME"`)
                
        def __repr__(self):
            return self._getRepresentation()

        def getName(self):
            name = baseClass.getName(self)
            if len(name) == 0:
                name = self._getRepresentation(style="name")
            return name
 
        def getShape(self):
            if self.opShape is not None:
                return self.opShape
            else:
                return baseClass.getShape(self)
##             return baseClass.getShape(self) or self.opShape

        def _isMasked(self):
            from fipy.tools import numerix
            return numerix.logical_or.reduce([var._isMasked() for var in self.var])
            
    return _OperatorVariable
    
def _testBinOp(self):
    """
    Test of _getRepresentation
    
        >>> v1 = Variable((1,2,3,4))
        >>> v2 = Variable((5,6,7,8))
        >>> v3 = Variable((9,10,11,12))
        >>> v4 = Variable((13,14,15,16))

        >>> (v1 * v2)._getRepresentation()
        '(Variable(value=array([1, 2, 3, 4])) * Variable(value=array([5, 6, 7, 8])))'
        
        >>> (v1 * v2)._getRepresentation(style='C', id="")
        '(var0[i] * var1[i])'
        
        >>> (v1 * v2 + v3 * v4)._getRepresentation(style='C', id="")
        '((var00[i] * var01[i]) + (var10[i] * var11[i]))'
        
        >>> (v1 - v2)._getRepresentation(style='C', id="")
        '(var0[i] - var1[i])'

        >>> (v1 / v2)._getRepresentation(style='C', id="")
        '(var0[i] / var1[i])'

        >>> (v1 - 1)._getRepresentation(style='C', id="")
        '(var0[i] - var1)'
            
        >>> (5 * v2)._getRepresentation(style='C', id="")
        '(var0[i] * var1)'

        >>> (v1 / v2 - v3 * v4 + v1 * v4)._getRepresentation(style='C', id="")
        '(((var000[i] / var001[i]) - (var010[i] * var011[i])) + (var10[i] * var11[i]))'
        
    Check that getUnit() works for a binOp

        >>> (Variable(value="1 m") * Variable(value="1 s")).getUnit()
        <PhysicalUnit s*m>

        >>> (Variable(value="1 m") / Variable(value="0 s")).getUnit()
        <PhysicalUnit m/s>

        >>> a = -((Variable() * Variable()).sin())

    Check that getTypeCode() works as expected.

        >>> a = Variable(1.) * Variable(1)
        >>> a.getTypecode()
        'd'

    The following test is to correct an `--inline` bug that was
    being thrown by the Cahn-Hilliard example. The fix for this
    bug was to add the last line to the following code in
    `_getRepresentation()`.
    
        >>> ##elif style == "C":
        >>> ##    counter = _popIndex()
        >>> ##    if not self.var[counter]._isCached():
        >>> ##        stack.append(self.var[counter]._getCstring(argDict, id=id + str(counter), freshen=freshen))
        >>> ##        self.var[counter].value=None

    This is the test that fails if the last line above is removed
    from `_getRepresentation()`, the `binOp.getValue()` statement
    below will return `1.0` and not `0.5`.
        
        >>> from fipy import numerix
        >>> def doBCs(binOp):
        ...     unOp1 = -binOp
        ...     print binOp.getValue()
        >>> var = Variable(1.)
        >>> binOp = 1. * var
        >>> unOp = -binOp
        >>> print unOp.getValue()
        -1.0
        >>> doBCs(binOp)
        1.0
        >>> var.setValue(0.5)
        >>> print unOp.getValue()
        -0.5
        >>> unOp2 = -binOp
        >>> print binOp.getValue()
        0.5

        >>> from fipy.variables.cellVariable import CellVariable
        >>> from fipy.variables.faceVariable import FaceVariable
        
        >>> from fipy.meshes.grid2D import Grid2D
        >>> mesh = Grid2D(nx=3)
        
        
    `CellVariable` * CellVariable
    
        >>> cv = CellVariable(mesh=mesh, value=(0, 1, 2))
        >>> cvXcv = cv * cv
        >>> print cvXcv
        [0 1 4]
        >>> print isinstance(cvXcv, CellVariable)
        1
    
    `CellVariable` * FaceVariable
    
        >>> fv = FaceVariable(mesh=mesh, value=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9))
        >>> fvXcv = fv * cv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> cvXfv = cv * fv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        
    rank-0 `CellVariable` * rank-1 `CellVariable`
    
        >>> vcv = CellVariable(mesh=mesh, value=((0, 1, 2), (1, 2, 3)), rank=1)
        >>> vcvXcv = vcv * cv
        >>> print vcvXcv
        [[0 1 4]
         [0 2 6]]
        >>> print isinstance(vcvXcv, CellVariable)
        1
        >>> print vcvXcv.getRank()
        1
        >>> cvXvcv = cv * vcv
        >>> print cvXvcv
        [[0 1 4]
         [0 2 6]]
        >>> print isinstance(cvXvcv, CellVariable)
        1
        >>> print cvXvcv.getRank()
        1

    `CellVariable` * rank-1 `FaceVariable`

        >>> vfv = FaceVariable(mesh=mesh, value=((0,1,2,3,1,2,3,6,2,1),
        ...                                      (1,2,3,4,3,4,5,9,6,3)), rank=1)
        >>> vfvXcv = vfv * cv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> cvXvfv = cv * vfv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

    `CellVariable` * Scalar
    
        >>> cvXs = cv * 3
        >>> print cvXs
        [0 3 6]
        >>> print isinstance(cvXs, CellVariable)
        1
        >>> sXcv = 3 * cv
        >>> print sXcv
        [0 3 6]
        >>> print isinstance(sXcv, CellVariable)
        1

    `CellVariable` * Vector
    
        >>> cvXv2 = cv * (3,2)
        >>> print cvXv2
        [[0 3 6]
         [0 2 4]]
        >>> cvXv2 = cv * [[3], [2]]
        >>> print cvXv2
        [[0 3 6]
         [0 2 4]]
        >>> print isinstance(cvXv2, CellVariable)
        1
        >>> print cvXv2.getRank()
        1
        >>> v2Xcv = (3,2) * cv
        >>> print v2Xcv
        [[0 3 6]
         [0 2 4]]
        >>> v2Xcv = [[3], [2]] * cv
        >>> print v2Xcv
        [[0 3 6]
         [0 2 4]]
        >>> print isinstance(v2Xcv, CellVariable)
        1
        >>> print v2Xcv.getRank()
        1
        
        >>> cvXv3 = cv * (3,2,1)
        >>> print cvXv3
        [0 2 2]
        >>> print isinstance(cvXv3, CellVariable)
        1
        >>> v3Xcv = (3,2,1) * cv
        >>> print v3Xcv
        [0 2 2]
        >>> print isinstance(v3Xcv, CellVariable)
        1
        
        >>> cvXv4 = cv * (3,2,1,0) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        TypeError: can't multiply sequence to non-int
        >>> v4Xcv = (3,2,1,0) * cv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
            ...
        TypeError: can't multiply sequence to non-int


    `CellVariable` * `Variable` Scalar
    
        >>> cvXsv = cv * Variable(value=3)
        >>> print cvXsv
        [0 3 6]
        >>> print isinstance(cvXsv, CellVariable)
        1
        >>> svXcv = Variable(value=3) * cv
        >>> print svXcv
        [0 3 6]
        >>> print isinstance(svXcv, CellVariable)
        1
    
    `binOp` `CellVariable` * `binOp` `Variable` Scalar

        >>> cvcvXsvsv = (cv * cv) * (Variable(value=3) * Variable(value=3))
        >>> print cvcvXsvsv
        [ 0  9 36]
        >>> print isinstance(cvcvXsvsv, CellVariable)
        1
        >>> svsvXcvcv = (Variable(value=3) * Variable(value=3)) * (cv * cv)
        >>> print svsvXcvcv
        [ 0  9 36]
        >>> print isinstance(svsvXcvcv, CellVariable)
        1
        
    `CellVariable` * `Variable` Vector
        
        >>> cvXv2v = cv * Variable(value=(3,2))
        >>> print cvXv2v
        [[0 3 6]
         [0 2 4]]
        >>> cvXv2v = cv * Variable(value=((3,),(2,)))
        >>> print cvXv2v
        [[0 3 6]
         [0 2 4]]
        >>> print isinstance(cvXv2v, CellVariable)
        1
        >>> print cvXv2v.getRank()
        1
        >>> v2vXcv = Variable(value=(3,2)) * cv
        >>> v2vXcv = Variable(value=((3,),(2,))) * cv
        >>> print v2vXcv
        [[0 3 6]
         [0 2 4]]
        >>> print isinstance(v2vXcv, CellVariable)
        1
        >>> print v2vXcv.getRank()
        1
        
        >>> cvXv3v = cv * Variable(value=(3,2,1))
        >>> print cvXv3v
        [0 2 2]
        >>> print isinstance(cvXv3v, CellVariable)
        1
        >>> v3vXcv = Variable(value=(3,2,1)) * cv
        >>> print v3vXcv
        [0 2 2]
        >>> print isinstance(v3vXcv, CellVariable)
        1

        >>> cvXv4v = cv * Variable(value=(3,2,1,0)) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v4vXcv = Variable(value=(3,2,1,0)) * cv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        

    `CellVariable` * CellGradVariable
    
        >>> cvXcgv = cv * cv.getGrad()
        >>> print cvXcgv
        [[ 0.  1.  1.]
         [ 0.  0.  0.]]
        >>> print isinstance(cvXcgv, CellVariable)
        1
        >>> print cvXcgv.getRank()
        1
        
    `FaceVariable` * FaceVariable

        >>> fvXfv = fv * fv
        >>> print fvXfv
        [ 0  1  4  9 16 25 36 49 64 81]
        >>> print isinstance(fvXfv, FaceVariable)
        1

    `FaceVariable` * rank-1 `CellVariable`

        >>> vcvXfv = vcv * fv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> fvXvcv = fv * vcv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

    `FaceVariable` * rank-1 `FaceVariable`

        >>> vfvXfv = vfv * fv
        >>> print vfvXfv
        [[ 0  1  4  9  4 10 18 42 16  9]
         [ 0  2  6 12 12 20 30 63 48 27]]
        >>> print isinstance(vfvXfv, FaceVariable)
        1
        >>> print vfvXfv.getRank()
        1
        >>> fvXvfv = fv * vfv
        >>> print fvXvfv
        [[ 0  1  4  9  4 10 18 42 16  9]
         [ 0  2  6 12 12 20 30 63 48 27]]
        >>> print isinstance(fvXvfv, FaceVariable)
        1
        >>> print fvXvfv.getRank()
        1

    `FaceVariable` * Scalar

        >>> fvXs = fv * 3
        >>> print fvXs
        [ 0  3  6  9 12 15 18 21 24 27]
        >>> print isinstance(fvXs, FaceVariable)
        1
        >>> sXfv = 3 * fv
        >>> print sXfv
        [ 0  3  6  9 12 15 18 21 24 27]
        >>> print isinstance(sXfv, FaceVariable)
        1

    `FaceVariable` * Vector

        >>> fvXv2 = fv * (3,2)
        >>> print fvXv2
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> fvXv2 = fv * ((3,),(2,))
        >>> print fvXv2
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> print isinstance(fvXv2, FaceVariable)
        1
        >>> print fvXv2.getRank()
        1
        >>> v2Xfv = (3,2) * fv
        >>> print v2Xfv
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> v2Xfv = ((3,),(2,)) * fv
        >>> print v2Xfv
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> print isinstance(v2Xfv, FaceVariable)
        1
        >>> print v2Xfv.getRank()
        1
        
        >>> fvXv3 = fv * (3,2,1) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v3Xfv = (3,2,1) * fv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

        >>> fvXv10 = fv * (9,8,7,6,5,4,3,2,1,0)
        >>> print fvXv10
        [ 0  8 14 18 20 20 18 14  8  0]
        >>> print isinstance(fvXv10, FaceVariable)
        1
        >>> v10Xfv = (9,8,7,6,5,4,3,2,1,0) * fv
        >>> print v10Xfv
        [ 0  8 14 18 20 20 18 14  8  0]
        >>> print isinstance(v10Xfv, FaceVariable)
        1

    `FaceVariable` * `Variable` Scalar

        >>> fvXsv = fv * Variable(value=3)
        >>> print fvXsv
        [ 0  3  6  9 12 15 18 21 24 27]
        >>> print isinstance(fvXsv, FaceVariable)
        1
        >>> svXfv = Variable(value=3) * fv
        >>> print svXfv
        [ 0  3  6  9 12 15 18 21 24 27]
        >>> print isinstance(svXfv, FaceVariable)
        1

    `FaceVariable` * `Variable` Vector
        
        >>> fvXv2v = fv * Variable(value=(3,2))
        >>> print fvXv2v
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> fvXv2v = fv * Variable(value=((3,),(2,)))
        >>> print fvXv2v
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> print isinstance(fvXv2v, FaceVariable)
        1
        >>> print fvXv2v.getRank()
        1
        >>> v2vXfv = Variable(value=(3,2)) * fv
        >>> print v2vXfv
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> v2vXfv = Variable(value=((3,),(2,))) * fv
        >>> print v2vXfv
        [[ 0  3  6  9 12 15 18 21 24 27]
         [ 0  2  4  6  8 10 12 14 16 18]]
        >>> print isinstance(v2vXfv, FaceVariable)
        1
        >>> print v2vXfv.getRank()
        1
        
        >>> fvXv3v = fv * Variable(value=(3,2,1)) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v3vXfv = Variable(value=(3,2,1)) * fv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

        >>> fvXv10v = fv * Variable(value=(9,8,7,6,5,4,3,2,1,0))
        >>> print fvXv10v
        [ 0  8 14 18 20 20 18 14  8  0]
        >>> print isinstance(fvXv10v, FaceVariable)
        1
        >>> v10vXfv = Variable(value=(9,8,7,6,5,4,3,2,1,0)) * fv
        >>> print v10vXfv
        [ 0  8 14 18 20 20 18 14  8  0]
        >>> print isinstance(v10vXfv, FaceVariable)
        1

        
        
    rank-1 `CellVariable` * rank-1 `CellVariable`

        >>> vcvXvcv = vcv * vcv
        >>> print vcvXvcv
        [[0 1 4]
         [1 4 9]]
        >>> print isinstance(vcvXvcv, CellVariable)
        1
        >>> print vcvXvcv.getRank()
        1

    rank-1 `CellVariable` * rank-1 `FaceVariable`

        >>> vfvXvcv = vfv * vcv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> vcvXvfv = vcv * vfv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

    rank-1 `CellVariable` * Scalar

        >>> vcvXs = vcv * 3
        >>> print vcvXs
        [[0 3 6]
         [3 6 9]]
        >>> print isinstance(vcvXs, CellVariable)
        1
        >>> print vcvXs.getRank()
        1
        >>> sXvcv = 3 * vcv
        >>> print sXvcv
        [[0 3 6]
         [3 6 9]]
        >>> print isinstance(vcvXs, CellVariable)
        1
        >>> print vcvXs.getRank()
        1

    rank-1 `CellVariable` * Vector

        >>> vcvXv2 = vcv * (3,2)
        >>> print vcvXv2
        [[0 3 6]
         [2 4 6]]
        >>> vcvXv2 = vcv * ((3,),(2,))
        >>> print vcvXv2
        [[0 3 6]
         [2 4 6]]
        >>> print isinstance(vcvXv2, CellVariable)
        1
        >>> print vcvXv2.getRank()
        1
        >>> v2Xvcv = (3,2) * vcv
        >>> print v2Xvcv
        [[0 3 6]
         [2 4 6]]
        >>> v2Xvcv = ((3,),(2,)) * vcv
        >>> print v2Xvcv
        [[0 3 6]
         [2 4 6]]
        >>> print isinstance(v2Xvcv, CellVariable)
        1
        >>> print v2Xvcv.getRank()
        1
        
        >>> vcvXv3 = vcv * (3,2,1)
        >>> print vcvXv3
        [[0 2 2]
         [3 4 3]]
        >>> isinstance(vcvXv3, CellVariable)
        1
        >>> print vcvXv3.getRank()
        1
        >>> v3Xvcv = (3,2,1) * vcv 
        >>> print v3Xvcv
        [[0 2 2]
         [3 4 3]]
        >>> isinstance(v3Xvcv, CellVariable)
        1
        >>> print v3Xvcv.getRank()
        1

        >>> vcvXv4 = vcv * (3,2,1,0) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v4Xvcv = (3,2,1,0) * vcv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

    rank-1 `CellVariable` * `Variable` Scalar

        >>> vcvXsv = vcv * Variable(value=3)
        >>> print vcvXsv
        [[0 3 6]
         [3 6 9]]
        >>> print isinstance(vcvXsv, CellVariable)
        1
        >>> print vcvXsv.getRank()
        1
        >>> svXvcv = Variable(value=3) * vcv
        >>> print svXvcv
        [[0 3 6]
         [3 6 9]]
        >>> print isinstance(svXvcv, CellVariable)
        1
        >>> print svXvcv.getRank()
        1

    rank-1 `CellVariable` * `Variable` Vector
        
        >>> vcvXv2v = vcv * Variable(value=(3,2))
        >>> print vcvXv2v
        [[0 3 6]
         [2 4 6]]
        >>> vcvXv2v = vcv * Variable(value=((3,),(2,)))
        >>> print vcvXv2v
        [[0 3 6]
         [2 4 6]]
        >>> print isinstance(vcvXv2v, CellVariable)
        1
        >>> print vcvXv2v.getRank()
        1
        >>> v2vXvcv = Variable(value=(3,2)) * vcv
        >>> print v2vXvcv
        [[0 3 6]
         [2 4 6]]
        >>> v2vXvcv = Variable(value=((3,),(2,))) * vcv
        >>> print v2vXvcv
        [[0 3 6]
         [2 4 6]]
        >>> print isinstance(v2vXvcv, CellVariable)
        1
        >>> print v2vXvcv.getRank()
        1
        
        >>> vcvXv3v = vcv * Variable(value=(3,2,1))
        >>> print vcvXv3v
        [[0 2 2]
         [3 4 3]]
        >>> isinstance(vcvXv3v, CellVariable)
        1
        >>> print vcvXv3v.getRank()
        1
        >>> v3vXvcv = Variable(value=(3,2,1)) * vcv 
        >>> print v3vXvcv
        [[0 2 2]
         [3 4 3]]
        >>> isinstance(v3vXvcv, CellVariable)
        1
        >>> print v3vXvcv.getRank()
        1

        >>> vcvXv4v = vcv * Variable(value=(3,2,1,0)) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v4vXvcv = Variable(value=(3,2,1,0)) * vcv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

                    
    rank-1 `FaceVariable` * rank-1 FaceVariable

        >>> vfvXvfv = vfv * vfv
        >>> print vfvXvfv
        [[ 0  1  4  9  1  4  9 36  4  1]
         [ 1  4  9 16  9 16 25 81 36  9]]
        >>> isinstance(vfvXvfv, FaceVariable)
        1
        >>> print vfvXvfv.getRank()
        1

    rank-1 `FaceVariable` * Scalar

        >>> vfvXs = vfv * 3
        >>> print vfvXs
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 3  6  9 12  9 12 15 27 18  9]]
        >>> print isinstance(vfvXs, FaceVariable)
        1
        >>> print vfvXs.getRank()
        1
        >>> sXvfv = 3 * vfv
        >>> print sXvfv
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 3  6  9 12  9 12 15 27 18  9]]
        >>> print isinstance(sXvfv, FaceVariable)
        1
        >>> print sXvfv.getRank()
        1

    rank-1 `FaceVariable` * Vector

        >>> vfvXv2 = vfv * (3,2)
        >>> print vfvXv2
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 2  4  6  8  6  8 10 18 12  6]]
        >>> print isinstance(vfvXv2, FaceVariable)
        1
        >>> print vfvXv2.getRank()
        1
        >>> v2Xvfv = (3,2) * vfv
        >>> print v2Xvfv
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 2  4  6  8  6  8 10 18 12  6]]
        >>> print isinstance(v2Xvfv, FaceVariable)
        1
        >>> print v2Xvfv.getRank()
        1
        
        >>> vfvXv3 = vfv * (2,1,0) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v3Xvfv = (2,1,0) * vfv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int


        >>> vfvXv10 = vfv * (9,8,7,6,5,4,3,2,1,0)
        >>> print vfvXv10
        [[ 0  8 14 18  5  8  9 12  2  0]
         [ 9 16 21 24 15 16 15 18  6  0]]
        >>> isinstance(vfvXv10, FaceVariable)
        1
        >>> print vfvXv10.getRank()
        1
        >>> v10Xvfv = (9,8,7,6,5,4,3,2,1,0) * vfv
        >>> print v10Xvfv
        [[ 0  8 14 18  5  8  9 12  2  0]
         [ 9 16 21 24 15 16 15 18  6  0]]
        >>> isinstance(v10Xvfv, FaceVariable)
        1
        >>> print v10Xvfv.getRank()
        1

    rank-1 `FaceVariable` * `Variable` Scalar

        >>> vfvXsv = vfv * Variable(value=3)
        >>> print vfvXsv
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 3  6  9 12  9 12 15 27 18  9]]
        >>> print isinstance(vfvXsv, FaceVariable)
        1
        >>> print vfvXsv.getRank()
        1
        >>> svXvfv = Variable(value=3) * vfv
        >>> print svXvfv
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 3  6  9 12  9 12 15 27 18  9]]
        >>> print isinstance(svXvfv, FaceVariable)
        1
        >>> print svXvfv.getRank()
        1

    rank-1 `FaceVariable` * `Variable` Vector
        
        >>> vfvXv2v = vfv * Variable(value=(3,2))
        >>> print vfvXv2v
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 2  4  6  8  6  8 10 18 12  6]]
        >>> print isinstance(vfvXv2v, FaceVariable)
        1
        >>> print vfvXv2v.getRank()
        1
        >>> v2vXvfv = Variable(value=(3,2)) * vfv
        >>> print v2vXvfv
        [[ 0  3  6  9  3  6  9 18  6  3]
         [ 2  4  6  8  6  8 10 18 12  6]]
        >>> print isinstance(v2vXvfv, FaceVariable)
        1
        >>> print v2vXvfv.getRank()
        1
        
        >>> vfvXv3v = vfv * Variable(value=(2,1,0)) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v3vXvfv = Variable(value=(2,1,0)) * vfv #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int


        >>> vfvXv10v = vfv * Variable(value=(9,8,7,6,5,4,3,2,1,0))
        >>> print vfvXv10v
        [[ 0  8 14 18  5  8  9 12  2  0]
         [ 9 16 21 24 15 16 15 18  6  0]]
        >>> isinstance(vfvXv10v, FaceVariable)
        1
        >>> print vfvXv10v.getRank()
        1
        >>> v10vXvfv = Variable(value=(9,8,7,6,5,4,3,2,1,0)) * vfv
        >>> print v10vXvfv
        [[ 0  8 14 18  5  8  9 12  2  0]
         [ 9 16 21 24 15 16 15 18  6  0]]
        >>> isinstance(v10vXvfv, FaceVariable)
        1
        >>> print v10vXvfv.getRank()
        1
        
        
    Scalar * `Variable` Scalar

        >>> sXsv = 3 * Variable(value=3)
        >>> print sXsv
        9
        >>> print isinstance(sXsv, Variable)
        1
        >>> svXs = Variable(value=3) * 3
        >>> print svXs
        9
        >>> print isinstance(svXs, Variable)
        1

    Scalar * `Variable` Vector
        
        >>> sXv2v = 3 * Variable(value=(3,2))
        >>> print sXv2v
        [9 6]
        >>> print isinstance(sXv2v, Variable)
        1
        >>> v2vXs = Variable(value=(3,2)) * 3
        >>> print v2vXs
        [9 6]
        >>> print isinstance(v2vXs, Variable)
        1
        
        
        
    Vector * `Variable` Scalar

        >>> vXsv = (3, 2) * Variable(value=3)
        >>> print vXsv
        [9 6]
        >>> print isinstance(vXsv, Variable)
        1
        >>> svXv = Variable(value=3) * (3, 2)
        >>> print svXv
        [9 6]
        >>> print isinstance(svXv, Variable)
        1

    Vector * `Variable` Vector
        
        >>> vXv2v = (3, 2) * Variable(value=(3,2))
        >>> print vXv2v
        [9 4]
        >>> print isinstance(vXv2v, Variable)
        1
        >>> v2vXv = Variable(value=(3,2)) * (3, 2)
        >>> print v2vXv
        [9 4]
        >>> print isinstance(v2vXv, Variable)
        1

        >>> vXv3v = (3, 2, 1) * Variable(value=(3,2)) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        >>> v3vXv = Variable(value=(3,2)) * (3, 2, 1) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int
        

    `Variable` Scalar * `Variable` Scalar

        >>> svXsv = Variable(value=3) * Variable(value=3)
        >>> print svXsv
        9
        >>> print isinstance(svXsv, Variable)
        1

    `Variable` Scalar * `Variable` Vector
        
        >>> svXv2v = Variable(value=3) * Variable(value=(3,2))
        >>> print svXv2v
        [9 6]
        >>> print isinstance(svXv2v, Variable)
        1
        >>> v2vXsv = Variable(value=(3,2)) * Variable(value=3)
        >>> print v2vXsv
        [9 6]
        >>> print isinstance(v2vXsv, Variable)
        1

        
    `Variable` Vector * `Variable` Vector
        
        >>> v2vXv2v = Variable(value=(3, 2)) * Variable(value=(3,2))
        >>> print v2vXv2v
        [9 4]
        >>> print isinstance(v2vXv2v, Variable)
        1
        
        >>> v3vXv2v = Variable(value=(3, 2, 1)) * Variable(value=(3,2)) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
              ...
        TypeError: can't multiply sequence to non-int

    Test for weird bug that was appearing in inline. Caused by the intermediate
    operators not getting marked fresh.

        >>> class Alpha(Variable):
        ...     def __init__(self, var):
        ...         Variable.__init__(self)
        ...         self.var = self._requires(var)
        ...     def _calcValue(self):
        ...         return self.var.getValue()

        >>> coeff = Variable()
        >>> alpha = Alpha(-coeff / 1)
        >>> print numerix.allclose(alpha.getValue(), 0.0)
        True
        >>> coeff.setValue(-10.0)
        >>> print numerix.allclose(alpha.getValue(), 10)
        True
        >>> coeff.setValue(10.0)
        >>> print numerix.allclose(alpha.getValue(), -10)
        True

    Test to prevent divide by zero evaluation before value is
    requested.  The request is caused by the Variable requiring
    its unit to see whether it can do an inline calculation in
    `_UnaryOperatorVariable()`.
    
        >>> T = Variable()
        >>> from fipy import numerix
        >>> v = numerix.exp(-T / (1. *  T))

    Following is a test case for an error when turing a binOp into an array

        >>> print numerix.array(Variable(value=numerix.array([ 1.,])) * [ 1.,])
        [ 1.]

    It seems that numpy's __rmul__ coercion is very strange

        >>> type(numerix.array([1., 2.]) * Variable([1., 2.]))
        <class 'fipy.variables.binaryOperatorVariable.binOp'>

    Test inlining

        >>> v0 = Variable(numerix.ones(2, 'd'))
        >>> v1 = Variable(numerix.ones(2, 'd'))
        >>> v = v1 * v0
        >>> print v
        [ 1.  1.]
        >>> v0[1] = 0.5
        >>> print v
        [ 1.   0.5]
        
    Test inline indexing

        >>> mesh = Grid2D(nx=3, ny=3)
        >>> v1 = CellVariable(mesh=mesh, value=numerix.arange(9))
        >>> a = v1 * (1, -1)
        >>> print a
        [[ 0  1  2  3  4  5  6  7  8]
         [ 0 -1 -2 -3 -4 -5 -6 -7 -8]]
        >>> v1[0] = 0
        >>> print a
        [[ 0  1  2  3  4  5  6  7  8]
         [ 0 -1 -2 -3 -4 -5 -6 -7 -8]]

    """
    pass

def _test(): 
    import doctest
    return doctest.testmod()
    
if __name__ == "__main__": 
    _test() 