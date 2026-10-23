// Edges and logo: cards.edges.{edges, logo, logo_back, grip_grooves?}. The back icon is stored in the CAD frame (seen
// from the front) and is flipped here to show it as seen from behind.
SC.card({
  id: 'edges', title: 'Edges and logo', order: 110, preset: 'edges',
  needs: ['cards.edges.edges', 'cards.edges.logo.polys', 'cards.edges.logo_back.polys'],
  render: function (D, ctx) {
    var f = function (x, n) { return SC.fmt(x, n == null ? 2 : n); };
    var fill = function (cls, html) { ctx.qa('.' + cls).forEach(function (e) { e.innerHTML = html; }); };
    var E = D.cards.edges, EG = E.edges, L = E.logo, LB = E.logo_back, pad = 0.4;
    var words = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
    var nl = Math.round(EG.front_r / 0.2);
    fill('ed-layers', words[nl] || String(nl));
    var lw = L.width || (L.bounds[2] - L.bounds[0]);
    fill('ed-logo-w', f(lw, 0));
    fill('ed-logo-d', L.depth ? ', engraved ' + f(L.depth, 1) + ' mm deep' : '');
    fill('ed-seam', EG.seam_chamfer ? 'V ' + f(EG.seam_chamfer, 1) : 'square');
    var onBack = L.on === 'back';
    fill('ed-back-d', LB.depth ? ', engraved ' + f(LB.depth, 1) + ' mm deep' : '');
    fill('ed-land', EG.window_land ? ' on a ' + f(EG.window_land, 1) + ' mm land' : '');
    // the 3.68 adapter also gives the bevel's angle and its corners (at the screen, on the face); square corners: none
    var WR = EG.window_corner_r;
    fill('ed-deg', EG.window_bevel_deg ? ' at ' + f(EG.window_bevel_deg, 0) + '&deg;' : '');
    fill('ed-corners', WR && WR[0] ? ', round at the corners (R' + f(WR[0], 1) + ' at the screen, R' + f(WR[1], 1) + ' on the face)' : '');
    var G = E.grip_grooves;
    fill('ed-grooves', G ? ' Along the bottom edge of the back, ' + G.y.length + ' grip grooves, ' + f(G.width, 1) + ' mm wide and ' + f(G.depth, 1) + ' mm deep, run from x ' + f(G.x[0], 0) + ' to ' + f(G.x[1], 0) + '.' : '');
    var b = L.bounds, host = ctx.q('#edges-logo');
    host.innerHTML = '';
    var svg = SC.svg('svg', { viewBox: (b[0] - pad) + ' ' + (-(b[3] + pad)) + ' ' + (b[2] - b[0] + 2 * pad) + ' ' + (b[3] - b[1] + 2 * pad), role: 'img', 'aria-label': 'The silkscreen wordmark as engraved in the back, above the grip grooves, seen from behind' }, host);
    SC.svg('path', { d: SC.dPath(L.polys), 'fill-rule': 'evenodd' }, svg);
    var bb = LB.bounds, hb = ctx.q('#edges-back');
    hb.innerHTML = '';
    var sb = SC.svg('svg', { viewBox: (-bb[2] - pad) + ' ' + (-(bb[3] + pad)) + ' ' + (bb[2] - bb[0] + 2 * pad) + ' ' + (bb[3] - bb[1] + 2 * pad), role: 'img', 'aria-label': 'The book icon on the back, seen from behind' }, hb);
    SC.svg('path', { d: SC.dPath(LB.polys), 'fill-rule': 'evenodd', transform: 'scale(-1 1)' }, sb);
    var row = function (t, v, s) { return '<div><dt>' + t + '</dt><dd>' + v + '<small>' + s + '</small></dd></div>'; };
    var nums = [
      row('Front edges', 'R' + f(EG.front_r, 1), nl + ' layers of 0.2 mm'),
      row('Back edges', 'R' + f(EG.back_r, 1), 'where the hand holds it'),
      EG.seam_chamfer ? row('Parting line', 'V ' + f(EG.seam_chamfer, 1), 'a chamfer on each half') : row('Parting line', 'square', 'no chamfer on either half'),
      EG.window_bevel_deg ? row('Screen window', f(EG.window_bevel, 1) + ' mm', f(EG.window_bevel_deg, 0) + '&deg; bevel' +
        (WR && WR[0] ? ', corners R' + f(WR[0], 1) + ' to R' + f(WR[1], 1) : ', square corners')) : null,
      D.meta.bottom_keys && D.meta.bottom_keys.length ? row('Key openings', f(EG.key_chamfer, 1) + ' mm', 'chamfer') : null,   // none: chinless
      row('Wordmark', f(lw, 0) + ' mm', (L.depth ? f(L.depth, 1) + ' mm deep, ' : '') + (onBack ? 'on the back, above the grip grooves' : 'in the chin')),
      row('Book icon', f(LB.width, 0) + ' mm', LB.depth ? f(LB.depth, 1) + ' mm deep, on the back' : 'on the back'),
    ];
    if (G) nums.push(row('Grip grooves', String(G.y.length), f(G.width, 1) + ' &times; ' + f(G.depth, 1) + ' mm, along the bottom of the back'));
    ctx.q('#edges-nums').innerHTML = nums.filter(Boolean).join('');
  },
});
