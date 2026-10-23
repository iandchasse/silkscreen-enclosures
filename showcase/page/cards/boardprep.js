// Board prep (3.68 only): the trim line, the power rework and SW5 left off. The plan is drawn from the trimmed board's
// outline (cards.battery.depth_map.outline), with the midplate pins, the post in SW5's site, J5 and the side switches.
SC.card({
  id: 'boardprep', title: 'Board prep', order: 85, preset: 'boardprep', sizes: ['368'],
  needs: ['cards.boardprep.trim_y', 'cards.boardprep.fit', 'cards.boardprep.remove', 'cards.boardprep.leave_off', 'cards.battery.depth_map.outline', 'cards.closing.holes'],
  render: function (D, ctx) {
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var BP = D.cards.boardprep, O = D.cards.battery.depth_map.outline, H = D.cards.closing.holes;
    var xs = O.map(function (p) { return p[0]; }), ys = O.map(function (p) { return p[1]; });
    var bx0 = Math.min.apply(null, xs), bx1 = Math.max.apply(null, xs), by0 = Math.min.apply(null, ys), ty = BP.trim_y;
    var band = 13, pad = 3, left = 16, right = 16;
    var host = ctx.q('#boardprep-plan');
    host.innerHTML = '';
    var big = (host.clientWidth || 440) < 420 ? 1.3 : 1;   // phone width: larger text in the same plan
    left = right = 16 * big;
    band = 15 * big;
    var vx0 = bx0 - left, vw = bx1 - bx0 + left + right, vy0 = -(ty + band + pad), vh = ty + band + 2 * pad - by0 + 4;
    var svg = SC.svg('svg', { viewBox: vx0 + ' ' + vy0 + ' ' + vw + ' ' + vh, class: 'bprep', role: 'img', 'aria-label': 'The board from the front: where it is cut, and what goes with the cut' }, host);
    var defs = SC.svg('defs', null, svg);
    var pat = SC.svg('pattern', { id: 'boardprep-hatch', patternUnits: 'userSpaceOnUse', width: 2, height: 2, patternTransform: 'rotate(45)' }, defs);
    SC.svg('line', { x1: 0, y1: 0, x2: 0, y2: 2, class: 'hl' }, pat);
    var P = function (x, y) { return x + ' ' + (-y); };
    // the cut-off extension: an open band above the line (its real top is not part of this case's data)
    SC.svg('path', { d: 'M' + P(bx0, ty) + 'L' + P(bx0, ty + band) + 'L' + P(bx1, ty + band) + 'L' + P(bx1, ty) + 'Z', class: 'gone' }, svg);
    SC.svg('path', { d: 'M' + O.map(function (p) { return P(p[0], p[1]); }).join('L') + 'Z', class: 'brd' }, svg);
    SC.svg('line', { x1: bx0 - 4, y1: -ty, x2: bx1 + 4, y2: -ty, class: 'cut' }, svg);
    var ext = [Infinity, -Infinity];   // the labels' x extent (monospace: 0.6 em a character), so the viewBox can hold them
    var tx = function (x, y, s, anchor, cls, fs) {
      var size = (fs || 2.7) * big, w = String(s).length * size * 0.6;
      var a = anchor || 'start', x0 = a === 'end' ? x - w : a === 'middle' ? x - w / 2 : x;
      ext[0] = Math.min(ext[0], x0); ext[1] = Math.max(ext[1], x0 + w);
      var e = SC.svg('text', { x: x, y: -y, 'font-size': size, 'text-anchor': a, 'dominant-baseline': 'middle', class: cls || null }, svg);
      e.textContent = s;
    };
    tx((bx0 + bx1) / 2, ty + band - 2.4 * big, 'upper extension, cut off', 'middle');
    var gone = BP.gone_with_cut || [];
    var prot = gone.filter(function (r) { return /^(CR\d+|D\d+|F\d+|U8)$/.test(r); }), goneRest = gone.filter(function (r) { return prot.indexOf(r) < 0; });
    if (gone.length) {
      tx((bx0 + bx1) / 2, ty + band - 5.9 * big, 'with ' + goneRest.map(SC.tag).join(', ') + (prot.length ? ',' : ''), 'middle', null, 2.2);
      if (prot.length) tx((bx0 + bx1) / 2, ty + band - 8.9 * big, 'and the protection parts', 'middle', null, 2.2);
    }
    tx((bx0 + bx1) / 2, ty + 1.8, 'cut: y ' + f(ty, 2) + ' here, KiCad y ' + f(BP.trim_kicad_y, 2), 'middle', 'hot');
    // posts and parts
    var post = function (xy, d, s, anchor, dx, dy) {
      SC.svg('circle', { cx: xy[0], cy: -xy[1], r: d / 2, class: 'post' }, svg);
      tx(xy[0] + (dx || 2.2), xy[1] + (dy || 0), s, anchor || 'start', null, 2.4);
    };
    (BP.snap_posts || []).forEach(function (h) { if (H[h]) post(H[h], 2.2, 'midplate pin ' + h); });
    if (H.H5) post(H.H5, 1.9, 'locating pin H5', 'end', -2.2, -3.4);
    if (BP.support_post) {
      var sp = BP.support_post;
      SC.svg('circle', { cx: sp[0], cy: -sp[1], r: (sp[2] || 3) / 2 + 1.1, class: 'off' }, svg);
      SC.svg('circle', { cx: sp[0], cy: -sp[1], r: (sp[2] || 3) / 2, class: 'post' }, svg);
      tx(sp[0] + 3.4, sp[1] + 2.4, (BP.leave_off || []).map(SC.tag).join(', ') + ' left off:', 'start', 'hot', 2.4);
      tx(sp[0] + 3.4, sp[1] + 2.4 - 3.0 * big, 'a post carries', 'start', 'hot', 2.4);
      tx(sp[0] + 3.4, sp[1] + 2.4 - 6.0 * big, 'this corner', 'start', 'hot', 2.4);
    }
    var j5 = D.cards.battery.battery.j5;
    if (j5) { SC.svg('rect', { x: j5[0], y: -j5[3], width: j5[1] - j5[0], height: j5[3] - j5[2], class: 'part' }, svg); tx(j5[0] - 1, (j5[2] + j5[3]) / 2, SC.tag('J5'), 'end'); }
    var roles = D.meta.roles || {};
    (D.cards.sidekeys.tabs || []).forEach(function (t) {
      var y = (t.pad_y[0] + t.pad_y[1]) / 2, x = t.side > 0 ? bx1 : bx0;
      SC.svg('rect', { x: x - 1.8, y: -(y + 2), width: 3.6, height: 4, class: 'part' }, svg);
      var lab = t.ref === BP.power_key ? 'power ' + t.ref : SC.tag(t.ref);
      tx(x + (t.side > 0 ? 2.8 : -2.8), y, lab, t.side > 0 ? 'start' : 'end', t.ref === BP.power_key ? 'hot' : null, 2.4);
    });

    if (ext[0] < vx0 + 1 || ext[1] > vx0 + vw - 1) {
      var nx0 = Math.min(vx0, ext[0] - 1), nx1 = Math.max(vx0 + vw, ext[1] + 1);
      svg.setAttribute('viewBox', nx0 + ' ' + vy0 + ' ' + (nx1 - nx0) + ' ' + vh);
    }
    var fv = BP.fit_values || {};
    var list = function (a) { return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; };   // R36, R73 and R62
    var steps = [
      '<b>Cut the board</b> across the upper extension at KiCad y ' + f(BP.trim_kicad_y, 2) + ' (y ' + f(ty, 2) + ' in the case frame) and dress the edge. ' +
        (gone.length ? 'Everything above goes with it: ' + goneRest.map(SC.part).join(', ') + (prot.length ? (goneRest.length ? ' and' : '') + ' the parts that protect the header and the frontlight lines (' + prot.map(SC.tag).join(', ') + ').' : '.') : ''),
      '<b>Power rework.</b> Remove ' + list(BP.remove) + ', then fit ' + list(BP.fit.map(function (r) { return r + (fv[r] ? ' (' + fv[r] + ')' : ''); })) +
        '. The power key moves to <b>' + SC.part(BP.power_key || '') + '</b>' + (roles[BP.power_key] ? ', ' + SC.esc(roles[BP.power_key]) : '') + '.',
      '<b>Leave ' + BP.leave_off.map(SC.part).join(', ') + ' off.</b> The lid post at mounting hole H2 would stand in the battery bay, so a post in the empty site carries the board&rsquo;s top-left corner instead; the midplate&rsquo;s pins in mounting holes ' + (BP.snap_posts || []).join(' and ') + ' still locate the board.',
      '<b>Trim</b> the battery connector&rsquo;s (J5&rsquo;s) through-hole leads and the switches&rsquo; pins to ' + f(BP.lead_trim_mm, 2) + ' mm proud of the front, so the midplate&rsquo;s springs keep their room.',
    ];
    ctx.q('#boardprep-steps').innerHTML = steps.map(function (s) { return '<li>' + s + '</li>'; }).join('');
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    ctx.q('#boardprep-nums').innerHTML = [
      row('Cut', 'y ' + f(ty, 2), 'KiCad y ' + f(BP.trim_kicad_y, 2) + ' &middot; board ' + f(bx1 - bx0, 1) + ' &times; ' + f(ty - by0, 2) + ' mm after'),
      row('Fit', BP.fit.join(', '), BP.fit.map(function (r) { return fv[r] || ''; }).join(', ')),
      row('Remove', BP.remove.join(', '), 'before powering up'),
      row('Leave off', BP.leave_off.map(SC.tag).join(', '), 'a post stands in its site'),
      row('Pins', f(BP.lead_trim_mm, 2) + ' mm', 'proud of the front, the battery connector and the switches'),
    ].join('');
  },
});
