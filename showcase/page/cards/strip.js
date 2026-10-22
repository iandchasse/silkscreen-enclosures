// The light-strip card: install steps that drive the stage through SC.strip3d (fold, tape, Kapton, light) and
// SC.viewer (camera, section, chips), the strip's section drawings, the tape flat pattern and table, the optics
// image, the parts, the standard-vs-light-strip table (from the manifest) and the strip's checks.
// It sits right after the bottom-keys card; opening it on the standard or chinless build switches to the light-strip
// build (the shell does that, with a toast and Undo, because CARDS gives it enter_build 'ls'); on the light-strip
// chinless build (CARDS home_builds) it works in place, with that build's steps (no SW9 lead, no bottom keys).
var STRIP = { idx: 0, pendingScroll: false, tok: 0, caseOn: false, cutOn: false, extra: null, steps: [] };

function stripStacked() { return matchMedia('(max-width: 1180px)').matches; }
function stripNeed3d() {
  if (SC.strip3d) return Promise.resolve(SC.strip3d);
  return new Promise(function (res) { var off = SC.on('strip3d', function (a) { off(); res(a); }); });
}
function stripFirstPara(html) {
  var m = /<p>([\s\S]*?)<\/p>/.exec(html || '');
  var t = SC.text((m ? m[1] : html || '').replace(/<[^>]+>/g, ''));
  if (t.length > 190) { var cut = t.lastIndexOf('. ', 190); t = cut > 60 ? t.slice(0, cut + 1) : t.slice(0, 187) + '...'; }
  return SC.esc(t);
}

// ---- stage: one step ----
function stripNeutralLook(V) {
  // clear another card's focus / highlight without moving the camera: run the plain 'home' preset, put the view back
  var c = V.camera.position.clone(), t = V.controls.target.clone(), u = V.camera.up.clone();
  V.preset('home', { animate: false });
  V.camera.position.copy(c); V.controls.target.copy(t); V.camera.up.copy(u); V.camera.lookAt(t);
}
function stripCam(V, cam) {
  // the steps' cameras were set for a wide view (about 1.6:1), Y up: back off for a narrow stage
  // (the far views frame the whole reader, which is taller than wide, so they fit a tall stage as they are)
  var el = V.renderer.domElement, aspect = el.clientWidth / Math.max(1, el.clientHeight);
  var p = cam[0], t = cam[1];
  var dist = Math.hypot(p[0] - t[0], p[1] - t[1], p[2] - t[2]);
  var k = dist > 100 ? 1 : Math.max(1, Math.min(1.8, 1.2 / Math.max(0.3, aspect)));
  // Y up (the board runs up the screen), as the light-strip page had it; a view along Y (the cuts across the bar)
  // takes Z up instead, so the face is on top and the roll is not left to a near-parallel up vector
  var d = [t[0] - p[0], t[1] - p[1], t[2] - p[2]], L = Math.hypot(d[0], d[1], d[2]) || 1;
  var up = Math.abs(d[1] / L) > 0.8 ? [0, 0, 1] : [0, 1, 0];
  V.tween([t[0] + (p[0] - t[0]) * k, t[1] + (p[1] - t[1]) * k, t[2] + (p[2] - t[2]) * k], t, up);
}
function stripApplyCase(V) {
  if (STRIP.caseOn) V.setVisible(null);
  else V.setVisible(['strip', 'display', 'pcba']);
}
function stripApplyCut(V, S3) {
  var s = STRIP.steps[STRIP.idx] || {};
  if (!STRIP.cutOn) { V.section('off'); return; }
  if (s.cutX != null) V.section('x', s.cutX, true);
  else V.section('y', s.cutY != null ? s.cutY : S3.ledY('D4'), true);
}
function stripGoStep(i, opt) {
  opt = opt || {};
  var n = STRIP.steps.length;
  if (!n) return;
  STRIP.idx = Math.max(0, Math.min(n - 1, i));
  stripMarkSteps();
  var V = SC.viewer, S3 = SC.strip3d, s = STRIP.steps[STRIP.idx];
  if (!V || !S3 || SC.state.card !== 'strip' || !SC.buildIs('ls')) return;
  stripNeutralLook(V);
  STRIP.caseOn = !!s.caseOn; STRIP.cutOn = !!s.cut;
  stripApplyCase(V);
  stripApplyCut(V, S3);
  S3.fold(s.f == null ? 1 : s.f);
  S3.tape(!!s.tape);
  S3.kapton(!!s.kapton || !!s.tape);
  stripCam(V, s.cam);
  V.caption('<b>' + (STRIP.idx + 1) + '. ' + SC.esc(SC.text(s.t)) + '.</b> ' + stripFirstPara(s.b), 'Light strip \u00b7 step ' + (STRIP.idx + 1) + ' of ' + n);
  stripSyncExtra();
  if (opt.scroll && stripStacked()) document.getElementById('viewport').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
}
function stripMarkSteps() {
  var ol = document.getElementById('strip-steps');
  if (!ol) return;
  Array.prototype.forEach.call(ol.children, function (li, k) {
    li.classList.toggle('now', k === STRIP.idx);
    li.setAttribute('aria-current', k === STRIP.idx ? 'step' : 'false');
  });
}

