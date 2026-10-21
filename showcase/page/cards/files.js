// Model files: one zip per size (models-S.js, loaded on the first download), everything / this build / one group.
// Names come from data.downloads.zip, sizes from the manifest (sizes.S.zip_bytes, files[models-S.js].bytes) and the
// groups' own file bytes. Saving goes through the host's downloads capability when there is one, and otherwise
// through a plain browser download (SC.dl.api()); if neither is possible the buttons stay off and say why.
SC.card({
  id: 'files', title: 'Model files', order: 140, preset: 'dummy',
  needs: ['downloads.zip', 'downloads.groups', 'downloads.readme', 'cards.files.dummy'],

  mb: function (n) { return n >= 1e6 ? SC.fmt(n / 1e6, 1) + '&nbsp;MB' : Math.max(1, Math.round(n / 1e3)) + '&nbsp;kB'; },

  // the entry paths of a download: 'all', 'build' (this build's files + the shared ones) or a group id
  paths: function (D, which, build) {
    var dl = D.downloads, out = [];
    if (which === 'all') return null;
    dl.groups.forEach(function (g) {
      if (which !== 'build' && g.id !== which) return;
      g.files.forEach(function (f) {
        if (which !== 'build') { out.push(f.path); return; }
        // this build's files and the shared ones it uses (skip_builds: the chinless case has its own lid, no keys or rod)
        if ((!f.builds || f.builds.indexOf(build) >= 0) && !(f.skip_builds && f.skip_builds.indexOf(build) >= 0)) out.push(f.path);
      });
    });
    if (dl.readme) out.push(dl.readme);
    return out;
  },
  // one name per distinct download (sc_contract.download_names): everything base.zip, a build base-<dir>.zip, a
  // group base-<dir or id>-only.zip, so the standard group (its own files only) never takes the standard build's name
  zipName: function (D, which, build) {
    var base = String(D.downloads.zip).replace(/\.zip$/i, ''), B = SC.manifest.builds;
    if (which === 'all') return base + '.zip';
    if (which === 'build') return base + '-' + ((B[build] && B[build].dir) || build) + '.zip';
    return base + '-' + ((B[which] && B[which].dir) || which) + '-only.zip';
  },
  // {name, blob, paths} for a download, without saving it (the files card's buttons and the tests use this)
  pack: function (which, D, build) {
    var self = SC.cards().files;
    D = D || SC.data; build = build || SC.state.build;
    var paths = self.paths(D, which, build), name = self.zipName(D, which, build);
    return SC.dl.zip(D.size).then(function (all) {
      var blob = paths ? SC.dl.subset(all, new Set(paths)) : new Blob([all], { type: 'application/zip' });
      return { name: name, blob: blob, paths: paths, zipBytes: all.length };
    });
  },

  render: function (D, ctx) {
    var self = SC.cards().files, MF = ctx.manifest || SC.manifest, dl = D.downloads, S = ctx.size, B = ctx.build;
    var mb = self.mb, fmt = SC.fmt;
    var jsName = (MF.load[S] && MF.load[S].models) || dl.file;
    var jsBytes = MF.files[jsName] ? MF.files[jsName].bytes : dl.js_bytes;
    var zipBytes = (MF.sizes[S] && MF.sizes[S].zip_bytes) || dl.zip_bytes;
    var sizeL = SC.text(MF.sizes[S].label), buildL = MF.builds[B].label.toLowerCase();
    var exts = {};
    dl.groups.forEach(function (g) { g.files.forEach(function (f) { var m = /\.(\w+)$/.exec(f.path); if (m) exts[m[1].toUpperCase()] = 1; }); });
    ctx.q('#files-refs').innerHTML = ['STL', 'STEP', '3MF'].filter(function (e) { return exts[e]; }).concat(['README']).map(function (e) {
      return '<span class="ref">' + e + '</span>';
    }).join('');

    var status = ctx.q('#files-status'), bAll = ctx.q('#files-all'), bBuild = ctx.q('#files-build');
    bAll.innerHTML = 'Download everything (.zip, ' + mb(zipBytes) + ')';
    var buildPaths = self.paths(D, 'build', B), buildRaw = 0;
    dl.groups.forEach(function (g) { g.files.forEach(function (f) { if (buildPaths.indexOf(f.path) >= 0) buildRaw += f.bytes; }); });
    bBuild.innerHTML = 'Only the ' + SC.esc(buildL) + ' build (.zip)';
    bBuild.title = 'The shared parts it uses and the ' + buildL + ' build\u2019s own files, ' + SC.text(mb(buildRaw)) + ' unzipped';

    // the groups
    var list = ctx.q('#files-list');
    list.innerHTML = '';
    var buttons = [bAll, bBuild];
    dl.groups.forEach(function (g) {
      var mine = g.files.filter(function (f) { return !f.builds || f.builds.indexOf(B) >= 0; });
      var allOther = !mine.length;
      var raw = g.files.reduce(function (s, f) { return s + f.bytes; }, 0);
      var tag = '';
      if (g.files.every(function (f) { return f.builds; })) {
        // a build's group: every file this build's, or none of them (the chinless lid is listed for both chinless
        // builds, so on the light-strip chinless the chinless group is mixed: its files say which is which)
        if (mine.length === g.files.length) tag = '<span class="tag">this build</span>';
        else if (allOther) tag = '<span class="tag other">other build</span>';
      }
      var names = g.files.map(function (f) {
        var nm = SC.esc(f.path.split('/').pop()) + ' (' + mb(f.bytes) + ')';
        var other = f.builds && f.builds.indexOf(B) < 0;
        return other && !allOther ? '<span class="other">' + nm + ', ' + SC.esc(f.builds.map(function (b) { return MF.builds[b].label.toLowerCase(); }).join(', ')) + ' build</span>' : nm;
      }).join(' &middot; ');
      var row = document.createElement('div');
      row.className = 'dl-row' + (allOther ? ' other' : '');
      row.setAttribute('data-group', g.id);
      row.innerHTML = '<div><b>' + g.label + '</b>' + tag + '<p>' + g.what + '</p><p class="files">' + names + '</p><p class="sum">' +
        g.files.length + ' file' + (g.files.length === 1 ? '' : 's') + ', ' + mb(raw) + ' unzipped</p></div>';
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'btn ghost'; b.disabled = true; b.textContent = 'Download';
      b.setAttribute('aria-label', 'Download ' + SC.text(g.label));
      b.addEventListener('click', function () { save(g.id); });
      row.appendChild(b); list.appendChild(row); buttons.push(b);
    });

    // text from the data
    var F = D.cards.files || {}, dm = F.dummy || {};
    ctx.q('#files-orient').innerHTML = 'The <strong>STL</strong> files are in print orientation, ready to slice. The <strong>STEP</strong> files are in the case&rsquo;s CAD frame (the board&rsquo;s coordinates), so they drop into CAD next to the board&rsquo;s own STEP.' +
      (exts['3MF'] ? ' The coupons come as <strong>3MF</strong>.' : '') + ' ' + (F.plate ? SC.esc(SC.text(F.plate)) : '') +
      ' Every zip has a <code>' + SC.esc(dl.readme) + '</code> that says what goes with what.';
    var pp = ctx.q('#files-print');
    pp.hidden = !F.print;
    if (F.print) pp.innerHTML = '<strong>Printing.</strong> ' + F.print;
    var sites = dm.open_sites ? Object.keys(dm.open_sites) : [];
    var real = dm.checks && dm.checks.real_switch_in_site ? dm.checks.real_switch_in_site : {};
    var realClear = Object.keys(real).length && Object.keys(real).every(function (k) { return +real[k] === 0; });
    var touch = [];
    if (dm.checks && dm.checks.case) Object.keys(dm.checks.case).forEach(function (k) {
      var v = dm.checks.case[k], mm3 = v && typeof v === 'object' ? v.mm3 : v;
      if (mm3 > 0) touch.push('the ' + SC.esc(k.replace(/_/g, ' ')) + ' (' + fmt(mm3, 2) + '&nbsp;mm&sup3;)');
    });
    ctx.q('#files-dummy').innerHTML = '<strong>The PCBA dummy</strong> is for trying the case before the real board goes in: ' +
      (dm.components_kept != null ? dm.components_kept + ' components' : 'the components') + ' as solid hulls fused to a ' + fmt(dm.board_t || 1.6, 1) +
      '&nbsp;mm board, legs trimmed flush' + (dm.size_mm ? ', ' + dm.size_mm.map(function (x) { return fmt(x, 1); }).join(' &times; ') + '&nbsp;mm' : '') +
      (dm.volume_mm3 ? ', about ' + fmt(dm.volume_mm3 * 1.24e-3, 0) + '&nbsp;g of PLA' : '') + '. ' +
      (dm.watertight ? 'It is one closed solid' + (dm.triangles ? ' (' + dm.triangles + ' triangles)' : '') + '. ' : '') +
      (dm.holes_kept != null ? dm.holes_kept + ' holes are kept and ' + dm.holes_filled + ' filled; kept holes are drilled ' + fmt(dm.hole_comp, 1) + '&nbsp;mm oversize because printed holes shrink. ' : '') +
      (sites.length ? '<strong>Every switch site is open</strong> (' + SC.esc(sites.join(', ')) + '), each in low walls ' + fmt(dm.cradle ? dm.cradle.w : 0.8, 1) + '&nbsp;mm wide, so each key can be tried with a real switch' +
        (realClear ? ': in the model a real switch in each site touches nothing' : '') + '. ' : '') +
      (touch.length ? 'The dummy touches no printed part but ' + touch.join(', ') + ', the same designed contact as the real board. ' : '') +
      (dm.small_parts_left_out && dm.small_parts_left_out.length ? 'Left out of the dummy: ' + SC.esc(dm.small_parts_left_out.join(', ')) + '.' : '');
    var u = dm.usb_mock;
    ctx.q('#files-usb').innerHTML = u ? '<strong>J1 that prints.</strong> A real USB-C receptacle is ' + fmt(u.real_wall_mm, 1) + '&nbsp;mm of steel, thinner than a 0.4&nbsp;mm nozzle can lay, so the dummy&rsquo;s shell is ' +
      fmt(u.body_w, 2) + '&nbsp;mm wide with ' + fmt(u.side_wall_mm, 2) + '&nbsp;mm side walls. Its bore is ' + u.bore.map(function (x) { return fmt(x, 2); }).join(' &times; ') + '&nbsp;mm and ' +
      fmt(u.bore_depth_mm, 1) + '&nbsp;mm deep, ' + u.plug_clearance_mm.map(function (x) { return fmt(x, 2); }).join(' / ') + '&nbsp;mm a side round a plug at the spec&rsquo;s ' +
      fmt(u.spec_insertion_mm, 2) + '&nbsp;mm insertion, so a cable shows at once how far your plugs seat.' : '';

    // the other size
    var other = S === '426' ? '368' : '426';
    var oz = MF.sizes[other];
    ctx.q('#files-other').innerHTML = oz ? '<span>The ' + SC.esc(SC.text(oz.label)) + ' case has its own zip (<code>' + SC.esc(oz.zip) + '</code>, ' + mb(oz.zip_bytes) +
      ').</span><button type="button" class="btn ghost" id="files-other-go">Switch to the ' + SC.esc(SC.text(oz.label)) + '</button>' : '';
    var og = ctx.q('#files-other-go');
    if (og) og.addEventListener('click', function () { SC.set({ size: other }).then(function () { SC.open('files', { scroll: true }); }); });

    // saving
    var api = null, busy = false;
    var setStatus = function (html, err) { status.innerHTML = html; status.classList.toggle('err', !!err); };
    var save = function (which) {
      if (!api || busy) return;
      busy = true;
      var name = self.zipName(D, which, B);
      setStatus('Preparing ' + SC.esc(name) + (self._loaded && self._loaded[S] ? '' : ' (loading ' + mb(jsBytes) + ' once)') + '&hellip;');
      self.pack(which, D, B).then(function (p) {
        (self._loaded = self._loaded || {})[S] = true;
        return api.save({ filename: p.name, data: p.blob });
      }).then(function (r) {
        setStatus(r && r.status === 'delivered' ? 'Sent ' + SC.esc(name) + '.' : 'Saved ' + SC.esc(name) + '.');
      }).catch(function (e) {
        var code = e && e.code;
        setStatus(code === 'declined' ? 'Download cancelled.'
          : code === 'extension_not_enabled' ? 'Zip downloads are switched off in this view.'
          : code === 'rate_limited' ? 'A save prompt is already open; try again in a moment.'
          : e && e.message === 'load' ? 'The model files could not be loaded in this view.'
          : 'The download did not go through (' + SC.esc(code || (e && e.message) || 'unknown error') + ').', true);
      }).then(function () { busy = false; });
    };
    bAll.onclick = function () { save('all'); };             // static buttons: onclick, so a re-render replaces it
    bBuild.onclick = function () { save('build'); };
    var tok = self._tok = {};
    SC.dl.api().then(function (a) {
      if (self._tok !== tok) return;                        // a newer render owns the buttons
      api = a;
      if (api) {
        buttons.forEach(function (b) { b.disabled = false; });
        setStatus((api.plain ? 'Each download is saved by your browser. ' : 'Each download asks you to confirm before it saves. ')
          + 'The first one loads the ' + SC.esc(sizeL) + ' model file (' + mb(jsBytes) + ') once.');
      } else setStatus('Downloads are not available in this view. The part files are in the repository&rsquo;s print/ folder.');
    });
    self._info = { zip: dl.zip, zipBytes: zipBytes, jsName: jsName, jsBytes: jsBytes, buildPaths: buildPaths, groups: dl.groups.map(function (g) { return g.id; }) };
  },

  // for tests
  info: function () { return SC.cards().files._info || null; },
});
