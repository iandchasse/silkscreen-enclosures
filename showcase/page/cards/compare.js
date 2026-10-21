// Next to the X4: cards.compare.{rows, views, budget, attribution} (compare.py's output, both sizes). The X4 reference
// model is Zorian22's (CC BY-NC-SA); the sources note below says so for both sizes.
SC.card({
  id: 'compare', title: 'Next to the X4', order: 115, preset: 'compare',
  needs: ['cards.compare.rows', 'cards.compare.views', 'cards.compare.budget', 'cards.compare.attribution'],
  render: function (D, ctx) {
    var f = function (x, n) { return SC.fmt(x, n == null ? 1 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var CM = D.cards.compare, rows = CM.rows, us = rows[0], x4 = rows[1], rc = rows[2];
    var pct = function (a, b) { return Math.round((a / b - 1) * 100); };
    var more = function (d, up, down) { return d >= 0 ? up : down; };
    fill('cmp-t', f(us.t, 1));
    var diag = function (r) { return Math.hypot(r.active_mm[0], r.active_mm[1]); };
    var same = Math.abs(diag(us) - diag(x4)) < 2;
    var fp = pct(us.footprint_cm2, x4.footprint_cm2);
    var screen = same ? 'Same screen size' : 'A ' + SC.esc(SC.text(D.meta.size_label)) + ' screen against the X4&rsquo;s ' + f(diag(x4) / 25.4, 2) + '&Prime;';
    ctx.q('#compare-thesis').innerHTML = screen + ', a footprint ' + Math.abs(fp) + '% ' + more(fp, 'over', 'under') + ' the bare X4&rsquo;s, and ' + f(us.t / x4.t, 1) + ' times its thickness. In the hand it is ' +
      f(Math.abs(rc.w - us.w), 1) + ' mm ' + more(rc.w - us.w, 'narrower', 'wider') + ' than the X4 in its retro case, and ' + f(Math.abs(us.t - rc.t), 1) + ' mm ' + more(us.t - rc.t, 'thicker', 'thinner') + '.';
    var cls = ['ours', 'x4', 'retro'];
    var t = ctx.q('#compare-table');
    t.innerHTML = '<thead><tr><th>Device</th><th>W &times; H &times; T, mm</th><th>Envelope, cm&sup3;</th><th>Footprint, cm&sup2;</th><th>Screen / face</th><th>Bezel side &middot; top &middot; chin, mm</th><th>Printed plastic</th></tr></thead>';
    var tb = document.createElement('tbody');
    rows.forEach(function (r, i) {
      var bz = r.bezels ? f(r.bezels.left, 1) + ' &middot; ' + f(r.bezels.top, 1) + ' &middot; ' + f(r.bezels.bottom, 1) : '&ndash;';
      var pl = r.plastic_cm3 != null ? f(r.plastic_cm3, 1) + ' cm&sup3; &middot; ' + f(r.plastic_g, 0) + ' g' : '&ndash;';
      tb.insertAdjacentHTML('beforeend', '<tr><td><span class="sw ' + cls[i] + '"></span><b>' + r.name + '</b></td><td>' + f(r.w, 1) + ' &times; ' + f(r.h, 1) + ' &times; ' + f(r.t, 1) +
        '</td><td>' + f(r.envelope_cm3, 1) + '</td><td>' + f(r.footprint_cm2, 1) + '</td><td>' + f(r.screen_ratio_pct, 1) + ' %</td><td>' + bz + '</td><td>' + pl + '</td></tr>');
    });
    t.appendChild(tb);
    // outlines
    var V = CM.views;
    var overlay = function (hostId, key, label) {
      var host = ctx.q('#' + hostId);
      host.innerHTML = '';
      var x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      [V.ours, V.x4, V.retro].forEach(function (d) { d[key].forEach(function (poly) { poly[0].forEach(function (p) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }); }); });
      var pad = key === 'front' ? 3 : 1.5;
      var svg = SC.svg('svg', { viewBox: (x0 - pad) + ' ' + (-(y1 + pad)) + ' ' + (x1 - x0 + 2 * pad) + ' ' + (y1 - y0 + 2 * pad), class: 'cmpv', role: 'img', 'aria-label': label }, host);
      if (key === 'front') { var s = V.ours.screen; SC.svg('rect', { x: s[0], y: -s[3], width: s[2] - s[0], height: s[3] - s[1], class: 'scr' }, svg); }
      else SC.svg('line', { x1: x0 - pad, y1: 0, x2: x1 + pad, y2: 0, class: 'axis' }, svg);
      SC.svg('path', { d: SC.dPath(V.ours[key]), class: 'o-ours', 'fill-rule': 'evenodd' }, svg);
      SC.svg('path', { d: SC.dPath(V.x4[key]), class: 'o-x4', 'fill-rule': 'evenodd' }, svg);
      SC.svg('path', { d: SC.dPath(V.retro[key]), class: 'o-retro', 'fill-rule': 'evenodd' }, svg);
    };
    overlay('compare-front', 'front', 'Front outlines of this case, the X4 and the retro case, centred on the screen');
    overlay('compare-side', 'side', 'Side outlines of this case, the X4 and the retro case, front faces level');
    // the stack, front to back
    var colour = function (n) {
      n = n.toLowerCase();
      if (/skin/.test(n)) return ['var(--d-case)', false];
      if (/panel/.test(n)) return ['var(--d-glass)', true];
      if (/midplate/.test(n)) return ['var(--d-plate)', false];
      if (/pcb/.test(n)) return ['var(--d-pcb)', true];
      if (/battery/.test(n)) return ['var(--d-cell)', false];
      if (/parts/.test(n)) return ['var(--d-part)', true];
      if (/back/.test(n)) return ['var(--d-case2)', false];
      return ['var(--paper)', false];
    };
    var total = CM.budget.reduce(function (s, b) { return s + b[1]; }, 0);
    var st = ctx.q('#compare-stack'), sk = ctx.q('#compare-stack-key');
    st.innerHTML = ''; sk.innerHTML = '';
    CM.budget.forEach(function (b) {
      var c = colour(b[0]), sp = document.createElement('span');
      sp.style.flex = b[1] + ' 0 0'; sp.style.background = c[0];
      if (c[1]) sp.style.color = '#f1f2ec';
      if (b[1] / total > 0.075) sp.textContent = f(b[1], 2);
      sp.title = SC.text(b[0]) + ': ' + f(b[1], 2) + ' mm';
      st.appendChild(sp);
      sk.insertAdjacentHTML('beforeend', '<span><i style="background:' + c[0] + ';outline:1px solid var(--rule)"></i>' + SC.esc(SC.text(b[0])) + ' ' + f(b[1], 2) + '</span>');
    });
    var big = CM.budget.slice().sort(function (p, q) { return q[1] - p[1]; })[0];
    var why = ctx.size === '426'
      ? 'The X4 is ' + f(x4.t, 1) + ' mm because it is one integrated design. This case stacks a separate board behind a ' + (D.meta.panel && D.meta.panel.touch ? 'front-lit, touch-layered' : 'plain') + ' panel. The biggest single item is the parts on the board&rsquo;s back (' + SC.esc(SC.text(big[0])) + ', ' + f(big[1], 2) + ' mm): a real cut needs lower-profile parts, or a board with the battery connector and header beside the cell.'
      : 'The X4 is ' + f(x4.t, 1) + ' mm because it is one integrated design. This case stacks a separate board behind the panel and carries its cell behind the board, over the board&rsquo;s shallow middle: the ' + SC.esc(SC.text(big[0]).toLowerCase()) + ' is ' + f(big[1], 1) + ' of the ' + f(us.t, 1) + ' mm.';
    ctx.q('#compare-why').innerHTML = why;
    var fr = pct(us.footprint_cm2, rc.footprint_cm2);
    var foot = 'Footprint is where it compares well. At ' + f(us.footprint_cm2, 1) + ' cm&sup2; it is ' + Math.abs(fp) + '% ' + more(fp, 'over', 'under') + ' the bare X4 and ' + Math.abs(fr) + '% ' + more(fr, 'over', 'under') + ' the X4 in its retro case. Across the body it is ' +
      f(Math.abs(x4.w - us.w), 1) + ' mm ' + more(x4.w - us.w, 'narrower', 'wider') + ' than the bare X4 and ' + f(Math.abs(rc.w - us.w), 1) + ' mm ' + more(rc.w - us.w, 'narrower', 'wider') + ' than the retro case.';
    if (us.bezels && rc.bezels) foot += ' The side bezels are ' + f(us.bezels.left, 1) + ' mm against the retro case&rsquo;s ' + f(rc.bezels.left, 1) + '.';
    if (us.plastic_g && rc.plastic_g) foot += ' The printed plastic is ' + f(us.plastic_g, 0) + ' g against the retro case&rsquo;s ' + f(rc.plastic_g, 0) + ' g.';
    ctx.q('#compare-foot').innerHTML = foot;
    ctx.q('#compare-src').innerHTML = 'X4: the reference model by <b>Zorian22</b> (Thingiverse thing:7287950, <b>CC BY-NC-SA</b>), measured with calipers. The model doesn&rsquo;t mark the screen, so its active area comes from ' +
      (CM.x4_active_from || 'Xteink&rsquo;s spec') + ', and its screen centre from the retro case&rsquo;s window. Retro case: its author&rsquo;s print files, reassembled: the frame is flipped, and each back half is pushed on until it seats past its snap bumps. Bezels are measured to the visible window at the front face. Neither model is in the downloads.';
  },
});
