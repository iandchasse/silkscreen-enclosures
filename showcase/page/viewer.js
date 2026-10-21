// The Silkscreen case stage: one three.js scene for both sizes and both builds.
// Generalised from Rev K's showcase_viewer.js. It attaches to window.SC (the shell's page core) as SC.viewer;
// the shell calls SC.viewer.mount(state, data) after every size / build / variant switch. See showcase/API.md.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const SC = window.SC;
const MF = SC.manifest;
const $ = id => document.getElementById(id);
const msg = $('vp-msg'), msgText = $('vp-msg-text');
const tag = $('vp-tag'), caption = $('caption');
const canvas = $('gl'), vp = $('viewport'), stage = $('stage');
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const coarse = matchMedia('(pointer: coarse)').matches;
const HOT = 0xc7782a;
const rad = THREE.MathUtils.degToRad;

function start() {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
  } catch (e) {
    msgText.textContent = 'This browser could not start WebGL, so the 3D view is off. The drawings below still work.';
    $('vp-bar').parentNode.hidden = true;
    SC.viewer = null;
    SC._viewerResolve(null);
    return;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.localClippingEnabled = true;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 0.94;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.42;
  const camera = new THREE.PerspectiveCamera(30, 1, 1, 3000);
  camera.up.set(0, 0, 1);
  camera.position.set(104, -158, 142);

  // ---- redraw only when something changed ----
  let dirty = 3, boundsDirty = true;
  const invalidate = bounds => { dirty = 3; if (bounds) boundsDirty = true; };

  // ---- lights: a warm key that follows the view and casts soft shadows, a cool fill, a rim ----
  const settings = { shadows: true, ao: !coarse, edges: true, free: true, shell: false };
  const key = new THREE.DirectionalLight(0xfff3e4, 2.7);
  key.castShadow = true;
  const SHADOW = coarse ? 2048 : 4096;
  key.shadow.mapSize.set(SHADOW, SHADOW);
  key.shadow.bias = -0.0002;
  key.shadow.normalBias = 0.04;
  const fill = new THREE.DirectionalLight(0xdce6ff, 0.5);
  const rim = new THREE.DirectionalLight(0xffffff, 0.85);
  scene.add(key, key.target, fill, fill.target, rim, rim.target);
  scene.add(new THREE.HemisphereLight(0xf3f0e8, 0x353c37, 0.3));
  const KEY_DIR = new THREE.Vector3(-0.5, 0.78, 0.6).normalize();
  const FILL_DIR = new THREE.Vector3(0.85, -0.15, 0.5).normalize();
  const RIM_DIR = new THREE.Vector3(0.35, 0.55, -0.75).normalize();
  const sphere = new THREE.Sphere(new THREE.Vector3(30, 54, 0), 75);

  // ---- stage background: a vertical gradient from the page's tokens ----
  const cssColor = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#cccccc';
  function applyTheme() {
    const c = document.createElement('canvas'); c.width = 2; c.height = 256;
    const g = c.getContext('2d'), grd = g.createLinearGradient(0, 0, 0, 256);
    grd.addColorStop(0, cssColor('--stage-top')); grd.addColorStop(1, cssColor('--stage-bottom'));
    g.fillStyle = grd; g.fillRect(0, 0, 2, 256);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
    if (scene.background && scene.background.dispose) scene.background.dispose();
    scene.background = t;
    if (look.focus) applyLook();
    invalidate();
  }
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);
  new MutationObserver(applyTheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // ---- post: MSAA beauty pass, ground-truth ambient occlusion, tone mapping ----
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 }));
  composer.addPass(new RenderPass(scene, camera));
  const gtao = new GTAOPass(scene, camera, 1, 1);
  gtao.output = GTAOPass.OUTPUT.Default;
  gtao.blendIntensity = 0.9;
  gtao.updateGtaoMaterial({ radius: 3.2, distanceExponent: 2.0, thickness: 2.0, scale: 1.0, samples: 16, distanceFallOff: 1.0 });
  gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 5, rings: 2, samples: 16 });
  gtao.normalMaterial.side = THREE.DoubleSide;
  {
    const base = gtao.renderOverride.bind(gtao);
    gtao.renderOverride = (r, mat, target, color, alpha) => {
      const bg = scene.background; scene.background = null;
      base(r, mat, target, color, alpha);
      scene.background = bg;
    };
  }
  composer.addPass(gtao);
  composer.addPass(new OutputPass());

  // ---- camera controls: free spin or turntable, off-axis pan, zoom at the cursor, pick a pivot ----
  class FreeControls {
    constructor(cam, el) {
      this.cam = cam; this.el = el; this.target = new THREE.Vector3(30, 50, -1);
      this.worldUp = new THREE.Vector3(0, 0, 1);
      this.pointers = new Map(); this.vel = new THREE.Vector2(); this.mode = null; this.moved = false; this.last = 0;
      el.addEventListener('pointerdown', e => this.down(e));
      el.addEventListener('pointermove', e => this.move(e));
      el.addEventListener('pointerup', e => this.up(e));
      el.addEventListener('pointercancel', e => this.up(e));
      el.addEventListener('wheel', e => this.wheel(e), { passive: false });
      el.addEventListener('contextmenu', e => e.preventDefault());
      el.addEventListener('mousedown', e => { if (e.button === 1) e.preventDefault(); });
      el.addEventListener('auxclick', e => { if (e.button === 1) e.preventDefault(); });
      el.addEventListener('dblclick', e => this.onPick && this.onPick(e));
      el.addEventListener('keydown', e => this.key(e));
    }
    basis() {
      const q = this.cam.quaternion;
      return { right: new THREE.Vector3(1, 0, 0).applyQuaternion(q), up: new THREE.Vector3(0, 1, 0).applyQuaternion(q),
               fwd: new THREE.Vector3(0, 0, -1).applyQuaternion(q) };
    }
    rotate(dx, dy) {
      const s = 0.0065, { right, up } = this.basis();
      const off = this.cam.position.clone().sub(this.target);
      let q;
      if (settings.free) {
        q = new THREE.Quaternion().setFromAxisAngle(up, -dx * s).multiply(new THREE.Quaternion().setFromAxisAngle(right, -dy * s));
      } else {
        const polar = off.angleTo(this.worldUp);
        const pitch = THREE.MathUtils.clamp(polar - dy * s, 0.03, Math.PI - 0.03) - polar;
        q = new THREE.Quaternion().setFromAxisAngle(this.worldUp, -dx * s).multiply(new THREE.Quaternion().setFromAxisAngle(right, pitch));
      }
      off.applyQuaternion(q);
      this.cam.position.copy(this.target).add(off);
      if (settings.free) {
        this.cam.quaternion.premultiply(q);
        this.cam.up.set(0, 1, 0).applyQuaternion(this.cam.quaternion);
      } else {
        this.cam.up.copy(this.worldUp);
        this.cam.lookAt(this.target);
      }
      this.moved = true;
    }
    level() { this.cam.up.copy(this.worldUp); this.cam.lookAt(this.target); this.moved = true; }
    pan(dx, dy) {
      const dist = this.cam.position.distanceTo(this.target);
      const per = 2 * dist * Math.tan(rad(this.cam.fov / 2)) / Math.max(1, this.el.clientHeight);
      const { right, up } = this.basis();
      const d = right.multiplyScalar(-dx * per).addScaledVector(up, dy * per);
      this.cam.position.add(d); this.target.add(d);
      this.moved = true;
    }
    zoomAt(factor, cx, cy) {
      const r = this.el.getBoundingClientRect();
      const ndc = new THREE.Vector3(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1, 0.5);
      const dist = this.cam.position.distanceTo(this.target);
      const f = THREE.MathUtils.clamp(dist * factor, 6, 1600) / dist;
      const ray = ndc.unproject(this.cam).sub(this.cam.position).normalize();
      const t = dist / Math.max(1e-6, ray.dot(this.basis().fwd));
      const P = this.cam.position.clone().addScaledVector(ray, t);
      this.cam.position.sub(P).multiplyScalar(f).add(P);
      this.target.sub(P).multiplyScalar(f).add(P);
      this.moved = true;
    }
    pinch() {
      const [a, b] = [...this.pointers.values()];
      return { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    }
    down(e) {
      if (e.button === 1) e.preventDefault();
      this.el.focus({ preventScroll: true });
      this.el.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      this.vel.set(0, 0);
      if (this.pointers.size === 1) this.mode = (e.button === 1 || e.button === 2 || e.shiftKey || e.ctrlKey || e.metaKey) ? 'pan' : 'rotate';
      else if (this.pointers.size === 2) { this.mode = 'pinch'; this.pz = this.pinch(); }
      if (this.onStart) this.onStart();
    }
    move(e) {
      const p = this.pointers.get(e.pointerId);
      if (!p) return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY;
      if (this.mode === 'pinch' && this.pointers.size === 2) {
        const s = this.pinch();
        this.zoomAt(this.pz.d / s.d, s.x, s.y);
        this.pan(s.x - this.pz.x, s.y - this.pz.y);
        this.pz = s;
      } else if (this.mode === 'rotate') { this.rotate(dx, dy); this.vel.set(dx, dy); this.last = performance.now(); }
      else if (this.mode === 'pan') this.pan(dx, dy);
    }
    up(e) {
      this.pointers.delete(e.pointerId);
      if (this.pointers.size === 0) {
        if (this.mode !== 'rotate' || reduce || performance.now() - this.last > 70) this.vel.set(0, 0);
        this.mode = null;
      } else if (this.pointers.size === 1) { this.mode = 'rotate'; this.vel.set(0, 0); }
    }
    wheel(e) {
      e.preventDefault();
      const d = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
      this.zoomAt(Math.exp(THREE.MathUtils.clamp(d, -120, 120) * 0.0014), e.clientX, e.clientY);
      if (this.onStart) this.onStart();
    }
    key(e) {
      const r = this.el.getBoundingClientRect(), step = 14;
      const k = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
      if (k) { e.preventDefault(); e.shiftKey ? this.pan(...k) : this.rotate(...k); }
      else if (e.key === '+' || e.key === '=') this.zoomAt(0.85, r.left + r.width / 2, r.top + r.height / 2);
      else if (e.key === '-' || e.key === '_') this.zoomAt(1 / 0.85, r.left + r.width / 2, r.top + r.height / 2);
      else return;
      if (this.onStart) this.onStart();
    }
    update() {
      if (!this.mode && this.vel.lengthSq() > 0.02) { this.rotate(this.vel.x, this.vel.y); this.vel.multiplyScalar(0.9); }
      const m = this.moved; this.moved = false;
      return m;
    }
  }
  const controls = new FreeControls(camera, canvas);
  canvas.tabIndex = 0;
  let tween = null;
  controls.onStart = () => { tween = null; };
  camera.lookAt(controls.target);

  // ---- part catalogue ----
  const COL = {
    tub: 0xd6d1c4, lid: 0xc5bfb0, skey: 0xc5bfb0, midplate: 0x76847c, key: 0x2f3236, crank: 0xd2a53c, rod: 0x2e86de,
    panel_epd: 0x2a2d31, panel_light: 0xbfd0d8, panel_touch: 0x3a4148, ribbon: 0xc98a2b, ribbon_ic: 0x1b1c1e,
    battery_cell: 0xaeb3b8, battery_leads: 0xb3342a, battery_plug: 0xece5d4, battery_pcm: 0x2a6b48, screw: 0xb7bcc2,
    pcba_pcb: 0x1d5e3d, pcba_switch: 0x313438, swbody: 0x313438, sw_T_body: 0x3a3d42, sw_T_nub: 0xeeeae0, nub: 0xd6d6cc,
    pcba_passive: 0x8b7a62, pcba_ic: 0x222427, pcba_module: 0xc4c8cd, pcba_usb: 0xd1d5da, pcba_connector: 0xe4dfd0,
    pcba_header: 0x1f2022, strip: 0xe0852b, cmp_x4: 0x34373c, cmp_retro: 0x9fb0bd, dummy_pcba: 0x5f9a78,
    pin: 0xb9bec4, plug_shell: 0xc9ced4, plug_body: 0x2b2e33,
  };
  const METAL = { screw: [0.9, 0.32], pcba_module: [0.85, 0.35], pcba_usb: [0.9, 0.25], battery_cell: [0.5, 0.5],
                  ribbon: [0.15, 0.55], panel_touch: [0.1, 0.25], panel_light: [0.0, 0.3], cmp_x4: [0.05, 0.45],
                  pin: [0.9, 0.3], plug_shell: [0.9, 0.28] };
  const GROUP_COL = { tub: COL.tub, keys: COL.key, rod: COL.crank, display: COL.ribbon, midplate: COL.midplate,
                      pcba: COL.pcba_pcb, battery: COL.battery_cell, lid: COL.lid, screws: COL.screw, strip: COL.strip,
                      dummy: COL.dummy_pcba, compare: COL.cmp_retro };
  const GROUPS = (MF.groups || []).map(g => ({
    ...g,
    test: n => g.match.some(p => p.endsWith('*') ? n.startsWith(p.slice(0, -1)) : n === p),
  }));
  const groupOf = n => { const g = GROUPS.find(x => x.test(n)); return g ? g.id : null; };
  const EDGED = n => /^(tub|skey|lid|midplate|key_|crank_|rod|gate|panel_|cmp_|dummy_|screw_|swbody_|sw_T_body)/.test(n);
  function colorFor(n) {
    if (n.startsWith('skey')) return COL.skey;
    if (n.startsWith('key_')) return COL.key;
    if (n.startsWith('crank_') || n === 'gate') return COL.crank;
    if (n === 'rod') return COL.rod;
    if (n.startsWith('screw_')) return COL.screw;
    if (n.startsWith('swbody_')) return COL.swbody;
    if (n.startsWith('sw_T_body')) return COL.sw_T_body;
    if (n.startsWith('sw_T_nub')) return COL.sw_T_nub;
    if (n.startsWith('nub_')) return COL.nub;
    if (n.startsWith('ribbon_')) return n.endsWith('_ic') ? COL.ribbon_ic : COL.ribbon;
    if (n.startsWith('strip_')) return COL.strip;
    if (n.startsWith('cmp_retro')) return n.includes('upper') ? 0xa8b7c3 : COL.cmp_retro;
    return COL[n] ?? 0x999999;
  }
  function metalFor(n) {
    const k = n.startsWith('screw_') ? 'screw' : n.startsWith('ribbon_') && !n.endsWith('_ic') ? 'ribbon' : n;
    return METAL[k] || [0.0, n.startsWith('pcba_pcb') ? 0.55 : 0.62];
  }
  function edgeColor(c) {
    const l = c.r * 0.3 + c.g * 0.59 + c.b * 0.11;
    return l > 0.25 ? c.clone().multiplyScalar(0.42) : c.clone().lerp(new THREE.Color(0xffffff), 0.28);
  }

  // e-paper page texture, sized to the active area
  const screenTex = {};
  function screenTexture(a) {
    const k = a.w + 'x' + a.h;
    if (screenTex[k]) return screenTex[k];
    const W = 1024, Hh = Math.round(1024 * a.h / a.w);
    const c = document.createElement('canvas'); c.width = W; c.height = Hh;
    const g = c.getContext('2d');
    g.fillStyle = '#e9e7df'; g.fillRect(0, 0, W, Hh);
    g.fillStyle = '#26262a';
    const m = 78;
    g.font = '600 30px Georgia, "Times New Roman", serif';
    g.fillText('MOBY-DICK', m, 96);
    g.fillText('CHAPTER 1. Loomings.', m, 170);
    g.font = '38px Georgia, "Times New Roman", serif';
    const text = 'Call me Ishmael. Some years ago\u2014never mind how long precisely\u2014having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world. It is a way I have of driving off the spleen, and regulating the circulation. Whenever I find myself growing grim about the mouth; whenever it is a damp, drizzly November in my soul; whenever I find myself involuntarily pausing before coffin warehouses, and bringing up the rear of every funeral I meet; and especially whenever my hypos get such an upper hand of me, that it requires a strong moral principle to prevent me from deliberately stepping into the street, and methodically knocking people\u2019s hats off\u2014then, I account it high time to get to sea as soon as I can.';
    let line = '', y = 250;
    for (const w of text.split(' ')) {
      const t = line ? line + ' ' + w : w;
      if (g.measureText(t).width > W - 2 * m) { g.fillText(line, m, y); line = w; y += 58; if (y > Hh - 140) break; }
      else line = t;
    }
    if (y <= Hh - 140) g.fillText(line, m, y);
    g.font = '28px Georgia, serif'; g.fillStyle = '#6a6a6e';
    g.fillText('1 / 724', W / 2 - 44, Hh - 60);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return (screenTex[k] = tex);
  }

  // ---- model files: base64 GLB in JSON -> {node: {geo, edges}} (parsed once per file) ----
  const loader = new GLTFLoader();
  const models = {};
  function b64ToBuf(s) {
    const bin = atob(s);
    const u = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return u.buffer;
  }
  function model(file) {
    if (models[file]) return models[file];
    models[file] = SC.load(file).then(obj => {
      if (!obj || obj.format !== 'glb-base64') throw new Error(file + ' is not a model file');
      const buf = b64ToBuf(obj.data);
      return loader.parseAsync(buf, '').then(gltf => {
        const out = {};
        gltf.scene.updateMatrixWorld(true);
        gltf.scene.traverse(o => {
          if (!o.isMesh) return;
          const name = o.name || (o.parent && o.parent.name);
          let geo = o.geometry.clone();
          geo.applyMatrix4(o.matrixWorld);
          geo.deleteAttribute('normal');
          geo = toCreasedNormals(geo, rad(32));
          geo.computeBoundingBox(); geo.computeBoundingSphere();
          out[name] = { geo, edges: EDGED(name) ? new THREE.EdgesGeometry(geo, 30) : null };
        });
        return out;
      });
    });
    models[file].catch(() => { delete models[file]; });
    return models[file];
  }

  // ---- scene graph: one root per chip group, plus the live strip and the tools (pin, plug) ----
  const clipPlane = new THREE.Plane(new THREE.Vector3(1, 0, 0), 0);
  const groupRoots = {};
  for (const g of GROUPS) { const r = new THREE.Group(); r.name = g.id; scene.add(r); groupRoots[g.id] = r; }
  const live = {};
  function liveGroup(id) {
    if (!groupRoots[id]) return null;
    if (!live[id]) { live[id] = new THREE.Group(); live[id].name = id + '-live'; groupRoots[id].add(live[id]); }
    return live[id];
  }
  const tools = new THREE.Group(); tools.name = 'tools'; scene.add(tools);
  let parts = {};            // name -> {name, obj, holder, mesh, cap, lines, group, base, mat, capMat, lineMat}
  let D = null;              // the current data-S-B
  let cur = { size: null, build: null, variant: SC.state.variant };
  let extrasMounted = null;  // size whose extras are in the scene

  function makePart(name, src, groupId, parent, opts = {}) {
    const base = new THREE.Color(opts.color ?? colorFor(src.baseName || name));
    const [metal, rough] = opts.metal || metalFor(src.baseName || name);
    const edged = !!src.edges;
    const mat = new THREE.MeshStandardMaterial({ color: base.clone(), metalness: metal, roughness: rough, clippingPlanes: [], clipShadows: true,
                                                 polygonOffset: edged, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
    const capMat = new THREE.MeshBasicMaterial({ color: base.clone().multiplyScalar(0.55), side: THREE.BackSide, clippingPlanes: [] });
    const mesh = new THREE.Mesh(src.geo, mat);
    mesh.castShadow = true; mesh.receiveShadow = true;
    const cap = new THREE.Mesh(src.geo, capMat);
    const holder = new THREE.Group();
    holder.add(mesh, cap);
    let lines = null, lineMat = null;
    if (edged) {
      lineMat = new THREE.LineBasicMaterial({ color: edgeColor(base), transparent: true, opacity: 0.55, depthWrite: false, clippingPlanes: [] });
      lines = new THREE.LineSegments(src.edges, lineMat);
      lines.visible = settings.edges;
      holder.add(lines);
    }
    let obj = holder;
    if (opts.pivot) {
      const piv = new THREE.Group();
      piv.position.set(...opts.pivot);
      holder.position.set(-opts.pivot[0] + (opts.dx || 0), -opts.pivot[1], -opts.pivot[2]);
      piv.add(holder); obj = piv;
    } else if (opts.dx) {
      holder.position.x = opts.dx;
    }
    obj.name = name;
    (parent || groupRoots[groupId]).add(obj);
    const p = { name, obj, holder, mesh, cap, lines, group: groupId, base, mat, capMat, lineMat, rest: obj.position.clone() };
    parts[name] = p;
    return p;
  }
  function disposePart(p) {
    if (p.obj.parent) p.obj.parent.remove(p.obj);
    p.mat.dispose(); if (p.capMat) p.capMat.dispose(); if (p.lineMat) p.lineMat.dispose();
    if (p.own) { p.mesh.geometry.dispose(); }
  }

  // one model file's nodes into the scene: cranks and TS365 envelopes instanced per bottom key, side keys on pivots
  // skip: names not to mount from this file (a build without bottom keys leaves those core nodes out, and its own
  // build file may replace a core node, the chinless lid)
  function addNodes(M, skip) {
    const K = D.keys || { refs: [], x: {}, rod: { yz: [0, 0] } }, ry = K.rod.yz[0], rz = K.rod.yz[1];
    const ctrlByNode = {};
    for (const c of D.controls || []) if (c.node) ctrlByNode[c.node] = c;
    for (const [name, src] of Object.entries(M)) {
      if (skip && skip.has(name)) continue;
      const g = groupOf(name);
      if (!g) { unmatched.add(name); continue; }
      if (name === 'crank_M' || name === 'crank_T') {
        const v = name.slice(-1);
        for (const ref of K.refs) {
          const p = makePart(`crank_${v}_${ref}`, { ...src, baseName: name }, g, null, { pivot: [K.x[ref], ry, rz], dx: 0 });
          p.variant = v; p.ref = ref;
          // the crank mesh sits at X = 0: the pivot's X places it
          p.holder.position.x = 0;
        }
        continue;
      }
      if (name === 'sw_T_body' || name === 'sw_T_nub') {
        for (const ref of K.refs) {
          const p = makePart(`${name}_${ref}`, { ...src, baseName: name }, g, null, { dx: K.x[ref] });
          p.variant = 'T'; p.ref = ref;
          p.rest = p.obj.position.clone();
        }
        continue;
      }
      const c = ctrlByNode[name];
      if (c && c.kind === 'flexure') { makePart(name, src, g, null, { pivot: c.pivot }); continue; }
      const p = makePart(name, src, g);
      if (name.startsWith('swbody_')) p.variant = 'M';
      if (name.startsWith('nub_') && K.refs.includes(name.slice(4))) { p.variant = 'M'; p.ref = name.slice(4); }
    }
  }
  const unmatched = new Set();

  // viewer-drawn parts: the page plane, the reset pin, the USB-C plug
  function addExtras() {
    const a = D.meta.active;
    const geo = new THREE.PlaneGeometry(a.w, a.h);
    const screen = makePart('screen', { geo, edges: null }, 'display', null, { color: 0xffffff, metal: [0, 0.9] });
    screen.own = true;
    screen.mat.map = screenTexture(a); screen.mat.color.set(0xffffff); screen.mat.needsUpdate = true;
    screen.cap.visible = false; screen.mesh.castShadow = false;
    screen.obj.position.set(a.cx, a.cy, D.meta.z.lip + 0.02);
    screen.rest = screen.obj.position.clone();
    for (const c of D.controls || []) {
      if (c.kind === 'pin') {
        const r = (c.hole_d ? c.hole_d * 0.4 : 0.45), len = 22;
        const geo2 = new THREE.CylinderGeometry(r, r, len, 20);
        geo2.rotateZ(Math.PI / 2); geo2.translate(len / 2, 0, 0);         // along +X from the tip
        const p = makePart('tool_pin', { geo: geo2, edges: null }, null, tools, { color: COL.pin, metal: METAL.pin });
        p.own = true; p.tool = c.id; p.obj.visible = false;
      }
      if (c.kind === 'plug') {
        const sl = c.shell_len || 6.65, om = c.overmold || [11, 5.6];
        const g1 = new RoundedBoxGeometry(sl, 8.34, 2.56, 3, 1.1); g1.translate(sl / 2, 0, 0);
        const g2 = new RoundedBoxGeometry(16, om[0], om[1], 3, 1.2); g2.translate(sl + 8, 0, 0);
        const s = makePart('tool_plug', { geo: g1, edges: null }, null, tools, { color: COL.plug_shell, metal: METAL.plug_shell });
        s.own = true; s.tool = c.id; s.obj.visible = false;
        const b = makePart('tool_plug_body', { geo: g2, edges: null }, null, s.obj, { color: COL.plug_body, metal: [0, 0.7] });
        b.own = true; b.tool = c.id;
      }
    }
  }

  // ---- chips ----
  const visible = Object.fromEntries(GROUPS.map(g => [g.id, !g.off]));
  const forcedOff = new Set();   // groups turned off by a mount only because the build lacks them
  const available = g => !g.builds || g.builds.includes(cur.build);
  const everyday = () => GROUPS.filter(g => !g.off && available(g)).map(g => g.id);
  function chipLabel(g) {
    if (g.id === 'display' && D) {
      const pl = D.meta.panel || {};
      return `Panel <small>${pl.label || ''}${pl.ribbons > 1 ? ', ribbons' : ', FPC'}</small>`;
    }
    return g.label;
  }
  function buildChips() {
    const host = $('chips');
    host.innerHTML = '';
    for (const g of GROUPS) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'chip'; b.dataset.group = g.id;
      b.innerHTML = `<i style="background:#${new THREE.Color(GROUP_COL[g.id] ?? 0x999999).getHexString()}"></i>${chipLabel(g)}`;
      b.hidden = !available(g);
      b.setAttribute('aria-pressed', String(!!visible[g.id]));
      b.addEventListener('click', () => setGroup(g.id, !visible[g.id]));
      host.appendChild(b);
    }
  }
  function syncChips() {
    for (const g of GROUPS) {
      if (groupRoots[g.id]) groupRoots[g.id].visible = !!visible[g.id] && available(g);
      const b = document.querySelector(`.chip[data-group="${g.id}"]`);
      if (b) { b.setAttribute('aria-pressed', String(!!visible[g.id])); b.hidden = !available(g); }
    }
    invalidate(true);
  }
  function setGroup(id, on) {
    visible[id] = !!on;
    const g = GROUPS.find(x => x.id === id);
    if (on && g && g.lazy) ensureExtras();
    syncChips();
  }
  function setVisible(ids) {
    for (const g of GROUPS) visible[g.id] = ids ? ids.includes(g.id) && available(g) : (!g.off && available(g));
    if (GROUPS.some(g => g.lazy && visible[g.id])) ensureExtras();
    syncChips();
  }
  let extrasBusy = null;
  function ensureExtras() {
    const S = cur.size;
    if (!S || extrasMounted === S) return Promise.resolve();
    if (extrasBusy && extrasBusy.S === S) return extrasBusy.p;
    const chips = GROUPS.filter(g => g.lazy).map(g => document.querySelector(`.chip[data-group="${g.id}"]`)).filter(Boolean);
    chips.forEach(b => b.classList.add('busy'));
    const p = model(MF.load[S].extras).then(M => {
      if (cur.size !== S || extrasMounted === S) return;
      addNodes(M);
      extrasMounted = S;
      refreshParts();
    }).catch(e => console.error('[viewer] extras', e)).finally(() => {
      chips.forEach(b => b.classList.remove('busy'));
      extrasBusy = null;
    });
    extrasBusy = { S, p };
    return p;
  }

  // after parts were added: clip planes, edges, look, variant, explode, press
  function refreshParts() {
    applyClip(clipOn);
    for (const p of Object.values(parts)) if (p.lines) p.lines.visible = settings.edges;
    applyVariant();
    applyLook();
    setExplode(+explodeIn.value, true);
    pressAgain();
    syncChips();
  }

  // ---- mount: the shell calls this after every switch; it keeps camera, section, press, explode, visibility ----
  let mountSeq = 0, mounted = false, readyResolve;
  const ready = new Promise(r => { readyResolve = r; });
  async function mount(st, data, opt = {}) {
    if (opt.variantOnly && mounted && st.size === cur.size && st.build === cur.build) {
      cur.variant = st.variant; D = data;
      applyVariant(); pressAgain();
      return;
    }
    const my = ++mountSeq;
    const F = SC.files(st.size, st.build);
    const wantExtras = GROUPS.some(g => g.lazy && visible[g.id]);
    const [core, build] = await Promise.all([model(F.core), model(F.build)]);
    const extras = wantExtras ? await model(F.extras) : null;
    if (my !== mountSeq) return;
    for (const p of Object.values(parts)) disposePart(p);
    parts = {}; unmatched.clear(); extrasMounted = null;
    D = data; cur = { size: st.size, build: st.build, variant: st.variant };
    addNodes(core, new Set([...(D.meta.absent_nodes || []), ...Object.keys(build)])); addNodes(build);
    if (extras) { addNodes(extras); extrasMounted = st.size; }
    addExtras();
    // a group that was off only because this build lacks it comes back on when it is available again
    for (const g of GROUPS) {
      if (!available(g)) { if (visible[g.id]) forcedOff.add(g.id); visible[g.id] = false; }
      else if (forcedOff.has(g.id)) { forcedOff.delete(g.id); visible[g.id] = !g.off; }
    }
    if (settings.shell) for (const id of SHELL) visible[id] = false;
    buildChips();
    buildPressSelect();
    refreshParts();
    if (secAxis.value !== 'off') setSection(secAxis.value, secVal, lastFlip);
    if (!mounted) {
      mounted = true;
      msg.hidden = true;
      frame('home', false);
      tag.textContent = D.presets.home.tag; caption.innerHTML = D.presets.home.cap;
      resize();
      requestAnimationFrame(animate);
      SC.timing.viewer = Math.round(performance.now());
      readyResolve(api);
      SC.emit('viewer', api);
    } else if (curPreset && D.presets[curPreset] && !playing) {
      tag.textContent = D.presets[curPreset].tag; caption.innerHTML = D.presets[curPreset].cap;
    } else if (explodeIn.value <= 0.0005 && !curPreset) {
      caption.innerHTML = D.presets.home.cap;
    }
    invalidate(true);
  }

  // ---- variant: crank-T + TS365ZJ, or crank-M + MJTP1117 ----
  function applyVariant() {
    for (const p of Object.values(parts)) if (p.variant) p.obj.visible = p.variant === cur.variant;
    invalidate();
  }

  // ---- explode / assembly ----
  const explodeIn = $('explode'), explodeOut = $('explode-out');
  const smooth = t => t * t * (3 - 2 * t);
  let lastStep = null;
  // step k (explode.order[k]) is on the stage while its group is arriving: a in ((k-1)/N, k/N]; step 0 (the first
  // group alone) at a = 0, i.e. fully apart. SC.viewer.explodeStep(k, f) puts the stage at fraction f of step k.
  function setExplode(e, quiet, finishing) {
    if (!D) return;
    const ORDER = D.explode.order, OFF = D.explode.offsets, STEPS = D.explode.steps;
    const N = ORDER.length - 1, a = 1 - e;
    let step = 0;
    for (const id in groupRoots) groupRoots[id].position.z = 0;
    ORDER.forEach((id, k) => {
      if (k === 0) return;
      const lo = (k - 1) / N, hi = k / N;
      const t = Math.min(1, Math.max(0, (a - lo) / (hi - lo)));
      if (groupRoots[id]) groupRoots[id].position.z = (OFF[id] || 0) * (1 - smooth(t));
      if (a > lo + 1e-9) step = k;
    });
    explodeOut.textContent = e <= 0.0005 ? 'assembled' : e >= 0.9995 ? 'apart' : `step ${Math.min(step, N) + 1} of ${ORDER.length}`;
    if (e > 0.0005) {
      const k = Math.min(step, N);
      if (!quiet || lastStep !== k) {
        caption.innerHTML = `<b>Step ${k + 1}.</b> ${STEPS[k] || ''}`;
        tag.textContent = 'Assembly';
      }
      if (lastStep !== k) { lastStep = k; SC.emit('step', k); }
    } else if (lastStep !== null) {
      lastStep = null;
      tag.textContent = 'Assembled';
      caption.innerHTML = D.explode.done;
      if (!finishing) SC.emit('step', -1);      // Play's end emits order.length instead
    }
    invalidate(true);
  }
  explodeIn.addEventListener('input', () => { stopPlay(); setExplode(+explodeIn.value); });
  function explode(e) { explodeIn.value = e; setExplode(e); }
  function explodeStep(k, f = 0.98) {
    if (!D) return 0;
    const N = Math.max(1, D.explode.order.length - 1);
    k = Math.max(0, Math.min(N, Math.round(k)));
    const a = k === 0 ? 0 : (k - 1 + Math.min(1, Math.max(0.001, f))) / N;
    explode(1 - a);
    return 1 - a;
  }

  let playing = null;
  function stopPlay() { if (playing) { cancelAnimationFrame(playing); playing = null; } }
  function play() {
    if (!D) return;
    stopPlay();
    look = {}; applyLook();
    setVisible(null);
    setSection('off');
    curPreset = 'assembly';
    frame('assembly', true);
    const t0 = performance.now(), hold = 900, dur = reduce ? 1 : 9000;
    explode(1);
    const tick = now => {
      const t = now - t0 - hold;
      const e = t < 0 ? 1 : Math.max(0, 1 - t / dur);
      explodeIn.value = e; setExplode(e, false, e <= 0);
      if (e > 0) playing = requestAnimationFrame(tick);
      else { playing = null; caption.innerHTML = D.explode.done; tag.textContent = 'Assembled'; SC.emit('step', D.explode.order.length); }
    };
    playing = requestAnimationFrame(tick);
  }
  $('play').addEventListener('click', play);
  SC.on('play', play);

  // ---- section: one clip plane with backside caps, over meta.envelope ----
  const secAxis = $('sec-axis'), secPos = $('sec-pos'), secFlip = $('sec-flip');
  let clipOn = false, lastFlip = false, secVal = null;
  function applyClip(on) {
    clipOn = on;
    const planes = on ? [clipPlane] : [];
    for (const p of Object.values(parts)) {
      p.mat.clippingPlanes = planes; p.mat.needsUpdate = true;
      if (p.capMat) { p.capMat.clippingPlanes = planes; p.capMat.needsUpdate = true; }
      if (p.lineMat) { p.lineMat.clippingPlanes = planes; p.lineMat.needsUpdate = true; }
    }
    for (const id in live) live[id].traverse(o => { if (o.material && 'clippingPlanes' in o.material && !o.userData.noClip) { o.material.clippingPlanes = planes; o.material.needsUpdate = true; } });
    gtao.normalMaterial.clippingPlanes = planes; gtao.normalMaterial.needsUpdate = true;
    invalidate();
  }
  function setSection(axis, value, flip) {
    if (flip == null) flip = lastFlip; else lastFlip = !!flip;
    secFlip.setAttribute('aria-pressed', String(lastFlip));
    secAxis.value = axis;
    secPos.disabled = axis === 'off';
    if (axis === 'off' || !D) { applyClip(false); return; }
    const ENV = D.meta.envelope;
    const i = 'xyz'.indexOf(axis);
    const lo = ENV[2 * i] - 1, hi = ENV[2 * i + 1] + 1;
    if (value == null) value = lo + (+secPos.value) * (hi - lo);
    value = Math.min(hi, Math.max(lo, value));
    secPos.value = (value - lo) / (hi - lo);
    secVal = value;
    const n = new THREE.Vector3(); n.setComponent(i, flip ? 1 : -1);
    clipPlane.normal.copy(n);
    clipPlane.constant = flip ? -value : value;
    applyClip(true);
  }
  secAxis.addEventListener('change', () => { lastFlip = false; secVal = null; setSection(secAxis.value); });
  secPos.addEventListener('input', () => setSection(secAxis.value));
  secFlip.addEventListener('click', () => { if (secAxis.value !== 'off') setSection(secAxis.value, secVal, !lastFlip); });

  // ---- press: every control in data.controls; the bottom keys from the exact crank kinematics ----
  const pressIn = $('press'), pressOut = $('press-out'), pressSel = $('press-sel');
  let ctrlState = {};      // id -> t or {theta}
  const rawCache = new Map();
  function crankRaw(v) {
    const k = D.keys, key = v;
    let m = rawCache.get(k);
    if (!m) { m = {}; rawCache.set(k, m); }
    return m[key] || (m[key] = SC.crank.raw(v, 0, k));
  }
  const exf = () => (SC.exag ? 4 : 1);
  const V3 = a => new THREE.Vector3(...a);
  function applyControl(c, t, opt = {}) {
    const ex = exf();
    const K = D.keys, CR = SC.crank;
    if (c.kind === 'crank') {
      const v = cur.variant, R = crankRaw(v);
      const th = opt.theta != null ? +opt.theta : R.theta_rest + t * (R.theta_bottom - R.theta_rest);
      const thv = R.theta_rest + (th - R.theta_rest) * ex;
      const ax = V3(c.axis || K.axis || [1, 0, 0]).normalize();
      for (const vv of ['M', 'T']) {
        const cp = parts[`crank_${vv}_${c.ref}`];
        if (cp) cp.obj.quaternion.setFromAxisAngle(ax, rad(thv - K.theta_built));
      }
      const kp = parts[c.node];
      if (kp) kp.obj.position.z = kp.rest.z - CR.keyDown(thv, K.theta_built, K);
      const push = CR.plungerIn(v, thv, 0, K);
      const nm = parts[c.plunger], nt = parts[`sw_T_nub_${c.ref}`];
      if (nm) nm.obj.position.y = nm.rest.y + (v === 'M' ? push : 0);
      if (nt) nt.obj.position.y = nt.rest.y + (v === 'T' ? push : 0);
      const tt = R.theta_bottom !== R.theta_rest ? (th - R.theta_rest) / (R.theta_bottom - R.theta_rest) : 0;
      // kept as the fraction of this variant's stroke, so a variant swap re-derives the angle for the new pair
      ctrlState[c.id] = opt.theta != null ? tt : t;
      return { id: c.id, kind: c.kind, t: tt, theta: th, key_down: CR.keyDown(th, R.theta_rest, K),
               plunger_in: CR.plungerIn(v, th, 0, K), state: CR.state(v, th, K) };
    }
    if (c.kind === 'flexure') {
      const d = t * c.max_travel, dv = d * ex;
      const p = parts[c.node];
      if (p) p.obj.quaternion.setFromAxisAngle(V3(c.axis).normalize(), (c.sign || 1) * dv / c.length);
      const push = Math.max(0, d - c.gap);
      const n = parts[c.plunger];
      if (n) n.obj.position.copy(n.rest).addScaledVector(V3(c.plunger_axis), push * ex);
      ctrlState[c.id] = t;
      return { id: c.id, kind: c.kind, t, travel: d, plunger_in: push, state: d >= c.click_travel - 1e-9 ? 'clicked' : 'open' };
    }
    if (c.kind === 'pin') {
      const pin = parts.tool_pin;
      const from = V3(c.pin_from), to = V3(c.pin_to), dir = to.clone().sub(from).normalize();
      const s = Math.min(1, t / 0.6), push = t > 0.6 ? (t - 0.6) / 0.4 * c.max_travel : 0;
      const tip = from.clone().lerp(to, s).addScaledVector(dir, push * ex);
      if (pin) {
        pin.obj.position.copy(tip);
        pin.obj.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir.clone().negate());
        pin.obj.visible = t > 0 || pressSel.value === c.id;
      }
      const n = parts[c.plunger];
      if (n) n.obj.position.copy(n.rest).addScaledVector(V3(c.plunger_axis), push * ex);
      ctrlState[c.id] = t;
      return { id: c.id, kind: c.kind, t, travel: push, plunger_in: push, state: push >= c.click_travel - 1e-9 ? 'clicked' : 'open' };
    }
    if (c.kind === 'plug') {
      const pl = parts.tool_plug;
      const from = V3(c.from), to = V3(c.to), dir = V3(c.axis).normalize();
      const tip = from.clone().lerp(to, t);
      if (pl) {
        pl.obj.position.copy(tip);
        pl.obj.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir.clone().negate());
        pl.obj.visible = t > 0 || pressSel.value === c.id;
      }
      ctrlState[c.id] = t;
      const ins = t * (c.insert_mm || from.distanceTo(to));
      return { id: c.id, kind: c.kind, t, travel: ins, state: t >= 0.999 ? 'seated' : t > 0 ? 'going in' : 'out' };
    }
    return null;
  }
  const isButton = c => c.kind === 'crank' || c.kind === 'flexure';
  function describe(r) {
    if (!r) return 'at rest';
    const f = SC.fmt;
    if (r.kind === 'crank') return `${f(r.theta, 2)}\u00b0 \u00b7 key ${f(r.key_down, 2)} mm \u00b7 ${r.state}`;
    if (r.kind === 'flexure') return `${f(r.travel, 2)} mm \u00b7 ${r.state}`;
    if (r.kind === 'pin') return `pin ${f(r.travel, 2)} mm \u00b7 ${r.state}`;
    if (r.kind === 'plug') return `${f(r.travel, 1)} mm in \u00b7 ${r.state}`;
    return '';
  }
  // id: a control id, 'all' (every crank and flexure), 'kind:<kind>' (e.g. 'kind:flexure', all side keys) or an
  // array of control ids. Only a single id (or 'all') moves the stage's Press selector.
  function press(id, t, opt = {}) {
    if (!D) return null;
    t = Math.min(1, Math.max(0, +t || 0));
    const many = Array.isArray(id) || (typeof id === 'string' && id.startsWith('kind:'));
    const list = id === 'all' ? D.controls.filter(isButton)
      : Array.isArray(id) ? D.controls.filter(c => id.includes(c.id))
      : many ? D.controls.filter(c => c.kind === id.slice(5))
      : D.controls.filter(c => c.id === id);
    let res = null;
    for (const c of list) {
      const r = applyControl(c, t, opt);
      if (!res || (id === 'all' && c.kind === 'crank' && c.ref === D.keys.draw_ref)) res = r;
    }
    if (!res) return null;
    if (many) {
      invalidate();
      const out = { ...res, id: Array.isArray(id) ? id.slice() : id, ids: list.map(c => c.id), src: opt.src || 'api' };
      SC.emit('pressed', out);
      return out;
    }
    if (pressSel.value === id || (pressSel.value === 'all' && id === 'all')) pressOut.textContent = describe(res);
    if (opt.src !== 'stage' && pressSel.value !== id && [...pressSel.options].some(o => o.value === id)) {
      pressSel.value = id; pressOut.textContent = describe(res);
    }
    if (opt.src !== 'stage') pressIn.value = res.t != null ? res.t : t;
    invalidate();
    const out = { ...res, id, src: opt.src || 'api' };
    SC.emit('pressed', out);
    return out;
  }
  function pressAgain() {
    if (!D) return;
    for (const c of D.controls) {
      const s = ctrlState[c.id];
      if (s == null) { applyControl(c, 0); continue; }
      applyControl(c, s);
    }
    ctrlState = Object.fromEntries(Object.entries(ctrlState).filter(([k, v]) => v > 0));
    const sel = pressSel.value;
    const c0 = sel === 'all' ? D.controls.find(c => c.kind === 'crank' && c.ref === D.keys.draw_ref) : D.controls.find(c => c.id === sel);
    if (c0) {
      const s = ctrlState[c0.id];
      pressOut.textContent = s == null ? 'at rest' : describe(applyControl(c0, s));
    } else pressOut.textContent = 'at rest';        // no bottom keys (chinless): 'All keys' has no crank to describe
    invalidate();
  }
  // every control back to rest; emits 'released' {src} so cards with their own sliders can follow
  function releaseAll(src = 'api') {
    if (!D) return;
    const was = Object.keys(ctrlState).length;
    for (const c of D.controls) applyControl(c, 0);      // tools (pin, plug) stay shown only while selected
    ctrlState = {};
    pressIn.value = 0; pressOut.textContent = 'at rest';
    invalidate();
    SC.emit('released', { src, was });
  }
  function buildPressSelect() {
    const keep = pressSel.value;
    pressSel.innerHTML = '';
    const add = (v, l) => { const o = document.createElement('option'); o.value = v; o.textContent = l; pressSel.appendChild(o); };
    add('all', 'All keys');
    for (const c of D.controls) add(c.id, SC.text(c.label || c.id));
    pressSel.value = [...pressSel.options].some(o => o.value === keep) ? keep : 'all';
  }
  pressIn.addEventListener('input', () => press(pressSel.value, +pressIn.value, { src: 'stage' }));
  pressSel.addEventListener('change', () => {
    releaseAll('stage');
    for (const c of D.controls) if (c.kind === 'pin' || c.kind === 'plug') applyControl(c, 0);
    pressOut.textContent = 'at rest';
  });
  const exagIn = $('exag');
  function exaggerate(on) {
    SC.exag = !!on; exagIn.checked = SC.exag;
    pressAgain();
    SC.emit('exag', SC.exag);
  }
  exagIn.addEventListener('change', () => exaggerate(exagIn.checked));

  // ---- presets (from data), views ----
  let curPreset = null;
  let look = {};          // {focus: [groups], highlight: [patterns]}
  function lerpView(cam, tgt, up, animateCam) {
    if (!animateCam || reduce) {
      tween = null;
      camera.position.copy(cam); controls.target.copy(tgt); camera.up.copy(up); camera.lookAt(tgt); invalidate(); return;
    }
    const c0 = camera.position.clone(), t0 = controls.target.clone(), u0 = camera.up.clone(), s = performance.now();
    tween = now => {
      const t = Math.min(1, (now - s) / 900), k = smooth(t);
      camera.position.lerpVectors(c0, cam, k); controls.target.lerpVectors(t0, tgt, k);
      camera.up.lerpVectors(u0, up, k).normalize();
      camera.lookAt(controls.target);
      if (t >= 1) tween = null;
    };
    invalidate();
  }
  function frame(name, animateCam = true) {
    const p = D && D.presets[name];
    if (!p) return;
    lerpView(fitCam(V3(p.cam), V3(p.tgt), p.fit), V3(p.tgt), V3(p.up || [0, 0, 1]), animateCam);
  }
  // a preset's fit: back off along the view line on a narrow stage (Rev K)
  function fitCam(cam, tgt, fit) {
    if (!fit) return cam;
    const aspect = Math.max(0.6, vp.clientWidth / Math.max(1, vp.clientHeight));
    return cam.clone().sub(tgt).multiplyScalar(Math.max(1, 1.25 / aspect)).add(tgt);
  }
  const VIEWS = {
    front: [[0, 0, 1], [0, 1, 0]], back: [[0, 0, -1], [0, 1, 0]], top: [[0, 1, 0], [0, 0, 1]], bottom: [[0, -1, 0], [0, 0, 1]],
    left: [[-1, 0, 0], [0, 1, 0]], right: [[1, 0, 0], [0, 1, 0]], iso: [[0.45, -0.6, 0.66], [0, 0, 1]],
  };
  function view(name) {
    if (!VIEWS[name]) return;
    updateBounds();
    const [d, u] = VIEWS[name];
    const aspect = vp.clientWidth / Math.max(1, vp.clientHeight);
    const half = rad(camera.fov / 2);
    const fit = Math.min(half, Math.atan(Math.tan(half) * aspect));
    const dist = sphere.radius / Math.sin(fit) * 1.02;
    const dir = V3(d).normalize();
    lerpView(sphere.center.clone().addScaledVector(dir, dist), sphere.center.clone(), V3(u), true);
  }
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => view(b.dataset.view)));

  const globToRe = p => new RegExp('^' + p.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$');
  function applyLook() {
    for (const [n, p] of Object.entries(parts)) {
      if (n === 'screen') continue;
      p.mat.color.copy(p.base);
      if (p.lineMat) p.lineMat.color.copy(edgeColor(p.base));
    }
    if (look.focus) {
      const bg = new THREE.Color(cssColor('--stage-top'));
      for (const [n, p] of Object.entries(parts)) {
        if (n === 'screen' || !p.group || look.focus.includes(p.group)) continue;
        p.mat.color.copy(p.base).lerp(bg, 0.72);
        if (p.lineMat) p.lineMat.color.copy(edgeColor(p.base)).lerp(bg, 0.72);
      }
    }
    if (look.highlight && look.highlight.length) {
      const res = look.highlight.map(globToRe), col = new THREE.Color(look.color ?? HOT);
      for (const [n, p] of Object.entries(parts)) if (res.some(r => r.test(n))) p.mat.color.copy(col);
    }
    invalidate();
  }
  function highlight(patterns, color = HOT) { look = { ...look, highlight: [].concat(patterns || []), color }; applyLook(); }
  function clearHighlight() { look = { ...look, highlight: null }; applyLook(); }
  // set or drop the focus / highlight look without running a preset (camera, chips and section stay)
  function setLook(l) {
    if (l !== undefined) {
      l = l || {};
      look = { focus: l.focus || null, highlight: l.highlight ? [].concat(l.highlight) : null, color: l.color };
      applyLook();
    }
    return { focus: look.focus || null, highlight: look.highlight || null };
  }
  function preset(name, opt = {}) {
    const p = D && D.presets[name];
    if (!p) { console.warn('[viewer] no preset ' + name + ' in data-' + cur.size + '-' + cur.build); return; }
    stopPlay();
    curPreset = name;
    explode(p.explode || 0);
    look = { focus: p.focus || null, highlight: p.highlight || null };
    if (p.show) setVisible(p.show);
    else if (p.hide) setVisible(everyday().filter(id => !p.hide.includes(id)));
    else setVisible(null);
    applyLook();
    if (p.sec) setSection(p.sec[0], p.sec[1], !!p.sec[2]); else setSection('off');
    if (p.variant && p.variant !== SC.state.variant) SC.set({ variant: p.variant });
    const pid = p.press != null && p.press !== false ? (p.press === true ? 'all' : String(p.press)) : 'all';
    if ([...pressSel.options].some(o => o.value === pid) && pressSel.value !== pid) { pressSel.value = pid; releaseAll('preset'); }
    frame(name, opt.animate !== false);
    tag.textContent = p.tag || name; caption.innerHTML = p.cap || '';
  }
  SC.on('focus', name => preset(name));
  function reset() {
    stopPlay(); look = {}; applyLook(); curPreset = null;
    setVisible(null); setSection('off'); explode(0); pressSel.value = 'all'; releaseAll('view');
    frame('home', true);
    if (D) { tag.textContent = D.presets.home.tag; caption.innerHTML = D.presets.home.cap; }
    if (SC.close) SC.close();
  }
  $('reset').addEventListener('click', reset);

  // ---- double-click: spin about the point under the cursor ----
  const raycaster = new THREE.Raycaster();
  const pivotDot = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 12), new THREE.MeshBasicMaterial({ color: HOT, transparent: true, depthTest: false }));
  pivotDot.renderOrder = 10; pivotDot.visible = false; scene.add(pivotDot);
  let pivotFade = 0;
  const shown = o => { for (let x = o; x; x = x.parent) if (!x.visible) return false; return true; };
  controls.onPick = e => {
    const r = canvas.getBoundingClientRect();
    raycaster.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const meshes = Object.values(parts).filter(p => shown(p.mesh)).map(p => p.mesh);
    for (const id in live) live[id].traverse(o => { if (o.isMesh && shown(o)) meshes.push(o); });
    const hit = raycaster.intersectObjects(meshes, false).find(h => !clipOn || clipPlane.distanceToPoint(h.point) >= 0);
    if (!hit) return;
    const d = hit.point.clone().sub(controls.target);
    lerpView(camera.position.clone().add(d), hit.point.clone(), camera.up.clone(), true);
    pivotDot.position.copy(hit.point);
    pivotDot.scale.setScalar(camera.position.distanceTo(hit.point) * 0.006);
    pivotDot.visible = true; pivotFade = performance.now();
  };

  // ---- render settings ----
  const SHELL = ['tub', 'lid', 'screws'];
  function setSetting(k, v) {
    settings[k] = !!v;
    if (k === 'shadows') key.castShadow = settings.shadows;
    if (k === 'edges') for (const p of Object.values(parts)) if (p.lines) p.lines.visible = settings.edges;
    if (k === 'free' && !settings.free) controls.level();
    if (k === 'shell') { for (const id of SHELL) visible[id] = !settings.shell; syncChips(); }
    const b = document.querySelector(`[data-setting="${k}"]`);
    if (b) b.setAttribute('aria-pressed', String(settings[k]));
    invalidate(true);
  }
  document.querySelectorAll('[data-setting]').forEach(b => {
    const k = b.dataset.setting;
    b.setAttribute('aria-pressed', String(settings[k]));
    b.addEventListener('click', () => setSetting(k, !settings[k]));
  });

  // ---- expand the stage to fill the window ----
  const expandBtn = $('expand');
  function setExpanded(on) {
    stage.classList.toggle('max', on);
    document.documentElement.classList.toggle('stage-max', on);
    expandBtn.setAttribute('aria-pressed', String(on));
    expandBtn.textContent = on ? 'Close' : 'Expand';
    requestAnimationFrame(resize);
  }
  expandBtn.addEventListener('click', () => setExpanded(!stage.classList.contains('max')));
  addEventListener('keydown', e => { if (e.key === 'Escape' && stage.classList.contains('max')) setExpanded(false); });

  // ---- render loop ----
  function updateBounds() {
    const box = new THREE.Box3();
    for (const id in groupRoots) if (groupRoots[id].visible) box.expandByObject(groupRoots[id]);
    if (!box.isEmpty()) box.getBoundingSphere(sphere);
    boundsDirty = false;
  }
  function placeLights() {
    const c = sphere.center, r = Math.max(15, sphere.radius);
    for (const [l, dir] of [[key, KEY_DIR], [fill, FILL_DIR], [rim, RIM_DIR]]) {
      l.position.copy(c).addScaledVector(dir.clone().applyQuaternion(camera.quaternion), r * 3);
      l.target.position.copy(c);
      l.target.updateMatrixWorld();
    }
    const sc = key.shadow.camera;
    sc.left = -r; sc.bottom = -r; sc.right = r; sc.top = r; sc.near = r * 1.5; sc.far = r * 4.5;
    sc.updateProjectionMatrix();
    const d = camera.position.distanceTo(c);
    camera.near = Math.max(0.5, d - r * 1.6); camera.far = d + r * 1.6 + 50;
    camera.updateProjectionMatrix();
  }
  function resize() {
    const w = Math.max(1, vp.clientWidth), h = Math.max(1, vp.clientHeight);
    renderer.setSize(w, h, false);
    composer.setPixelRatio(renderer.getPixelRatio());
    composer.setSize(w, h);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    invalidate();
  }
  new ResizeObserver(resize).observe(vp);
  let frames = 0;
  function animate(now) {
    requestAnimationFrame(animate);
    now = now || performance.now();
    if (tween) { tween(now); dirty = 3; }
    if (controls.update()) dirty = 3;
    if (playing) dirty = 3;
    if (pivotDot.visible) {
      const t = (now - pivotFade) / 1400;
      pivotDot.material.opacity = Math.max(0, 1 - t);
      if (t >= 1) pivotDot.visible = false;
      dirty = Math.max(dirty, 1);
    }
    if (dirty <= 0) return;
    if (boundsDirty) updateBounds();
    placeLights();
    if (settings.ao) composer.render(); else renderer.render(scene, camera);
    frames++;
    dirty--;
  }
  applyTheme();

  // ---- the API (SC.viewer), see showcase/API.md section 5 ----
  const node = name => {
    if (parts[name]) return parts[name].obj;
    const m = /^crank_(SW\w+)$/.exec(name);
    if (m && parts[`crank_${cur.variant}_${m[1]}`]) return parts[`crank_${cur.variant}_${m[1]}`].obj;
    return null;
  };
  const api = {
    ready, mount, THREE, scene, camera, controls, renderer,
    get state() { return { ...cur, preset: curPreset, explode: +explodeIn.value, section: secAxis.value === 'off' ? null : [secAxis.value, secVal, lastFlip] }; },
    groups: () => GROUPS.map(g => ({ id: g.id, label: g.label, visible: !!visible[g.id], available: available(g), off: !!g.off, lazy: !!g.lazy })),
    visible: (id, on) => { if (on !== undefined) setGroup(id, on); return !!visible[id]; },
    setVisible, show: ids => { for (const id of [].concat(ids)) visible[id] = true; setVisible(Object.keys(visible).filter(k => visible[k])); },
    hide: ids => { for (const id of [].concat(ids)) visible[id] = false; syncChips(); },
    ensureExtras,
    preset, frame: (n, a = true) => frame(n, a), view,
    section: (axis, pos, flip) => setSection(axis || 'off', pos, flip),
    explode, explodeStep, play, stop: stopPlay, reset,
    press, release: (src = 'api') => releaseAll(src), pressState: id => (ctrlState[id] != null ? ctrlState[id] : 0),
    look: setLook, clearLook: () => setLook(null),
    variant: v => { if (v === 'T' || v === 'M') { cur.variant = v; applyVariant(); pressAgain(); } },
    exaggerate,
    highlight, clearHighlight,
    node, nodes: () => Object.keys(parts), part: name => parts[name] || null,
    caption: (html, t) => { if (html != null) caption.innerHTML = html; if (t != null) tag.textContent = t; },
    invalidate: () => invalidate(true),
    group: id => liveGroup(id),
    // opt: {fit} backs off on a narrow stage like a preset's fit; {animate: false} jumps
    tween: (cam, tgt, up, opt = {}) => lerpView(fitCam(V3(cam), V3(tgt), opt.fit), V3(tgt), V3(up || [0, 0, 1]), opt.animate !== false),
    setting: (k, v) => { if (v !== undefined) setSetting(k, v); return settings[k]; },
    clip: () => (clipOn ? clipPlane : null),
    extraSlot: () => $('stage-extra'),
    stats: () => ({ parts: Object.keys(parts).length, unmatched: [...unmatched], frames, extras: extrasMounted, size: cur.size, build: cur.build, variant: cur.variant }),
  };
  SC.viewer = api;
  SC._viewerResolve(api);
  // the shell may have loaded the data before this module ran: mount what it shows now
  if (SC.data) {
    mount(SC.state, SC.data).then(() => SC.emit('state', { ...SC.state, prev: null })).catch(e => {
      console.error('[viewer] mount', e);
      msgText.textContent = 'The 3D model could not be loaded. ' + (e && e.message || '');
    });
  }
}

try { start(); } catch (e) {
  console.error('[viewer]', e);
  msgText.textContent = 'The 3D view could not start. The drawings below still work.';
  SC._viewerResolve(null);
}
