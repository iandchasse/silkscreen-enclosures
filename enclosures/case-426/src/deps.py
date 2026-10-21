"""What a function of src/ can read from params.py: the static closure the share guards compare (2026-10-08).

params_read(roots) -> (names, nodes): every params name (P.<NAME>) that the functions `roots` ('module.function')
can reach: through every src/ function, class and module-level name they refer to (a module-level name brings its
assignments' right-hand sides, so a constant derived from params at import counts), followed to the end. It is an
over-approximation (every branch, every name a function body mentions) for code written the way src/ is: `import
params as P` and P.<NAME>, `import <module>` / `from <module> import <name>`. Function parameters and local names
shadow module names (a function's own `tub_s` is not mechanics' __main__ `tub_s`).
One read it misses: a module's name that another module sets at import. params.py sets hw.DNP from BOTTOM_KEYS and
DEV_HEADER (the only such assignment in src/); hw.DNP resolves here to hw.py's own `DNP = frozenset()`, so DEV_HEADER
is in no item's names. guard.py covers it with the fitted hardware near each region (see its docstring); counting it
here would end every share across the dev axis.

Standard library only, no import of the analysed code: the guard step calls it, and a key holds deps.py itself.
"""
import ast
from functools import lru_cache
from pathlib import Path

SRC = Path(__file__).resolve().parent


class Module:
    def __init__(self, name, src=SRC):
        self.name = name
        tree = ast.parse((src / f'{name}.py').read_text(encoding='utf-8'))
        self.defs, self.assigns, self.alias = {}, {}, {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    m = a.name.split('.')[0]
                    if (src / f'{m}.py').exists():
                        self.alias[a.asname or m] = ('mod', m)
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0 and (src / f'{n.module}.py').exists():
                for a in n.names:
                    self.alias[a.asname or a.name] = ('name', n.module, a.name)

        def top(body):
            for n in body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self.defs[n.name] = n
                elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                        for x in ast.walk(t):
                            if isinstance(x, ast.Name):
                                self.assigns.setdefault(x.id, []).append(n.value)
                elif isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    for f in ('body', 'orelse', 'finalbody'):
                        top(getattr(n, f, []) or [])
                    for h in getattr(n, 'handlers', []) or []:
                        top(h.body)
        top(tree.body)


@lru_cache(maxsize=None)
def module(name, src=SRC):
    return Module(name, src)


def _locals(fn):
    """The names local to a function (its parameters and every name it binds), not counting nested scopes."""
    out = set()
    a = fn.args
    for x in (*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg):
        if x is not None:
            out.add(x.arg)
    glob = set()

    def walk(n):
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.add(c.name)
                continue                                # a nested scope: its own locals
            if isinstance(c, ast.Lambda):
                continue
            if isinstance(c, (ast.Global, ast.Nonlocal)):
                glob.update(c.names)
            if isinstance(c, ast.Name) and isinstance(c.ctx, (ast.Store, ast.Del)):
                out.add(c.id)
            if isinstance(c, ast.ExceptHandler) and c.name:
                out.add(c.name)
            walk(c)
    walk(fn)
    return out - glob


def _refs(m, node, shadow=frozenset()):
    """(params names, [(module, name)]) that node reads, with `shadow` local names not resolved to module names."""
    pn, out = set(), []

    def visit(n, shadow):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for d in getattr(n, 'decorator_list', []):
                visit(d, shadow)
            for d in [*n.args.defaults, *[k for k in n.args.kw_defaults if k is not None]]:
                visit(d, shadow)
            inner = shadow | (_locals(n) if not isinstance(n, ast.Lambda) else
                              {a.arg for a in (*n.args.posonlyargs, *n.args.args, *n.args.kwonlyargs)})
            for c in (n.body if isinstance(n.body, list) else [n.body]):
                visit(c, inner)
            return
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id not in shadow:
            a = m.alias.get(n.value.id)
            if a and a[0] == 'mod':
                if a[1] == 'params':
                    pn.add(n.attr)
                else:
                    out.append((a[1], n.attr))
                return
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in shadow:
            if n.id in m.defs or n.id in m.assigns:
                out.append((m.name, n.id))
            elif n.id in m.alias:
                a = m.alias[n.id]
                if a[0] == 'name':
                    out.append((a[1], a[2]))
                elif a[1] == 'params':                  # the module itself passed on (P as an argument)
                    pn.add('*')
        for c in ast.iter_child_nodes(n):
            visit(c, shadow)
    visit(node, frozenset(shadow))
    return pn, out


def params_read(roots, src=SRC):
    """-> (sorted params names, sorted 'module.name' nodes reached) for roots ['module.function', ...]. A '*' among
    the names: the params module itself is passed or stored somewhere (every name must then count)."""
    seen, pn = set(), set()
    todo = [tuple(r.split('.', 1)) for r in roots]
    while todo:
        k = todo.pop()
        if k in seen:
            continue
        seen.add(k)
        mname, name = k
        if mname == 'params':
            pn.add(name)
            continue
        if not (src / f'{mname}.py').exists():
            continue
        m = module(mname, src)
        nodes = ([m.defs[name]] if name in m.defs else []) + m.assigns.get(name, [])
        for nd in nodes:
            p, o = _refs(m, nd)
            pn |= p
            todo += o
    return sorted(pn), sorted(f'{a}.{b}' for a, b in seen)
