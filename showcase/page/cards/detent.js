// Stack detents: the midplate's four spring strips and the tub's pockets. Drawings 'detent_plan' and 'detent'.
SC.card({
  id: 'detent', title: 'Stack detents', order: 65, preset: 'detent',
  needs: ['cards.detent.detents', 'cards.detent.detents.rows', 'cards.detent.detents.p'],
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
    var DT = D.cards.detent.detents, DP = DT.p;
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var rows = DT.rows || [];
    // which row the drawings cut: the one whose strip holds the section's y (right, bottom on both sizes)
    var dsec = SC.drawing('detent');
    var r0 = rows.filter(function (r) { return dsec && r.bump_y[0] <= dsec.at && dsec.at <= r.strip_y[1] + 0.5; })[0] || rows[0];
    var byWall = {};
    rows.forEach(function (r) { (byWall[r.wall] = byWall[r.wall] || []).push(r); });
    var walls = Object.keys(byWall);
    var lowOf = function (r) { var same = byWall[r.wall]; return same.every(function (s) { return s.strip_y[0] >= r.strip_y[0]; }); };
    fill('detent-which', (r0.wall === 'right' ? 'right-hand' : 'left-hand') + ' ' + (lowOf(r0) ? 'bottom' : 'top'));
    fill('detent-where', (rows.length === 4 ? 'four' : String(rows.length)) + ' places, ' + walls.map(function (w) { return byWall[w].length + ' on the ' + w + ' wall'; }).join(' and '));
    fill('detent-strip', f(DT.strip_mm[0], 1));
    fill('detent-plate', f(DT.strip_mm[1], 1));
    fill('detent-short', f(DT.plate_rear_z[0] - DT.catch_z, 2) + '&ndash;' + f(DT.plate_rear_z[1] - DT.catch_z, 2));
    fill('detent-pz0', f(DT.pocket_z[0], 2));
    fill('detent-pz1', f(DT.pocket_z[1], 2));
    var SCR = D.cards.screen && D.cards.screen.screw_clear;
    fill('detent-screws', SCR ? ' Held there, the two bottom screws pass ' + f(SCR.panel_mm, 1) + ' mm from the glass&rsquo;s edge and at least ' + f(SCR.ribbon_mm, 1) + ' mm from every ribbon.' : '');

    var side = r0.wall === 'right' ? 1 : -1;
    var xw = side > 0 ? DT.wall_x[1] : DT.wall_x[0], xe = xw - side * DT.edge_clr;
    ctx.Drawing('detent_plan', 'dw-detent-plan', {
      label: 'Plan of a midplate detent', order: ['tub', 'midplate'],
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        a.label(xe - side * DP.w / 2, (r0.strip_y[0] + r0.strip_y[1]) / 2 - 1.5, 'strip ' + f(DP.w, 1) + ' wide', -40 * side, -10, { hot: true });
        a.label(xe - side * (DP.w + DP.slot / 2), r0.strip_y[0] + 1.2, 'slot ' + f(DP.slot, 1), -40 * side, -24);
        a.label(xe + side * DP.bump * 0.6, (r0.bump_y[0] + r0.bump_y[1]) / 2, 'bump', 30 * side, 20, { hot: true });
        a.label(xw + side * DP.depth * 0.6, r0.bump_y[1] + 0.2, 'pocket\nin the wall', 20 * side, 34);
        a.label(xe - side * DP.w / 2, r0.strip_y[0] - 0.4, 'root', -40 * side, -16);
      },
    });
    var z = D.meta.z;
    ctx.Drawing('detent', 'dw-detent-sec', {
      label: 'Section across a midplate detent bump',
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        a.label(xe + side * DP.bump / 2, z.mid_rear + 0.5, 'bump', 30 * side, -30, { hot: true });
        a.label(xw + side * DP.depth / 2, DP.z0 + DP.depth / 2 + 0.05, '45\u00b0 roof\n(the catch)', 30 * side, -24, { hot: true });
        a.label(xw + side * DP.depth / 2, DP.z1 - 0.2, 'pocket', 30 * side, 20);
        var ui = xw - side * 1.4;
        a.label(ui, z.mid_rear + 0.5, 'midplate', -30 * side, 26);
        if (dsec && dsec.layers.some(function (l) { return ['epd', 'glass'].indexOf(l.id) >= 0; })) a.label(ui, z.disp_rear + 0.4, 'display', -30 * side, 30);
        a.label(ui, (z.pcb_front + (z.pcb_rear || 0)) / 2, 'PCB', -30 * side, -20);
      },
    });
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    var nums = [
      row('Detents', String(DT.count), walls.map(function (w) { return byWall[w].length + ' ' + w; }).join(', ')),
      row('Hold', f(DT.hold_N_total, 1) + ' N', 'in all &middot; ' + f(DT.hold_N_each, 2) + ' N each, 45\u00b0 roof'),
      row('Ride', f(DT.ride_mm, 2) + ' mm', 'into the wall on the way in &middot; ' + f(DT.drag_N_each, 2) + ' N drag each'),
      row('Strip', f(DT.strip_mm[0], 1) + ' &times; ' + f(DT.strip_mm[1], 1) + ' mm', f(DT.arm_mm, 1) + ' mm to the bump &middot; ' + f(DT.strain_pct, 1) + ' % strain'),
      row('Caught at', 'z ' + f(DT.catch_z, 2), 'plate sits at ' + f(DT.plate_rear_z[0], 2) + '&ndash;' + f(DT.plate_rear_z[1], 2) + ' with the lid on'),
    ];
    if (SCR) nums.push(row('Screws', f(SCR.panel_mm, 1) + ' mm', 'from the glass &middot; ' + f(SCR.ribbon_mm, 1) + '+ from the ribbons'));
    ctx.q('#detent-nums').innerHTML = nums.join('');
  },
});
