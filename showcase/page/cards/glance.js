// At a glance: the size's bullets (cards.glance.bullets), a one-line summary from the facts, and what the two builds share.
SC.card({
  id: 'glance', title: 'At a glance', order: 10, preset: 'home',
  needs: ['cards.glance.bullets', 'facts', 'meta.printed.count'],
  render: function (D, ctx) {
    var fact = function (id) { return (D.facts || []).filter(function (f) { return f.id === id; })[0] || null; };
    var env = fact('envelope'), panel = fact('panel'), bat = fact('battery');
    var S = ctx.size, B = ctx.build, MF = ctx.manifest || {};
    var sizeLab = SC.text(D.meta.size_label || S), buildLab = SC.text(D.meta.build_label || B);
    var bits = [];
    if (env) bits.push(SC.esc(String(env.value).replace(/ x /g, ' \u00d7 ')) + (env.unit ? ' ' + SC.esc(env.unit) : ''));
    if (panel) bits.push(SC.esc(SC.text(panel.value)).replace(/ x /g, ' \u00d7 ') + ' panel');
    if (bat) bits.push(SC.esc(SC.text(bat.value)) + ' battery');
    ctx.q('#glance-thesis').innerHTML = 'The ' + SC.esc(sizeLab) + ' case, ' + SC.esc(buildLab.toLowerCase()) + ' build: ' + bits.join(', ') + '.';
    ctx.q('#glance-list').innerHTML = (D.cards.glance.bullets || []).map(function (b, i) {
      return '<li><span>' + (i + 1) + '</span><span>' + b + '</span></li>';
    }).join('');
    var sz = MF.sizes && MF.sizes[S];
    var diff = sz && sz.build_diff ? sz.build_diff : '';
    ctx.q('#glance-diff').textContent = diff || buildLab;
    var other = B === 'std' ? 'ls' : 'std', otherLab = MF.builds && MF.builds[other] ? MF.builds[other].label.toLowerCase() : other;
    var byB = sz && sz.build_diff_by && sz.build_diff_by[B];
    if (byB) {                                            // a chinless build: against the standard or light-strip build
      var nb = (sz.builds || []).length, words = { 3: 'Three', 4: 'Four', 5: 'Five' };
      ctx.q('#glance-diff').textContent = byB;
      ctx.q('#glance-builds').innerHTML = '<b>' + (words[nb] || 'Several') + ' builds of this size.</b> ' +
        (D.cards.glance.against || ('Against the standard build, the ' + SC.esc(byB) + '; the midplate, the side keys and the panel are the same, and the board leaves the four bottom-row buttons (SW9, SW8, SW3, SW2) off.')) +
        ' The size and build buttons above the 3D view switch the whole page; every card follows.';
      return;
    }
    ctx.q('#glance-builds').innerHTML = '<b>Two builds of this size.</b> Against the ' + SC.esc(otherLab) + ' build, ' +
      (diff ? 'the ' + SC.esc(diff.replace(/ differs?$/, '')) + ' ' + (/ differs$/.test(diff) ? 'differs' : 'differ') + '; everything else is the same part.' : 'the printed parts are shared.') +
      ' The size and build buttons above the 3D view switch the whole page; every card follows.';
  },
});
