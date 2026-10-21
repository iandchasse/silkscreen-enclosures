// The light strip in the main stage: the flex folded from strip.json, its PI stiffeners and 3M 9077 tape, the Kapton
// you add, the LEDs and the light they paint on the page. Ported from the light-strip page (docs/showcase/index.html at
// git HEAD: walk / place / triangulate / Sheet / buildKapton / refreshLight). It draws into SC.viewer.group('strip')
// (the light overlay into group('display')), so there is one WebGL context. API: SC.strip3d, see showcase/API.md.
const SC = window.SC;

function init(V) {
  if (!V || SC.strip3d) return;
  const THREE = V.THREE;
  const DEG = Math.PI / 180;
  const X0 = 44.237, Y0 = 148.25;             // strip.json is in KiCad mm; X = x - X0, Y = Y0 - y (the CAD frame)
  const TAPE = 0.05;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const dev = (x, y) => [x - X0, Y0 - y];

  let G = null;                                // strip.json
  let H = 0.055, T = 0.11, STIFF = 0.225, H0 = 0, H1 = 0, LED = null;
  const CASES = {};
  // the fold paths per reader (the light-strip page's CASES; tools/blender_fold.py): tail segments after the fold
  // line, the solve that stretches them so the contacts land in J3, and (3.68) the hinge folding the top pair back
  function makeCases() {
    CASES['426'] = {
      key: '426', panel: G.panel, active: G.active, thick: G.panel.thickness, foldY: G.fold_y, psEnd: G.panel.ps_bottom,
      zFront0: 3.0 + G.panel.thickness,
      path: [['line', 0.12], ['arc', 0.8 + H, 180], ['line', 0.38], ['arc', 0.8 + H, -90], ['line', 0.58], ['arc', 0.8 + H, 90], ['line', 60]],
      solve: { kind: 'legs', idx: [0, 2] }, hinge: null,
    };
    CASES['368'] = {
      key: '368', panel: G.panel_368, active: G.active_368, thick: G.panel_368.thickness, foldY: G.panel_368.bottom, psEnd: G.panel_368.ps_bottom,
      zFront0: 2.6 + G.panel_368.thickness,
      path: [['line', 1.0], ['arc', 0.65 + H, 180], ['line', 0.45], ['arc', 0.4 + H, -90], ['line', 0.74], ['arc', 0.8 + H, 90],
             ['arc', 0.6, -40], ['arc', 0.6, 80], ['arc', 0.6, -40], ['line', 60]],
      solve: { kind: 'bump', idx: [6, 7, 8] },
      hinge: [['line', 0.25], ['arc', 0.55, -180], ['arc', 1.5, -31.5], ['arc', 1.5, 31.5], ['line', 60]],
    };
    const TIP_TARGET_Y = Y0 - 125.0;
    for (const c of Object.values(CASES)) {
      setZ(c, c.zFront0);
      const base = c.solve.idx.map(i => c.path[i].slice());
      const apply = k => {
        if (c.solve.kind === 'legs') c.solve.idx.forEach((i, j) => { c.path[i] = ['line', base[j][1] + k / 2]; });
        else { const a = 5 + k; c.path[c.solve.idx[0]] = ['arc', base[0][1], -a]; c.path[c.solve.idx[1]] = ['arc', base[1][1], 2 * a]; c.path[c.solve.idx[2]] = ['arc', base[2][1], -a]; }
      };
      let lo = -0.3, hi = c.solve.kind === 'bump' ? 160 : 8, mid = 0;
      for (let n = 0; n < 60; n++) {
        mid = (lo + hi) / 2; apply(mid);
        const [y] = walk(c.path, G.tip_y - c.foldY, Y0 - c.foldY, c.zLedge, 180, null);
        if (y > TIP_TARGET_Y) lo = mid; else hi = mid;
      }
      apply(mid);
    }
  }
  function setZ(c, zFront) {
    c.zFront = zFront;
    c.zRear = zFront - c.thick;
    c.zFoot = c.zFront + TAPE + STIFF + H;
    c.zLedge = c.zRear + 0.5 + H;
  }

  function walk(path, s, y, z, ang, prog) {
    for (let i = 0; i < path.length; i++) {
      const seg = path[i];
      if (seg[0] === 'line') {
        const d = Math.min(s, seg[1]);
        y += d * Math.cos(ang * DEG); z += d * Math.sin(ang * DEG); s -= d;
      } else {
        const r = seg[1], sweep = seg[2] * (prog ? prog[i] : 1);
        if (Math.abs(sweep) < 1e-9) continue;
        const L = Math.abs(sweep * DEG) * r, d = Math.min(s, L), sg = sweep > 0 ? 1 : -1;
        const cy = y + r * Math.cos((ang + 90 * sg) * DEG), cz = z + r * Math.sin((ang + 90 * sg) * DEG);
        const a1 = ang - 90 * sg + (d / r) / DEG * sg;
        y = cy + r * Math.cos(a1 * DEG); z = cz + r * Math.sin(a1 * DEG);
        ang += (d / r) / DEG * sg; s -= d;
      }
      if (s <= 0) break;
    }
    return [y, z, ang];
  }
  // fitting progress 0..1 -> per-arc progress. Order: hinge (3.68), U round the glass edge, slot bend, back bend, loop
  function progFor(c, f) {
    const ease = (a, b) => Math.min(1, Math.max(0, (f - a) / (b - a)));
    const tail = c.path.map(() => 1), hinge = (c.hinge || []).map(() => ease(0.0, 0.25));
    const t0 = c.hinge ? 0.3 : 0.0;
    tail[1] = ease(t0, t0 + 0.3);
    tail[3] = ease(t0 + 0.3, t0 + 0.5);
    tail[5] = ease(t0 + 0.5, t0 + 0.68);
    for (const i of [6, 7, 8]) if (i < tail.length && c.path[i][0] === 'arc') tail[i] = ease(t0 + 0.6, 1.0);
    return { tail, hinge };
  }
  // a point of the flat pattern (KiCad x, y) -> [X, Y, Z, nx, ny, nz] in the case frame
  function place(c, st, x, y) {
    const X = x - X0;
    if (c.hinge && y < H1) {
      const [Y, Z, ang] = walk(c.hinge, H1 - y, Y0 - H1, c.zFoot, 0, st.hinge);
      return [X, Y, Z, 0, -Math.sin(ang * DEG), Math.cos(ang * DEG)];
    }
    if (y <= c.foldY) {
      let Z;
      if (y <= G.foot_b) Z = c.zFoot;
      else {
        const t = Math.min(1, (y - G.foot_b) / Math.max(0.6, c.psEnd - G.foot_b + 0.8));
        Z = c.zFoot + (c.zLedge - c.zFoot) * (0.5 - 0.5 * Math.cos(Math.PI * t));
      }
      return [X, Y0 - y, Z, 0, 0, 1];
    }
    const [Y, Z, ang] = walk(c.path, y - c.foldY, Y0 - c.foldY, c.zLedge, 180, st.tail);
    return [X, Y, Z, 0, Math.sin(ang * DEG), -Math.cos(ang * DEG)];
  }

  // ---- flat pattern -> bands -> triangles ----
  function clipBelow(poly, y0) {
    const out = [];
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i], b = poly[(i + 1) % poly.length], ia = a[1] >= y0, ib = b[1] >= y0;
      if (ia) out.push(a);
      if (ia !== ib) { const t = (y0 - a[1]) / (b[1] - a[1]); out.push([a[0] + t * (b[0] - a[0]), y0]); }
    }
    return out;
  }
  const clipAbove = (poly, y1) => clipBelow(poly.map(([x, y]) => [x, -y]), -y1).map(([x, y]) => [x, -y]);
  let CUTS = [];
  function cuts() {
    const s = new Set();
    const add = (a, b, step) => { for (let y = a; y <= b + 1e-9; y += step) s.add(Math.round(y * 1000) / 1000); };
    add(38.0, 170.0, 0.8);
    add(138.6, 141.8, 0.1);
    add(140.4, 153.6, 0.08);
    add(H0 - 0.5, H1 + 0.5, 0.06);
    [H0, H1, G.foot_b, G.fold_y, G.panel_368.bottom].forEach(v => s.add(v));
    return [...s].sort((a, b) => a - b);
  }
  function triangulate(poly) {
    const flat = [], idx = [];
    for (let k = 0; k + 1 < CUTS.length; k++) {
      let band = clipAbove(clipBelow(poly, CUTS[k]), CUTS[k + 1]);
      band = band.filter((p, i) => { const q = band[(i + 1) % band.length]; return Math.hypot(p[0] - q[0], p[1] - q[1]) > 1e-6; });
      if (band.length < 3) continue;
      const faces = THREE.ShapeUtils.triangulateShape(band.map(([x, y]) => new THREE.Vector2(x, y)), []);
      const base = flat.length / 2;
      band.forEach(([x, y]) => flat.push(x, y));
      faces.forEach(f => idx.push(base + f[0], base + f[1], base + f[2]));
    }
    return { flat: new Float32Array(flat), idx };
  }
  class Sheet {
    constructor(poly, offset, thick, mat) {
      const { flat, idx } = triangulate(poly);
      this.flat = flat; this.n = flat.length / 2; this.offset = offset; this.thick = thick;
      const all = idx.slice();
      for (let i = 0; i < idx.length; i += 3) all.push(idx[i] + this.n, idx[i + 2] + this.n, idx[i + 1] + this.n);
      this.geo = new THREE.BufferGeometry();
      this.pos = new Float32Array(this.n * 2 * 3);
      this.geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
      this.geo.setIndex(all);
      this.mesh = new THREE.Mesh(this.geo, mat);
    }
    update(c, st) {
      for (let i = 0; i < this.n; i++) {
        const p = place(c, st, this.flat[2 * i], this.flat[2 * i + 1]);
        for (const [layer, o] of [[0, this.offset + this.thick / 2], [1, this.offset - this.thick / 2]]) {
          const j = (i + layer * this.n) * 3;
          this.pos[j] = p[0] + p[3] * o; this.pos[j + 1] = p[1] + p[4] * o; this.pos[j + 2] = p[2] + p[5] * o;
        }
      }
      this.geo.attributes.position.needsUpdate = true;
      this.geo.computeVertexNormals();
      this.geo.computeBoundingBox();
      this.geo.computeBoundingSphere();
    }
  }

  // ---- materials: every one clips with the stage's section plane (the viewer re-applies it to live groups) ----
  const mats = [];
  const clipNow = () => { const p = V.clip(); return p ? [p] : []; };
  function mat(M) { M.clippingPlanes = clipNow(); M.clipShadows = true; mats.push(M); return M; }
  const M = {
    flex: mat(new THREE.MeshStandardMaterial({ color: 0x141615, roughness: 0.45, side: THREE.DoubleSide })),
    pi: mat(new THREE.MeshStandardMaterial({ color: 0xa8661b, roughness: 0.5, side: THREE.DoubleSide })),
    tape: mat(new THREE.MeshStandardMaterial({ color: 0xc2417a, roughness: 0.6, side: THREE.DoubleSide, transparent: true, opacity: 0.9 })),
    led: mat(new THREE.MeshStandardMaterial({ color: 0xf4f3ee, roughness: 0.35 })),
    gold: mat(new THREE.MeshStandardMaterial({ color: 0xcfa24a, roughness: 0.3, metalness: 1.0 })),
    sot: mat(new THREE.MeshStandardMaterial({ color: 0x3a3c3e, roughness: 0.4 })),
    kapton: mat(new THREE.MeshStandardMaterial({ color: 0xd99a24, roughness: 0.4, transparent: true, opacity: 0.8, side: THREE.DoubleSide })),
  };
  const lensMat = colour => mat(colour === 'warm'
    ? new THREE.MeshStandardMaterial({ color: 0xffc98a, emissive: 0xe0852b, emissiveIntensity: 0.25 })
    : new THREE.MeshStandardMaterial({ color: 0xd5e6fa, emissive: 0x4f8fcf, emissiveIntensity: 0.25 }));

  // the light cones are glow, not surfaces: keep them out of the AO normal / depth pass (it renders with an
  // override material), or they would darken the page around them
  function noAO(obj) {
    obj.onBeforeRender = (r, scene) => { if (scene && scene.overrideMaterial) { obj.userData.mw = obj.matrixWorld.clone(); obj.matrixWorld.makeScale(0, 0, 0); } };
    obj.onAfterRender = () => { if (obj.userData.mw) { obj.matrixWorld.copy(obj.userData.mw); obj.userData.mw = null; } };
  }

  // ---- scene objects (built once from strip.json; the case only changes where they sit) ----
  const root = V.group('strip');
  const stripG = new THREE.Group(); stripG.name = 'strip3d';
  const kapton = new THREE.Group(); kapton.name = 'strip3d-kapton'; kapton.visible = false;
  root.add(stripG, kapton);
  let flex, piS, piBack, tapeS, ledObjs = [], smalls = [];
  let overlay = null, overlayTex = null, overlayCanvas = null;

  function box(x0, y0, z0, x1, y1, z1, m) {
    const g = new THREE.BoxGeometry(Math.abs(x1 - x0), Math.abs(y1 - y0), Math.abs(z1 - z0));
    const o = new THREE.Mesh(g, m);
    o.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
    o.castShadow = true; o.receiveShadow = true;
    return o;
  }
  function buildStrip() {
    CUTS = cuts();
    flex = new Sheet(G.outline, 0, T, M.flex);
    piS = G.front_pieces.map(p => new Sheet(p, -(H + STIFF / 2), STIFF, M.pi));
    piBack = new Sheet(G.back_stiffener, -(H + STIFF / 2), STIFF, M.pi);
    tapeS = G.front_pieces.map(p => new Sheet(p, -(H + STIFF + TAPE / 2), TAPE, M.tape));
    for (const s of [flex, ...piS, piBack, ...tapeS]) { s.mesh.castShadow = true; s.mesh.receiveShadow = true; stripG.add(s.mesh); }
    tapeS.forEach(s => { s.mesh.visible = false; s.mesh.name = 'strip3d-tape'; });
    flex.mesh.name = 'strip3d-flex';
    ledObjs = G.leds.map(d => {
      const g = new THREE.Group(); g.name = 'strip3d-' + d.ref;
      const body = new THREE.Mesh(new THREE.BoxGeometry(LED.face_ahead + LED.rear_behind, LED.len, LED.h), M.led);
      body.position.set((LED.face_ahead - LED.rear_behind) / 2, 0, H + LED.h / 2);
      body.castShadow = true; body.receiveShadow = true;
      const lens = new THREE.Mesh(new THREE.BoxGeometry(0.03, LED.window, LED.h - 0.2), lensMat(d.colour));
      lens.position.set(LED.face_ahead + 0.01, 0, H + LED.h / 2);
      const beam = new THREE.Mesh(new THREE.ConeGeometry(9, 22, 32, 1, true), mat(new THREE.MeshBasicMaterial({
        color: d.colour === 'warm' ? 0xffb36b : 0x9cc8f5, transparent: true, opacity: 0.14, depthWrite: false,
        blending: THREE.AdditiveBlending, side: THREE.DoubleSide })));
      beam.rotation.z = Math.PI / 2; beam.scale.set(1, 1, 0.18); beam.position.set(LED.face_ahead + 11, 0, H + LED.h / 2);
      beam.visible = false; noAO(beam);
      g.add(body, lens, beam); stripG.add(g);
      return { d, g, lens, beam, folded: false };
    });
    const small = (geo, m, x, y, lift, name) => {
      const o = new THREE.Mesh(geo, m); o.name = name; o.castShadow = true; o.receiveShadow = true;
      stripG.add(o); smalls.push({ m: o, x, y, lift });
    };
    for (const d of G.diodes) small(new THREE.BoxGeometry(1.25, 2.0, 0.9), M.sot, d.x, d.y, H + 0.45, 'strip3d-' + d.ref);
    for (const d of G.tps) small(new THREE.BoxGeometry(0.8, 0.8, 0.02), M.gold, d.x, d.y, H + 0.01, 'strip3d-' + d.ref);
    for (const fx of G.fingers) small(new THREE.BoxGeometry(0.3, 1.8, 0.02), M.gold, fx, G.tip_y - 1.1, H + 0.01, 'strip3d-finger');
    // the Kapton you add (device frame; the same places on both readers)
    const add = (x0, y0, z0, x1, y1, z1, name) => { const o = box(x0, y0, z0, x1, y1, z1, M.kapton); o.name = 'strip3d-kapton-' + name; kapton.add(o); };
    add(7.3, 5.45, 1.60, 14.7, 6.05, 1.66, 'slot-glass');     // slot edge (glass side)
    add(7.3, 6.75, 1.60, 14.7, 7.35, 1.66, 'slot-board');     // slot edge (board side)
    add(7.3, 3.5, 1.60, 8.9, 5.1, 1.75, 'sw9');               // SW9 lead or pin, covered
    add(6.3, 17.2, -0.12, 15.2, 19.4, -0.06, 'strap');         // strap over the stiffened back run
  }
  function orient(obj, p, lift) {
    const nY = p[4], nZ = p[5];
    obj.position.set(p[0], p[1] + nY * lift, p[2] + nZ * lift);
    obj.rotation.set(Math.atan2(-nY, nZ), 0, 0);
  }

  // ---- state ----
  const st = { size: null, fold: 1, target: 1, tape: false, kapton: false, light: 'off', built: false, active: false };
  let cur = null;               // CASES[size]
  let raf = 0;
  let loading = null;
  function updateStrip() {
    if (!cur || !st.built) return;
    const pr = progFor(cur, st.fold);
    flex.update(cur, pr); piS.forEach(s => s.update(cur, pr)); piBack.update(cur, pr); tapeS.forEach(s => s.update(cur, pr));
    for (const o of ledObjs) { const p = place(cur, pr, o.d.x, o.d.y); orient(o.g, p, 0); o.folded = p[5] < -0.5; }
    for (const s of smalls) orient(s.m, place(cur, pr, s.x, s.y), s.lift);
    refreshLight();
    V.invalidate();
  }
  let lastT = 0;
  function tick(now) {
    raf = 0;
    // eased by time, not by frame, so a slow frame rate does not slow the fold (time constant 0.22 s)
    const dt = lastT ? Math.min(250, now - lastT) : 16;
    lastT = now;
    const d = st.target - st.fold;
    if (Math.abs(d) > 1e-3 && !reduce) st.fold += d * (1 - Math.exp(-dt / 220)); else st.fold = st.target;
    updateStrip();
    SC.emit('stripfold', { fold: st.fold, target: st.target });
    if (st.fold !== st.target) raf = requestAnimationFrame(tick); else lastT = 0;
  }
  function kick() { if (!raf) raf = requestAnimationFrame(tick); }

  // ---- the light on the page (tools/optics_sim.py's grazing model), on a plane just over the viewer's screen ----
  function buildOverlay(D) {
    const disp = V.group('display');
    if (overlay) { disp.remove(overlay); overlay.geometry.dispose(); }
    if (!cur) return;
    const [ax0, ay1] = dev(cur.active.left, cur.active.top), [ax1, ay0] = dev(cur.active.right, cur.active.bottom);
    overlayCanvas = document.createElement('canvas');
    overlayCanvas.width = 220; overlayCanvas.height = Math.round(220 * (ay1 - ay0) / (ax1 - ax0));
    if (overlayTex) overlayTex.dispose();
    overlayTex = new THREE.CanvasTexture(overlayCanvas); overlayTex.colorSpace = THREE.SRGBColorSpace;
    const m = overlay && overlay.material ? overlay.material : mat(new THREE.MeshBasicMaterial({ toneMapped: false }));
    m.map = overlayTex; m.needsUpdate = true;
    overlay = new THREE.Mesh(new THREE.PlaneGeometry(ax1 - ax0, ay1 - ay0), m);
    overlay.name = 'strip3d-light';
    const zl = D && D.meta && D.meta.z && D.meta.z.lip != null ? D.meta.z.lip : cur.zFront;
    overlay.position.set((ax0 + ax1) / 2, (ay0 + ay1) / 2, zl + 0.06);
    overlay.visible = false;
    disp.add(overlay);
  }
  function refreshLight() {
    const on = st.light !== 'off' && st.active;
    for (const o of ledObjs) {
      const lit = on && !o.folded && o.d.colour === st.light;
      o.beam.visible = lit;
      o.lens.material.emissiveIntensity = lit ? 3.0 : 0.25;
    }
    if (!overlay) return;
    overlay.visible = on;
    if (!on) { V.invalidate(); return; }
    const c = cur, ctx = overlayCanvas.getContext('2d'), W = overlayCanvas.width, Hh = overlayCanvas.height;
    const aw = c.active.right - c.active.left, ah = c.active.bottom - c.active.top;
    const face = 45.20, gap = c.active.left - face, hgt = 0.785;
    const leds = ledObjs.filter(o => !o.folded && o.d.colour === st.light).map(o => o.d.y - c.active.top);
    const img = ctx.createImageData(W, Hh), vals = new Float32Array(W * Hh);
    let max = 0;
    for (let j = 0; j < Hh; j++) for (let i = 0; i < W; i++) {
      const x = (i + 0.5) / W * aw, y = (j + 0.5) / Hh * ah;
      let e = 0;
      for (const p of leds) {
        const dx = x + gap, dl = y - p, rho = Math.hypot(dx, dl), r = Math.hypot(rho, hgt);
        e += Math.max(0, Math.cos(Math.atan2(Math.abs(dl), dx))) * Math.max(0, Math.cos(Math.atan2(hgt, rho))) * (hgt / r) / (r * r);
      }
      vals[j * W + i] = e; if (e > max) max = e;
    }
    const tint = st.light === 'warm' ? [255, 176, 96] : [150, 196, 255];
    for (let k = 0; k < vals.length; k++) {
      const v = max > 0 ? Math.max(0, Math.min(1, (Math.log10(vals[k] / max) + 3) / 3)) : 0;
      const b = 40 + 200 * v;
      img.data[4 * k] = b * tint[0] / 255; img.data[4 * k + 1] = b * tint[1] / 255; img.data[4 * k + 2] = b * tint[2] / 255; img.data[4 * k + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    overlayTex.needsUpdate = true;
    V.invalidate();
  }

  // ---- follow the page state: build on a light-strip build (light strip, light-strip chinless: SC.buildIs('ls')),
  // rest (hidden by the chip's build rule) otherwise ----
  let lastBuild = null;
  function sync() {
    const s = SC.state, D = SC.data;
    const prevBuild = lastBuild;
    lastBuild = s.build;
    st.active = !!(SC.buildIs && SC.buildIs('ls', s.build));
    if (!st.active) {
      if (st.light !== 'off') { st.light = 'off'; refreshLight(); emitSet(); }
      return Promise.resolve(false);
    }
    // (the viewer's mount turns the strip chip back on when a build without it had forced it off)
    return load().then(() => {
      if (!SC.buildIs('ls') || !SC.data) return false;
      const S = SC.state.size, c = CASES[S];
      if (!c) { console.warn('[strip3d] no fold path for size ' + S); return false; }
      const g = SC.get(SC.data, 'cards.strip.geometry');
      if (g && g.flex_top != null && g.stack) setZ(c, g.flex_top - (g.stack.tape + g.stack.pi + g.stack.flex));
      cur = c; st.size = S;
      // the Kapton over SW9's lead: a board without the bottom keys has no SW9 (the light-strip chinless)
      const k9 = kapton.getObjectByName('strip3d-kapton-sw9');
      if (k9) k9.visible = !!(SC.data.meta.bottom_keys && SC.data.meta.bottom_keys.length);
      buildOverlay(SC.data);
      for (const m of mats) { m.clippingPlanes = clipNow(); m.needsUpdate = true; }
      updateStrip();
      emitSet();
      return true;
    });
  }
  function load() {
    if (st.built) return Promise.resolve(true);
    if (loading) return loading;
    const f = (SC.manifest && SC.manifest.assets && SC.manifest.assets.strip) || 'strip.json';
    loading = SC.load(f).then(g => {
      G = g;
      T = G.flex_t; H = T / 2; STIFF = G.stiffener; [H0, H1] = G.hinge_y; LED = G.led;
      makeCases();
      buildStrip();
      st.built = true;
      return true;
    }).catch(e => { loading = null; console.error('[strip3d] strip.json', e); throw e; });
    return loading;
  }
  function emitSet() { SC.emit('stripset', api.stats()); }

  // ---- API ----
  const api = {
    get ready() { return st.built ? Promise.resolve(api) : load().then(() => api); },
    sync,
    built: () => st.built && !!cur,
    fold(f, opt = {}) {
      if (f == null) return st.target;
      st.target = Math.min(1, Math.max(0, +f));
      if (opt.animate === false || reduce) { st.fold = st.target; if (raf) { cancelAnimationFrame(raf); raf = 0; } updateStrip(); SC.emit('stripfold', { fold: st.fold, target: st.target }); }
      else kick();
      return st.target;
    },
    foldNow: () => st.fold,
    tape(on) { if (on != null) { st.tape = !!on; if (tapeS) tapeS.forEach(s => { s.mesh.visible = st.tape; }); V.invalidate(); emitSet(); } return st.tape; },
    kapton(on) { if (on != null) { st.kapton = !!on; kapton.visible = st.kapton; V.invalidate(); emitSet(); } return st.kapton; },
    light(mode) { if (mode != null) { st.light = mode === 'warm' || mode === 'cool' ? mode : 'off'; refreshLight(); emitSet(); } return st.light; },
    // the default section through LED D4, in the case frame (Y)
    ledY: ref => { const d = G && G.leds.find(x => x.ref === (ref || 'D4')); return d ? Y0 - d.y : null; },
    reset(opt = {}) { api.tape(false); api.kapton(false); api.light('off'); api.fold(1, opt); },
    // for tests: where things are
    probe() {
      if (!cur || !st.built) return null;
      const pr = progFor(cur, st.fold), tip = place(cur, pr, 55.0, G.tip_y - 1.1), d4 = G.leds.find(x => x.ref === 'D4');
      const led = place(cur, pr, d4.x, d4.y);
      flex.geo.computeBoundingBox();
      const b = flex.geo.boundingBox;
      return { size: st.size, fold: st.fold, zFront: cur.zFront, zFoot: cur.zFoot, tip: tip.slice(0, 3), d4: led.slice(0, 3),
               folded: ledObjs.filter(o => o.folded).map(o => o.d.ref), bbox: [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z] };
    },
    stats: () => ({ built: st.built, size: st.size, active: st.active, fold: st.fold, target: st.target, tape: st.tape,
                    kapton: st.kapton, light: st.light, meshes: stripG.children.length + kapton.children.length,
                    visible: !!(root.parent && root.parent.visible) }),
    group: root,
  };
  SC.strip3d = api;
  SC.on('state', () => { sync().catch(() => {}); });
  if (SC.data && V.stats().parts > 0) sync().catch(() => {});
  SC.emit('strip3d', api);
}

try {
  if (SC && SC.viewer) init(SC.viewer);
  else if (SC && SC._viewerP) SC._viewerP.then(v => { try { init(v); } catch (e) { console.error('[strip3d]', e); } });
} catch (e) { console.error('[strip3d]', e); }