// ---- stage: the controls under the model while the card is open (SC.viewer.extraSlot()) ----
function stripMountExtra(ctx) {
  var V = SC.viewer;
  if (!V || !V.extraSlot) return;
  stripUnmountExtra();
  var slot = V.extraSlot();
  var box = document.createElement('div');
  box.setAttribute('data-strip-extra', '');
  box.style.cssText = 'display:grid;gap:8px;border-top:1px solid var(--rule);padding-top:10px';
  box.innerHTML =
    '<div style="display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center">' +
      '<span class="lab" style="font:500 11px/1.2 var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-2)">Light strip</span>' +
      '<button type="button" class="btn ghost" data-sx="prev" aria-label="Previous step">&larr;</button>' +
      '<span data-sx="label" style="font:500 12.5px/1.3 var(--f-mono);min-width:0;flex:1 1 12em"></span>' +
      '<button type="button" class="btn ghost" data-sx="next" aria-label="Next step">&rarr;</button>' +
    '</div>' +
    '<div class="ctl"><label for="strip-x-fold">Fold <output id="strip-x-fold-out">fitted</output></label>' +
      '<input type="range" id="strip-x-fold" min="0" max="1" step="0.001" value="1" aria-label="Fold progress, flat to fitted"></div>' +
    '<div class="render-row" role="group" aria-label="Light strip view">' +
      '<span class="lab">Show</span>' +
      '<button type="button" class="chip" data-sx="case" aria-pressed="false" title="The case parts around the strip">Case</button>' +
      '<button type="button" class="chip" data-sx="cut" aria-pressed="false" title="Cut through LED D4, or the step\'s own cut">Cut</button>' +
      '<button type="button" class="chip" data-sx="tape" aria-pressed="false" title="The factory tape and the Kapton you add">Tape</button>' +
      '<button type="button" class="chip" data-sx="light" aria-pressed="false" title="Light one string and paint it on the page">Light</button>' +
    '</div>';
  slot.appendChild(box);
  slot.hidden = false;
  STRIP.extra = box;
  var q = function (k) { return box.querySelector('[data-sx="' + k + '"]'); };
  var fold = box.querySelector('#strip-x-fold');
  fold.addEventListener('input', function () { if (SC.strip3d) SC.strip3d.fold(+fold.value, { animate: false }); });
  q('prev').addEventListener('click', function () { stripGoStep(STRIP.idx - 1); });
  q('next').addEventListener('click', function () { stripGoStep(STRIP.idx + 1); });
  q('case').addEventListener('click', function () {
    STRIP.caseOn = !STRIP.caseOn;
    if (!STRIP.caseOn && STRIP.cutOn) { STRIP.cutOn = false; stripApplyCut(SC.viewer, SC.strip3d); }
    stripApplyCase(SC.viewer); stripSyncExtra();
  });
  q('cut').addEventListener('click', function () {
    STRIP.cutOn = !STRIP.cutOn;
    if (STRIP.cutOn && !STRIP.caseOn) { STRIP.caseOn = true; stripApplyCase(SC.viewer); }
    stripApplyCut(SC.viewer, SC.strip3d); stripSyncExtra();
  });
  q('tape').addEventListener('click', function () {
    var S3 = SC.strip3d; if (!S3) return;
    var on = !S3.tape(); S3.tape(on); S3.kapton(on || !!(STRIP.steps[STRIP.idx] || {}).kapton);
  });
  q('light').addEventListener('click', function () {
    var S3 = SC.strip3d; if (!S3) return;
    var m = S3.light();
    S3.light(m === 'off' ? 'warm' : m === 'warm' ? 'cool' : 'off');
  });
  ctx.on('stripfold', function (e) {
    if (document.activeElement !== fold) fold.value = e.fold;
    var o = box.querySelector('#strip-x-fold-out');
    o.textContent = e.fold >= 0.999 ? 'fitted' : e.fold <= 0.001 ? 'flat' : Math.round(e.fold * 100) + '%';
  });
  ctx.on('stripset', stripSyncExtra);
  stripSyncExtra();
}
function stripSyncExtra() {
  var box = STRIP.extra, S3 = SC.strip3d;
  if (!box) return;
  var q = function (k) { return box.querySelector('[data-sx="' + k + '"]'); };
  var s = STRIP.steps[STRIP.idx];
  q('label').textContent = s ? (STRIP.idx + 1) + ' / ' + STRIP.steps.length + '  ' + SC.text(s.t) : '';
  q('prev').disabled = STRIP.idx <= 0;
  q('next').disabled = STRIP.idx >= STRIP.steps.length - 1;
  q('case').setAttribute('aria-pressed', String(STRIP.caseOn));
  q('cut').setAttribute('aria-pressed', String(STRIP.cutOn));
  if (S3) {
    q('tape').setAttribute('aria-pressed', String(S3.tape()));
    var m = S3.light();
    q('light').setAttribute('aria-pressed', String(m !== 'off'));
    q('light').textContent = m === 'off' ? 'Light' : 'Light: ' + m;
    var f = S3.foldNow(), fold = box.querySelector('#strip-x-fold');
    if (document.activeElement !== fold) fold.value = f;
  }
}
function stripUnmountExtra() {
  var V = SC.viewer;
  if (STRIP.extra && STRIP.extra.parentNode) STRIP.extra.parentNode.removeChild(STRIP.extra);
  STRIP.extra = null;
  if (V && V.extraSlot) { var slot = V.extraSlot(); if (slot && !slot.children.length) slot.hidden = true; }
}

