"""mechanics.json of one build with its three slow entries taken from builds whose guard matches (pipeline.py's
mechanics step, 2026-10-08): the side keys' sweep (side_key_sweep: the tub, lid and midplate built and every key swung
against them, about 300 s) and the bottom keys' key_hooks and key_sweep (on the tub as built, about 180 s). Every other
entry is computed here, by mechanics.py's own functions in its order, in this build's own params.

    $env:SILKSCREEN_VARIANT = '<slug>'; python -B src/mechanics_share.py --sks-from <slug> [--kk-from <slug>] [--out f]

--sks-from: a build whose out/<it>/mechanics.json has this build's side keys and whose guard (guard.py: the tub's and
the lid's BREP over each key's zone, the midplate, the hardware there, the key's root, the params side_key_sweep can
read) is this build's for every one of them: its rows are this build's, in this build's key order (body.side_tabs:
params.TAB_ROOTS). --kk-from (with the bottom keys): a build whose guard's mech_kk (the tub's facets round the key
slots, the params key_hooks and key_sweep read) is this build's. pipeline.py compares the guards before it runs this;
without a match it runs mechanics.py. The file is byte-for-byte mechanics.py's (28 composed ones against
mechanics.py's, 2026-10-08, and all 32 in the cold run of 2026-10-10; pipeline.py --unshared --verify compares them).
"""
import json, sys
import params as P
import hw
import mechanics as M


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def main():
    sks_from, kk_from = arg('--sks-from'), arg('--kk-from')
    assert sks_from, '--sks-from <slug>'
    assert kk_from or not P.BOTTOM_KEYS, '--kk-from <slug>: this build has the bottom keys'
    out_root = P.OUT.parent
    own = json.loads((out_root / sks_from / 'mechanics.json').read_text())['side_key_sweep']
    missing = [r for r in P.TAB_ROOTS if r not in own]
    assert not missing, f'{sks_from} has no side_key_sweep rows for {missing}'
    ssweep = {r: own[r] for r in P.TAB_ROOTS}          # side_key_sweep's order: body.side_tabs() -> TAB_ROOTS
    import panel
    import joint
    sp = M.springs()
    if P.BOTTOM_KEYS:
        kd = json.loads((out_root / kk_from / 'mechanics.json').read_text())
        kk = {'key_forces': M.key_forces(), 'key_hooks': kd['key_hooks'], 'key_fit': M.key_fit(),
              'key_proud': M.key_proud(), 'key_overpress': M.overpress(), 'key_sweep': kd['key_sweep']}
    else:
        kk = {}
    rep = {**kk,
           'springs': sp, 'side_key_reach': M.side_key_reach(sp['side_keys']), 'screen_stack': M.screen_stack(),
           **({'plain_stack': M.plain_stack()} if P.LIGHT_STRIP else {}),
           'joint': joint.summary(), 'latches': M.latches(), 'board_snap': M.board_snap(), 'mid_detents': M.mid_detents(),
           'ribbons': {f'{dt:+.1f}mm_panel': panel.report(total=hw.PANEL_T + dt) for dt in (-0.2, 0.0, 0.2)},
           'side_key_sweep': ssweep, **({'rod_gate': M.rod_gate()} if P.BOTTOM_KEYS else {})}
    from pathlib import Path
    Path(arg('--out') or (P.OUT / 'mechanics.json')).write_text(json.dumps(rep, indent=1))     # as mechanics.py writes it
    print(f'{P.BUILD}: mechanics.json with side_key_sweep from {sks_from}'
          + (f', key_hooks and key_sweep from {kk_from}' if P.BOTTOM_KEYS else '') + '; the rest computed here', flush=True)


if __name__ == '__main__':
    main()
