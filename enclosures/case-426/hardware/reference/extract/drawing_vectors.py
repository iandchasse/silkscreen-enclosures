"""Pull the GDEQ0426T82-FT01C drawing's vector geometry into millimetres.

The PDF page is rotated: page y runs along the drawing's horizontal axis and page x
runs down the drawing. Scale is calibrated on the EPD outline (62.37 x 105.33)."""
import json, sys
import pymupdf

d = pymupdf.open(sys.argv[1] if len(sys.argv) > 1 else 'GDEQ0426T82-FT01C.pdf')
p = d[0]
segs = []
for path in p.get_drawings():
    w = path.get('width') or 0
    for it in path['items']:
        if it[0] == 'l':
            segs.append((it[1].x, it[1].y, it[2].x, it[2].y, w))
        elif it[0] == 're':
            r = it[1]
            for a, b in (((r.x0, r.y0), (r.x1, r.y0)), ((r.x1, r.y0), (r.x1, r.y1)), ((r.x1, r.y1), (r.x0, r.y1)), ((r.x0, r.y1), (r.x0, r.y0))):
                segs.append((a[0], a[1], b[0], b[1], w))
        elif it[0] == 'c':
            pts = [it[1], it[2], it[3], it[4]]
            for a, b in zip(pts[:-1], pts[1:]):
                segs.append((a.x, a.y, b.x, b.y, w))
        elif it[0] == 'qu':
            q = it[1]
            pts = [q.ul, q.ur, q.lr, q.ll, q.ul]
            for a, b in zip(pts[:-1], pts[1:]):
                segs.append((a.x, a.y, b.x, b.y, w))
json.dump(segs, open('extract/segments_pt.json', 'w'))
print(len(segs), 'segments')
