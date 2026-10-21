// Front to back: cards.zstack.bars drawn to scale in Z (pixel-true SVG, redrawn on resize), with the other size's
// stack (same build) beside it on request or when the card is opened (SC.load of that size's data file).
var zsRO = null, zsOther = {}, zsLoad = null, zsUser = false;   // zsUser: the reader has used the button, so opening the card no longer adds the other size
SC.card({
  id: 'zstack', title: 'Front to back', order: 90, preset: 'zstack',
  needs: ['cards.zstack.bars', 'cards.zstack.total', 'cards.zstack.budget'],
  render: function (D, ctx) {
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var Z = D.cards.zstack, S = ctx.size, B = ctx.build, MF = ctx.manifest || {};
    var thick = Z.total[1] - Z.total[0];
    fill('zs-thick', f(thick, 1));
    var cell = Z.bars.filter(function (b) { return /battery/i.test(b.name) && !b.beside; })[0];
    if (cell) fill('zs-cell', f(cell.z[1] - cell.z[0], 1));
    var rear = Z.bars.filter(function (b) { return /parts behind/i.test(b.name); })[0];
    if (rear) fill('zs-rear', f(rear.z[1] - rear.z[0], 2));
    var otherS = S === '426' ? '368' : '426';
    var otherLab = MF.sizes && MF.sizes[otherS] ? SC.text(MF.sizes[otherS].label) : otherS;
    var btn = ctx.q('#zstack-other'), state = ctx.q('#zstack-state');
    // the other size may not have this build (the 3.68 has no chinless): compare with its build of the same panel then
    // (light strip for the light-strip chinless, standard for the chinless)
    var oB = (SC.files(otherS, B) || {}).data ? B : SC.buildIs('ls', B) ? 'ls' : 'std';
    var key = otherS + '-' + oB;
    btn.textContent = 'Put the ' + otherLab + ' beside it';
    fill('zs-cap', Z.bars.some(function (b) { return b.beside; }) ? 'The narrow bar beside the stack is a part that sits level with others rather than behind them.' : '');

    var colour = function (n) {
      n = n.toLowerCase();
      if (/strip/.test(n)) return 'var(--warm)';
      if (/skin/.test(n)) return 'var(--d-case)';
      if (/stops/.test(n)) return 'var(--d-case2)';
      if (/panel/.test(n)) return 'var(--d-glass)';
      if (/midplate/.test(n)) return 'var(--d-plate)';
      if (/pcb/.test(n)) return 'var(--d-pcb)';
      if (/battery/.test(n)) return 'var(--d-cell)';
      if (/parts/.test(n)) return 'var(--d-part)';
      if (/back/.test(n)) return 'var(--d-case2)';
      return 'var(--paper)';
    };
    var host = ctx.q('#zstack-svg');
    var draw = function () {
      var W = Math.max(300, Math.round(host.clientWidth - 12) || 560);
      var OZ = zsOther[key] && zsOther[key].zstack;
      var zt = Math.max(Z.total[1], OZ ? OZ.total[1] : -99), zb = Math.min(Z.total[0], OZ ? OZ.total[0] : 99);
      var k = W < 480 ? 16 : 20, top = 44, Y = function (z) { return top + (zt - z) * k; };
      var main = Z.bars.filter(function (b) { return !b.beside; }), side = Z.bars.filter(function (b) { return b.beside; });
      var x0 = 4, w0 = W < 480 ? 46 : 60, xs = x0 + w0 + 6, ws = 12, xo = xs + (side.length ? ws + 8 : 0), wo = OZ ? (W < 480 ? 26 : 36) : 0;
      var lx = xo + (OZ ? wo + 14 : 6) + 24;
      var out = [];
      var H = Y(zb) + 16;
      out.push('<line class="z0" x1="0" x2="' + W + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>');
      var bar = function (x, w, b) { return '<rect class="bar" x="' + x + '" y="' + Y(b.z[1]).toFixed(1) + '" width="' + w + '" height="' + ((b.z[1] - b.z[0]) * k).toFixed(1) + '" fill="' + colour(b.name) + '"><title>' + SC.esc(SC.text(b.name)) + ': ' + f(b.z[1] - b.z[0], 2) + ' mm</title></rect>'; };
      main.forEach(function (b) { out.push(bar(x0, w0, b)); });
      side.forEach(function (b, i) { out.push(bar(xs + i * (ws + 2), ws, b)); });
      out.push('<text class="hd" x="' + x0 + '" y="' + (Y(zt) - 22) + '">' + SC.esc(SC.text(D.meta.size_label || S)) + '</text>');
      out.push('<text x="' + x0 + '" y="' + (Y(zt) - 8) + '">' + f(thick, 2) + (OZ ? '' : ' mm') + '</text>');   // two columns: numbers only (the unit crowded the other size's)
      if (OZ) {
        var om = OZ.bars.filter(function (b) { return !b.beside; });
        out.push('<g data-other="' + otherS + '">' + om.map(function (b) { return bar(xo, wo, b); }).join('') +
          '<text class="hd" x="' + xo + '" y="' + (Y(zt) - 22) + '">' + SC.esc(otherLab) + '</text>' +
          '<text x="' + xo + '" y="' + (Y(zt) - 8) + '">' + f(OZ.total[1] - OZ.total[0], 2) + '</text></g>');
      }
      out.push('<text x="' + (W - 2) + '" y="' + (Y(zt) - 22) + '" text-anchor="end">dashed: board&#x2019;s rear, z 0</text>');
      // labels: one per bar of this size, spread 13 px apart, wrapped to the room left of the right edge
      var maxc = Math.max(14, Math.floor((W - lx - 4) / 6.7));
      var wrap = function (s) {
        var words = s.split(' '), lines = [''];
        words.forEach(function (w) { var l = lines[lines.length - 1]; if ((l + ' ' + w).trim().length > maxc && l) lines.push(w); else lines[lines.length - 1] = (l + ' ' + w).trim(); });
        return lines;
      };
      var labs = Z.bars.map(function (b) {
        var txt = SC.text(b.name) + ' ' + f(b.z[1] - b.z[0], 2);
        return { y: (Y(b.z[0]) + Y(b.z[1])) / 2, lines: wrap((b.beside ? 'beside: ' : '') + txt), ax: b.beside ? xs + ws : x0 + w0 };
      }).sort(function (p, q) { return p.y - q.y; });
      var lh = 13;
      labs.forEach(function (l, i) {
        var hgt = l.lines.length * lh;
        l.ly = i ? Math.max(l.y, labs[i - 1].ly + labs[i - 1].lines.length * lh / 2 + hgt / 2 + 2) : l.y;
      });
      var last = labs[labs.length - 1], over = last.ly + last.lines.length * lh / 2 - (H - 4);
      if (over > 0) labs.forEach(function (l) { l.ly -= over; });
      labs.forEach(function (l) {
        out.push('<path class="ld" d="M' + (l.ax + 2) + ' ' + l.y.toFixed(1) + 'L' + (lx - 6) + ' ' + l.ly.toFixed(1) + 'L' + (lx - 2) + ' ' + l.ly.toFixed(1) + '"/>');
        l.lines.forEach(function (s, j) {
          out.push('<text x="' + lx + '" y="' + (l.ly + (j - (l.lines.length - 1) / 2) * lh + 4).toFixed(1) + '">' + SC.esc(s) + '</text>');
        });
      });
      var minY = Math.min(0, labs[0].ly - labs[0].lines.length * lh / 2 - 4);
      host.innerHTML = '<svg viewBox="0 ' + minY.toFixed(1) + ' ' + W + ' ' + (H - minY).toFixed(1) + '" role="img" aria-label="The stack from front to back, to scale in Z">' + out.join('') + '</svg>';
    };
    if (zsRO) zsRO.disconnect();
    var lastW = 0;
    zsRO = new ResizeObserver(function () { var w = host.clientWidth; if (w && Math.abs(w - lastW) > 2) { lastW = w; draw(); } });
    zsRO.observe(host);
    draw();
    var setBtn = function () {
      var on = !!zsOther[key];
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      btn.textContent = on ? 'Hide the ' + otherLab : 'Put the ' + otherLab + ' beside it';
    };
    setBtn();
    var load = function () {
      if (zsOther[key]) return Promise.resolve();
      state.textContent = 'Loading the ' + otherLab + '...';
      return SC.load(SC.files(otherS, oB).data).then(function (OD) {
        zsOther[key] = { zstack: OD.cards && OD.cards.zstack };
        state.textContent = '';
        if (ctx.q('#zstack-svg') === host) { draw(); setBtn(); }
      }, function () { state.textContent = 'Could not load the ' + otherLab + '.'; });
    };
    btn.onclick = function () {
      zsUser = true;
      if (zsOther[key]) { delete zsOther[key]; draw(); setBtn(); } else load();
    };
    zsLoad = load;
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    var nums = [
      row('Total', f(thick, 2) + ' mm', 'front face to back'),
      row('In front of z 0', f(Z.total[1], 2) + ' mm', 'skin, panel, midplate, gap, board'),
      row('Behind it', f(-Z.total[0], 2) + ' mm', 'parts, ' + (cell ? 'the cell, ' : '') + 'the back'),
    ];
    if (Z.with_keys) nums.push(row('Over the keys', f(Z.with_keys, 2) + ' mm', 'the bottom keys stand proud of the face'));
    if (Z.without_battery) nums.push(row('Without the cell', f(Z.without_battery, 2) + ' mm', 'what the battery costs: ' + f(thick - Z.without_battery, 2) + ' mm'));
    ctx.q('#zstack-nums').innerHTML = nums.join('');
  },
  onEnter: function (D, ctx) {
    if (zsLoad && !zsUser) zsLoad();
  },
});
