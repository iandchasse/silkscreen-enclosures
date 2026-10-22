// Bottom keys: the bell crank. One pose (a press fraction t and a board offset dy) drives the section drawing, the
// readouts and, while the card is open, the stage (SC.viewer.press). The kinematics are SC.crank's, which are the
// sc_contract reference: the crank turns about the rod, the key rides the pad crown's top, the plunger the nose's front.
(function () {
  'use strict';
  var TOL = [-0.2, 0, 0.2];
  var CYCLE = [[0, 0], [0.5, 0], [1.6, 1], [2.1, 1], [3.0, 0], [3.6, 0]];     // [s, press fraction]
  var REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var ease = function (x) { return 0.5 - 0.5 * Math.cos(Math.PI * x); };
  var f = function (x, d) { return SC.fmt(x, d); };
  var deg = '\u00b0', nd = '\u2013', thin = '\u2009';

  // survives re-renders (size / build switches)
  var st = { t: 0, dy: 0, playing: false, userPaused: false, stepI: 0, inView: false };
  var R = null;             // the live render: {D, K, ctx, dw, ...}
  var open = false;
  var raf = 0, t0 = 0, io = null;

  function variant() { return SC.state.variant; }
  function other(v) { return v === 'T' ? 'M' : 'T'; }
  function rangeOf(v, dy, K) { return SC.crank.raw(v, dy, K); }
  function stateOf(th, r) {
    return Math.abs(th - r.theta_bottom) <= 0.05 || th > r.theta_bottom ? 'bottom' : th >= r.theta_click - 1e-9 ? 'clicked' : 'open';
  }
  function proudAt(th, K, C) { return C.proud_mm - SC.crank.keyDown(th, K.theta_built, K); }
  function bbox(polys) {
    var b = [Infinity, -Infinity, Infinity, -Infinity];
    polys.forEach(function (poly) { poly.forEach(function (ring) { ring.forEach(function (p) {
      b[0] = Math.min(b[0], p[0]); b[1] = Math.max(b[1], p[0]); b[2] = Math.min(b[2], p[1]); b[3] = Math.max(b[3], p[1]);
    }); }); });
    return b;
  }
  function layerBox(dr, id) {
    var l = (dr.layers || []).filter(function (x) { return x.id === id; })[0] || (dr.beyond || []).filter(function (x) { return x.id === id; })[0];
    return l ? bbox(l.polys) : null;
  }

  // ---------------- pose: the one place the kinematics are applied ----------------
  function pose(push) {
    if (!R || !R.dw || !R.dw.svg.isConnected) return;
    var K = R.K, C = R.C, v = variant(), CR = SC.crank;
    var r = rangeOf(v, st.dy, K);
    var th = r.theta_rest + st.t * (r.theta_bottom - r.theta_rest);
    var rot = th - K.theta_built;
    var down = CR.keyDown(th, K.theta_built, K);              // since the drawing's pose (theta_built)
    var pl = CR.plungerIn(v, th, st.dy, K);
    var ry = K.rod.yz[0], rz = K.rod.yz[1];
    var g = R.dw.groups;
    // drawing frame: x = Y, y = -Z; +theta (right-handed about +X) is a negative SVG rotation
    if (g.crank) g.crank.setAttribute('transform', 'rotate(' + (-rot).toFixed(4) + ' ' + ry + ' ' + (-rz) + ')');
    if (g.key) g.key.setAttribute('transform', 'translate(0 ' + down.toFixed(5) + ')');
    if (g.board) g.board.setAttribute('transform', 'translate(' + st.dy.toFixed(3) + ' 0)');
    if (g.nub) g.nub.setAttribute('transform', 'translate(' + (st.dy + pl).toFixed(5) + ' 0)');
    var s = stateOf(th, r), hit = s !== 'open';
    R.dw.svg.classList.toggle('keys-hit', hit);
    R.dw.svg.setAttribute('data-theta', th.toFixed(4));
    var keyDown = CR.keyDown(th, r.theta_rest, K), proud = proudAt(th, K, C);
    var q = R.ctx.q;
    q('#keys-r-th').textContent = f(th, 2) + deg;
    q('#keys-r-key').textContent = f(keyDown, 3) + ' mm';
    q('#keys-r-pl').textContent = f(pl, 3) + ' mm';
    var sd = q('#keys-r-st'); sd.textContent = s; sd.classList.toggle('hit', hit);
    q('#keys-r-proud').textContent = f(proud, 2) + ' mm';
    var sc = q('#keys-scrub');
    sc.value = Math.round(1000 * st.t);
    sc.setAttribute('aria-valuetext', f(th, 1) + ' degrees, key ' + f(keyDown, 2) + ' mm down, switch ' + s);
    R.last = { t: st.t, dy: st.dy, variant: v, theta: th, key_down: keyDown, key_from_built: down, plunger_in: pl, state: s, proud: proud, range: r };
    applyLive();
    if (push !== false) push3D();
  }
  // the stage: nominal board (dy 0), same kinematics; a press with theta when the drawing is nominal too
  function push3D() {
    if (!open || !R || !SC.viewer || !SC.viewer.press) return;
    var ref = R.K.draw_ref;
    if (st.dy === 0) SC.viewer.press(ref, st.t, { theta: R.last.theta, src: 'keys' });
    else SC.viewer.press(ref, st.t, { src: 'keys' });
  }

  // ---------------- play / scrub ----------------
  function tick(now) {
    if (!st.playing) return;
    if (!R || !R.dw || !R.dw.svg.isConnected) { st.playing = false; return; }
    var T = CYCLE[CYCLE.length - 1][0], t = ((now - t0) / 1000) % T, i = 0;
    while (i < CYCLE.length - 2 && t > CYCLE[i + 1][0]) i++;
    var a = CYCLE[i], b = CYCLE[i + 1];
    st.t = a[1] + (b[1] - a[1]) * ease((t - a[0]) / (b[0] - a[0]));
    pose();
    raf = requestAnimationFrame(tick);
  }
  function setPlaying(on) {
    st.playing = !!on;
    cancelAnimationFrame(raf);
    var btn = R && R.ctx.q('#keys-play');
    if (btn && !REDUCED) { btn.setAttribute('aria-pressed', String(st.playing)); btn.textContent = st.playing ? 'Pause' : 'Play'; }
    if (st.playing) { t0 = performance.now(); raf = requestAnimationFrame(tick); }
  }
  function stopPlay() { st.userPaused = true; if (st.playing) setPlaying(false); }

  // ---------------- selectors ----------------
  function segs(host, items, cur, pick) {
    host.innerHTML = '';
    items.forEach(function (it) {
      var b = document.createElement('button');
      b.type = 'button'; b.innerHTML = it.label; b.dataset.value = String(it.value);
      if (it.title) b.title = it.title;
      b.setAttribute('aria-pressed', String(it.value === cur));
      b.addEventListener('click', function () { pick(it.value); });
      host.appendChild(b);
    });
  }
  function drawSelectors() {
    var q = R.ctx.q, K = R.K, v = variant();
    segs(q('#keys-var'), ['T', 'M'].map(function (x) {
      var sw = K.switches[x];
      return { value: x, label: SC.esc(sw.part) + ' + ' + SC.esc(sw.crank), title: SC.text(sw.label) };
    }), v, function (x) { if (x !== variant()) SC.set({ variant: x }); });
    segs(q('#keys-tol'), TOL.map(function (dy) {
      return { value: dy, label: dy === 0 ? 'nominal' : (dy > 0 ? '+' : '\u2212') + f(Math.abs(dy), 1) + ' mm',
               title: dy === 0 ? 'Plunger face where the board model puts it' : 'Plunger face ' + f(Math.abs(dy), 1) + ' mm ' + (dy > 0 ? 'further from' : 'closer to') + ' the crank' };
    }), st.dy, function (dy) { st.dy = dy; drawSelectors(); fillTolerance(); pose(); });
    q('#keys-ref-part').textContent = K.switches[v].part;
    q('#keys-ref-crank').textContent = K.switches[v].crank;
  }

  // ---------------- info boxes ----------------
  function nums(el, rows) {
    el.innerHTML = rows.filter(Boolean).map(function (r) {
      return '<div><dt>' + r[0] + '</dt><dd>' + r[1] + (r[2] ? '<small>' + r[2] + '</small>' : '') + '</dd></div>';
    }).join('');
  }
  function band(a, d, u) { return f(a[0], d) + nd + f(a[1], d) + (u ? thin + u : ''); }
  // the force table, one shape in both sizes (sc_contract.force_table):
  // {"MJTP 1.27": {"mu_0.3": [N at each forces.press_ys]}}; this variant's switch's rows, by mu then force
  function forceRows(K, v) {
    var T = K.forces.table, pre = v === 'M' ? 'MJTP ' : 'TS365 ', out = [];
    Object.keys(T).forEach(function (k) {
      if (k.indexOf(pre) !== 0) return;
      Object.keys(T[k]).forEach(function (mk) { out.push({ N: +k.slice(pre.length), mu: +mk.slice(3), vals: T[k][mk] }); });
    });
    out.sort(function (a, b) { return a.mu - b.mu || a.N - b.N; });
    return out;
  }
  function fillInfo() {
    var q = R.ctx.q, K = R.K, C = R.C, v = variant(), CR = SC.crank, sw = K.switches[v];
    var fo = K.forces, lev = fo.lever;
    // forces
    var rows = forceRows(K, v), ys = fo.press_ys;
    var yName = function (y, i) { return i === 0 ? 'near the chin' : i === ys.length - 1 ? 'top edge' : 'centre'; };
    q('#keys-f-tab').innerHTML = rows.length ? '<thead><tr><th>' + SC.esc(sw.part) + '</th>' + ys.map(function (y, i) {
      return '<th class="n">' + yName(y, i) + '<br>y ' + f(y, 1) + '</th>';
    }).join('') + '</tr></thead><tbody>' + rows.map(function (r) {
      return '<tr><td>' + f(r.N, 2) + ' N, &mu; ' + f(r.mu, 2) + '</td>' + r.vals.map(function (x) { return '<td class="n">' + f(x, 2) + ' N</td>'; }).join('') + '</tr>';
    }).join('') + '</tbody>' : '';
    q('#keys-f-lead').innerHTML = 'Force at the key for the ' + SC.esc(sw.part) + ', across its rated ' + band(sw.force_N, 2, 'N') + ', at three points along the key.';
    var rk = fo['rev_k_rocker_N_at_1.86'];
    nums(q('#keys-f-nums'), [
      ['At the key&rsquo;s centre, &mu; ' + f(fo.mu, 2), band(fo.finger_N[v], 2, 'N')],
      ['Other switch (' + SC.esc(K.switches[other(v)].part) + ')', band(fo.finger_N[other(v)], 2, 'N')],
      ['Lever, pad : nose', f(lev.input_arm, 2) + ' : ' + f(lev.output_arm, 2) + thin + 'mm', 'ratio ' + f(lev.ratio, 3)],
    ]);
    q('#keys-ideal').textContent = f(lev.output_arm / lev.input_arm, 2);
    q('#keys-rocker').innerHTML = rk ? 'The rocker it replaces took ' + f(rk.centre, 2) + '&nbsp;N at its centre on a 1.86&nbsp;N switch.'
      : fo.rocker_for_comparison ? 'For comparison, ' + SC.esc(fo.rocker_for_comparison) + '.' : '';
    // travel (nominal board)
    var r0 = rangeOf(v, 0, K);
    nums(q('#keys-t-nums'), [
      ['Key to the click', f(r0.key_click, 3) + thin + 'mm', 'crank ' + f(r0.theta_click, 2) + deg],
      ['Key to the switch&rsquo;s bottom', f(r0.key_bottom, 3) + thin + 'mm', 'crank ' + f(r0.theta_bottom, 2) + deg],
      ['Plunger to click / bottom', f(sw.travel.click, 2) + ' / ' + f(sw.travel.bottom, 2) + thin + 'mm'],
      ['Key over plunger travel', f(r0.key_click / sw.travel.click, 2), 'the lever&rsquo;s ratio, as moved'],
    ]);
    // proud
    var lo = rangeOf(v, 0.2, K), hi = rangeOf(v, -0.2, K);
    var thW = CR.thetaAt(other(v), CR.face(v, 0, K), K), proudW = proudAt(thW, K, C);
    nums(q('#keys-p-nums'), [
      ['Above the face at rest', f(C.proud_mm, 2) + thin + 'mm', 'nominal board'],
      ['Over the board tolerance', f(proudAt(lo.theta_rest, K, C), 2) + nd + f(proudAt(hi.theta_rest, K, C), 2) + thin + 'mm', 'plunger face &plusmn;0.2 mm'],
      ['At the switch&rsquo;s bottom, lowest', f(proudAt(lo.theta_bottom, K, C), 2) + thin + 'mm', 'still above the face'],
      ['With the wrong crank', f(proudW, 2) + thin + 'mm', SC.esc(K.switches[other(v)].crank) + ' on this ' + SC.esc(sw.part)],
    ]);
    var diffNose = Math.abs(K.nose.c.M[0] - K.nose.c.T[0]);
    q('#keys-nose-diff').textContent = f(diffNose, 2);
    var dW = proudW - C.proud_mm;
    q('#keys-wrong').innerHTML = 'with ' + SC.esc(K.switches[other(v)].crank) + ' on a ' + SC.esc(sw.part) + ' the key rests ' +
      f(Math.abs(dW), 2) + '&nbsp;mm ' + (dW > 0 ? 'higher' : 'lower') + ', ' + f(proudW, 2) + '&nbsp;mm proud.';
    // rod
    var rc = K.rod_check;
    nums(q('#keys-r-nums'), [
      ['Rod bending', f(rc.bending_MPa, 1) + thin + 'MPa'],
      ['Rod deflection', f(rc.deflection_um, 1) + thin + '&micro;m'],
      rc.shear_MPa != null ? ['Rod shear', f(rc.shear_MPa, 1) + thin + 'MPa'] : null,
      rc.plunger_N != null ? ['Nose on the plunger', f(rc.plunger_N, 1) + thin + 'N'] : null,
      rc.pin_N != null ? ['Crank on the rod', f(rc.pin_N, 1) + thin + 'N'] : null,
    ]);
    // hooks (test 2: rigid hooks in slots; no drag, no preload)
    var hk = K.hooks, w = hk.key_mass_g * 9.81e-3, po = hk.pull_out;
    nums(q('#keys-h-nums'), [
      ['Face down', f(hk.W_OUT_mm, 2) + thin + 'mm out', 'onto both hooks, level'],
      ['First press, face down', band(hk.face_down_free_travel_mm, 2, 'mm'), 'before the click; face up there is none'],
      ['Hooks', f(hk.hook_h_mm, 2) + thin + 'mm tall', band(hk.hook_dx, 2, 'mm') + ' each side of the key&rsquo;s centre'],
      ['Tip to the slot&rsquo;s back', f(hk.hook_tip_y - hk.slot_back_y, 2) + thin + 'mm', 'the slot&rsquo;s roof at z ' + f(hk.slot_roof_z, 2)],
      po ? ['Pulled at ' + f(po.pull_N, 1) + ' N', f(po.root_bending_MPa, 1) + thin + 'MPa', 'bending at the hooks&rsquo; roots'] : null,
      ['Load on the plunger at rest', f(hk.rest_load_on_plunger_N, 4) + thin + 'N', (w ? 'gravity only, the key ' + f(w, 4) + ' N; ' : 'gravity only; ') + 'the switch needs ' + f(sw.force_N[0], 2) + ' N'],
    ]);
  }
  function fillTolerance() {
    var q = R.ctx.q, K = R.K, C = R.C, v = variant();
    var rows = (K.rest_rows || []).filter(function (r) { return r.variant === v; });
    var srcs = {};
    (K.rest_rows || []).forEach(function (r) { var m = /(\S+\.json)/.exec(r.source || ''); if (m) srcs[m[1]] = 1; });
    q('#keys-tol-src').innerHTML = Object.keys(srcs).map(function (s) { return '<code>' + SC.esc(s) + '</code>'; }).join(', ') || 'its output';
    q('#keys-tol-tab').innerHTML = '<thead><tr><th>Plunger face</th><th class="n">Rest</th><th class="n">Proud</th><th class="n">Click</th><th class="n">Bottom</th><th class="n">Key to click</th><th class="n">Solver</th></tr></thead><tbody>' +
      TOL.map(function (dy) {
        var r = rangeOf(v, dy, K), row = rows.filter(function (x) { return Math.abs(x.face_dy - dy) < 1e-6; })[0];
        var chk = '';
        if (row) {
          var dth = Math.abs(row.theta - r.theta_rest), dz = Math.abs(row.key_dz - SC.crank.keyDown(r.theta_rest, K.theta_built, K));
          var ok = dth <= 0.015 && dz <= 0.0015;
          chk = '<td class="n ' + (ok ? 'ok' : 'bad') + '" title="' + SC.esc(row.source || '') + '">' + f(row.theta, 2) + deg + ' ' + (ok ? '\u2713' : '\u2717') + '</td>';
        } else chk = '<td class="n">&ndash;</td>';
        return '<tr' + (dy === st.dy ? ' class="now"' : '') + '><td>' + (dy === 0 ? 'nominal' : (dy > 0 ? '+' : '\u2212') + f(Math.abs(dy), 1) + ' mm') + '</td>' +
          '<td class="n">' + f(r.theta_rest, 2) + deg + '</td><td class="n">' + f(proudAt(r.theta_rest, K, C), 2) + ' mm</td>' +
          '<td class="n">' + f(r.theta_click, 2) + deg + '</td><td class="n">' + f(r.theta_bottom, 2) + deg + '</td>' +
          '<td class="n">' + f(r.key_click, 3) + ' mm</td>' + chk + '</tr>';
      }).join('') + '</tbody>';
  }
  function detailText(d) {
    if (d == null || d === '') return '';
    var x = d;
    if (typeof d === 'string' && /^[\[{]/.test(d)) { try { x = JSON.parse(d); } catch (e) { x = d; } }
    var flat = function (a) { return Array.isArray(a) ? a.map(flat).join(', ') : typeof a === 'number' ? f(a) : String(a); };
    return flat(x);
  }
  function fillChecks() {
    var q = R.ctx.q, list = R.K.checks || [];
    var ok = list.filter(function (c) { return c.ok === true; }).length, bad = list.filter(function (c) { return c.ok === false; }).length;
    var acc = list.filter(function (c) { return c.status === 'accepted'; }).length, nr = list.filter(function (c) { return c.ok == null; }).length;
    q('#keys-chk-sum').innerHTML = ok + ' of ' + list.length + ' pass' + (bad ? ', <b>' + bad + ' fail</b>' : '') + (acc ? ', ' + acc + ' accepted finding' + (acc > 1 ? 's' : '') : '') + (nr ? ', ' + nr + ' not run' : '');
    q('#keys-chk').innerHTML = list.map(function (c) {
      var cls = c.ok === false ? 'fail' : c.ok == null ? 'nr' : c.status === 'accepted' ? 'acc' : '';
      var mark = c.ok === false ? '\u2717' : c.ok == null ? '?' : c.status === 'accepted' ? '!' : '\u2713';
      var det = detailText(c.detail), val = c.value != null && c.value !== '' && !det ? detailText(c.value) : '';
      var extra = [det || val, c.status === 'accepted' ? 'accepted finding' : '', c.source ? SC.esc(c.source) : ''].filter(Boolean).join(' &middot; ');
      return '<li class="' + cls + '"><b aria-label="' + (c.ok === false ? 'fails' : c.ok == null ? 'not run' : 'passes') + '">' + mark + '</b><span>' + c.label + '</span>' + (extra ? '<small>' + extra + '</small>' : '') + '</li>';
    }).join('');
  }

  // ---------------- the drawing ----------------
  function makeDrawing(D, ctx) {
    var K = D.keys, dr = SC.drawing('key');
    if (!dr) throw new Error('no key drawing in this data');
    var w = dr.window;
    // the card's own copy with a wider window, so the labels sit beside the parts and not on them
    var mine = Object.assign({}, dr, { window: [w[0] - 6.8, w[1] + 6.4, w[2] - 0.4, w[3] + 1.1] });
    var v = variant(), o = other(v);
    var host = ctx.q('#keys-dwg');
    host.innerHTML = '';
    var moving = { crank_M: 'crank', crank_T: 'crank', cheek: 'crankb', key: 'key', hook: 'key', pcb: 'board', sw_M: 'board', sw_T: 'board',
                   nub_M: 'nub', nub_T: 'nub', rod: 'rod' };
    var boxes = {};
    ['tub', 'key', 'pcb', 'sw_M', 'sw_T', 'nub_M', 'nub_T', 'crank_M', 'crank_T', 'rod', 'rail'].forEach(function (id) { boxes[id] = layerBox(dr, id); });
    var faceZ = D.meta && D.meta.z && D.meta.z.front != null ? D.meta.z.front : boxes.key[3] - R.C.proud_mm;
    var dw = ctx.Drawing(mine, host, {
      label: 'Cut through bottom key ' + (dr.notes && dr.notes.ref || K.draw_ref) + ': key, bell crank, rod and switch',
      moving: moving, hide: ['crank_' + o, 'sw_' + o, 'nub_' + o],
      groupOrder: ['crankb', 'board', 'nub', 'crank', 'rod', 'key'],
      annotate: function (A, self) { annotate(A, self, D, boxes, faceZ); },
    });
    // on a phone the drawing keeps its width and scrolls sideways: open it at scroll 0, so the left-hand labels read
    // in full and the reader scrolls on toward the mechanism (opening mid-way cut the labels on both sides)
    host.scrollLeft = 0;
    return dw;
  }
  function annotate(A, self, D, bx, faceZ) {
    if (!R) return;
    var K = D.keys, v = variant(), px = A.px, sw = K.switches[v];
    var colL = -10.2, colR = 4.75;
    var lab = function (u, vv, s, side, tv, hot) {
      var X = side === 'l' ? colL + 9 * px : colR - 9 * px;
      A.label(u, vv, s, (X - u) / px, (tv - vv) / px, { hot: hot });
    };
    var kb = bx.key, kc = (kb[0] + kb[1]) / 2;
    var ry = K.rod.yz[0], rz = K.rod.yz[1];
    var pad = K.pad.c, nc = K.nose.c[v], nr = K.nose.r;
    // left column, top to bottom
    lab(kb[0] + 0.55, faceZ - 1.6, 'key: slides\nstraight down', 'l', Math.max(faceZ + 0.9, 5.0));
    var hz = K.hooks.hook_z_rest;
    lab(kb[0] - 0.05, (hz[0] + hz[1]) / 2, 'hook in its slot\n(dashed, behind)', 'l', 2.75);
    lab(pad[0], pad[1] + K.pad.r, 'crowned pad', 'l', 0.15);
    lab(pad[0] + 1.6, pad[1] - 1.55, 'bell crank\nturns on the rod', 'l', -2.4);
    lab(-8.6, -5.2, 'lid', 'l', -5.4);
    // right column
    lab(2.4, faceZ - 0.35, 'tub skin', 'r', faceZ + 1.3);
    if (bx.rail) lab(ry + 1.25, rz + 1.2, 'rod rail: rings\n(dashed), seats', 'r', 3.3);
    lab(ry + 0.62, rz + 0.62, 'rod, ' + f(K.rod.d, 2) + ' mm\nPLA filament', 'r', 1.3);
    if (bx.pcb) lab(Math.min(3.2, bx.pcb[1] - 0.8), 1.0, 'board', 'r', -0.45);
    var sb = bx['sw_' + v];
    if (sb) lab(Math.min(2.6, sb[1] - 0.8), (sb[2] + sb[3]) / 2 - 0.2, 'switch\n' + sw.part, 'r', -2.2);
    var nb = bx['nub_' + v];
    if (nb) lab((nb[0] + nb[1]) / 2, (nb[2] + nb[3]) / 2, 'plunger\npushed sideways', 'r', -4.1, true);
    lab(nc[0] + nr * 0.72, nc[1] - nr * 0.7, 'crowned nose\n' + sw.crank, 'r', -6.2, true);
    // live: the press arrow, the key-top tick and the proud text ride with the key; the face tick and the
    // dimension line (redrawn on each pose) stay in the fixed annotation layer
    var top = kb[3], au = kc - 0.3, du = kb[1] + 0.45, hl = 7 * px, hw = 3.2 * px;
    var P = function (d, cls, parent) { return SC.svg('path', { d: d, 'class': cls }, parent); };
    var T = function (x, y, s, parent) {
      var t = SC.svg('text', { x: x, y: y, 'font-size': 11.5 * px, 'stroke-width': 3.2 * px, 'dominant-baseline': 'middle', 'class': 'hot' }, parent);
      t.textContent = s; return t;
    };
    P('M' + (du - 0.3) + ' ' + (-faceZ) + 'L' + (du + 0.3) + ' ' + (-faceZ), 'ann', self.ann);
    R.dim = P('M' + du + ' ' + (-faceZ) + 'L' + du + ' ' + (-top), 'ann hot', self.ann);
    var g = SC.svg('g', { 'class': 'keys-live' }, self.ann);
    P('M' + au + ' ' + (-(top + 2.1)) + 'L' + au + ' ' + (-(top + 0.35)), 'ann hot', g);
    P('M' + au + ' ' + (-(top + 0.25)) + 'L' + (au - hw) + ' ' + (-(top + 0.25 + hl)) + 'L' + (au + hw) + ' ' + (-(top + 0.25 + hl)) + 'Z', 'head hot', g);
    T(au + 0.35, -(top + 1.55), 'press', g);
    P('M' + (kb[1] - 0.05) + ' ' + (-top) + 'L' + (du + 0.3) + ' ' + (-top), 'ann', g);
    R.proudText = T(du + 0.4, -(top + 0.55), f(R.C.proud_mm, 2) + ' proud', g);
    R.live = g; R.dimU = du; R.faceZ = faceZ; R.top = top;
    applyLive();
  }
  // the parts of the annotation that follow the key (after a pose, and after a redraw rebuilt them)
  function applyLive() {
    if (!R || !R.live || !R.last) return;
    var down = R.last.key_from_built;
    R.live.setAttribute('transform', 'translate(0 ' + down.toFixed(5) + ')');
    R.dim.setAttribute('d', 'M' + R.dimU + ' ' + (-R.faceZ) + 'L' + R.dimU + ' ' + (-(R.top - down)));
    R.proudText.textContent = f(R.last.proud, 2) + ' proud';
  }

  function wire(ctx) {
    var q = ctx.q;
    var btn = q('#keys-play'), sc = q('#keys-scrub');
    if (REDUCED) {
      btn.textContent = 'Press';
      btn.onclick = function () {
        var r = rangeOf(variant(), st.dy, R.K);
        st.stepI = (st.stepI + 1) % 3;
        st.t = [0, (r.theta_click - r.theta_rest) / (r.theta_bottom - r.theta_rest), 1][st.stepI];
        btn.textContent = st.stepI === 2 ? 'Release' : 'Press';
        pose();
      };
    } else {
      btn.onclick = function () { st.userPaused = st.playing; setPlaying(!st.playing); };
      btn.textContent = st.playing ? 'Pause' : 'Play';
      btn.setAttribute('aria-pressed', String(st.playing));
    }
    sc.oninput = function () { stopPlay(); st.t = +sc.value / 1000; pose(); };
    // play by itself while the drawing is on screen, until the reader takes over
    if (io) io.disconnect();
    io = null;
    if (!REDUCED && 'IntersectionObserver' in window) {
      io = new IntersectionObserver(function (es) {
        st.inView = es[es.length - 1].isIntersecting;
        if (!st.userPaused) setPlaying(st.inView);
      }, { threshold: 0.35 });
      io.observe(R.dw.svg);
    }
    // a variant swap re-mounts the stage with the old angle: put this pose back once it has
    ctx.on('state', function () { if (open) pose(); });
    // the stage's own slider (or another card) pressing SW8 / all keys moves the drawing
    ctx.on('pressed', function (p) {
      if (!p || p.src === 'keys' || p.kind !== 'crank' || !R) return;
      if (p.id !== R.K.draw_ref && p.id !== 'all') return;
      stopPlay();
      st.t = Math.min(1, Math.max(0, p.t || 0));
      pose(false);
    });
  }
  function markClick() {
    var r = rangeOf(variant(), st.dy, R.K), m = R.ctx.q('#keys-mark-click');
    var p = (r.theta_click - r.theta_rest) / (r.theta_bottom - r.theta_rest);
    m.style.left = (100 * p).toFixed(1) + '%';
    m.textContent = 'click ' + f(r.theta_click, 1) + deg;
  }
  function caption() {
    var K = R.K, v = variant(), sw = K.switches[v], dr = SC.drawing('key'), M = SC.manifest;
    var S = SC.state, sizeL = M && M.sizes[S.size] ? M.sizes[S.size].label : S.size, bL = M && M.builds[S.build] ? M.builds[S.build].label.toLowerCase() : S.build;
    var x = dr && dr.notes && dr.notes.x != null ? dr.notes.x : K.x[K.draw_ref];
    R.ctx.q('#keys-cap').innerHTML = 'Cut through the centre of ' + SC.part(K.draw_ref) + ' (X ' + f(x, 2) + ') of the ' + SC.esc(sizeL) + ' ' + SC.esc(bL) +
      ' build, seen from the right: ' + SC.esc(sw.crank) + ' on a ' + SC.esc(sw.part) + '. Hatched: tub and lid. Pale, dashed: the crank&rsquo;s cheek behind the cut, the rod rail&rsquo;s ring beside the crank and the key&rsquo;s +X hook. ' +
      'Tub, lid, key, crank and rod are sections of the built parts; the ' + (v === 'M' ? 'MJTP1117 is the board model&rsquo;s own' : 'TS365ZJ is a drawn envelope of the switch') + '.';
  }
  function renderAll(D, ctx) {
    cancelAnimationFrame(raf);
    R = { D: D, K: D.keys, C: D.cards.keys, ctx: ctx, dw: null };
    R.dw = makeDrawing(D, ctx);
    drawSelectors(); fillInfo(); fillTolerance(); fillChecks(); markClick(); caption();
    wire(ctx);
    pose(false);
    if (st.playing) setPlaying(true);
  }

  function now() { return R && R.last ? Object.assign({}, R.last, { open: open, playing: st.playing }) : null; }
  SC.card({
    id: 'keys',
    title: 'Bottom keys: a straight key over a bell crank',
    order: 20,
    preset: 'keys',
    needs: ['keys.rod.yz', 'keys.pad.c', 'keys.nose.c.M', 'keys.nose.c.T', 'keys.switches.T.face_y', 'keys.switches.M.face_y',
            'keys.forces.finger_N.T', 'keys.forces.table', 'keys.forces.press_ys', 'keys.forces.lever.ratio', 'keys.hooks.W_OUT_mm', 'keys.hooks.face_down_free_travel_mm', 'keys.hooks.hook_z_rest', 'keys.hooks.key_mass_g', 'keys.rod_check.bending_MPa',
            'keys.rest_rows', 'keys.checks', 'cards.keys.proud_mm', 'meta.z.front'],
    render: function (D, ctx) { renderAll(D, ctx); },
    onVariant: function (v, D, ctx) {
      if (!R || !R.dw) return;
      ['M', 'T'].forEach(function (x) { ['crank_', 'sw_', 'nub_'].forEach(function (p) { R.dw.show(p + x, x === v); }); });
      R.dw.redraw();
      drawSelectors(); fillInfo(); fillTolerance(); markClick(); caption();
      pose();
    },
    onEnter: function (D, ctx) {
      open = true;
      // "Show in 3D" runs the preset (which may release the press); put the drawing's pose back on the stage after it
      ctx.on('focus', function (name) { if (name === 'keys') setTimeout(function () { pose(); }, 0); });
      ctx.on('viewer', function () { pose(); });
      pose();
    },
    onLeave: function () { open = false; },
    // for tests and other cards: the current pose, and a way to set it
    now: now,
    pose: function (t, dy) {
      stopPlay();
      if (dy != null && TOL.indexOf(dy) >= 0 && dy !== st.dy) { st.dy = dy; if (R) { drawSelectors(); fillTolerance(); markClick(); } }
      st.t = Math.min(1, Math.max(0, +t || 0)); pose(); return now();
    },
  });
})();
