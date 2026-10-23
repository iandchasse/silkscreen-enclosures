// Closing up: drawings clamp, pin and top (cards.closing), the board pins (snap posts until 2026-10-23), and the rod's printed side gate
// (keys.rod, cards.closing.gate; its 3D view frames the gate part on the stage). The screws come from
// cards.closing.screw_list: three on the 4.26 (H3, H4, top), four on the 3.68 (its bottom pair in the chin's corners,
// whose 'clamp' drawing cuts the bottom-left one along x; notes.u is the screw's place across the cut).
SC.card({
  id: 'closing', title: 'Closing up', order: 100, preset: 'close',
  // cards.closing.gate and keys.rod: not on the chinless builds (no rod); its rod paragraph is data-not="cl"
  needs: ['cards.closing.holes', 'cards.closing.top_screw', 'cards.closing.screws', 'cards.closing.board_snap'],
  render: function (D, ctx) {
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
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
    var inRing = function (r, u, v) {
      var c = false;
      for (var i = 0, j = r.length - 1; i < r.length; j = i++) {
        var a = r[i], b = r[j];
        if ((a[1] > v) !== (b[1] > v) && u < (b[0] - a[0]) * (v - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
      }
      return c;
    };
    var layerOf = function (dr, id) { return (dr.layers || []).concat(dr.beyond || []).filter(function (l) { return l.id === id; })[0] || null; };
    var inside = function (L, u, v) { var n = 0; L.polys.forEach(function (p) { p.forEach(function (r) { if (inRing(r, u, v)) n++; }); }); return n % 2 === 1; };
    var P = function (dr, id, u, v) {
      var L = layerOf(dr, id);
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
    var CL = D.cards.closing, Hs = CL.holes, BS = CL.board_snap, z = D.meta.z, R = D.keys && D.keys.rod, G = CL.gate;
    var words = ['no', 'one', 'two', 'three', 'four', 'five'];
    var posts = BS.posts || [];
    var list = function (a) { return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; };
    fill('cl-nposts', words[posts.length] || String(posts.length));
    fill('cl-posts', list(posts));
    var scrRefs = (CL.screw_list || [{ id: 'top', label: 'top screw' }]).filter(function (s) { return !Hs[s.id]; });
    ctx.q('#closing-refs').innerHTML = Object.keys(Hs).sort().map(function (h) { return '<span class="ref">' + SC.tag(h) + '</span>'; }).join('')
      + scrRefs.map(function (s) { return '<span class="ref">' + SC.esc(s.label) + '</span>'; }).join('') + (G ? '<span class="ref">rod gate</span>' : '');
    var SL = CL.screw_list || [], nS = SL.length || 3, HD = CL.head || {}, CB = CL.cb_depth;
    var nw = words[nS] || String(nS);
    fill('cl-nscrews', nw);
    fill('cl-nscrews-cap', nw.charAt(0).toUpperCase() + nw.slice(1));
    var iso = (/ISO \d+/.exec(String(CL.screws)) || [''])[0];
    var scr = String(CL.screws).replace(/ x /g, ' \u00d7 ').replace(/ ISO \d+/, '');      // 'M2 x 8 socket head'
    var kinds = scr.replace(/^.* (socket head|pan head)$/, '$1').replace(/^socket head$/, 'socket head caps').replace(/^pan head$/, 'pan heads');
    var also = HD.also ? /^(ISO \d+) (.*)$/.exec(HD.also) : null;
    fill('cl-screws', SC.esc(scr.replace(/ (socket|pan) head$/, '')) + ' ' + kinds + ' (' + iso + (also ? '; a ' + also[2] + ', ' + also[1] + ', also fits' : '') + ')');
    fill('cl-pilot', CL.pilot ? ' (' + f(CL.pilot, 1) + ' mm)' : '');
    var bb = HD.below_back ? Object.keys(HD.below_back).map(function (k) { return HD.below_back[k]; }) : [];
    var bLo = bb.length ? Math.min.apply(null, bb) : null, bHi = bb.length ? Math.max.apply(null, bb) : null;
    var flush = bb.length ? (bHi < 0.005 ? ': a socket head&rsquo;s top is flush with the back'
      : ': a socket head&rsquo;s top sits ' + (bHi - bLo < 0.005 ? f(bLo, 1) : f(bLo, 1) + '&ndash;' + f(bHi, 1)) + ' mm below the back') : '';
    fill('cl-cb', CB ? (Math.abs(CB.bottom - CB.top) < 1e-6 ? ', all ' + nw + ' ' + f(CB.bottom, 1) + ' mm deep'
      : ', the bottom pair ' + f(CB.bottom, 1) + ' mm deep and the top ' + (nS - 2 > 1 ? 'pair ' : 'one ') + f(CB.top, 1)) + flush : '');
    fill('cl-pinned', list(CL.pinned || ['H3', 'H4']));
    var dC = SC.drawing('clamp'), dP = SC.drawing('pin'), dT = SC.drawing('top');
    var cref = (dC.notes && (dC.notes.hole || dC.notes.ref)) || 'H3', pref = (dP.notes && (dP.notes.hole || dP.notes.ref)) || 'H2';
    var corner = !Hs[cref];                              // the 3.68: the clamp drawing cuts a corner screw, not a hole
    fill('cl-clamp-ref', SC.esc(cref));
    fill('cl-other-clamp', cref === 'H3' ? 'H4' : 'H3');
    fill('cl-clamp-pair', 'H3 and H4');
    fill('cl-pin-ref', SC.esc(pref));
    var others = posts.filter(function (p) { return p !== pref; });
    fill('cl-pin-others', others.length ? list(others) + (others.length > 1 ? ' are' : ' is') + ' the same.' : '');
    fill('cl-top-x', f(dT.at, 2));
    var seat = CL.screw_seat_z != null ? CL.screw_seat_z : (CL.seat_z && CL.seat_z.H3);
    var topSeat = CL.seat_z && CL.seat_z.top != null ? CL.seat_z.top : seat;
    var sname = scr.replace(/ (socket|pan) head$/, '').replace(/^M2 \u00d7 /, 'M2\u00d7');
    var hx = dC.notes && dC.notes.u != null ? dC.notes.u : (Hs[cref] || Hs.H3)[0], px_ = (Hs[pref] || [dP.at, dP.at])[0];
    var ra = dC.notes && dC.notes.rod_axis;
    var clampOrder = ['tub', 'lid', 'pcb', 'screw'].concat(dC.layers.map(function (l) { return l.id; }).filter(function (i) { return ['tub', 'lid', 'pcb', 'screw'].indexOf(i) < 0; }));
    ctx.Drawing(dC, 'dw-closing-clamp', {
      label: corner ? 'Section through the ' + cref + ' corner screw' : 'Section through the ' + cref + ' clamp screw', order: clampOrder,
      annotate: function (a0, d) {
        var a = fitA(a0, d);
        lab(a, dC, 'screw', hx, seat - 0.8, sname, 26, -8);
        if (corner) {
          lab(a, dC, 'tub', hx - 1.9, 0.5, 'tub corner block', -20, 24, { hot: true });
          lab(a, dC, 'lid', hx + 2.2, seat - 1.0, 'lid post', 22, -12);
          if (ra) lab(a, dC, 'rod', ra[0], ra[1], 'rod', 20, 22);
          return;
        }
        lab(a, dC, 'pcb', hx - 1.9, 0.8, 'board clamped', -12, 60, { hot: true });
        lab(a, dC, 'tub', hx + 1.9, Math.min(3.4, z.front - 1), 'tub boss', 26, 20);
        lab(a, dC, 'lid', hx + 2.4, -2.5, 'lid boss', 22, -10);
      },
    });
    ctx.Drawing(dP, 'dw-closing-pin', {
      label: 'Section through the ' + pref + (BS.style === 'pole' ? ' pin' : ' snap post'),
      annotate: function (a0, d) {
        var a = fitA(a0, d);
        lab(a, dP, 'midplate', px_ + 0.95 * (dP.axis === 'y' ? 1 : 1), 0.8, '\u00d8' + f(BS.post_d, 1) + (BS.style === 'pole' ? ' pin in\n\u00d8' : ' post in\n\u00d8') + f(BS.hole_d, 1) + ' hole', 30, 30, { hot: true });
        if (BS.style === 'pole') lab(a, dP, 'midplate', px_ + 0.5, BS.geom.tip + 0.15, 'rounded tip', 34, -30, { hot: true });
        else lab(a, dP, 'midplate', px_ + 1.25, -0.35, 'barb catches\nthe board', 34, -30, { hot: true });
        lab(a, dP, 'lid', px_ + 2.4, -3.2, 'lid post,\nbored', 26, -12);
        lab(a, dP, 'midplate', px_ - 2.0, (z.mid_rear + z.pcb_front) / 2 + 0.4, 'midplate', -34, 22);
      },
    });
    var ty = CL.top_screw[1];
    ctx.Drawing(dT, 'dw-closing-top', {
      label: 'Section through the top screw',
      annotate: function (a0, d) {
        var a = fitA(a0, d);
        lab(a, dT, 'tub', ty + 1, 1.5, 'tub boss', 26, 20);
        lab(a, dT, 'screw', ty, topSeat - 0.8, sname, -26, -10);
        lab(a, dT, 'lid', ty + 2.5, topSeat - 0.5, 'lid', 24, -16);
      },
    });
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    var nums = [
      row('Screws', nS + ' &times; ' + SC.esc(sname), iso + ' ' + kinds + (also ? ' (or ' + also[2] + 's)' : '')
        + (CB ? ' &middot; counterbores ' + (Math.abs(CB.bottom - CB.top) < 1e-6 ? f(CB.bottom, 1) : f(CB.bottom, 1) + ' / ' + f(CB.top, 1)) + ' mm deep' : '')),
      BS.style === 'pole' ? row('Board pins', list(posts), '\u00d8' + f(BS.post_d, 2) + ' in \u00d8' + f(BS.hole_d, 1) + ' holes &middot; locate only, no snap') : row('Snap posts', list(posts), f(BS.push_on_N_each, 1) + ' N on, ' + f(BS.pull_off_N_each, 1) + ' N off, each'),
      BS.style === 'pole' ? row('Board clearance', f(BS.xy_clearance_mm, 3) + ' mm', 'a side, in X and Y &middot; nothing holds it in Z until the lid is on') : row('Finger strain', f(BS.root_strain_pct, 2) + ' %', 'in PLA &middot; catch ' + f(BS.catch_mm, 2) + ' mm'),
      BS.style === 'pole' ? null : row('Board play', f(BS.board_z_play_mm, 2) + ' mm', 'captured, not clamped, until the lid is on'),
      G && row('Rod gate', 'printed', 'web ' + f(G.web, 2) + ' + flange ' + f(G.flange, 2) + ' mm &middot; stops the rod at x ' + f(G.stop_x, 2) + ' &middot; &Oslash;' + f(G.pull_d, 1) + ' mm pull hole'),
      R && row('Rod', f(R.cut, 2) + ' mm', 'of ' + f(R.d, 2) + ' mm filament &middot; ' + (D.cards.keys.end_play ? f(D.cards.keys.end_play[0], 1) + '&ndash;' + f(D.cards.keys.end_play[1], 1) + ' mm end play' : '')),
    ];
    ctx.q('#closing-nums').innerHTML = nums.filter(Boolean).join('');
    // the rod gate on the stage: the close preset's look, no cut, the camera on the gate from the left
    ctx.q('#closing-rod').onclick = function () {
      var V = SC.viewer;
      if (!V || !V.part) return;
      var p = G && V.part('gate');
      if (!p || !p.obj) return;
      V.preset('close', { animate: false });
      V.section('off');
      V.highlight(['gate', 'rod']);
      var box = new V.THREE.Box3().setFromObject(p.obj), c = box.getCenter(new V.THREE.Vector3());
      V.tween([c.x - 42, c.y - 34, c.z + 26], [c.x + 6, c.y + 2, c.z], [0, 0, 1]);
      V.caption('<b>The rod&rsquo;s gate.</b> A printed T in a slot in the chin&rsquo;s left wall: its flat stops the rod&rsquo;s square tail, and the lid&rsquo;s rim closes ' + f(G.top_clr, 2) + ' mm over it.', 'Rod gate');
    };
  },
});
