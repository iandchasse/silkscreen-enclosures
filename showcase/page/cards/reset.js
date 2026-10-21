// Reset: the pinhole onto SW11. The slider uses the stage's pin mapping (t 0-0.6 brings the pin from pin_from to the
// plunger face, 0.6-1 pushes it on by max_travel), so the drawing and the 3D pin agree; it drives and follows the stage.
SC.card({
  id: 'reset', title: 'Reset', order: 55, preset: 'reset',
  needs: ['cards.reset.reset', 'cards.reset.ref'],
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
    var R = D.cards.reset.reset, ref = D.cards.reset.ref, CR = D.cards.reset;
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var c = (D.controls || []).filter(function (x) { return x.kind === 'pin' && x.ref === ref; })[0] || null;
    var from = c ? c.pin_from : [R.face[0] + 10, R.face[1], R.face[2]];
    var to = c ? c.pin_to : R.face;
    var ax = c ? c.plunger_axis[0] : -(R.axis ? R.axis[0] : 1);  // -1: the pin goes in along -X (right wall)
    var maxT = c ? c.max_travel : 0.45, click = c ? c.click_travel : 0.25;
    var hole = CR.hole_d != null ? CR.hole_d : (c && c.hole_d != null ? c.hole_d : null);
    if (hole != null) fill('reset-hole', f(hole, 1));
    fill('reset-sink', CR.sink_d != null ? ' to \u00d8' + f(CR.sink_d, 1) : '');
    var usb = D.cards.usb && D.cards.usb.usb;
    fill('reset-below', CR.below_usb_mm != null ? f(CR.below_usb_mm, 0) : usb ? f(usb.yc - R.face[1], 0) : '?');
    fill('reset-click', f(click, 2));
    fill('reset-max', f(maxT, 2));
    var wall = ax < 0 ? D.meta.walls_x[1] : D.meta.walls_x[0];
    var pinR = (hole != null ? Math.min(hole, 1.2) : 1.2) / 3;   // a paperclip: about 0.8 mm
    var resetD = ctx.Drawing('reset', 'dw-reset-sec', {
      label: 'Section through the reset pinhole',
      moving: { nub: 'nub' }, groupOrder: ['nub'],
      overlay: function (d) {
        var g = d.extra;
        while (g.firstChild) g.removeChild(g.firstChild);
        var tip = d._pinTip != null ? d._pinTip : from[0];
        var z = R.face[2];
        var u0 = ax < 0 ? tip : d.u0 - 2, u1 = ax < 0 ? d.u1 + 2 : tip;
        if (u1 > u0 && tip > d.u0 - 1 && tip < d.u1 + 1) SC.svg('rect', { x: u0, y: -(z + pinR), width: u1 - u0, height: 2 * pinR, class: 'metal L' }, g);
      },
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        a.label(wall + 0.5 * ax, R.face[2] + 0.6, '\u00d8' + f(hole != null ? hole : 1.2, 1) + ' pinhole,\ncountersunk', 22 * ax, 46);
        a.label(R.face[0] + 0.9 * ax, R.face[2] - 1.2, ref, 26 * ax, -26);
        a.label(R.face[0] - 2.2 * ax, R.face[2] - 1.1, 'lid trough', -16 * ax, -40);
      },
    });
    var input = ctx.q('#reset-pin'), outEl = ctx.q('#reset-out');
    function set(t, toStage) {
      var ex = SC.exag ? 4 : 1;
      var s = Math.min(1, t / 0.6), push = t > 0.6 ? (t - 0.6) / 0.4 * maxT : 0;
      var tip = from[0] + (to[0] - from[0]) * s + ax * push * ex;
      if (resetD) {
        resetD._pinTip = tip; resetD.redraw();
        if (resetD.groups.nub) resetD.groups.nub.setAttribute('transform', 'translate(' + (ax * push * ex) + ' 0)');
      }
      var realTip = from[0] + (to[0] - from[0]) * s;
      var inWall = ax < 0 ? realTip < wall : realTip > wall;
      outEl.textContent = push >= click - 1e-9 ? (push >= maxT - 1e-9 ? 'clicked, bottomed at ' + f(maxT, 2) + ' mm' : 'clicked, ' + f(push, 2) + ' mm')
        : push > 0 ? 'pushing ' + f(push, 2) + ' mm' : s >= 1 ? 'on the plunger' : inWall ? 'in the hole' : 'pin outside';
      if (SC.exag && push > 0) outEl.textContent += ' (motion \u00d74)';
      if (toStage && c && SC.viewer && SC.viewer.press) SC.viewer.press(c.id, t, { src: 'reset' });
    }
    input.oninput = function () { set(+input.value, true); };
    ctx.on('pressed', function (r) {
      if (!r || r.src === 'reset' || !c || r.id !== c.id) return;
      input.value = r.t; set(r.t, false);
    });
    ctx.on('exag', function () { set(+input.value, false); });
    ctx.on('focus', function () { input.value = 0; set(0, false); });
    ctx.on('released', function () { input.value = 0; set(0, false); });
    set(+input.value, false);
  },
});
