// Side keys: the lid's flexures (5 on 4.26, 3 on 3.68). Drawings key_side / tab_plan / tab_elev, a press slider that
// drives the drawings and the stage's flexure control for the chosen key, and the per-key table.
SC.card({
  id: 'sidekeys', title: 'Side keys', order: 30, preset: 'tabs',
  needs: ['cards.sidekeys.tabs', 'cards.sidekeys.tab_mech', 'cards.sidekeys.tab_geom', 'cards.sidekeys.draw', 'cards.sidekeys.summary'],
  render: function (D, ctx) {
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
    var S = D.cards.sidekeys, TG = S.tab_geom, TM = S.tab_mech, SUM = S.summary || {};
    var E = (D.cards.edges && D.cards.edges.edges) || {};
    var J = (D.cards.joint && D.cards.joint.joint) || {};
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var rng = function (v, n, u) { var a = Math.min.apply(null, v), b = Math.max.apply(null, v); return (f(a, n) === f(b, n) ? f(a, n) : f(a, n) + '\u2013' + f(b, n)) + (u || ''); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var by = {};
    S.tabs.forEach(function (t) { by[t.ref] = t; });
    var ctrl = {};
    (D.controls || []).forEach(function (c) { if (c.kind === 'flexure') ctrl[c.ref] = c; });
    var nubW = function (t) { return t.nub_w || (TG.nub_w && TG.nub_w[t.ref]) || TG.nub[0]; };
    var padLen = function (t) { return t.pad_len || (t.pad_y[1] - t.pad_y[0]); };
    // the power key: named by the data (3.68), else the one key with the narrower nub (SW10 on 4.26)
    var power = S.power_key;
    if (!power) {
      var w = S.tabs.map(nubW), wmin = Math.min.apply(null, w);
      var narrow = S.tabs.filter(function (t) { return nubW(t) === wmin; });
      if (narrow.length === 1 && wmin < Math.max.apply(null, w)) power = narrow[0].ref;
    }
    var role = function (t) {
      if (S.roles && S.roles[t.ref]) return S.roles[t.ref];
      if (t.role) return t.role;
      if (t.ref === power) return 'power';
      var same = S.tabs.filter(function (u) { return u.side === t.side && u.ref !== power; });
      var low = same.every(function (u) { return u.face[1] >= t.face[1]; });
      return (t.side > 0 ? 'right' : 'left') + ', ' + (low ? 'lower' : 'upper');
    };

    // ---- head, captions, numbers in the text
    ctx.q('#sidekeys-refs').innerHTML = S.refs.map(function (r) { return '<span class="ref">' + SC.esc(r) + '</span>'; }).join('');
    var P = by[S.draw.plan] || S.tabs[0], SD = by[S.draw.side] || S.tabs[0], EL = by[S.draw.elev] || P;
    var dside = SC.drawing('key_side');
    fill('sidekeys-sref', SC.esc(SD.ref));
    fill('sidekeys-sx', dside ? f(dside.at, 1) : f(SD.root[0], 1));
    fill('sidekeys-pref', SC.esc(P.ref));
    fill('sidekeys-prole', SC.esc(role(P)));
    fill('sidekeys-backr', f(E.back_r != null ? E.back_r : 2, 1));
    fill('sidekeys-footgap', f(TG.foot_gap ? TG.foot_gap[0] : 0.75, 2));
    fill('sidekeys-footgap2', f(TG.foot_gap ? TG.foot_gap[1] : 1.2, 1));
    fill('sidekeys-barh', f(TG.bar_top - TG.z[0], 1));
    var keys = SUM.keys || {};
    var flens = Object.keys(keys).map(function (k) { return keys[k].flex_len; }).filter(function (x) { return x != null; });
    fill('sidekeys-flexlen', flens.length ? rng(flens, 1) : '?');
    var pads = S.tabs.map(padLen), padMax = Math.max.apply(null, pads);
    fill('sidekeys-padlen', f(padMax, 0));
    fill('sidekeys-face', f(S.tab_pad[0], 1) + ' &times; ' + f(S.tab_pad[1], 1));
    var pw = by[power];
    fill('sidekeys-powerpad', pw && padLen(pw) !== padMax ? f(padLen(pw), 0) + ' mm on ' + SC.esc(pw.ref) + ', power' : 'the same on every key');
    fill('sidekeys-nub', f(TG.nub[0], 1) + ' &times; ' + f(TG.nub[1], 1));
    fill('sidekeys-powernub', pw && nubW(pw) !== TG.nub[0] ? f(nubW(pw), 1) + ' wide on ' + SC.esc(pw.ref) : 'the same on every key');
    fill('sidekeys-plunger', TG.plunger ? f(TG.plunger[0], 2) + ' &times; ' + f(TG.plunger[1], 2) : '2.88 &times; 1.50');
    var gaps = S.tabs.map(function (t) { return t.gap; });
    fill('sidekeys-gap', rng(gaps, 2));
    var cen = S.tabs.map(function (t) { return TM[t.ref].finger_force_N.pad_centre; });
    fill('sidekeys-force', rng(cen, 1, ' N'));
    fill('sidekeys-stop', rng(S.tabs.map(function (t) { return TM[t.ref].stop_travel_mm; }), 2));
    fill('sidekeys-over', rng(S.tabs.map(function (t) { return TM[t.ref].overtravel_past_click_mm; }), 1));
    fill('sidekeys-strain', f(Math.max.apply(null, S.tabs.map(function (t) { return TM[t.ref].strain_at_stop_pct; })), 1));
    if (J.clr != null) fill('sidekeys-gaprange', f(Math.min.apply(null, gaps) - J.clr, 2) + ' to ' + f(Math.max.apply(null, gaps) + J.clr, 2));
    // the swept check: every key through its travel against the tub, lid, midplate, board and switch body.
    // The sweep runs a step past the hard stop, where the key meets the tub and the lid: that contact is the stop.
    var sw = S.sweep || {}, stopT = Math.max.apply(null, S.tabs.map(function (t) { return TM[t.ref].stop_travel_mm; }));
    var inside = 0, past = {}, pastT = 0, steps = 0, bodies = {};
    var nm = { pcb: 'board', switch_body: "switch's body" };
    Object.keys(sw).forEach(function (r) {
      sw[r].forEach(function (row) {
        steps++;
        Object.keys(row).forEach(function (k) {
          if (k === 'nub_travel_mm' || k === 'plunger_push_mm') return;
          bodies[nm[k] || k] = 1;
          if (row.nub_travel_mm <= stopT + 1e-9) inside = Math.max(inside, row[k] || 0);
          else if (row[k] > 0) { past[nm[k] || k] = 1; pastT = Math.max(pastT, row.nub_travel_mm - stopT); }
        });
      });
    });
    var bl = Object.keys(bodies), pl = Object.keys(past);
    fill('sidekeys-sweep', steps ? ('Each key was swung through its travel (' + steps + ' positions over ' + Object.keys(sw).length + ' keys) against the ' + bl.slice(0, -1).join(', ') + ' and the ' + bl[bl.length - 1] + ': ' +
      (inside <= 1e-9 ? 'nothing touches until the stop' : 'the worst overlap before the stop is ' + f(inside, 3) + ' mm\u00b3') +
      (pl.length ? '; ' + f(pastT, 2) + ' mm past it the key meets the ' + pl.join(' and the ') + ', which is the stop.' : '.')) : '');

    // ---- drawings
    var Wx = D.meta.walls_x;
    var z0 = TG.z[0], zb = TG.bar_top;
    var dir = function (t) { return Math.sign(t.free - t.y_root) || 1; };
    ctx.Drawing('key_side', 'dw-sidekeys-side', {
      label: 'Side section through the ' + SD.ref + ' side key', order: ['tub', 'lid', 'tab'],
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        var d = dir(SD);
        a.label(SD.y_root, (z0 + zb) / 2 + 0.3, "root, in the\nlid's wall", -24 * d, 44, { hot: true });
        a.label(SD.y_root + d * TG.hinge / 2, z0 + 0.5, 'hinge notch', -20 * d, -34, { hot: true });
        a.label(SD.y_root + d * 3.7, (z0 + zb) / 2, 'bar: bends,\n' + f(TG.flex_t, 2) + ' thick', -14 * d, 84, { hot: true });
        a.label(SD.face[1] + d * 2.5, -0.2, "block, in the\ntub's slot", 40 * d, 40, { hot: true });
        a.label(SD.y_root + d * 4.5, 1.6, "tub: whole wall\nover the bar", -40 * d, 4);
        a.label(SD.free + d * TG.end_clr / 2, z0 + 1.7, 'free-end\nslot', 34 * d, 30);
        a.label(SD.face[1] - d * 4.5, z0, "the lid's back face, its bed", 30 * d, -14);
      },
    });
    // plan and elevation of the drawn key; sx mirrors a left-wall key, sy follows the direction root -> free end
    var sx = P.side, sy = -dir(P);
    var padNear = sy > 0 ? P.pad_y[1] : P.pad_y[0];
    var tabPlan = ctx.Drawing('tab_plan', 'dw-sidekeys-plan', {
      label: 'Plan of the ' + P.ref + ' side key',
      moving: { tab: 'tab', nub: 'nub' }, groupOrder: ['tab', 'nub'],
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        a.label(P.root[0] - 0.4 * sx, P.y_block - 0.4 * sy, 'block rises\nfrom the lid', 26 * sx, 20 * sy, { hot: true });
        a.label(P.root[0] + 0.3 * sx, P.free + 0.3 * sy, 'free end', -30 * sx, -22 * sy);
        a.label(P.face[0], P.face[1] + 0.9 * sy, 'plunger\n' + f(P.gap, 2) + ' gap', -36 * sx, 30 * sy, { hot: true });
        a.label(P.nub_to - 0.05 * sx, P.face[1] - 1.2 * sy, 'nub', -30 * sx, -26 * sy);
        a.label(P.root[0] + 1.0 * sx, padNear - 0.8 * sy, 'pad', 20 * sx, 14 * sy);
        a.label(P.stop - 0.45 * sx, padNear + 3.5 * sy, 'sliver', -34 * sx, -8 * sy);
      },
    });
    var Xw = EL.side > 0 ? Wx[1] : Wx[0], ex_ = EL.side;
    var tabElev = ctx.Drawing('tab_elev', 'dw-sidekeys-elev', {
      label: 'Section across the ' + EL.ref + ' side key',
      moving: { tab: 'tab', nub: 'nub' }, groupOrder: ['tab', 'nub'],
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        a.label(Xw + ex_ * (TG.proud - 0.1), D.meta.z.seam + 2.4, 'pad ' + f(TG.proud, 1) + '\nproud', 14 * ex_, 26, { hot: true });
        a.label(Xw - 0.3 * ex_, TG.z[1] + TG.slot_clr / 2, f(TG.slot_clr, 1) + ' over the key', 14 * ex_, 30);
        a.label(Xw - 0.5 * ex_, TG.z[0] + 0.3, 'key: part of\nthe lid', 28 * ex_, 10, { hot: true });
        a.label(EL.stop - 0.45 * ex_, 0.2, 'sliver', -30 * ex_, 30);
        a.label(EL.nub_to + 0.9 * ex_, EL.face[2] - 1.6, 'nub, 45\u00b0\nunderside', -30 * ex_, -36);
        a.label(EL.face[0] - 1.2 * ex_, EL.face[2], EL.ref, -30 * ex_, -34);
      },
    });

    // ---- table and numbers
    ctx.q('#sidekeys-table').innerHTML = '<thead><tr><th>Key</th><th>Pad</th><th>Root \u2192 plunger</th><th>Flexure</th><th>Gap</th><th>Travel to click</th><th>Press at centre</th><th>At root end</th><th>At free end</th><th>Rev I key</th><th>Hard stop</th><th>Strain there</th></tr></thead><tbody>' +
      S.tabs.map(function (t) {
        var m = TM[t.ref], ff = m.finger_force_N;
        return '<tr><td>' + SC.esc(t.ref) + ' ' + SC.esc(role(t)) + '</td><td>' + f(padLen(t), 0) + ' mm</td><td>' + f(m.length_root_to_plunger_mm, 1) + ' mm</td><td>' +
          f(Math.abs(t.y_block - t.y_root), 1) + ' mm</td><td>' + f(m.gap_mm, 2) + ' mm</td><td>' + f(m.pad_travel_to_click_mm, 2) + ' mm</td><td>' + f(ff.pad_centre, 1) + ' N</td><td>' +
          f(ff.pad_end_near_root, 1) + ' N</td><td>' + f(ff.pad_end_far, 1) + ' N</td><td>' + (m.rev_i_N != null ? f(m.rev_i_N, 1) + ' N' : '&ndash;') + '</td><td>' + f(m.stop_travel_mm, 2) + ' mm</td><td>' +
          f(m.strain_at_stop_pct, 2) + ' %</td></tr>';
      }).join('') + '</tbody>';
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    ctx.q('#sidekeys-nums').innerHTML = [
      row('Contact', f(TG.nub[0], 1) + ' &times; ' + f(TG.nub[1], 2) + ' mm', TG.plunger ? 'on a ' + f(TG.plunger[0], 2) + ' &times; ' + f(TG.plunger[1], 1) + ' plunger' : ''),
      row('Pad', f(TG.proud, 1) + ' mm proud', f(S.tab_pad[0], 1) + ' &times; ' + f(S.tab_pad[1], 1) + ' mm flat face'),
      row('Gap to plunger', rng(gaps, 2) + ' mm', 'every key, nominal' + (J.clr != null ? ' &middot; ' + f(Math.min.apply(null, gaps) - J.clr, 2) + '&ndash;' + f(Math.max.apply(null, gaps) + J.clr, 2) + ' as the lid sits' : '')),
      row('Flexure', f(TG.flex_t, 2) + ' &times; ' + f(TG.bar_top - TG.z[0], 1) + ' mm', 'the bar, in the lid'),
      row('Hard stop', f(TG.void, 2) + ' mm', "on the lid's own edge, " + rng(S.tabs.map(function (t) { return TM[t.ref].overtravel_past_click_mm; }), 1) + ' after the click'),
      row('Slots', f(TG.slot_clr, 1) + ' over, ' + f(TG.end_clr, 1) + ' at the end', 'in the tub; in the lid ' + f(TG.end_clr, 1) + ' at the end, ' + f(TG.end_foot, 1) + ' chamfer at the bed'),
      row('Bottom', "the lid's " + f(E.back_r != null ? E.back_r : 2, 1) + ' round', 'on a ' + f(TG.foot, 2) + ' mm 45\u00b0 foot &middot; ' + f(TG.hinge, 0) + ' mm hinge notch at the root'),
      row('Prints', "on the lid's back face", "like the lid's own back edge"),
    ].join('');

    // ---- press: the chosen key on the stage, the drawn key in the drawings (every key has the same gap and travel)
    var input = ctx.q('#sidekeys-press'), out = ctx.q('#sidekeys-out'), stateEl = ctx.q('#sidekeys-state');
    var refs = S.tabs.map(function (t) { return t.ref; });
    var sel = ctx.el._skSel && refs.indexOf(ctx.el._skSel) >= 0 ? ctx.el._skSel : P.ref;
    var selHost = ctx.q('#sidekeys-sel');
    var drawSel = function () {
      selHost.innerHTML = '';
      refs.forEach(function (r) {
        var b = document.createElement('button');
        b.type = 'button'; b.textContent = r; b.title = r + ' ' + role(by[r]);
        b.setAttribute('aria-pressed', String(r === sel));
        b.onclick = function () { sel = ctx.el._skSel = r; drawSel(); set(+input.value, true); };
        selHost.appendChild(b);
      });
    };
    function set(p, toStage) {
      var c = ctrl[sel] || ctrl[P.ref];
      var maxT = c ? c.max_travel : P.gap + 0.45;
      var ex = SC.exag ? 4 : 1;
      var d = p * maxT;                                  // pad travel at the nub, real
      var dv = d * ex;
      var push = Math.max(0, d - P.gap);
      var phi = dv / (c && c.length ? c.length : P.nub_arm) * 180 / Math.PI;
      var sgn = ctrl[P.ref] ? ctrl[P.ref].sign : P.side * dir(P);
      if (tabPlan) {
        if (tabPlan.groups.tab) tabPlan.groups.tab.setAttribute('transform', 'rotate(' + (-sgn * phi) + ' ' + P.root[0] + ' ' + (-P.root[1]) + ')');
        if (tabPlan.groups.nub) tabPlan.groups.nub.setAttribute('transform', 'translate(' + (-P.side * push * ex) + ' 0)');
      }
      if (tabElev) {
        if (tabElev.groups.tab) tabElev.groups.tab.setAttribute('transform', 'translate(' + (-EL.side * dv) + ' 0)');
        if (tabElev.groups.nub) tabElev.groups.nub.setAttribute('transform', 'translate(' + (-EL.side * push * ex) + ' 0)');
      }
      var t = by[sel] || P, gap = t.gap, click = c ? c.click_travel : gap + t.click_mm;
      out.textContent = 'pad ' + f(d, 2) + ' mm';
      var st = d < 0.005 ? 'At rest: ' + f(gap, 2) + ' mm clear of the plunger'
        : d < gap ? 'Closing the ' + f(gap - d, 2) + ' mm gap'
        : d < click - 1e-9 ? 'Pushing the plunger: ' + f(d - gap, 2) + ' mm of ' + f(click - gap, 2) + ' to the click'
        : d < maxT - 1e-9 ? 'Clicked; ' + f(maxT - d, 2) + ' mm to the hard stop'
        : 'On the hard stop: the lid takes the press';
      stateEl.textContent = sel + ': ' + st + (SC.exag ? '  (motion \u00d74)' : '');
      if (toStage && SC.viewer && SC.viewer.press) SC.viewer.press(sel, p, { src: 'sidekeys' });
    }
    drawSel();
    input.oninput = function () { set(+input.value, true); };
    ctx.on('pressed', function (r) {
      if (!r || r.src === 'sidekeys') return;
      if (r.kind === 'flexure' && refs.indexOf(r.id) >= 0) {
        if (r.id !== sel) { sel = ctx.el._skSel = r.id; drawSel(); }
        input.value = r.t; set(r.t, false);
      } else if (r.id === 'all') { input.value = r.t; set(r.t, false); }
    });
    ctx.on('exag', function () { set(+input.value, false); });
    // a preset releases the stage's presses (the Show in 3D buttons): follow it
    ctx.on('focus', function () { input.value = 0; set(0, false); });
    ctx.on('released', function () { input.value = 0; set(0, false); });
    set(+input.value, false);
  },
});