// ---- the card's page content ----
function stripLayerBox(dr, id) {
  var L = (dr.layers || []).filter(function (l) { return l.id === id; })[0];
  if (!L) return null;
  var b = [1e9, -1e9, 1e9, -1e9];
  L.polys.forEach(function (poly) { poly.forEach(function (ring) { ring.forEach(function (p) {
    b[0] = Math.min(b[0], p[0]); b[1] = Math.max(b[1], p[0]); b[2] = Math.min(b[2], p[1]); b[3] = Math.max(b[3], p[1]);
  }); }); });
  return b[0] > b[1] ? null : b;
}
var STRIP_DWG = {
  strip_led: function (dr, g) {
    return 'Through LED ' + ((dr.notes && (dr.notes.led || dr.notes.ref)) || 'D4') + ' at Y ' + SC.fmt(dr.at, 2) + '. The light-strip tub raises the ceiling over the left border to Z ' +
      SC.fmt(g.ceiling, 2) + ', so the LED tops (' + SC.fmt(g.led_top, 3) + ') clear it, and the light passes under the skin to the window.';
  },
  strip_holddown: function (dr) { return 'Between two pairs, at Y ' + SC.fmt(dr.at, 2) + ': a hold-down pad in the tub presses the bar onto the plain panel.'; },
  strip_fold: function (dr) { return 'Through the folded top pair, at Y ' + SC.fmt(dr.at, 2) + ': it lies under the bar with its LEDs facing the back, where the tub\u2019s frame is cut away and the midplate is notched.'; },
  strip_neck: function (dr) { return 'Along the neck, at X ' + SC.fmt(dr.at, 2) + ': over the bottom glass edge, down the board\u2019s slot and onto the back to the frontlight connector.'; },
};
var STRIP_DWG_ORDER = ['strip_led', 'strip_holddown', 'strip_fold', 'strip_neck'];
function stripAnnotate(dr, g) {
  return function (A) {
    var lab = function (id, text, fu, fv, dx, dy) {
      var b = stripLayerBox(dr, id);
      if (b) A.label(b[0] + (b[1] - b[0]) * fu, b[2] + (b[3] - b[2]) * fv, text, dx, dy, { fit: true });   // fit: the 3.68 neck ran off the right edge
    };
    if (dr.name === 'strip_led' || dr.name === 'strip_fold') {
      var led = stripLayerBox(dr, 'led');
      if (led && g && g.ceiling != null) {
        var u = (led[0] + led[1]) / 2;
        A.dim(u, led[3], u, g.ceiling, SC.fmt(g.ceiling - led[3], 3), -26, true);
      }
      lab('led', 'LED', 0.95, 0.75, 34, 26);
      lab('strip', 'flex bar', 0.05, 0.5, -30, -22);
    }
    if (dr.name === 'strip_fold') lab('folded', 'folded pair', 0.05, 0.5, -30, -30);
    if (dr.name === 'strip_holddown') lab('strip', 'bar under the pad', 0.95, 0.8, 40, 30);
    if (dr.name === 'strip_neck') {
      lab(dr.layers.some(function (l) { return l.id === 'neck'; }) ? 'neck' : 'tail', 'neck', 0.5, 0.9, 30, 24);
      lab('pcb', 'board', 0.3, 0.5, 24, -26);
    }
  };
}
function stripDrawFlat(svg, G) {
  var NS = 'http://www.w3.org/2000/svg';
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  var y0 = 38.0, sx = 9.6, cx = 43.0;
  var P = function (x, y) { return [20 + (y - y0) * sx, 60 + (x - cx) * sx]; };
  var el = function (n, a) { var e = document.createElementNS(NS, n); for (var k in a) e.setAttribute(k, a[k]); svg.appendChild(e); return e; };
  var poly = function (pts, a) { var o = { points: pts.map(function (p) { return P(p[0], p[1]).join(','); }).join(' ') }; for (var k in a) o[k] = a[k]; return el('polygon', o); };
  var defs = el('defs', {});
  defs.innerHTML = '<pattern id="strip-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2.2" height="6" fill="var(--ink-3)"/></pattern>';
  var H0 = G.hinge_y[0], H1 = G.hinge_y[1];
  poly(G.outline, { fill: '#131514', stroke: 'var(--ink-3)', 'stroke-width': 1 });
  G.front_pieces.forEach(function (p) { poly(p, { fill: 'none', stroke: 'var(--tape)', 'stroke-width': 3, 'stroke-dasharray': '7 4' }); });
  G.front_pieces.concat([G.back_stiffener]).forEach(function (p) { poly(p, { fill: 'var(--pi)', opacity: 0.45 }); });
  poly([[43.0, H0], [45.3, H0], [45.3, H1], [43.0, H1]], { fill: 'url(#strip-hatch)', opacity: 0.9 });
  poly([[52.487, 140.7], [58.0, 140.7], [58.0, 152.3], [52.487, 152.3]], { fill: 'url(#strip-hatch)', opacity: 0.7 });
  G.leds.forEach(function (d) {
    var a = P(44.2 - 0.4, d.y - 2.0), b = P(44.2 + 1.0, d.y + 2.0);
    el('rect', { x: a[0], y: a[1], width: b[0] - a[0], height: b[1] - a[1], fill: d.colour === 'warm' ? 'var(--warm)' : 'var(--cool)', rx: 2 });
  });
  G.tps.forEach(function (d) { var a = P(d.x, d.y); el('circle', { cx: a[0], cy: a[1], r: 3.8, fill: 'var(--gold)' }); });
  G.fingers.forEach(function (fx) { var a = P(fx - 0.15, G.tip_y - 2.0), b = P(fx + 0.15, G.tip_y - 0.2); el('rect', { x: a[0], y: a[1], width: b[0] - a[0], height: b[1] - a[1], fill: 'var(--gold)' }); });
  var label = function (x, y, lx, ly, text, col) {
    var a = P(x, y);
    el('line', { x1: a[0], y1: a[1], x2: lx, y2: ly, stroke: col || 'var(--ink-3)', 'stroke-width': 1 });
    var t = el('text', { x: lx, y: ly + (ly < a[1] ? -4 : 14), fill: 'var(--ink-2)', 'font-size': 13, 'text-anchor': 'middle' });
    t.textContent = text;
  };
  label(44.0, (H0 + H1) / 2, P(0, (H0 + H1) / 2)[0], 22, 'hinge: keep free (3.68\u2033 folds here)', 'var(--ink-3)');
  label(44.2, 47.15, P(0, 44)[0], 22, 'top pair', 'var(--ink-3)');
  label(44.0, 90, P(0, 90)[0], 22, 'bar: 3M 9077 + PI on the back', 'var(--tape)');
  label(50.0, 137.2, P(0, 128)[0], 212, 'foot', 'var(--ink-3)');
  label(55.2, 146.5, P(0, 146.5)[0], 22, 'bend zone: keep free', 'var(--ink-3)');
  label(55.2, 158.0, P(0, 159)[0], 212, 'diodes + S/C/W pads (PI behind)', 'var(--ink-3)');
  label(54.2, 165.6, P(0, 165)[0], 22, 'contacts into the frontlight connector', 'var(--gold)');
}
var STRIP_TAPE = [
  ['<span class="tag tape">3M 9077</span>factory', 'Back of the top-pair piece and of the bar + foot',
   '4.26&Prime;: holds the strip on the panel border. 3.68&Prime;: holds the folded pair to the bar (tape to tape) and the foot to the panel; the rest of the bar&rsquo;s liner stays on'],
  ['<span class="tag kapton">Kapton</span>you add', 'Both edges of the board&rsquo;s FPC slot, where the neck passes', 'Routed FR4 edges would scuff the neck'],
  ['<span class="tag kapton">Kapton</span>you add', 'The Back key&rsquo;s (SW9&rsquo;s) left lug lead (4.26&Prime;, trimmed flush first) or pin (3.68&Prime;), just below the slot', 'The neck&rsquo;s U or loop passes within 0.1 mm of it'],
  ['<span class="tag kapton">Kapton</span>you add', 'A strap across the stiffened back run, onto the board&rsquo;s back', 'The frontlight connector holds only about 3 N; the tape takes any pull'],
  ['<span class="tag free">none</span>', 'The hinge and the bend zone', 'They have to bend freely; tape or stiffener there would crack the copper'],
];
// standard vs light strip, from the manifest: a part differs when one of its nodes is in parts[S].per_build
function stripDiffRows(D, S) {
  var MF = SC.manifest, per = (MF.parts[S] && MF.parts[S].per_build) || [], shared = (MF.parts[S] && MF.parts[S].shared) || [];
  var sz = MF.sizes[S] || {}, dn = sz.display_nodes || { std: [], ls: [] };
  var diff = SC.get(D, 'cards.strip.diff') || [];
  var textFor = function (re) { var r = diff.filter(function (x) { return re.test(SC.text(x.part)); })[0]; return r || null; };
  var anyIn = function (list, re) { return list.some(function (n) { return re.test(n); }); };
  var displayDiffers = dn.std.join(' ') !== dn.ls.join(' ');
  var keyless = !(D.meta.bottom_keys && D.meta.bottom_keys.length);   // the light-strip chinless: no keys or cranks
  var rows = [
    { part: 'Tub (front shell)', own: anyIn(per, /^tub$/), row: textFor(/^Tub/) },
    { part: 'Bottom keys', own: anyIn(per, /^key_SW/), row: textFor(/^Bottom keys/) },
    { part: 'Lid, midplate', own: anyIn(per, /^(lid|lid_body|midplate)$/), row: textFor(/^Lid/), shared: anyIn(shared, /^(lid|lid_body|midplate)$/) },
    { part: 'Cranks, rod, gate', own: anyIn(per, /^crank/), row: textFor(/^Cranks/), shared: anyIn(shared, /^crank/) },
    { part: 'Side keys (in the lid)', own: anyIn(per, /^skey_/), row: null, shared: anyIn(shared, /^skey_/) },
    { part: 'Panel (not printed)', own: displayDiffers, row: textFor(/^Panel/), panel: sz.panel },
  ].filter(function (r) { return !(keyless && /^(Bottom keys|Cranks)/.test(r.part)); });
  var bad = [];
  rows.forEach(function (r) {
    if (r.row && typeof r.row.same === 'boolean' && r.row.same === r.own) bad.push(r.part);
  });
  return { rows: rows, bad: bad, per: per };
}
function stripRowsTable(title, rows, unitNote) {
  var keys = [];
  Object.keys(rows).forEach(function (k) { Object.keys(rows[k]).forEach(function (c) { if (keys.indexOf(c) < 0 && typeof rows[k][c] === 'number') keys.push(c); }); });
  var head = '<tr><th>Case</th>' + keys.map(function (k) { return '<th>' + SC.esc(k.replace(/_/g, ' ')) + '</th>'; }).join('') + '</tr>';
  var body = Object.keys(rows).map(function (k) {
    return '<tr><td>' + SC.esc(k.replace(/_/g, ' ')) + '</td>' + keys.map(function (c) {
      var v = rows[k][c]; return '<td class="num">' + (typeof v === 'number' ? SC.fmt(v) : '') + '</td>';
    }).join('') + '</tr>';
  }).join('');
  return '<details><summary>' + SC.esc(title) + '</summary>' + (unitNote ? '<p class="body" style="font-size:13.5px">' + unitNote + '</p>' : '') +
    '<div class="tbl-wrap"><table class="forces"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div></details>';
}

