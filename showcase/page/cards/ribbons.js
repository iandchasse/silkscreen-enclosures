// Display ribbons, per build: the FT01C's three (4.26 standard), or one FPC (4.26 plain panel, 3.68). Drawing
// 'ribbon' (x = 28) and the per-ribbon table. On builds whose connectors list only the main FPC, the report's other
// rows are not shown: the 4.26 light-strip data carries the FT01C report unchanged (see the step log).
SC.card({
  id: 'ribbons', title: 'Display ribbons', order: 70, preset: 'ribbons',
  needs: ['cards.ribbons.ribbons', 'cards.ribbons.ribbons.outlines', 'cards.ribbons.ribbons.connectors', 'cards.screen.panel'],
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
    var RB = D.cards.ribbons.ribbons, PN = D.cards.screen.panel;
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var tol = function (o) { return Object.keys(o || {}).filter(function (k) { return /mm_panel$/.test(k); }).sort(function (a, b) { return parseFloat(a) - parseFloat(b); }); };
    var tk = tol(RB.report), nomK = tk.filter(function (k) { return parseFloat(k) === 0; })[0] || tk[Math.floor(tk.length / 2)];
    var keys = ['touch', 'light', 'main'].filter(function (k) { return RB.connectors[k] && RB.outlines[k]; });
    var plain = PN.touch === false && PN.plain;                        // the 4.26 plain panel
    var s = RB.slot;
    fill('ribbons-slotw', f(s[3] - s[2], 1));
    var dr = SC.drawing('ribbon');
    fill('ribbons-at', dr ? f(dr.at, 0) : '28');
    fill('ribbons-what', keys.length > 1 ? 'main (EPD) ribbon' : 'FPC');
    // the tail's centre (the outline's points below y -20.5, panel-local x) against the connector's centre
    var off = function (k) {
      var o = RB.outlines[k], us = o.filter(function (p) { return p[1] <= -20.5; }).map(function (p) { return p[0]; });
      return (Math.min.apply(null, us) + Math.max.apply(null, us)) / 2 + PN.x0 - RB.connectors[k].x;
    };
    var flat = function (k) { return -Math.min.apply(null, RB.outlines[k].map(function (p) { return p[1]; })); };
    keys.forEach(function (k) { fill('ribbons-off-' + k, f(Math.abs(off(k)) + 1e-9, 2)); });
    if (keys.indexOf('main') >= 0) fill('ribbons-len', f(flat('main'), 1));
    var sl = tk.map(function (k) { var r = RB.report[k].main; return r ? r.slack_mm : null; }).filter(function (x) { return x != null; });
    if (sl.length) fill('ribbons-slack', f(Math.min.apply(null, sl), 1) + '&ndash;' + f(Math.max.apply(null, sl), 1));
    var pins = { J2: 'EPD 24p', J3: 'light 6p', J4: 'touch 6p' };
    var refs = keys.map(function (k) { var r = RB.connectors[k].ref; return r + (keys.length > 1 && pins[r] ? ' ' + pins[r] : ''); });
    if (RB.strip_tail) refs.push(RB.strip_tail.ref + ' light strip');
    refs.push('slot ' + f(s[3] - s[2], 1) + ' mm');
    ctx.q('#ribbons-refs').innerHTML = refs.map(function (r) { return '<span class="ref">' + SC.esc(r) + '</span>'; }).join('');

    var find = function (id) { return dr ? dr.layers.filter(function (l) { return l.id === id; })[0] || null : null; };
    var bb = function (l) {
      var b = [1e9, -1e9, 1e9, -1e9];
      l.polys.forEach(function (p) { p[0].forEach(function (q) { b[0] = Math.min(b[0], q[0]); b[1] = Math.max(b[1], q[0]); b[2] = Math.min(b[2], q[1]); b[3] = Math.max(b[3], q[1]); }); });
      return b;
    };
    var pts = function (l) { var a = []; l.polys.forEach(function (p) { p[0].forEach(function (q) { a.push(q); }); }); return a; };
    ctx.Drawing('ribbon', 'dw-ribbons-sec', {
      label: 'Section through the display ribbon',
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        var rb = find('ribbon'), pcb = find('pcb'), j2 = find('j2');
        if (rb) {
          var P = pts(rb);
          var fold = P.reduce(function (m, q) { return q[0] < m[0] ? q : m; }, P[0]);     // outermost point of the fold
          a.label(fold[0], fold[1], 'folds past\nthe glass edge', -16, 34, { hot: true });
          var low = P.filter(function (q) { return q[0] > s[3] + 1; }).reduce(function (m, q) { return !m || q[1] < m[1] ? q : m; }, null);
          if (low) a.label(low[0], low[1], 'slack bows\ntoward the lid', 26, -26, { hot: true });
        }
        if (pcb) { var pb = bb(pcb); a.label((s[2] + s[3]) / 2, (pb[2] + pb[3]) / 2, 'board slot ' + f(s[3] - s[2], 1), 26, 30); }
        if (j2) { var jb = bb(j2); a.label((jb[0] + jb[1]) / 2, jb[2], RB.connectors.main.ref, 18, -30); }
        var pn = ['epd', 'glass', 'touch', 'film', 'ps'].map(find).filter(Boolean)[0];
        if (pn) { var nb = bb(pn); a.label(Math.min(nb[1] - 1, dr.window[1] - 4), (nb[2] + nb[3]) / 2, 'panel', 18, 28); }
      },
    });

    var nm = { main: plain || keys.length === 1 ? 'Display FPC' : 'EPD (main, 24-pin)', light: 'Frontlight (6-pin)', touch: 'Touch (6-pin)' };
    var sgn = function (v) { var r = Math.round(v * 100) / 100; return (r > 0 ? '+' : r < 0 ? '\u2212' : '') + f(Math.abs(r), 2) + ' mm'; };
    var rng = function (k, fld, n) {
      var v = tk.map(function (t) { return RB.report[t][k] && RB.report[t][k][fld]; }).filter(function (x) { return x != null; });
      if (!v.length) return '&ndash;';
      var lo = f(Math.min.apply(null, v), n), hi = f(Math.max.apply(null, v), n);
      return (lo === hi ? lo : lo + '&ndash;' + hi) + ' mm';
    };
    var t = ctx.q('#ribbons-table');
    if (plain) {
      // the report is the FT01C's (unchanged in this build's data): show only what the outline gives
      t.innerHTML = '<thead><tr><th>FPC</th><th>Flat length</th><th>Tail vs connector</th></tr></thead><tbody>' +
        keys.map(function (k) { return '<tr><td>' + nm[k] + ' \u2192 ' + SC.esc(RB.connectors[k].ref) + '</td><td>' + f(flat(k), 2) + ' mm</td><td>' + sgn(off(k)) + '</td></tr>'; }).join('') + '</tbody>';
    } else {
      t.innerHTML = '<thead><tr><th>Ribbon</th><th>Leaves at</th><th>Flat length</th><th>Slack</th><th>Tail vs connector</th></tr></thead><tbody>' +
        keys.map(function (k) {
          var r = RB.report[nomK][k] || {};
          return '<tr><td>' + nm[k] + ' \u2192 ' + SC.esc(RB.connectors[k].ref) + '</td><td>z ' + f(r.exit_z, 2) + '</td><td>' + f(r.flat_length_mm, 2) + ' mm</td><td>' + rng(k, 'slack_mm', 1) + '</td><td>' + sgn(off(k)) + '</td></tr>';
        }).join('') + '</tbody>';
    }
  },
});
