// Battery. 4.26: the midplate slot (drawings bay_lip, fence, battery). 3.68: the cell in the lid, the board-rear depth
// map (cards.battery.depth_map), drawings bay and bay_plan, and the table of layouts from the x3 README.
SC.card({
  id: 'battery', title: 'Battery', order: 80, preset: 'battery',
  needs: ['cards.battery.battery', 'cards.battery.battery.box'],
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
    var bbox = function (dr, id) {
      var L = layerOf(dr, id), b = [Infinity, -Infinity, Infinity, -Infinity];
      if (!L) return null;
      L.polys.forEach(function (p) { p[0].forEach(function (q) { b[0] = Math.min(b[0], q[0]); b[1] = Math.max(b[1], q[0]); b[2] = Math.min(b[2], q[1]); b[3] = Math.max(b[3], q[1]); }); });
      return isFinite(b[0]) ? b : null;
    };
    var lab = function (a, dr, id, u, v, s, dx, dy, opt) { var p = P(dr, id, u, v); a.label(p[0], p[1], s, dx, dy, opt); };
    // a label whose text goes to (tu, tv) in model units
    var labAt = function (a, dr, id, u, v, s, tu, tv, opt) { var p = P(dr, id, u, v); a.label(p[0], p[1], s, (tu - p[0]) / a.px, (tv - p[1]) / a.px, opt); };
    // a copy of a drawing with room for labels above and below (the parts stay where they are)
    var widen = function (dr, dv0, dv1) { var c = Object.assign({}, dr); c.window = [dr.window[0], dr.window[1], dr.window[2] - dv0, dr.window[3] + dv1]; return c; };
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    var B = D.cards.battery.battery, z = D.meta.z;
    var nums = [];

    if (ctx.size === '426') {
      var BY = B.bay, C = B.card, F = B.fence, bd = B.data || {};
      var dLip = SC.drawing('bay_lip'), dF = SC.drawing('fence'), dB = SC.drawing('battery');
      fill('bat-lip-at', f(dLip.at, 1));
      fill('bat-fence-at', f(dF.at, 1));
      fill('bat-card-at', f(dB.at, 1));
      fill('bat-cleat-gap', f(BY.cleats_y[1] - BY.cleats_y[0], 1));
      fill('bat-mouth', f(B.box.y[0] - C.mouth_y, 1));
      fill('bat-dims', f(B.box.x[1] - B.box.x[0], 2) + ' &times; ' + f(B.box.y[1] - B.box.y[0], 2) + ' &times; ' + f(B.box.z[1] - B.box.z[0], 2));
      var disp = function (dr) { return dr.layers.filter(function (l) { return ['glass', 'lgp', 'film'].indexOf(l.role) >= 0; }).map(function (l) { return l.id; }); };
      var wLip = widen(dLip, 5.6, 4);
      ctx.Drawing(wLip, 'dw-battery-lip', {
        label: 'Section across the cell through a snap', order: ['lid', 'tub', 'pcb', 'cell', 'midplate'].concat(disp(dLip)),
        annotate: function (a0, d) {
          var a = fitA(a0, d), L = BY.lip, SN = BY.snaps;
          var r1 = d.v0 + 3.4, r2 = d.v0 + 1.4, up = d.v1 - 1.6;
          labAt(a, dLip, 'midplate', (L.x[0] + L.x[1]) / 2, L.z_tip + 0.3, 'lip, ' + f(L.over_cell, 1) + ' over', 4, r1, { hot: true });
          labAt(a, dLip, 'midplate', SN.x[0] + 0.2, SN.tip_z, 'snap, ' + f(SN.over_cell, 1) + ' over', 30, r1, { hot: true });
          labAt(a, dLip, 'cell', 20.0, (B.box.z[0] + B.box.z[1]) / 2, '503035 cell', 14, up);
          labAt(a, dLip, 'midplate', 12.0, z.mid_rear + 0.5, 'midplate', 22, up);
          labAt(a, dLip, 'lid', 28.0, B.box.z[0] - 0.9, 'lid spring', 20, r2);
        },
      });
      ctx.Drawing(dF, 'dw-battery-fence', {
        label: 'Plan of the battery slot, the cleats and the microSD card path', order: ['tub', 'pcb', 'j5', 'cell', 'midplate'],
        annotate: function (a0, d) {
          var a = fitA(a0, d), ym = (BY.left_rail[2] + BY.left_rail[3]) / 2;
          lab(a, dF, 'midplate', (BY.left_rail[0] + BY.left_rail[1]) / 2, ym + 6, 'rail + lip', 14, 0, { hot: true });
          lab(a, dF, 'midplate', BY.right_posts[0], (BY.snaps.y[0][1] + BY.snaps.y[1][0]) / 2, 'lead out', 18, 26);
          lab(a, dF, 'midplate', (BY.cleat_x[0] + BY.cleat_x[1]) / 2, BY.cleats_y[1], 'cleats: wind\nspare lead', 16, 26, { hot: true });
          lab(a, dF, 'midplate', 12.0, (BY.stop_y[0] + BY.stop_y[1]) / 2, 'stop, ' + f(B.bay_p.stop_h, 0) + ' mm tall', -16, -26, { hot: true });
          lab(a, dF, 'cell', (B.box.x[0] + B.box.x[1]) / 2, (B.box.y[0] + B.box.y[1]) / 2, '503035 cell', 24, 30);
          lab(a, dF, 'j7', B.j7[0] + 1.0, (B.j7[2] + B.j7[3]) / 2, 'J7 microSD,\nbehind the board', -30, -10);
          var cx = (C.x[0] + C.x[1]) / 2;
          a.arrow(cx, C.mouth_y + 0.2, cx, C.out_y, true);
          a.label(cx, (C.mouth_y + C.out_y) / 2, 'card out,\ncell swung out', 20, -12, { hot: true });
          var j5 = bbox(dF, 'j5');
          if (j5) lab(a, dF, 'j5', (j5[0] + j5[1]) / 2, (j5[2] + j5[3]) / 2, 'J5', 20, -30);
        },
      });
      var wB = widen(dB, 5, 2.5);
      ctx.Drawing(wB, 'dw-battery-card', {
        label: 'Section down the microSD card centre line', order: ['lid', 'tub', 'pcb', 'j7', 'cell', 'midplate'].concat(disp(dB)),
        annotate: function (a0, d) {
          var a = fitA(a0, d), bz = B.box.z[0], cz = (C.z[0] + C.z[1]) / 2;
          var r1 = d.v0 + 3.1, r2 = d.v0 + 1.2, up = d.v1 - 1.3;
          labAt(a, dB, 'lid', B.springs_y[0], bz - 0.2, 'lid springs', 88, r1);
          labAt(a, dB, 'cell', (B.box.y[0] + B.box.y[1]) / 2 + 4, (B.box.z[0] + B.box.z[1]) / 2, '503035 cell', 104.5, r1);
          labAt(a, dB, 'j7', (B.j7[2] + B.j7[3]) / 2, (B.j7[4] + B.j7[5]) / 2, 'J7', 64, r2);
          a.arrow(C.mouth_y + 0.1, cz, C.out_y, cz, true);
          a.label(C.mouth_y + 1.2, cz, 'card out, once the cell is out', (76 - C.mouth_y - 1.2) / a.px, (r2 - cz) / a.px, { hot: true });
          labAt(a, dB, 'midplate', (BY.stop_y[0] + BY.stop_y[1]) / 2, (BY.stop_z[0] + BY.stop_z[1]) / 2, 'low stop', 84, up, { hot: true });
          labAt(a, dB, 'midplate', (d.u0 + B.j7[2]) / 2, z.mid_rear + 0.5, 'midplate', 70, up);
        },
      });
      nums = [
        row('Slot', 'rails ' + f(BY.rail_z[1] - BY.rail_z[0], 1) + ' mm, stop ' + f(B.bay_p.stop_h, 0) + ' mm', f(F.clr, 2) + ' mm off the cell; click in, or slide in from the top edge'),
        row('Hold-down', 'lip ' + f(BY.lip.over_cell, 1) + ', 2 snaps ' + f(BY.snaps.over_cell, 1), 'over the cell&rsquo;s back edges, ' + f(BY.lip.clear_of_back, 1) + ' off it; 45&deg; undersides, no supports'),
        row('Cleats', '2, ' + f(BY.cleat_z[1] - BY.cleat_z[0], 1) + ' mm tall', f(BY.cleats_y[1] - BY.cleats_y[0], 1) + ' mm apart, capped, for spare lead'),
        row('Card path', 'clear', 'J7&rsquo;s mouth is ' + f(B.box.y[0] - C.mouth_y, 1) + ' mm from the cell; the stop is ' + f(BY.stop_z[0] - C.z[1], 2) + ' mm in front of the card'),
        row('Pack model', f(B.box.x[1] - B.box.x[0], 2) + ' &times; ' + f(B.box.y[1] - B.box.y[0], 2) + ' &times; ' + f(B.box.z[1] - B.box.z[0], 2), 'site 503035 with wrap and protection board'),
      ];
      if (bd['+0.0mm_pack']) nums.push(row('Springs', f(bd['+0.0mm_pack'].force_N, 2) + ' N each', f(bd['-0.3mm_pack'].force_N, 2) + '&ndash;' + f(bd['+0.3mm_pack'].force_N, 2) + ' N over &plusmn;0.3 mm pack thickness'));
    } else {
      var DM = D.cards.battery.depth_map, dp = B.deep_parts || {};
      var deepOrder = Object.keys(dp).sort(function (p, q) { return dp[q] - dp[p]; });
      fill('bat-deep', deepOrder.filter(function (k) { return dp[k] > 3; }).map(function (k) { return k + ' ' + f(dp[k], 1); }).join(', ') + ' mm');
      fill('bat-shallow', f(1.6, 1));
      // ---- depth map, seen from behind (X mirrored): one rect per run of cells in the same band ----
      var bins = [
        [0.6, 'bare board'],
        [1.7, '1.7 mm or less'],
        [3.3, 'ESP32 module' + (dp.U4 ? ' ' + f(dp.U4, 1) : '')],
        [4.2, 'USB-C' + (dp.J1 ? ' ' + f(dp.J1, 1) : '') + ', L1' + (dp.L1 ? ' ' + f(dp.L1, 1) : '')],
        [99, 'switches' + (dp.SW7 ? ' ' + f(dp.SW7, 1) : '') + ', J5' + (dp.J5 ? ' ' + f(dp.J5, 1) : '')],
      ];
      var binOf = function (dd) { for (var i = 0; i < bins.length; i++) if (dd <= bins[i][0]) return i; return bins.length - 1; };
      var host = ctx.q('#battery-map');
      host.innerHTML = '';
      var x0 = DM.x0, x1 = DM.x0 + DM.nx * DM.res, y0 = DM.y0, y1 = DM.y0 + DM.ny * DM.res, pad = 2;
      var svg = SC.svg('svg', { viewBox: (-x1 - pad) + ' ' + (-y1 - pad) + ' ' + (x1 - x0 + 2 * pad) + ' ' + (y1 - y0 + 2 * pad + 5), class: 'dmap', role: 'img',
        'aria-label': 'Map of the board\u2019s back: the tallest part over each millimetre, with the battery bay outlined' }, host);
      var defs = SC.svg('defs', null, svg);
      var pat = SC.svg('pattern', { id: 'battery-hatch', patternUnits: 'userSpaceOnUse', width: 1.6, height: 1.6, patternTransform: 'rotate(45)' }, defs);
      SC.svg('line', { x1: 0, y1: 0, x2: 0, y2: 1.6, class: 'hl' }, pat);
      var X = function (x) { return -x; }, Y = function (y) { return -y; };
      var cells = SC.svg('g', null, svg);
      for (var j = 0; j < DM.ny; j++) {
        var run = null;
        var flush = function () { if (run) SC.svg('rect', { x: X(DM.x0 + (run.i1 + 1) * DM.res), y: Y(DM.y0 + (j + 1) * DM.res), width: (run.i1 - run.i0 + 1) * DM.res + 0.02, height: DM.res + 0.02, class: 'dm' + run.b }, cells); run = null; };
        for (var i = 0; i < DM.nx; i++) {
          var dd = DM.depth[j][i], on = DM.on[j][i];
          if (!on && !dd) { flush(); continue; }
          var b = binOf(dd);
          if (run && run.b === b) run.i1 = i; else { flush(); run = { b: b, i0: i, i1: i }; }
        }
        flush();
      }
      var poly = function (pts, cls) { return SC.svg('path', { d: 'M' + pts.map(function (p) { return X(p[0]) + ' ' + Y(p[1]); }).join('L'), class: cls }, svg); };
      poly(DM.outline.concat([DM.outline[0]]), 'outl');
      var rect = function (r, cls) { return SC.svg('rect', { x: X(r[1]), y: Y(r[3]), width: r[1] - r[0], height: r[3] - r[2], class: cls }, svg); };
      if (B.antenna) rect(B.antenna, 'ant');
      var BAY = B.bay.pocket;
      rect(BAY, 'bay');
      if (B.lead_xy) poly(B.lead_xy, 'lead');
      if (B.plug) rect(B.plug, 'box');
      if (B.j5) rect(B.j5, 'box');
      var tx = function (x, y, s, anchor, cls) { var e = SC.svg('text', { x: X(x), y: Y(y), 'font-size': 2.6, 'text-anchor': anchor || 'start', 'dominant-baseline': 'middle', class: cls || null }, svg); e.textContent = s; };
      if (B.j5) tx((B.j5[0] + B.j5[1]) / 2, B.j5[3] + 2.2, 'J5', 'middle');
      tx(BAY[1] - 1.5, BAY[3] - 3, 'battery bay');
      if (B.antenna) tx(B.antenna[1] + 1, (B.antenna[2] + B.antenna[3]) / 2, 'antenna', 'end');
      tx(x1 - 0.5, y0 - 2.5, '\u2190 USB-C side', 'start', 'dim');
      tx(x0 + 0.5, y0 - 2.5, 'power key side \u2192', 'end', 'dim');
      ctx.q('#battery-map-leg').innerHTML = bins.map(function (b, k) { return '<span><i class="dm" style="background:' + ['color-mix(in srgb, var(--copper) 8%, var(--paper))', 'color-mix(in srgb, var(--copper) 24%, var(--paper))', 'color-mix(in srgb, var(--copper) 46%, var(--paper))', 'color-mix(in srgb, var(--copper) 70%, var(--paper))', 'color-mix(in srgb, var(--copper) 94%, var(--paper))'][k] + '"></i>' + SC.esc(b[1]) + '</span>'; }).join('');

      // ---- sections ----
      var dBay = SC.drawing('bay'), dPl = SC.drawing('bay_plan'), BB = B.bay, R = B.retention || {};
      fill('bat-bay-at', f(dBay.at, 2));
      fill('bat-plan-at', f(dPl.at, 2));
      var ym = (B.box.y[0] + B.box.y[1]) / 2, xm = (B.box.x[0] + B.box.x[1]) / 2;
      var wBay = widen(dBay, 6, 4);
      ctx.Drawing(wBay, 'dw-battery-bay', {
        label: 'Section down the middle of the cell',
        annotate: function (a0, d) {
          var a = fitA(a0, d);
          var r1 = d.v0 + 3.4, r2 = d.v0 + 1.3, up = d.v1 - 1.6, u0 = dBay.window[0];
          // rows below (r1, r2) and above (up); a label's text starts at tu when tu is past its dot, else ends there
          labAt(a, dBay, 'cell', ym, (B.box.z[0] + B.box.z[1]) / 2, '503035 cell', ym + 5, r1, { hot: true });
          a.dim(ym + 10, B.box.z[0], ym + 10, B.box.z[1], f(B.allowance_mm, 1), 14, true);
          labAt(a, dBay, 'lid', BB.lip.y[1], (BB.lip.z_edge + BB.lip.z_top) / 2, 'lip over the cell\u2019s bottom edge', BB.lip.y[1] + 1.5, r2);
          labAt(a, dBay, 'lid', BB.end_stop.y, BB.end_stop.top - 0.3, 'end stop', BB.end_stop.y - 1.5, r2);
          labAt(a, dBay, 'lid', ym - 6, B.box.z[0] - B.floor_t / 2, f(B.floor_t, 1) + ' floor', ym - 4.5, r1);
          var j7u = (B.j7[2] + B.j7[3]) / 2;
          labAt(a, dBay, 'j7', j7u, (B.j7[4] + B.j7[5]) / 2, 'J7, ' + f(B.deepest_under_mm, 2) + ' deep', j7u - 9, up);
          labAt(a, dBay, 'pcb', ym + 8, 0.8, 'board', ym + 5.5, up);
          if (layerOf(dBay, 'pcm')) { var pb = bbox(dBay, 'pcm'); labAt(a, dBay, 'pcm', (pb[0] + pb[1]) / 2, (pb[2] + pb[3]) / 2, 'protection\nboard', pb[1] + 1, up - 0.4); }
        },
      });
      ctx.Drawing(dPl, 'dw-battery-plan', {
        label: 'Plan of the bay at the cell mid-thickness',
        annotate: function (a0, d) {
          var a = fitA(a0, d);
          lab(a, dPl, 'cell', xm, ym, '503035 cell', 20, 20);
          lab(a, dPl, 'lid', xm, (BB.lip.y[0] + BB.lip.y[1]) / 2, 'lip', 20, -20, { hot: true });
          lab(a, dPl, 'lid', BB.pocket[0] + 3, BB.end_stop.y, 'end stop', -30, 22);
          var jb = bbox(dPl, 'j5') || bbox(dPl, 'j5_beyond');
          if (jb) lab(a, dPl, layerOf(dPl, 'j5') ? 'j5' : 'j5_beyond', (jb[0] + jb[1]) / 2, (jb[2] + jb[3]) / 2, 'J5', 16, 22);
          var lb = bbox(dPl, 'leads') || bbox(dPl, 'leads_beyond');
          if (lb) lab(a, dPl, layerOf(dPl, 'leads') ? 'leads' : 'leads_beyond', (lb[0] + lb[1]) / 2, lb[3], 'lead to J5', 30, 18);
        },
      });
      var LD = B.lead || {};
      var ex = LD.length_by_exit_position_mm || {};
      var exv = Object.keys(ex).map(function (k) { return ex[k]; });
      ctx.q('#battery-lead').innerHTML = 'It leaves the middle of the pack&rsquo;s top edge, U-turns up over that edge (' + f(LD.min_bend_r, 2) + ' mm bend radius) and crosses to the midplate&rsquo;s bare back above J5, where one strip of tape holds it; from there it runs along the midplate and past the board&rsquo;s round corner into the plug. Any spare coils flat in a well beside the tape. ' +
        f(LD.routed_length_mm, 1) + ' mm of wire from a centre exit' + (exv.length === 3 ? ', ' + f(exv[2], 1) + ' mm if the lead leaves near the right-hand end (toward J5) and ' + f(exv[0], 1) + ' from the left' : '') +
        '. These packs ship with about 50 mm of lead: coil the spare in the well, do not wedge it under the pack.';
      var cellsT = [
        ['503035 behind the board (this)', B.capacity_mAh + ' mAh', f(D.meta.body[2], 1) + ' mm deep, ' + f(D.meta.body[1], 0) + ' tall', 'fits as sold; its lead end is next to J5', true],
        ['503035 beside the board, top left (the 4.26&Prime;&rsquo;s layout)', '500 mAh', '10.3 deep, 123 tall', 'nothing under it, so only J5 sets the depth; lead 17 mm'],
        ['Liter 402050 (20 &times; 50 &times; 3.65) beside the board, across the top', '500 mAh', '10.3 deep, 118 tall', 'a 25 mm lead; over the ESP32 instead it is 12.8 mm'],
        ['LP203180 (2.0 &times; 31 &times; 80) over the ESP32', '800 mAh', '&asymp;10.7 deep, 107 tall', 'battery makers only; one listing gives 3.2 mm with its protection board, which would make it 11.9'],
      ];
      ctx.q('#battery-cells tbody').innerHTML = cellsT.map(function (r) {
        return '<tr' + (r[4] ? ' class="pick"' : '') + '><td>' + r[0] + '</td><td>' + r[1] + '</td><td>' + r[2] + '</td><td><small>' + r[3] + '</small></td></tr>';
      }).join('');
      var ref = B.ref || {};
      nums = [
        row('Cell', B.capacity_mAh + ' mAh', SC.esc(SC.text(ref.name || '503035')) + (ref.size ? ' &middot; ' + ref.size.map(function (v) { return f(v, 2); }).join(' &times; ') + ' mm' : '')),
        row('Allowance', f(B.envelope_mm, 2) + ' mm', 'a 5.3 mm cell with two layers of tape on each face &middot; ' + f(B.air_under_j7_mm, 2) + ' mm of air under J7'),
        row('Pocket', B.pocket_mm.map(function (v) { return f(v, 1); }).join(' &times; ') + ' mm', 'sunk ' + f(B.floor_t, 1) + ' mm into the lid&rsquo;s floor'),
        row('Hold-down', 'lip ' + f(R.lip_over_mm, 1) + ' mm', 'tape on the cell; the lid presses nothing'),
        row('Lead', f(LD.routed_length_mm, 1) + ' mm', 'pack edge to plug, centre exit'),
        row('Antenna', f(B.antenna_gap_mm, 2) + ' mm', 'from the cell&rsquo;s corner to the antenna end: check Wi-Fi range'),
      ];
    }
    ctx.q('#battery-nums').innerHTML = nums.join('');
  },
});
