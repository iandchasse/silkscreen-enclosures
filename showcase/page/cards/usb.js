// USB-C: the divot floored by the tub. Two drawings with the plug drawn over them; the slider moves the plug in the
// drawings and the stage's 'usb' plug control (t 0 = 9 mm out, 1 = seated), and follows the stage's plug.
SC.card({
  id: 'usb', title: 'USB-C', order: 50, preset: 'usb',
  needs: ['cards.usb.usb', 'cards.usb.ref'],
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
    var U = D.cards.usb.usb, ref = D.cards.usb.ref;
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var r2 = function (v) { return SC.fmt(v + 1e-6, 2); };        // round half up, as the text does
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var ctrl = (D.controls || []).filter(function (c) { return c.kind === 'plug'; })[0] || null;
    var insert = ctrl && ctrl.insert_mm ? ctrl.insert_mm : 9;
    var seatFace = U.mouth_x + U.spare;                              // overmold face of a fully seated plug
    var shellLen = ctrl && ctrl.shell_len ? ctrl.shell_len - U.spare : 6.2;
    var skey = null;
    var dplan = SC.drawing('usb_plan');
    var sref = (dplan && dplan.notes && dplan.notes.skey) || 'SW1';
    ((D.cards.sidekeys && D.cards.sidekeys.tabs) || []).forEach(function (t) { if (t.ref === sref) skey = t; });
    fill('usb-skey', SC.part(sref));
    fill('usb-depth', f(U.x1 - U.mouth_x, 1));
    fill('usb-corr', f(U.insert_x - U.mouth_x, 3));
    fill('usb-face', r2(U.face_to_mouth));
    fill('usb-short', r2(U.plug_short_mm));

    var plugOverlay = function (plan) {
      return function (d) {
        var g = d.extra;
        while (g.firstChild) g.removeChild(g.firstChild);
        var out = d._plugOut != null ? d._plugOut : insert * 0.4;
        var face = Math.max(U.face_x, seatFace + out);               // a typical overmold fits the recess: the floor is the stop
        var tip = face - (shellLen + U.spare);                      // the shell: receptacle depth plus the spare
        var c = plan ? U.yc : U.zc;
        var sh = plan ? 8.25 / 2 : 2.4 / 2;                        // a USB-C plug's shell, 8.25 x 2.4
        var om = plan ? U.typical[0] / 2 : U.typical[1] / 2;
        var r = function (u0, u1, v0, v1, cls) { if (u1 > u0) SC.svg('rect', { x: u0, y: -v1, width: u1 - u0, height: v1 - v0, class: cls + ' L' }, g); };
        r(Math.min(tip, d.u1 + 1), Math.min(face + 0.01, d.u1 + 1), c - sh, c + sh, 'metal');
        r(Math.min(face, d.u1 + 1), d.u1 + 1, c - om, c + om, 'plug');
      };
    };
    var usbD = ctx.Drawing('usb', 'dw-usb-sec', {
      label: 'Section through the USB-C port',
      overlay: plugOverlay(false),
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        a.line(U.mouth_x, U.zc - 3.3, U.mouth_x, U.zc + 3.3);
        a.dim(U.mouth_x, U.recess_z[1] + 1.9, U.face_x, U.recess_z[1] + 1.9, r2(U.face_to_mouth), 10, true);
        a.dim(U.face_x, U.recess_z[1] + 1.9, U.x1, U.recess_z[1] + 1.9, f(U.x1 - U.face_x, 2), 10);
        a.label(U.mouth_x - 0.1, U.zc - 2.6, ref + ' mouth', -40, -30);
        a.label((U.floor_x[0] + U.floor_x[1]) / 2, U.recess_z[1] - 0.3, 'floor ' + f(U.floor_t, 1), -30, 28, { hot: true });
        a.label(U.face_x + 0.6, U.recess_z[0] + 0.4, 'recess', 30, -24);
        a.label(U.x1, U.recess_z[1] + 0.4, 'case face', 18, 22);
        a.label((U.floor_x[0] + U.floor_x[1]) / 2, U.seam + 0.2, 'lid block closes\nthe hole', 30, -26);
      },
    });
    var usbPlan = ctx.Drawing('usb_plan', 'dw-usb-plan', {
      label: 'Plan of the USB-C port',
      overlay: plugOverlay(true),
      annotate: function (a0, dd) {
        var a = fitA(a0, dd);
        a.dim(U.x1 + 0.6, U.recess_y[0], U.x1 + 0.6, U.recess_y[1], f(U.recess[0], 2), 12);
        a.label(U.mouth_x - 0.8, U.yc + 3.0, ref, -30, 20);
        a.label((U.floor_x[0] + U.floor_x[1]) / 2, U.recess_y[1] - 0.6, 'floor', -26, 24, { hot: true });
        if (skey) a.label(skey.root[0] - 0.86, skey.root[1] - 0.2, sref + ' key root', -30, 14);
      },
    });
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    ctx.q('#usb-nums').innerHTML = [
      row('Floor face to ' + SC.esc(ref), r2(U.face_to_mouth) + ' mm', 'its inside on the panel\u2019s corridor, ' + f(U.insert_x - U.mouth_x, 3) + ' in front of the mouth'),
      row('Typical plug', r2(U.plug_short_mm) + ' mm short', 'of full depth; the overmold stops on the floor'),
      row('Recess', f(U.recess[0], 2) + ' &times; ' + f(U.recess[1], 2) + ' mm', 'typical cables; ' + f(U.x1 - U.face_x, 2) + ' deep, R' + f(U.r, 1) + ', 45\u00b0 lead-in'),
      row('Port hole', f(U.hole[0], 2) + ' &times; ' + f(U.hole[1], 2) + ' mm', SC.esc(ref) + '\u2019s opening plus 0.1 a side; open below, closed by the lid'),
    ].join('');

    var input = ctx.q('#usb-plug'), outEl = ctx.q('#usb-out');
    function set(p, toStage) {
      var out = (1 - p) * insert;
      [usbD, usbPlan].forEach(function (d) { if (d) { d._plugOut = out; d.redraw(); } });
      outEl.textContent = seatFace + out <= U.face_x + 0.001
        ? 'in as far as it goes: ' + r2(U.plug_short_mm) + ' mm short of full depth'
        : 'out ' + f(out, 1) + ' mm';
      if (toStage && ctrl && SC.viewer && SC.viewer.press) SC.viewer.press(ctrl.id, p, { src: 'usb' });
    }
    input.oninput = function () { set(+input.value, true); };
    ctx.on('pressed', function (r) {
      if (!r || r.src === 'usb' || !ctrl || r.id !== ctrl.id) return;
      input.value = r.t; set(r.t, false);
    });
    ctx.on('released', function () { input.value = 0; set(0, false); });
    set(+input.value, false);
  },
});
