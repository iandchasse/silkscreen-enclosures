"""Which builds each cover serves: the 4.26's 32 configurations split by the bottom keys, and the 3.68's standard build.
Standard library only (the slugs come from case-426/src/variants.py, read from its file as make_plates.py does)."""
import importlib.util
from pathlib import Path

ENC = Path(__file__).resolve().parent.parent


def _variants():
    spec = importlib.util.spec_from_file_location('variants_426', ENC / 'case-426' / 'src' / 'variants.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def builds(group, only=None):
    """[(case, slug)] the cover of `group` serves ('keyed', 'chinless', 'x3'); `only`: a list of slugs to keep."""
    if group == 'x3':
        out = [('case-368', 'standard')]
    else:
        V = _variants()
        keep = group == 'keyed'
        out = [('case-426', s) for s in V.ORDER if V.parse(s).bottom_keys == keep]
    out = [(c, s) for c, s in out if (ENC / c / 'out' / s / 'tub.stl').exists()]
    if only:
        out = [(c, s) for c, s in out if s in only]
    return out


def served():
    """{group: [slug]} for the docs."""
    return {g: [s for _, s in builds(g)] for g in ('keyed', 'chinless', 'x3')}


if __name__ == '__main__':
    for g, v in served().items():
        print(g, len(v), v)
