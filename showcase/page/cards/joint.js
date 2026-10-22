// Tub to lid joint: the parting-line map (cards.joint.joint) and the drawings joint_tongue, joint_at_tab, joint_top, joint_latch.
SC.card({
  id: 'joint', title: 'Tub to lid joint', order: 40, preset: 'joint',
  needs: ['cards.joint.joint', 'cards.joint.joint.runs', 'cards.joint.joint.snaps', 'cards.joint.joint.walls', 'cards.joint.latches', 'cards.sidekeys.tabs', 'cards.sidekeys.tab_geom'],
  render: function (D, ctx) {
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    // labels that stay inside the drawing's window (flip to the other side, else slide in)
    var fitA = function (a, d) {
      var o = Object.create(a), px = a.px;
      o.label = function (u, v, s, dx, dy, opt) {
        var ls = String(s).split('\n');
        var tw = (Math.max.apply(null, ls.map(function (l) { return l.length; })) * 7 + 12) * px, hh = (ls.length * 7.2 + 4) * px;
        var tv = v + dy * px, tu = u + dx * px;
        if (tv + hh > d.v1) dy -= (tv + hh - d.v1) / px;
        if (tv - hh < d.v0) dy += (d.v0 - tv + hh) / px;
        if (dx >= 0 && tu + tw > d.u1) dx = u - Math.abs(dx) * px - tw >= d.u0 ? -Math.abs(dx) : dx - (tu + tw - d.u1) / px;
        else if (dx < 0 && tu - tw < d.u0) dx = u + Math.abs(dx) * px + tw <= d.u1 ? Math.abs(dx) : dx + (d.u0 - tu + tw) / px;
        return a.label(u, v, s, dx, dy, opt);
      };
      return o;
    };
    // the nearest point to (u, v) that lies inside layer id of drawing dr (so a label's dot sits on that part)
    var inRing = function (r, u, v) {
      var c = false;
      for (var i = 0, j = r.length - 1; i < r.length; j = i++) {
        var a = r[i], b = r[j];
        if ((a[1] > v) !== (b[1] > v) && u < (b[0] - a[0]) * (v - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
      }
      return c;
    };
    var inside = function (L, u, v) {
      var n = 0;
      L.polys.forEach(function (p) { p.forEach(function (r) { if (inRing(r, u, v)) n++; }); });
      return n % 2 === 1;
    };
    var P = function (dr, id, u, v) {
      var L = (dr.layers || []).concat(dr.beyond || []).filter(function (l) { return l.id === id; })[0];
      if (!L) return [u, v];
      var w = dr.window, st = Math.max(w[1] - w[0], w[3] - w[2]) / 300;
      for (var k = 0; k < 90; k++) {
        var r = k * st, n = Math.max(1, Math.round(k * 6));
        for (var i = 0; i < n; i++) {
          var t = 2 * Math.PI * i / n, pu = u + r * Math.cos(t), pv = v + r * Math.sin(t);
          if (pu > w[0] && pu < w[1] && pv > w[2] && pv < w[3] && inside(L, pu, pv)) return [pu, pv];
        }
      }
      return [u, v];
    };
    var lab = function (a, dr, id, u, v, s, dx, dy, opt) { var p = P(dr, id, u, v); a.label(p[0], p[1], s, dx, dy, opt); };

    var CJ = D.cards.joint, JT = CJ.joint, LT = CJ.latches || JT.latch || {};
    var W = JT.walls, tt = JT.tongue_t, th = JT.tongue_h, sz = JT.seam;
    var GV = D.cards.sidekeys.tab_geom || {}, slv = GV.sliver || tt;
    var words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen'];
    fill('joint-n-word', words[CJ.latch_count] || String(CJ.latch_count));
    var nRuns = 0, gaps = [];
    Object.keys(JT.runs).forEach(function (w) {
      var rs = JT.runs[w].slice().sort(function (a, b) { return a[0] - b[0]; });
      nRuns += rs.length;
      for (var i = 1; i < rs.length; i++) gaps.push(rs[i][0] - rs[i - 1][1]);
    });
    fill('joint-runs', String(nRuns));
    fill('joint-stops', gaps.length ? ' (' + gaps.length + ' short gaps, ' + f(Math.min.apply(null, gaps), 1) + '&ndash;' + f(Math.max.apply(null, gaps), 1) + ' mm)' : '');
    var topN = (JT.snaps.top || []).length;
    fill('joint-top-latches', topN ? '; ' + (words[topN] || topN) + ' more stand on the top wall, where the board was cut away' : '');

    // ---- plan of the parting line ----
    var host = ctx.q('#joint-map');
    host.innerHTML = '';
    var O = JT.outline, OX0 = O[0], OX1 = O[1], OY0 = O[2], OY1 = O[3], OR = O[4], pad = 7;
    var svg = SC.svg('svg', { viewBox: (OX0 - pad) + ' ' + (-(OY1 + pad)) + ' ' + (OX1 - OX0 + 2 * pad) + ' ' + (OY1 - OY0 + 2 * pad), class: 'jmap', role: 'img',
      'aria-label': 'Plan of the parting line: where the tongue and the latches run, and what else uses the wall' }, host);
    SC.svg('rect', { x: OX0, y: -OY1, width: OX1 - OX0, height: OY1 - OY0, rx: OR, class: 'shell' }, svg);
    SC.svg('rect', { x: W.left, y: -W.top, width: W.right - W.left, height: W.top - W.bottom, rx: 1.5, fill: 'var(--paper)', class: 'shell' }, svg);
    var mid = { left: W.left - tt / 2, right: W.right + tt / 2, top: W.top + tt / 2 };
    var seg = function (wall, a0, a1, cls) {
      return wall === 'top' ? SC.svg('line', { x1: a0, y1: -mid.top, x2: a1, y2: -mid.top, class: cls }, svg)
        : SC.svg('line', { x1: mid[wall], y1: -a0, x2: mid[wall], y2: -a1, class: cls }, svg);
    };
    (JT.tabs || []).forEach(function (t) { seg(t[0] > 0 ? 'right' : 'left', t[1], t[2], 'busy'); });
    if (JT.usb_y) seg('right', JT.usb_y[0] - 0.6, JT.usb_y[1] + 0.6, 'busy');
    if (JT.reset_y != null) seg('right', JT.reset_y - 1.4, JT.reset_y + 1.4, 'busy');
    if (JT.j6_x) seg('top', JT.j6_x[0], JT.j6_x[1], 'busy');
    SC.svg('line', { x1: 6.0, y1: -(W.bottom + 0.4), x2: 54.0, y2: -(W.bottom + 0.4), class: 'busy' }, svg);
    if (JT.top_screw) SC.svg('circle', { cx: JT.top_screw[0], cy: -JT.top_screw[1], r: 1.7, class: 'scr' }, svg);
    // the 3.68 lists all its screws (the top-left one stands where two tongue runs end; the bottom pair in the chin)
    var xtra = (JT.screws || []).filter(function (q) { return q[0] !== 'top'; });
    xtra.forEach(function (q) { SC.svg('circle', { cx: q[1], cy: -q[2], r: 1.7, class: 'scr' }, svg); });
    Object.keys(JT.runs).forEach(function (w) { JT.runs[w].forEach(function (r) { seg(w, r[0], r[1], 'run'); }); });
    var S = JT.snap;
    Object.keys(JT.snaps).forEach(function (wall) {
      JT.snaps[wall].forEach(function (c) {
        if (wall === 'top') SC.svg('rect', { x: c - S.w / 2, y: -(W.top - S.gap), width: S.w, height: S.t_root, class: 'latch' }, svg);
        else {
          var x = wall === 'left' ? W.left + S.gap : W.right - S.gap - S.t_root;
          SC.svg('rect', { x: x, y: -(c + S.w / 2), width: S.t_root, height: S.w, class: 'latch' }, svg);
        }
      });
    });
    var tx = function (x, y, s, anchor) {
      var e = SC.svg('text', { x: x, y: -y, 'font-size': 3.0, 'text-anchor': anchor || 'start', 'dominant-baseline': 'middle' }, svg);
      e.textContent = s;
    };
    var tabs = D.cards.sidekeys.tabs || [];
    ['left', 'right'].forEach(function (wall) {
      var ts = tabs.filter(function (t) { return (t.side > 0) === (wall === 'right'); });
      if (!ts.length) return;
      var ys = ts.map(function (t) { return (t.pad_y[0] + t.pad_y[1]) / 2; });
      var y = ys.reduce(function (s, v) { return s + v; }, 0) / ys.length;
      var refs = ts.slice().sort(function (p, q) { return q.pad_y[0] - p.pad_y[0]; }).map(function (t) { return t.ref; }).join(', ');
      if (wall === 'left') tx(W.left + 2, y, refs + (ts.length > 1 ? ' keys' : ' key'));
      else tx(W.right - 2, y, refs + (ts.length > 1 ? ' keys' : ' key'), 'end');
    });
    if (JT.usb_y) tx(W.right - 2, (JT.usb_y[0] + JT.usb_y[1]) / 2, 'USB-C', 'end');
    if (JT.reset_y != null) tx(W.right - 2, JT.reset_y - 3.2, 'reset pin', 'end');
    if (JT.j6_x) tx((JT.j6_x[0] + JT.j6_x[1]) / 2, W.top - 2.6, 'expansion header J6', 'middle');
    if (JT.top_screw) tx(JT.top_screw[0] - 2.5, JT.top_screw[1] - 2.6, 'top screw', 'end');
    xtra.forEach(function (q) { if (q[0] === 'top-left') tx(q[1] + 2.5, q[2] - 2.6, 'top-left screw'); });
    tx((W.left + W.right) / 2, W.bottom + 2.6, D.meta.bottom_keys && !D.meta.bottom_keys.length ? 'chin wall, no keys' : 'bottom keys and their ledge', 'middle');
    tx(W.left + 2, 12 + S.w, 'latches');

    // ---- the four sections ----
    var dT = SC.drawing('joint_tongue'), dA = SC.drawing('joint_at_tab'), dP = SC.drawing('joint_top'), dL = SC.drawing('joint_latch');
    fill('joint-at-tongue', f(dT.at, 0));
    fill('joint-at-tab', f(dA.at, 1).replace(/\.0$/, ''));
    fill('joint-at-top', f(dP.at, 0));
    var tabRef = (dA.notes && dA.notes.ref) || '', tab = tabs.filter(function (t) { return t.ref === tabRef; })[0];
    fill('joint-tab-ref', SC.part(tabRef));
    fill('joint-tab-wall', !tab || tab.side > 0 ? 'Right' : 'Left');
    fill('joint-latch-ref', SC.part((dL.notes && dL.notes.ref) || 'SW1'));
    var z = D.meta.z;
    ctx.Drawing('joint_tongue', 'dw-joint-tongue', {
      label: 'Section through the tongue on the left wall', order: ['tub', 'lid', 'pcb'],
      annotate: function (a0, d) {
        var a = fitA(a0, d);
        lab(a, dT, 'tub', W.left - tt / 2, sz - th * 0.5, 'tongue ' + f(tt, 2), 76, 2, { hot: true });
        a.label(W.left - tt - JT.clr / 2, sz - th * 0.5, f(JT.clr, 2) + ' per face', 98, 24);
        lab(a, dT, 'lid', W.left - tt - JT.clr - 0.5, sz - th * 0.5, 'lid leg', 121, 46);
        lab(a, dT, 'lid', W.left + JT.lip / 2, sz - th * 0.8, 'lid lip', 40, -4);
        a.label(W.left, sz, 'parting line', 57, 40);
        lab(a, dT, 'tub', -2.6, -1.0, 'tub wall', 74, 16);
        lab(a, dT, 'pcb', 1.6, 0.8, 'PCB', 22, -6);
      },
    });
    ctx.Drawing('joint_at_tab', 'dw-joint-at-tab', {
      label: 'Section behind a side key', order: ['tub', 'lid', 'pcb', 'tab'],
      annotate: function (a0, d) {
        var a = fitA(a0, d);
        lab(a, dA, 'tub', W.right + slv / 2, sz - th * 0.5, 'sliver, on down\nas the tongue', -58, -8, { hot: true });
        lab(a, dA, 'tub', W.right + (GV.wall || 2) / 2, 0.0, 'the tub\u2019s whole wall\nover the key', -70, 22);
        lab(a, dA, 'tab', W.right + (GV.wall || 0) - (GV.t || 0) / 2, -5.2, 'side key:\nthe lid\'s wall', -60, -40, { hot: true });
        a.label(W.right + slv + JT.clr / 2, sz - th * 0.8, 'key\'s travel', -86, -40);
        lab(a, dA, 'lid', (d.u0 + d.u1) / 2, d.v0 + 1.0, 'lid', 22, 0);
      },
    });
    ctx.Drawing('joint_top', 'dw-joint-top', {
      label: 'Section through the top-wall tongue beside the battery', order: ['tub', 'lid', 'pcb', 'cell'],
      annotate: function (a0, d) {
        var a = fitA(a0, d);
        lab(a, dP, 'tub', W.top + tt / 2, sz - th * 0.5, 'tongue', -64, -40, { hot: true });
        var cell = (dP.layers.filter(function (l) { return l.id === 'cell'; })[0] || {}).polys;
        if (cell && cell.length) lab(a, dP, 'cell', W.top - 4, (z.back + z.pcb_rear) / 2, 'battery', -14, 16);
        lab(a, dP, 'tub', W.top + 1.2, -1.0, 'tub top wall', -70, 34);
        lab(a, dP, 'lid', d.u1 - 2.0, d.v0 + 1.0, 'lid', -60, 0);
      },
    });
    var SZ = JT.snap_z;
    ctx.Drawing('joint_latch', 'dw-joint-latch', {
      label: 'Section through a right-wall latch over a side key', order: ['tub', 'lid', 'pcb', 'midplate', 'tab'],
      annotate: function (a0, d) {
        var a = fitA(a0, d), xr = W.right;
        lab(a, dL, 'lid', xr - S.gap - S.t_root * 0.5, (SZ.z_root + SZ.z_c) / 2, 'arm ' + f(S.t_root, 2) + ' \u2192 ' + f(S.t_tip, 2), -52, 0, { hot: true });
        lab(a, dL, 'lid', xr + 0.25, (SZ.z_c + SZ.z_flat) / 2, 'barb, ' + f(JT.engage, 2) + ' caught', 34, 26, { hot: true });
        lab(a, dL, 'tub', xr + S.pocket, SZ.z_top - 0.1, 'pocket in\nsolid wall', 40, 30);
        lab(a, dL, 'tab', xr + slv + 0.35, -5.0, 'side key', 38, -26);
        lab(a, dL, 'midplate', xr - 0.8, (z.mid_rear + z.pcb_front) / 2 + 0.5, 'midplate,\nnotched', -40, 26);
        lab(a, dL, 'lid', d.u1 - 4.0, d.v0 + 1.0, 'lid', -22, 0);
      },
    });

    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    var lg = JT.longest_gap_mm || {};
    var lgv = Math.max(lg.left || 0, lg.right || 0);
    ctx.q('#joint-nums').innerHTML = [
      row('Tongue', f(CJ.tongue_len, 0) + ' mm', nRuns + ' runs &middot; ' + f(tt, 2) + ' &times; ' + f(th, 1) + ' mm, on the tub'),
      row('Registration', '&plusmn;' + f(JT.clr, 2) + ' mm', 'per face &middot; ends ' + f(JT.end_clr, 1)),
      row('Latches', String(CJ.latch_count), Object.keys(JT.snaps).map(function (w) { return JT.snaps[w].length + ' ' + w; }).join(', ') + (lgv ? ' &middot; longest gap ' + f(lgv, 0) + ' mm' : '')),
      row('Catch', f(LT.catch_mm, 2) + ' mm', 'in solid wall above the key slots'),
      row('Latch push-on', f(LT.push_on_N_each, 1) + ' N', 'each &middot; ' + f(S.lead_deg, 0) + '&deg; lead-in &middot; ' + f(LT.push_on_N_all, 0) + ' N for all'),
      row('Pull-off, screws out', f(LT.pull_off_N_each, 1) + ' N', 'each &middot; ' + f(LT.pull_off_N_all, 0) + ' N for all'),
      row('Arm root strain', f(LT.root_strain_pct, 2) + ' %', f(LT.root_stress_MPa, 0) + ' MPa in PLA &middot; arm ' + f(LT.arm_mm, 1) + ' mm to the barb'),
    ].join('');
  },
});
