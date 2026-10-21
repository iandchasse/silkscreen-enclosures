// Assembly order: the build's steps (D.assembly), what you need (meta.printed + facts), and the stage in sync.
// The stage's Play assembly (and its explode slider) emit 'step' k = the index in D.explode.order of the group that
// is arriving; walk() maps each k to a run of assembly items that contain that group, in order, so the list marks
// the step on the stage. A tap on an item puts the stage at that step (explode) or runs the item's preset.
SC.card({
  id: 'assembly', title: 'Assembly order', order: 120, preset: 'assembly',
  needs: ['assembly', 'explode.order', 'explode.steps', 'meta.printed.parts'],

  // item runs per explode index: runs[k] = [item indexes], plus the items before the first run and after the last
  walk: function (D) {
    var A = D.assembly || [], order = (D.explode && D.explode.order) || [];
    var has = function (i, g) { return A[i] && (A[i].groups || []).indexOf(g) >= 0; };
    var runs = [], cur = 0;
    order.forEach(function (g) {
      var i = cur;
      while (i < A.length && !has(i, g)) i++;
      if (i >= A.length) { runs.push([]); return; }           // a group no item names: nothing to mark
      var run = [];
      for (var j = i; j < A.length && has(j, g); j++) run.push(j);
      runs.push(run);
      cur = i;
    });
    var all = [].concat.apply([], runs);
    var first = all.length ? Math.min.apply(null, all) : A.length, last = all.length ? Math.max.apply(null, all) : -1;
    // the explode index a tap on item i shows: the last group of its runs, unless the next item shares that group
    var kOf = A.map(function (a, i) {
      var ks = [], ksNext = [];
      runs.forEach(function (r, k) { if (r.indexOf(i) >= 0) { ks.push(k); if (r.indexOf(i + 1) >= 0) ksNext.push(k); } });
      if (!ks.length) return null;
      var own = ks.filter(function (k) { return ksNext.indexOf(k) < 0; });
      return Math.max.apply(null, own.length ? own : ks);
    });
    return { runs: runs, first: first, last: last, kOf: kOf, n: order.length };
  },

  render: function (D, ctx) {
    var self = SC.cards().assembly;
    var A = D.assembly || [], W = self.walk(D), order = D.explode.order;
    var fact = function (id) { return (D.facts || []).filter(function (f) { return f.id === id; })[0] || null; };
    var MF = ctx.manifest || SC.manifest;

    // ---- refs and the screw count in the thesis ----
    var refs = ctx.q('#assembly-refs');
    var P = (D.meta.printed && D.meta.printed.parts) || [];
    var chips = D.meta.bottom_keys && !D.meta.bottom_keys.length ? ['tub', 'midplate', 'PCBA', 'lid']   // chinless
      : ['tub', 'keys &times;4', 'cranks &times;4', 'rod', 'gate', 'midplate', 'PCBA', 'lid'];
    if (SC.buildIs('ls', ctx.build)) chips.splice(1, 0, 'light strip');
    if ((D.explode.order || []).indexOf('battery') >= 0) chips.splice(chips.indexOf('PCBA') + 1, 0, 'battery');
    refs.innerHTML = chips.map(function (c) { return '<span class="ref">' + c + '</span>'; }).join('');
    var hw = fact('hardware'), m = hw && /^(\d+)\s*x\s*(M[\d.]+)\s*x\s*(\d+)/.exec(SC.text(String(hw.value)));
    var words = ['no', 'one', 'two', 'three', 'four', 'five', 'six'];
    if (m) ctx.q('#assembly-screws').innerHTML = (words[+m[1]] || m[1]) + ' ' + m[2] + '&times;' + m[3] + ' screws';

    // ---- what you need ----
    var v = ctx.variant || SC.state.variant;
    var need = ctx.q('#assembly-need'), rows = [];
    var row = function (dt, dd, small) { rows.push('<div><dt>' + dt + '</dt><dd>' + dd + (small ? '<small>' + small + '</small>' : '') + '</dd></div>'); };
    var fp = fact('printed'), fpl = fact('plastic');
    if (fp) row(SC.esc(SC.text(fp.label)), fp.value, fpl ? SC.esc(SC.text(String(fpl.value))) + (fpl.unit ? '&thinsp;' + String(fpl.unit).replace(/^(c?m|mm)([23])$/, function (m0, u, e) { return u + (e === '2' ? '&sup2;' : '&sup3;'); }) : '') + (fpl.note ? ', ' + fpl.note : '') : fp.note);
    ['panel', 'battery', 'rod', 'hardware'].forEach(function (id) {
      var f = fact(id);
      if (f) row(SC.esc(SC.text(f.label)), f.value + (f.unit ? '&thinsp;' + f.unit : ''), f.note);
    });
    if (SC.buildIs('ls', ctx.build)) row('Light strip', 'Silkscreen light strip', 'on the panel&rsquo;s left border: <a href="#m=strip" data-goto="strip">the light-strip card</a> has every step');
    need.innerHTML = rows.join('');

    // ---- the print list (this build, this switch variant) ----
    var pr = ctx.q('#assembly-print');
    var crankFile = function (p) {
      var f = p.file || '';
      if (/crank/i.test(p.name) || /crank-[TM]/.test(f)) {
        if (p.alt && v === 'M' && /crank-T/.test(f)) return p.alt;
        return f.replace(/crank-[TM]/, 'crank-' + v);
      }
      return f;
    };
    var trs = P.map(function (p) {
      var isCrank = /crank/i.test(p.name) || /crank-[TM]/.test(p.file || '');
      var name = isCrank ? 'crank-' + v : SC.text(p.name);
      var sub = isCrank ? SC.esc(SC.text((MF.variants && MF.variants[v]) || '')) : (p.note ? SC.esc(SC.text(p.note)) : '');
      return '<tr><td class="n">' + p.count + ' &times;</td><td>' + SC.esc(name) + (sub ? '<small>' + sub + '</small>' : '') +
        '</td><td><code>' + SC.esc(crankFile(p)) + '</code></td></tr>';
    });
    pr.innerHTML = '<div class="tbl-wrap"><table><thead><tr><th></th><th>Print for the ' + SC.esc(MF.builds[ctx.build].label.toLowerCase()) +
      ' build</th><th>File</th></tr></thead><tbody>' + trs.join('') + '</tbody></table></div>';
    self._pr = pr;

    // ---- the steps ----
    var ol = ctx.q('#assembly-steps');
    ol.innerHTML = '';
    var lis = A.map(function (a, i) {
      var li = document.createElement('li');
      li.setAttribute('data-step', String(i));
      li.setAttribute('tabindex', '0');
      li.id = 'assembly-step-' + a.id;
      if (i < W.first) li.classList.add('prep');
      var meta = [];
      if (i < W.first) meta.push('<span class="as-when">before you start</span>');
      else if (i > W.last) meta.push('<span class="as-when">closed up</span>');
      if (W.kOf[i] != null) meta.push('<span class="as-3d">3D step ' + (W.kOf[i] + 1) + ' of ' + W.n + '</span>');
      (a.groups || []).forEach(function (g) { meta.push('<span>' + SC.esc(g) + '</span>'); });
      li.innerHTML = '<div><span class="as-text"><b>' + a.title + '.</b> ' + a.text + '</span><span class="as-meta">' + meta.join('') + '</span></div>';
      ol.appendChild(li);
      return li;
    });
    self._lis = lis;

    // mark the items of explode step k (-1 = assembled, n = play finished)
    var mark = function (k, src) {
      var now = [];
      if (k >= 0 && k < W.n) now = W.runs[k] || [];
      else if (k >= W.n) for (var i = W.last + 1; i < A.length; i++) now.push(i);
      var lo = now.length ? Math.min.apply(null, now) : (k >= W.n ? A.length : -1);
      lis.forEach(function (li, i) {
        li.classList.toggle('now', now.indexOf(i) >= 0);
        li.classList.toggle('done', k !== -1 && i < lo && now.indexOf(i) < 0);
      });
      self._now = { k: k, items: now.map(function (i) { return A[i].id; }), src: src || 'stage' };
    };
    self._mark = mark;
    ctx.on('step', function (k) { mark(k, 'stage'); });

    // a tap: the stage at that step
    var groupParts = function (groups) {
      var V = SC.viewer;
      if (!V || !V.nodes) return [];
      return V.nodes().filter(function (n) { var p = V.part(n); return p && groups.indexOf(p.group) >= 0; });
    };
    var go = function (i) {
      var a = A[i], k = W.kOf[i], V = SC.viewer;
      SC.open('assembly');
      if (V && k != null) {
        SC.emit('focus', 'assembly');
        V.explode(Math.min(1, Math.max(0, 1 - (k - 0.02) / Math.max(1, W.n - 1))));
        var hp = groupParts(a.groups || [order[k]]);
        if (hp.length && V.highlight) V.highlight(hp);
        if (V.caption) V.caption('<b>' + a.title + '.</b> ' + a.text, 'Assembly ' + (i + 1) + ' of ' + A.length);
      } else if (a.preset && D.presets[a.preset]) {
        SC.emit('focus', a.preset);
        if (V && V.caption) V.caption('<b>' + a.title + '.</b> ' + a.text, 'Assembly ' + (i + 1) + ' of ' + A.length);
      }
      lis.forEach(function (li, j) { li.classList.toggle('now', j === i); li.classList.toggle('done', j < i); });
      self._now = { k: k == null ? null : k, items: [a.id], src: 'tap' };
      if (SC.viewer && typeof matchMedia === 'function' && matchMedia('(max-width: 1180px)').matches) {
        var vp = document.getElementById('viewport');
        if (vp) vp.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
      }
    };
    lis.forEach(function (li, i) {
      li.addEventListener('click', function () { go(i); });
      li.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(i); } });
    });
    ctx.q('#assembly-play').onclick = function () { SC.open('assembly'); };   // static: onclick, not a listener per render
    mark(-1);
  },

  // the crank row follows the switch selector
  onVariant: function (v, D, ctx) {
    var self = SC.cards().assembly;
    if (!self._pr) return;
    var MF = ctx.manifest || SC.manifest;
    self._pr.querySelectorAll('tbody tr').forEach(function (tr, i) {
      var p = D.meta.printed.parts[i];
      if (!p || !(/crank/i.test(p.name) || /crank-[TM]/.test(p.file || ''))) return;
      var f = (p.alt && v === 'M' && /crank-T/.test(p.file)) ? p.alt : String(p.file).replace(/crank-[TM]/, 'crank-' + v);
      tr.children[1].innerHTML = SC.esc('crank-' + v) + '<small>' + SC.esc(SC.text((MF.variants && MF.variants[v]) || '')) + '</small>';
      tr.children[2].innerHTML = '<code>' + SC.esc(f) + '</code>';
    });
  },

  // for tests: the marked items and the step on the stage
  now: function () { return SC.cards().assembly._now || null; },
});
