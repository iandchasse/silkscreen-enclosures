// What's been checked: D.checks plus the bottom keys' own D.keys.checks (the 4.26 lists them in both; ids dedupe),
// grouped by the report they come from. No prose: labels, values, details and sources are the projects' own.
SC.card({
  id: 'checks', title: "What's been checked", order: 130, preset: null,
  needs: ['checks', 'cards.checks.measure'],

  GROUPS: [
    { id: 'keys', title: 'Bottom keys', test: function (c) { return !/side_key/.test((c.source || '') + ' ' + c.id) && /bottom-keys|crank\.json|key_forces|key_drag|key_hooks|key_fit|key_overpress|key_sweep|key_preload|crank_stress|rod_gate|gate\.checks/.test(c.source || '') || /^(bk\d|bottom_keys|crank_|rod_path|key_in|x_gaps|logo|mech_key|mech_crank|mech_gate|gate_|rod_gate)/.test(c.id); } },
    { id: 'strip', title: 'Light strip', test: function (c) { return /strip/i.test(c.id) || /light-strip\.json|_strip|_across|interference\.json strip/.test(c.source || ''); } },
    { id: 'fit', title: 'Interference', test: function (c) { return /^interference/.test(c.source || '') || /^interference|^display_vs_board/.test(c.id); } },
    { id: 'paths', title: 'Assembly paths', test: function (c) { return /insertion/.test(c.source || '') || /^insertion|^later_moves/.test(c.id); } },
    { id: 'side', title: 'Side keys', test: function (c) { return /side_key/.test(c.source || '') || /^side_key/.test(c.id); } },
    { id: 'snaps', title: 'Snaps and detents', test: function (c) { return /latches|board_snap|mid_detents/.test(c.source || ''); } },
    { id: 'print', title: 'Printing', test: function (c) { return /slice|print-report/.test(c.source || '') || /^slic|^print_/.test(c.id); } },
    { id: 'dummy', title: 'PCBA dummy', test: function (c) { return /pcba-dummy/.test(c.source || '') || c.id === 'dummy'; } },
    { id: 'chin', title: 'Chinless case', test: function (c) { return /chin\.json/.test(c.source || ''); } },
    { id: 'other', title: 'Other', test: function () { return true; } },
  ],
  STATUS: {
    expected: 'a designed contact on the project&rsquo;s list of expected overlaps',
    designed: 'a designed contact (a preload or a seat) that the list does not name',
    accepted: 'a finding the design accepts, with the reason in its detail',
  },

  // one list: D.checks, then the keys' checks that D.checks does not already hold
  list: function (D) {
    var seen = {}, out = [];
    (D.checks || []).concat((D.keys && D.keys.checks) || []).forEach(function (c) {
      if (!c || seen[c.id]) return;
      seen[c.id] = 1; out.push(c);
    });
    return out;
  },

  // a value or detail as text: numbers through SC.fmt, JSON strings parsed, lists and objects spelled out
  pretty: function (v, top) {
    var self = SC.cards().checks;
    if (v == null) return '';
    if (typeof v === 'number') return SC.fmt(v);
    if (typeof v === 'boolean') return v ? 'yes' : 'no';
    if (typeof v === 'string') {
      var s = v.trim();
      if (top !== false && /^[\[{]/.test(s)) { try { return self.pretty(JSON.parse(s), false); } catch (e) { /* plain text */ } }
      return s.replace(/<(?![a-zA-Z\/!])/g, '&lt;');
    }
    if (Array.isArray(v)) {
      if (!v.length) return 'none';
      if (v.length === 2 && typeof v[0] === 'string' && typeof v[1] === 'number') return self.pretty(v[0], false) + ': ' + SC.fmt(v[1]);
      var sep = v.some(function (x) { return x && typeof x === 'object'; }) ? '; ' : ', ';
      return v.map(function (x) { return self.pretty(x, false); }).join(sep);
    }
    var ks = Object.keys(v);
    if (!ks.length) return 'none';
    return ks.map(function (k) {
      var x = v[k], t = x && typeof x === 'object' ? self.pretty(x, false) : self.pretty(x, false);
      return SC.esc(k.replace(/_/g, ' ')) + ' ' + t;
    }).join('; ');
  },

  render: function (D, ctx) {
    var self = SC.cards().checks, MF = ctx.manifest || SC.manifest;
    var all = self.list(D);
    var groups = self.GROUPS.map(function (g) { return { g: g, items: [] }; });
    all.forEach(function (c) {
      for (var i = 0; i < groups.length; i++) if (groups[i].g.test(c)) { groups[i].items.push(c); return; }
    });
    groups = groups.filter(function (x) { return x.items.length; });
    var count = function (items, f) { return items.filter(f).length; };
    var nOk = count(all, function (c) { return c.ok === true; }), nBad = count(all, function (c) { return c.ok === false; });
    var nSkip = all.length - nOk - nBad;
    var sizeL = SC.text(MF.sizes[ctx.size].label), buildL = MF.builds[ctx.build].label.toLowerCase();
    var srcs = {};
    all.forEach(function (c) { if (c.source) srcs[String(c.source).split(/[ ,]/)[0]] = 1; });

    // cross-check with the adapter's own count
    var cc = D.cards && D.cards.checks;
    if (cc && typeof cc.count === 'number' && cc.count !== all.length)
      console.warn('[card checks] ' + all.length + ' checks listed, cards.checks.count says ' + cc.count);

    ctx.q('#checks-refs').innerHTML = '<span class="ref">' + SC.esc(sizeL) + '</span><span class="ref">' + SC.esc(MF.builds[ctx.build].label) +
      '</span><span class="ref">' + all.length + ' checks</span><span class="ref">' + Object.keys(srcs).length + ' reports</span>';
    var verdict = nBad ? '<strong>' + nBad + ' fail</strong>' + (nSkip ? ', ' + nSkip + ' not run' : '') :
      nSkip ? 'all that ran pass; ' + nSkip + ' not run' : 'all pass';
    ctx.q('#checks-thesis').innerHTML = all.length + ' checks on the ' + SC.esc(sizeL) + ' ' + SC.esc(buildL) +
      ' build, straight from the case project&rsquo;s reports: ' + verdict + '.';

    var stCount = function (items) {
      var n = {};
      items.forEach(function (c) { if (c.status) n[c.status] = (n[c.status] || 0) + 1; });
      return Object.keys(n).map(function (k) { return n[k] + ' ' + k; }).join(', ');
    };

    // the lists
    var host = ctx.q('#checks-groups');
    host.innerHTML = '';
    groups.forEach(function (x) {
      var d = document.createElement('details');
      d.setAttribute('data-group', x.g.id);
      var bad = count(x.items, function (c) { return c.ok === false; });
      if (bad) d.open = true;
      var rows = x.items.map(function (c) {
        var cls = c.ok === true ? '' : c.ok === false ? 'bad' : 'skip';
        var mark = c.ok === true ? '&#x2713;' : c.ok === false ? '&#x2717;' : '&ndash;';
        var val = c.value != null && c.value !== '' ? self.pretty(c.value) : '';
        var det = c.detail != null && c.detail !== '' ? self.pretty(c.detail) : '';
        return '<li class="' + cls + '" data-check="' + SC.esc(c.id) + '"><i aria-label="' + (c.ok === true ? 'pass' : c.ok === false ? 'fail' : 'not run') + '">' + mark + '</i><div>' +
          '<span class="lbl">' + self.pretty(c.label, false) + '</span>' + (val ? '<span class="val">' + val + '</span>' : '') +
          (c.status ? '<span class="st ' + SC.esc(c.status) + '">' + SC.esc(c.status) + '</span>' : '') +
          (det ? '<span class="det">' + det + '</span>' : '') +
          (c.source ? '<span class="src">' + SC.esc(c.source) + '</span>' : '') + '</div></li>';
      });
      var okN = count(x.items, function (c) { return c.ok === true; }), skip = x.items.length - okN - bad, st = stCount(x.items);
      d.className = bad ? 'fail' : skip ? 'warn' : '';
      d.innerHTML = '<summary><b>' + x.g.title + '</b><em>' + okN + '/' + x.items.length + '</em><span>' +
        (bad ? bad + ' of ' + x.items.length + ' fail' : skip ? okN + ' pass, ' + skip + ' not run' : x.items.length === 1 ? 'passes' : 'all ' + x.items.length + ' pass') +
        (st ? '; ' + st : '') + '</span></summary><ul class="chk">' + rows.join('') + '</ul>';
      host.appendChild(d);
    });

    // the status legend, for the statuses this build uses
    var used = {};
    all.forEach(function (c) { if (c.status) used[c.status] = 1; });
    ctx.q('#checks-legend').innerHTML = Object.keys(self.STATUS).filter(function (k) { return used[k]; }).map(function (k) {
      return '<span><span class="st ' + k + '">' + k + '</span>' + self.STATUS[k] + '</span>';
    }).join('');

    // Rev K's "Measure before printing", this size and build's own (cards.checks.measure: HTML from the adapter)
    var ms = (cc && cc.measure) || [];
    ctx.q('#checks-measure-wrap').hidden = !ms.length;
    ctx.q('#checks-measure').innerHTML = ms.map(function (h) { return '<li>' + h + '</li>'; }).join('');
    self._summary = { total: all.length, ok: nOk, bad: nBad, skip: nSkip, groups: groups.map(function (x) { return [x.g.id, x.items.length]; }), count: cc ? cc.count : null, measure: ms.length };
  },

  // for tests
  summary: function () { return SC.cards().checks._summary || null; },
});