SC.card({
  id: 'strip',
  title: 'Light strip',
  order: 25,
  preset: 'strip',
  enter_build: 'ls',
  needs: ['cards.strip.steps', 'cards.strip.case_cards', 'cards.strip.diff', 'cards.strip.geometry', 'cards.strip.checks'],
  render: function (D, ctx) {
    var S = ctx.size, C = D.cards.strip, g = C.geometry || {};
    STRIP.steps = C.steps || [];
    if (STRIP.idx >= STRIP.steps.length) STRIP.idx = 0;

    // steps
    var ol = ctx.q('#strip-steps');
    ol.innerHTML = '';
    STRIP.steps.forEach(function (s, i) {
      var li = document.createElement('li');
      li.tabIndex = 0;
      var more = s.drawing ? ' <a href="#strip-dw-' + s.drawing + '" data-strip-dwg="' + s.drawing + '">See the section.</a>' : '';
      li.innerHTML = '<div><b>' + s.t + '</b><div class="strip-b">' + s.b + (more ? '<p>' + more + '</p>' : '') + '</div></div>';
      var pick = function (e) {
        if (e.target.closest && e.target.closest('a')) {
          var dw = e.target.closest('a').getAttribute('data-strip-dwg');
          if (dw) { e.preventDefault(); var f = document.getElementById('strip-dw-' + dw); if (f) f.scrollIntoView({ block: 'center' }); }
          return;
        }
        STRIP.idx = i;
        if (SC.state.card === 'strip') stripGoStep(i, { scroll: true });
        else { STRIP.pendingScroll = true; stripMarkSteps(); }
      };
      li.addEventListener('click', pick);
      li.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); STRIP.idx = i; SC.open('strip').then(function () { stripGoStep(i, { scroll: true }); }); } });
      ol.appendChild(li);
    });
    stripMarkSteps();
    var nav = function (id, d) {
      ctx.q(id).onclick = function () {
        var i = d === 0 ? STRIP.idx : STRIP.idx + d;
        if (SC.state.card === 'strip') stripGoStep(i, { scroll: d === 0 });
        else { STRIP.idx = Math.max(0, Math.min(STRIP.steps.length - 1, i)); STRIP.pendingScroll = d === 0; }
      };
    };
    nav('#strip-show', 0); nav('#strip-prev', -1); nav('#strip-next', 1);

    // section drawings
    var host = ctx.q('#strip-dwgs');
    host.innerHTML = '';
    STRIP_DWG_ORDER.forEach(function (name) {
      var dr = SC.drawing(name);
      if (!dr) return;
      var fig = document.createElement('figure');
      fig.id = 'strip-dw-' + name;
      fig.innerHTML = '<div class="dwg-host"></div><figcaption></figcaption>';
      host.appendChild(fig);
      ctx.Drawing(dr, fig.firstChild, { label: STRIP_DWG[name] ? SC.text(STRIP_DWG[name](dr, g)) : name, annotate: stripAnnotate(dr, g) });
      fig.lastChild.textContent = STRIP_DWG[name] ? SC.text(STRIP_DWG[name](dr, g)) : name;
    });

    // tape: flat pattern (strip.json, shared with strip3d.js through SC.load's cache) and table
    var svg = ctx.q('#strip-flat');
    SC.load((SC.manifest.assets && SC.manifest.assets.strip) || 'strip.json').then(function (G) {
      if (document.body.contains(svg)) stripDrawFlat(svg, G);
    }).catch(function (e) { console.error('[card strip] strip.json', e); });
    var noSW9 = !(D.meta.bottom_keys && D.meta.bottom_keys.length);  // a chinless board has no SW9 lead to cover
    ctx.q('#strip-tape').innerHTML = STRIP_TAPE.filter(function (r) { return !(noSW9 && /SW9/.test(r[1])); })
      .map(function (r) { return '<tr><td>' + r[0] + '</td><td>' + r[1] + '</td><td>' + r[2] + '</td></tr>'; }).join('');

    // light
    var img = ctx.q('#strip-optics'), of = (SC.manifest.assets && SC.manifest.assets.optics) || 'optics_heatmaps.png';
    var info = SC.manifest.files[of];
    var src = of + (info && info.sha1 ? '?v=' + info.sha1.slice(0, 10) : '');
    if (img.getAttribute('src') !== src) img.setAttribute('src', src);
    ctx.q('#strip-light').onclick = function () {
      SC.open('strip').then(function () {
        var S3 = SC.strip3d;
        if (!S3) return;
        var m = S3.light();
        S3.light(m === 'off' ? 'warm' : m === 'warm' ? 'cool' : 'off');
        if (stripStacked()) document.getElementById('viewport').scrollIntoView({ block: 'start' });
      });
    };

    // the case: this size's bullets, then standard vs light strip from the manifest
    var cc = (C.case_cards || []).map(function (c) {
      return '<h4>' + c.h + '</h4><ul>' + c.items.map(function (i) { return '<li>' + i + '</li>'; }).join('') + '</ul>';
    }).join('');
    ctx.q('#strip-casecard').innerHTML = cc;
    var DR = stripDiffRows(D, S);
    ctx.q('#strip-diff tbody').innerHTML = DR.rows.map(function (r) {
      var what = r.row ? r.row.text : r.panel ? SC.esc(SC.text(r.panel.std)) + ' / ' + SC.esc(SC.text(r.panel.ls)) : 'Shared';
      var files = r.row && r.row.std && r.row.ls && r.row.std !== r.row.ls ? ' <code>' + SC.esc(r.row.std) + '</code> / <code>' + SC.esc(r.row.ls) + '</code>' : '';
      return '<tr><td>' + r.part + '</td><td class="' + (r.own ? 'strip-own' : 'strip-same') + '">' + (r.own ? 'own per build' : 'shared') + '</td><td>' + what + files + '</td></tr>';
    }).join('');
    if (DR.bad.length) console.warn('[card strip] the data\u2019s build-diff rows disagree with manifest.parts for ' + DR.bad.join(', '));
    ctx.q('#strip-diff-note').innerHTML = C.diff_note ? C.diff_note    // the light-strip chinless: against the chinless build
      : 'Printed per build on the ' + SC.esc(SC.text(SC.manifest.sizes[S].label)) + ': <code>' +
      DR.per.map(SC.esc).join('</code> <code>') + '</code> (' + SC.esc(SC.manifest.sizes[S].build_diff) + '). Every other printed part is the same file in both builds; the download zip holds both sets.';

    // checks: the strip's own rows from the top-level checks, then this size's tables
    var items = (D.checks || []).filter(function (c) { return /^strip/.test(c.id); });
    ctx.q('#strip-checks tbody').innerHTML = items.map(function (c) {
      var res = c.ok === false ? '<span class="strip-bad">fails</span>' : c.ok == null ? 'not run' : '<span class="strip-ok">ok</span>';
      var det = c.detail ? SC.esc(SC.text(c.detail)) : '';
      return '<tr><td>' + SC.esc(SC.text(c.label).replace(/^Light strip: /, '')) + '</td><td>' + res + (det ? '<br><small>' + det + '</small>' : '') + '</td></tr>';
    }).join('') || '<tr><td colspan="2">No strip checks in this data.</td></tr>';
    var K = C.checks || {}, t = '';
    if (K.plain_stack && K.plain_stack.rows) t += stripRowsTable('Plain panel on its ' + (K.plain_stack.springs || '') + ' springs, by panel thickness', K.plain_stack.rows, 'Stops at Z ' + SC.fmt(K.plain_stack.stop_face_z) + '; travel limit ' + SC.fmt(K.plain_stack.travel_limit_mm) + ' mm.');
    if (K.foot_stop && K.foot_stop.rows) t += stripRowsTable('Foot under the corner stop, by panel and stack', K.foot_stop.rows, 'Roof at Z ' + SC.fmt(K.foot_stop.roof_z) + ', foot top ' + SC.fmt(K.foot_stop.foot_top_z) + '; deflection within the ' + SC.fmt(K.foot_stop.travel_limit_mm) + ' mm travel: ' + (K.foot_stop.within_travel ? 'yes' : 'no') + '.');
    if (K.seat_entry && K.seat_entry.rows) t += stripRowsTable('Bar entering the seat (mm clear)', K.seat_entry.rows, 'Worst ' + SC.fmt(K.seat_entry.worst_mm) + ' mm; all clear: ' + (K.seat_entry.all_clear ? 'yes' : 'no') + '.');
    if (K.channel_skin && K.channel_skin.cases) t += stripRowsTable('Skin over the LEDs under a press (mm)', K.channel_skin.cases, 'LED clearance ' + SC.fmt(K.channel_skin.led_clearance_mm) + ' mm; nominal margin ' + SC.fmt(K.channel_skin.margin_mm_nominal_case) + ' mm.');
    if (K.tail) {
      var tl = {}; tl[K.tail.case || 'nominal'] = K.tail;
      t += stripRowsTable('The tail round the glass edge (mm)', tl, '');
    }
    ctx.q('#strip-tables').innerHTML = t;
  },
  onEnter: function (D, ctx) {
    // the stage may not exist yet (three.js still loading) or may be mid-mount (a size switch re-enters the card
    // before the new meshes are in): go now, and again whenever the viewer reports a finished state
    var tok = ++STRIP.tok;
    var scroll = STRIP.pendingScroll; STRIP.pendingScroll = false;
    var go = function (sc) {
      if (tok !== STRIP.tok || SC.state.card !== 'strip') return;
      if (!STRIP.extra) stripMountExtra(ctx);
      stripNeed3d().then(function (S3) { return S3.sync(); }).then(function () {
        if (tok !== STRIP.tok || SC.state.card !== 'strip') return;
        stripGoStep(STRIP.idx, { scroll: sc });
      }).catch(function (e) { SC.cardError('strip', e); });
    };
    go(scroll);
    ctx.on('state', function () { go(false); });
    ctx.on('viewer', function () { go(false); });
  },
  onLeave: function () {
    STRIP.tok++;
    // a size switch re-enters the card and keeps its step; leaving for another card (or closing) starts over at 1
    setTimeout(function () { if (SC.state.card !== 'strip') STRIP.idx = 0; }, 0);
    stripUnmountExtra();
    var V = SC.viewer, S3 = SC.strip3d;
    if (S3) S3.reset();
    if (V) {
      if (!STRIP.caseOn) V.setVisible(null);
      if (STRIP.cutOn) V.section('off');
    }
    STRIP.caseOn = false; STRIP.cutOn = false;
  },
});
