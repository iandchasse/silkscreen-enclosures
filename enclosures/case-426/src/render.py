"""Offscreen VTK renderer for STL parts, CAD mm frame (+Z screen, +Y top).

Usage:
  python claude/render.py --out shot.png --view iso_front --parts a.stl:#aabbcc:1.0 b.stl:#ff0000:0.4
  Optional section: --clip x|y|z:value[:flip]   (cuts everything on one side of a plane)
  Optional zoom box: --focus xmin,xmax,ymin,ymax,zmin,zmax
"""
import argparse, sys
from pathlib import Path
import vtk

VIEWS = {
    # name: (direction camera looks FROM (unit-ish vector from focal point), view-up)
    'front': ((0, 0, 1), (0, 1, 0)),
    'back': ((0, 0, -1), (0, 1, 0)),
    'left': ((-1, 0, 0), (0, 0, 1)),
    'right': ((1, 0, 0), (0, 0, 1)),
    'top': ((0, 1, 0), (0, 0, 1)),
    'bottom': ((0, -1, 0), (0, 0, 1)),
    'iso_front': ((0.55, -0.75, 0.9), (0, 0, 1)),
    'iso_front_r': ((0.8, -0.5, 0.7), (0, 0, 1)),
    'iso_back': ((-0.55, -0.75, -0.9), (0, 0, -1)),
    'iso_bottom': ((0.35, -1.0, 0.55), (0, 0, 1)),
    'iso_top': ((0.35, 1.0, 0.55), (0, 0, 1)),
    'iso_back_r': ((0.45, -0.55, -1.0), (0, 1, 0)),      # from behind, low and to the right, +Y up
    'iso_back_l': ((-0.45, -0.55, -1.0), (0, 1, 0)),
}


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--view', default='iso_front')
    ap.add_argument('--parts', nargs='+', required=True)
    ap.add_argument('--clip', action='append', default=[])
    ap.add_argument('--focus', default=None)
    ap.add_argument('--size', default='1400x1000')
    ap.add_argument('--ortho', action='store_true')
    ap.add_argument('--edges', action='store_true')
    ap.add_argument('--bg', default='#f4f1ea')
    a = ap.parse_args()

    ren = vtk.vtkRenderer()
    ren.SetBackground(*hex_rgb(a.bg))
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    w, h = (int(v) for v in a.size.split('x'))
    win.SetSize(w, h)
    win.AddRenderer(ren)
    win.SetMultiSamples(8)

    planes = []
    for c in a.clip:
        bits = c.split(':')
        axis, val = bits[0], float(bits[1])
        flip = len(bits) > 2 and bits[2] == 'flip'
        n = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}[axis]
        if flip:
            n = tuple(-v for v in n)
        p = vtk.vtkPlane()
        p.SetOrigin(*(val if n[i] else 0 for i in range(3)))
        p.SetNormal(*n)  # keeps the side the normal points to
        planes.append(p)

    for spec in a.parts:
        bits = spec.split(':')
        # windows drive letters contain ':'; re-join if needed
        if len(bits) > 1 and len(bits[0]) == 1:
            bits = [bits[0] + ':' + bits[1]] + bits[2:]
        path = Path(bits[0])
        color = hex_rgb(bits[1]) if len(bits) > 1 and bits[1] else (0.75, 0.75, 0.72)
        opacity = float(bits[2]) if len(bits) > 2 else 1.0
        if not path.exists():
            print('missing', path, file=sys.stderr)
            continue
        r = vtk.vtkSTLReader()
        r.SetFileName(str(path))
        src = r
        for p in planes:
            clip = vtk.vtkClipPolyData()
            clip.SetInputConnection(src.GetOutputPort())
            clip.SetClipFunction(p)
            src = clip
        nrm = vtk.vtkPolyDataNormals()
        nrm.SetInputConnection(src.GetOutputPort())
        nrm.SetFeatureAngle(35)
        nrm.SplittingOn()
        m = vtk.vtkPolyDataMapper()
        m.SetInputConnection(nrm.GetOutputPort())
        act = vtk.vtkActor()
        act.SetMapper(m)
        pr = act.GetProperty()
        pr.SetColor(*color)
        pr.SetOpacity(opacity)
        pr.SetAmbient(0.25)
        pr.SetDiffuse(0.75)
        pr.SetSpecular(0.15)
        pr.SetSpecularPower(20)
        if a.edges:
            pr.EdgeVisibilityOn()
            pr.SetEdgeColor(0.2, 0.2, 0.2)
        # show the cut interior rather than culling it
        bp = vtk.vtkProperty()
        bp.SetColor(*(min(1, c * 0.55 + 0.1) for c in color))
        bp.SetAmbient(0.5)
        act.SetBackfaceProperty(bp)
        ren.AddActor(act)

    if opacity_used(ren):
        win.SetAlphaBitPlanes(1)
        win.SetMultiSamples(0)
        ren.SetUseDepthPeeling(1)
        ren.SetMaximumNumberOfPeels(60)
        ren.SetOcclusionRatio(0.02)

    cam = ren.GetActiveCamera()
    d, up = VIEWS[a.view]
    if a.focus:
        b = [float(v) for v in a.focus.split(',')]
    else:
        b = list(ren.ComputeVisiblePropBounds())
    cx, cy, cz = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2
    cam.SetFocalPoint(cx, cy, cz)
    cam.SetPosition(cx + d[0] * 300, cy + d[1] * 300, cz + d[2] * 300)
    cam.SetViewUp(*up)
    if a.ortho:
        cam.ParallelProjectionOn()
    ren.ResetCamera(*b)
    cam.Zoom(1.3 if not a.ortho else 0.95)
    ren.ResetCameraClippingRange()

    # light kit gives legible shading from any direction
    ren.RemoveAllLights()
    kit = vtk.vtkLightKit()
    kit.SetKeyLightIntensity(0.95)
    kit.AddLightsToRenderer(ren)

    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(a.out)
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    print('wrote', a.out)


def opacity_used(ren):
    acts = ren.GetActors()
    acts.InitTraversal()
    for _ in range(acts.GetNumberOfItems()):
        if acts.GetNextActor().GetProperty().GetOpacity() < 1.0:
            return True
    return False


if __name__ == '__main__':
    main()
