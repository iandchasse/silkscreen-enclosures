"""Offscreen vtk renders of meshes (no GUI window): render(meshes, path, view=..., size=...).

meshes: [(trimesh.Trimesh, (r, g, b), opacity)] in one frame. view: 'iso', 'front', 'back', 'top', 'side', or a dict
(position, focal, up). Clip planes can cut a mesh open for section views."""
import numpy as np
import trimesh
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

from raycast import to_poly


def _actor(m, rgb, opacity, smooth_deg=30.0):
    pd = to_poly(m)
    nrm = vtk.vtkPolyDataNormals()
    nrm.SetInputData(pd)
    nrm.SetFeatureAngle(smooth_deg)
    nrm.SplittingOn()
    nrm.ConsistencyOn()
    nrm.Update()
    mp = vtk.vtkPolyDataMapper()
    mp.SetInputConnection(nrm.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(mp)
    pr = a.GetProperty()
    pr.SetColor(*rgb)
    pr.SetOpacity(opacity)
    pr.SetSpecular(0.25)
    pr.SetSpecularPower(30)
    pr.SetAmbient(0.30)
    pr.SetDiffuse(0.75)
    return a


def render(meshes, path, position, focal, up=(0, 0, 1), size=(1400, 900), parallel_scale=None, bg=(1, 1, 1),
           view_angle=30.0, edges=False):
    ren = vtk.vtkRenderer()
    ren.SetBackground(*bg)
    ren.SetBackground2(0.88, 0.9, 0.95)
    ren.GradientBackgroundOn()
    for m, rgb, op in meshes:
        a = _actor(m, rgb, op)
        if edges:
            a.GetProperty().EdgeVisibilityOn()
        ren.AddActor(a)
    cam = ren.GetActiveCamera()
    cam.SetPosition(*position)
    cam.SetFocalPoint(*focal)
    cam.SetViewUp(*up)
    cam.SetViewAngle(view_angle)
    if parallel_scale:
        cam.ParallelProjectionOn()
        cam.SetParallelScale(parallel_scale)
    ren.ResetCameraClippingRange()
    ren.AutomaticLightCreationOff()
    kit = vtk.vtkLightKit()
    kit.SetKeyLightIntensity(0.9)
    kit.SetKeyToFillRatio(2.2)
    kit.AddLightsToRenderer(ren)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetMultiSamples(8)
    rw.AddRenderer(ren)
    rw.SetSize(*size)
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(path))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    return path
