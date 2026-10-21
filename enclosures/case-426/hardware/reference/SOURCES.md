# Vendor reference files not in this repo

These are the panel maker's and part makers' documents. They are not ours to redistribute, so they are not in git.
The builds don't read them: the numbers taken from them are in `src/params.py` and the case README.

| File (put it here, in `hardware/reference/`) | What | Where to get it | sha256 of the copy used |
|---|---|---|---|
| `GDEQ0426T82-FT01C.pdf` | Good Display's mechanical drawing of the GDEQ0426T82-FT01C module (touch + frontlight), 1 page | Good Display (good-display.com) or your panel's seller; ask for the FT01C module drawing | `c103941840f275e7a98fec174657b984a33288b51d0273ae14dd0f2e1d36c276` |

`extract/drawing_vectors.py` and `extract/plot_views.py` read the PDF (with `pymupdf`) when the drawing's vectors are
to be extracted again; nothing else does.
