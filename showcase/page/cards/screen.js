// Screen stack, per build: the 4.26 FT01C (touch + light guide), the 4.26 plain GDEY0426T82 (light strip), and the
// 3.68 bare panel (standard / light strip). Drawings 'bezel' and 'stack'; labels are placed from the drawings' own
// layers, so they follow each size's geometry.
SC.card({
  id: 'screen', title: 'Screen stack', order: 60, preset: 'stack',
  needs: ['cards.screen.panel', 'cards.screen.stack', 'cards.detent.midplate'],
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
    var SC_ = D.cards.screen, PN = SC_.panel, ST = SC_.stack, PS = SC_.plain_stack || null;
    var MP = D.cards.detent.midplate, MD = MP.data || {};
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    // tolerance-keyed blocks ('-0.2mm_panel', ...) in numeric order
    var tol = function (o) { return Object.keys(o || {}).filter(function (k) { return /mm_panel$/.test(k); }).sort(function (a, b) { return parseFloat(a) - parseFloat(b); }); };
    var rng = function (v, n) { var a = Math.min.apply(null, v), b = Math.max.apply(null, v); return f(a, n) === f(b, n) ? f(a, n) : f(a, n) + '\u2013' + f(b, n); };
    var nom = function (o) { var k = tol(o); return o[k.filter(function (x) { return parseFloat(x) === 0; })[0] || k[Math.floor(k.length / 2)]]; };

    // ---- layers of the drawings: role and a readable name per layer id
    var NAME = { epd: 'EPD', light: 'light guide', touch: 'touch film', glass: 'glass', fpl: 'FPL', ps: 'PS film', film: 'PS film', strip: 'light strip',
      midplate: 'midplate', pcb: 'board', tub: 'tub' };
    var thick = {};
    if (PN.layers) PN.layers.forEach(function (l) { thick[l[0]] = l[1]; });
    var dz = function (id) { var z = PN.z && PN.z[id]; return z ? z[1] - z[0] : thick[id]; };
    var bez = SC.drawing('bezel'), stk = SC.drawing('stack');
    fill('screen-bat', bez ? f(bez.at, 0) : '60');
    var PANEL = ['touch', 'light', 'epd', 'ps', 'film', 'fpl', 'glass'];
    var disp = bez ? bez.layers.filter(function (l) { return PANEL.indexOf(l.id) >= 0; }) : [];
    var bb = function (l) {
      var b = [1e9, -1e9, 1e9, -1e9];
      l.polys.forEach(function (p) { p[0].forEach(function (q) { b[0] = Math.min(b[0], q[0]); b[1] = Math.max(b[1], q[0]); b[2] = Math.min(b[2], q[1]); b[3] = Math.max(b[3], q[1]); }); });
      return b;
    };
    var sorted = disp.map(function (l) { return { l: l, b: bb(l) }; }).sort(function (a, b) { return b.b[3] - a.b[3]; });
    var layerText = function (l) {
      var id = l.id, t = id === 'epd' ? (PN.z && PN.z.epd ? PN.z.epd[1] - PN.z.epd[0] : (dz('glass') || 0) + (dz('epl') || 0)) : id === 'film' ? dz('ps') : id === 'light' ? dz('lgp') : dz(id);
      var nm = id === 'epd' && !PN.touch ? 'glass + EPL' : NAME[id] || id;
      return nm + (t ? ' ' + f(t, 2) : '');
    };
    fill('screen-layers', sorted.map(function (s) { return layerText(s.l); }).join(', ') || '?');
    fill('screen-sat', stk ? (stk.notes && stk.notes.what ? stk.notes.what.charAt(0).toUpperCase() + stk.notes.what.slice(1) : 'Along one spring') + ' (' + stk.axis + ' = ' + f(stk.at, 1) + ' mm)' : 'Along one spring');
    fill('screen-springt', f(MP.T, 1));
    // numbers in the text
    var tk = tol(ST.tolerance), defl = tk.map(function (k) { return ST.tolerance[k].spring_deflection_mm; });
    var limit = MD.travel_limit_mm != null ? MD.travel_limit_mm : PS ? PS.travel_limit_mm : null;
    fill('screen-defl-hi', f(Math.max.apply(null, defl), 2));
    fill('screen-defl', rng(defl, 1));
    fill('screen-limit', limit != null ? f(limit, 1) : '?');
    var bear = ST.lip_bearing_on_touch_film_mm || ST.lip_bearing_on_ps_film_mm || {};
    var bv = Object.keys(bear).map(function (k) { return bear[k]; });
    fill('screen-bear', bv.length ? rng(bv, 2) : '?');
    ['ps', 'epl', 'glass'].forEach(function (k) { if (dz(k) != null) fill('screen-' + k, f(dz(k), 2)); });
    // the light-strip build's left border: no lip there, only hold-down pads (the data gives it as a note)
    var lb = ST.left_border || '';
    var pads = (lb.match(/Y\s*\[([^\]]*)\]/) || [])[1];
    fill('screen-left', lb ? ' On the left border there is no lip: the strip lies there' + (pads ? ', held by pads at y ' + pads.split(/,\s*/).map(function (x) { return f(+x, 1); }).join(', ') : '') + '.' : '');
    if (PS) {
      var pk = tol(PS.rows), pr = pk.map(function (k) { return PS.rows[k]; });
      fill('screen-pl-nom', f(nom(PS.rows).spring_deflection_mm, 2));
      fill('screen-pl-rng', rng(pr.map(function (r) { return r.spring_deflection_mm; }), 2));
    }

    // ---- drawings
    var zlip = D.meta.z.lip, zmr = D.meta.z.mid_rear;
    var find = function (dr, id) { return dr ? dr.layers.filter(function (l) { return l.id === id; })[0] || null : null; };
    var lowest = function (l) { var best = null; l.polys.forEach(function (p) { p[0].forEach(function (q) { if (!best || q[1] < best[1]) best = q; }); }); return best; };
    ctx.Drawing('bezel', 'dw-screen-bezel', {
      label: 'Section through the left bezel edge',
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        var x0 = PN.x0 != null ? PN.x0 : 0;
        if (PS) a.label(x0 + 1.4, PS.stop_face_z + 0.02, 'stop face on the panel', 34, 30, { hot: true });
        else if (!find(bez, 'strip')) a.label(x0 + Math.min(0.9, (bear.left || 1.5) * 0.6), zlip + 0.02, 'lip on the ' + (PN.touch ? 'touch' : 'PS') + ' film', 34, 30, { hot: true });
        var st = find(bez, 'strip');
        if (st) { var sb = bb(st); a.label((sb[0] + sb[1]) / 2, sb[3] - 0.05, 'light strip', 30, 30, { hot: true }); }
        var E = D.cards.edges && D.cards.edges.edges;
        if (E && E.front_r != null) a.label(D.meta.walls_x[0] + 0.55, D.meta.z.front - 0.35, 'front edge R' + f(E.front_r, 1), 30, 36);
        sorted.forEach(function (s, i) {
          var u = Math.min(s.b[1] - 0.3, (bez.window[1] - 1.6) - 0.6 * (sorted.length - 1 - i));
          a.label(u, (s.b[2] + s.b[3]) / 2, layerText(s.l), 26, 12 - 14 * i);
        });
        var mp = find(bez, 'midplate');
        if (mp) { var mb = bb(mp); a.label(Math.min(mb[1] - 0.4, bez.window[1] - 1.2), (mb[2] + mb[3]) / 2, 'midplate', 24, -30); }
      },
    });
    ctx.Drawing('stack', 'dw-screen-stack', {
      label: 'Section along a midplate spring',
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        var mp = find(stk, 'midplate'), pcb = find(stk, 'pcb');
        if (mp) {
          var lo = lowest(mp), mb = bb(mp);
          a.label(lo[0], lo[1] + 0.05, 'nub on the board', 30, -22, { hot: true });
          a.label(mb[0] + 0.25 * (mb[1] - mb[0]), zmr + ((D.cards.detent.detents && D.cards.detent.detents.strip_mm) ? D.cards.detent.detents.strip_mm[1] / 2 : 0.4), 'midplate', 12, 44);
        }
        var top = sorted.length ? find(stk, sorted[sorted.length - 1].l.id) : null;
        if (top) { var tb = bb(top); a.label(tb[0] + 0.8 * (tb[1] - tb[0]), (tb[2] + tb[3]) / 2, 'panel', 18, 30); }
        if (pcb) { var pb = bb(pcb); a.label(pb[0] + 0.85 * (pb[1] - pb[0]), (pb[2] + pb[3]) / 2, 'board', 18, -24); }
      },
    });

    // ---- numbers
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    var mk = tol(MD), md = nom(MD);
    var rows = [];
    if (PS) {
      var pk2 = tol(PS.rows), pn = nom(PS.rows), prs = pk2.map(function (k) { return PS.rows[k]; });
      rows.push(row('Panel', f(PN.plain.t, 3) + ' mm', '&plusmn;' + f(PN.plain.t_tol, 1) + ' &middot; glass, FPL, PS film; no touch, no light guide'));
      rows.push(row('Panel face', 'z ' + f(PS.stop_face_z, 2), 'on the tub\u2019s stop face at every tolerance'));
      rows.push(row('Spring travel used', rng(prs.map(function (r) { return r.spring_deflection_mm; }), 2) + ' mm', 'of ' + f(PS.travel_limit_mm, 1) + ' in the plate; ' + f(pn.spring_deflection_mm, 2) + ' nominal'));
      rows.push(row('Preload each', f(pn.force_N_each, 2) + ' N', rng(prs.map(function (r) { return r.force_N_each; }), 2) + ' N, ' + PS.springs + ' springs, ' + f(pn.force_N_total, 1) + ' N in all'));
      rows.push(row('Strip hold-down', f(PS.holddown_gap_mm, 3) + ' mm', 'over the strip\u2019s bar at z ' + f(PS.bar_flex_top_z, 3)));
    } else {
      var gaps = tk.map(function (k) { return ST.tolerance[k].gap_glass_to_lip_mm; });
      rows.push(row((PN.touch ? 'Glass' : 'Panel') + ' to lip', f(Math.max.apply(null, gaps), 2) + ' mm', 'at ' + tk.map(function (k) { return f(parseFloat(k), 1); }).join(', ') + ' mm panel: the springs keep it seated'));
      rows.push(row('Spring travel used', rng(defl, 2) + ' mm', limit != null ? 'of ' + f(limit, 1) + ' available in the plate' : ''));
      rows.push(row('Lip on ' + (PN.touch ? 'touch' : 'PS') + ' film', rng(bv, 2) + ' mm', lb ? 'overlap on three sides; the strip has the left border' : 'overlap all round the window'));
      if (md) rows.push(row('Preload each', f(md.force_N, 2) + ' N', rng(mk.map(function (k) { return MD[k].force_N; }), 2) + ' N, ' + (MD.count || (MP.springs || []).length) + ' springs'));
      if (SC_.strip_stack) rows.push(row('LEDs under the case', f(SC_.strip_stack.led_clr, 3) + ' mm', 'LED tops z ' + f(SC_.strip_stack.led_top, 3) + ', ceiling ' + f(SC_.strip_stack.ceiling, 2)));
    }
    ctx.q('#screen-nums').innerHTML = rows.join('');
  },
});
