# Vendor reference files not in this repo

These are the panel maker's and part makers' documents. They are not ours to redistribute, so they are not in git.
The builds don't read them: the numbers taken from them are in `src/params.py`, `src/hw.py`, `src/panel.py` and the
case README.

| File (put it here, in `hardware/reference/`) | What | Where to get it | sha256 of the copy used |
|---|---|---|---|
| `panel-3p68.png` | Good Display's mechanical drawing of the 3.68" 528 × 792 panel (outline, active area, FPC, pin table) | Good Display or the panel's seller | `82f0a86fa15dd1e4408284db1b2f4301dda23c50654b7efcca0068c8a3546757` |
| `switches/apem-mjtp-through-hole.pdf` | APEM MJTP series datasheet (6 mm tact switches) | https://media.digikey.com/pdf/Data%20Sheets/APEM%20Components%20PDFs/MJTP%20Series-6MM.pdf | `af72254dd71218f89db471168523f7c23e0cb2f8a6ee42d7c885298ab6a5e437` |
| `switches/apem-phap33.pdf` | APEM PHAP33 datasheet | https://www.enika.eu/data/files/produkty/komponenty/spinani/PHAP33-B.pdf | `d503da8a47a3e73a5b3d9db821b4695e20e41f6b6bfc9d74ea66d51079431611` |

`switches/provenance.json` records the same two URLs and hashes.
