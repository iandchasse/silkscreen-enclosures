"""A vtk ray caster over a trimesh (no rtree or embree in the venv): first_hit(p0, p1) -> the first surface point on the
segment, or None. Used for end-face and face height maps."""
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray


def to_poly(m):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(m.vertices, dtype=np.float64), deep=True))
    f = np.asarray(m.faces, dtype=np.int64)
    cells = vtk.vtkCellArray()
    cells.SetCells(len(f), numpy_to_vtkIdTypeArray(np.c_[np.full(len(f), 3), f].ravel(), deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(cells)
    return pd


class Caster:
    def __init__(self, m):
        self.pd = to_poly(m)
        self.loc = vtk.vtkStaticCellLocator()
        self.loc.SetDataSet(self.pd)
        self.loc.BuildLocator()

    def first_hit(self, p0, p1):
        t = vtk.mutable(0.0)
        x = [0.0, 0.0, 0.0]
        pc = [0.0, 0.0, 0.0]
        sub = vtk.mutable(0)
        cid = vtk.mutable(0)
        if self.loc.IntersectWithLine(list(p0), list(p1), 1e-6, t, x, pc, sub, cid):
            return tuple(x)
        return None
