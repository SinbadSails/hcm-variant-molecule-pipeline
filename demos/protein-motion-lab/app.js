/* Protein Motion Lab. No network services, analytics, or external dependencies. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const canvas = $('molecule-canvas');
  const chart = $('rmsd-chart');
  const ctx = canvas.getContext('2d');
  const chartCtx = chart.getContext('2d');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const state = { data: null, frame: 0, playing: false, yaw: -0.42, pitch: 0.32, zoom: 1, radius: 1, lastTick: 0, accumulator: 0, animationId: null, drag: null, chartDrag: false };
  const initialView = { yaw: -0.42, pitch: 0.32, zoom: 1 };
  const fmt = (v, digits = 2) => Number(v).toFixed(digits);

  function fitCanvas(element, context) {
    const bounds = element.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 3);
    const width = Math.max(1, bounds.width), height = Math.max(1, bounds.height);
    if (element.width !== Math.round(width * ratio) || element.height !== Math.round(height * ratio)) {
      element.width = Math.round(width * ratio); element.height = Math.round(height * ratio);
    }
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { width, height };
  }

  function validate(data) {
    if (!data || !Array.isArray(data.residues) || !data.residues.length || !Array.isArray(data.frames) || !data.frames.length) throw new Error('The trajectory needs residues and at least one frame.');
    let previous = -Infinity;
    for (const frame of data.frames) {
      if (!Number.isFinite(frame.time_ps) || frame.time_ps < previous || !Number.isFinite(frame.rmsd_angstrom) || frame.rmsd_angstrom < 0) throw new Error('Frame times and RMSD measurements must be valid numbers.');
      if (!Array.isArray(frame.positions_angstrom) || frame.positions_angstrom.length !== data.residues.length || !frame.positions_angstrom.every((p) => Array.isArray(p) && p.length === 3 && p.every(Number.isFinite))) throw new Error('Every residue needs three coordinates in every frame.');
      previous = frame.time_ps;
    }
    if (data.frames.length > 1 && data.frames.at(-1).time_ps === data.frames[0].time_ps) throw new Error('A multi-frame trajectory needs advancing simulation times.');
    return data;
  }

  function centered(positions) {
    const center = positions.reduce((sum, p) => sum.map((v, i) => v + p[i]), [0, 0, 0]).map((v) => v / positions.length);
    return positions.map((p) => p.map((v, i) => v - center[i]));
  }

  function chainColor(fraction, depth = 1) {
    const colors = [[36, 70, 92], [24, 133, 121], [189, 154, 99]];
    const segment = fraction < 0.55 ? 0 : 1;
    const t = segment === 0 ? fraction / 0.55 : (fraction - 0.55) / 0.45;
    return `rgb(${colors[segment].map((v, i) => Math.round((v + (colors[segment + 1][i] - v) * t) * depth)).join(',')})`;
  }

  function project(p, width, height) {
    const cy = Math.cos(state.yaw), sy = Math.sin(state.yaw), cp = Math.cos(state.pitch), sp = Math.sin(state.pitch);
    const x = p[0] * cy + p[2] * sy;
    const z = -p[0] * sy + p[2] * cy;
    const y = p[1] * cp - z * sp;
    const zz = p[1] * sp + z * cp;
    const perspective = state.radius * 5 / (state.radius * 5 - zz);
    const scale = Math.min(width * 0.78, height * 0.72) / (state.radius * 2) * state.zoom;
    return { x: width / 2 + x * scale * perspective, y: height / 2 - y * scale * perspective, z: zz, perspective };
  }

  function drawMolecule() {
    const { width, height } = fitCanvas(canvas, ctx);
    ctx.clearRect(0, 0, width, height);
    if (!state.data) return;
    const points = centered(state.data.frames[state.frame].positions_angstrom).map((p) => project(p, width, height));
    const segments = points.slice(0, -1).map((p, i) => ({ a: p, b: points[i + 1], index: i, z: (p.z + points[i + 1].z) / 2 })).sort((a, b) => a.z - b.z);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const lineWidth = Math.max(3.8, Math.min(width, height) / 63) * Math.sqrt(state.zoom);
    for (const s of segments) {
      const fraction = s.index / Math.max(points.length - 2, 1);
      const shade = 0.87 + (s.z / state.radius + 1) * 0.07;
      ctx.beginPath(); ctx.moveTo(s.a.x, s.a.y); ctx.lineTo(s.b.x, s.b.y);
      ctx.lineWidth = lineWidth * (s.a.perspective + s.b.perspective) / 2 + 1.5;
      ctx.strokeStyle = '#eef2e9'; ctx.stroke();
      ctx.lineWidth = lineWidth * (s.a.perspective + s.b.perspective) / 2;
      ctx.strokeStyle = chainColor(fraction, shade); ctx.stroke();
      ctx.beginPath(); ctx.arc(s.a.x, s.a.y, lineWidth * .28, 0, Math.PI * 2);
      ctx.fillStyle = chainColor(fraction, Math.min(1.13, shade + .14)); ctx.fill();
    }
    // The terminal letters identify sequence direction, not spatial axes.
    [[0, 'N', '#24465c'], [points.length - 1, 'C', '#9a7c47']].forEach(([i, label, color]) => {
      const p = points[i]; ctx.font = '600 10px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineWidth = 4; ctx.strokeStyle = '#f3f5ef';
      ctx.strokeText(label, p.x + 11, p.y - 11); ctx.fillStyle = color; ctx.fillText(label, p.x + 11, p.y - 11);
    });
    // A real-space scale bar changes with zoom; its length is defined at the view center.
    const unitScale = Math.min(width * .78, height * .72) / (state.radius * 2) * state.zoom;
    const angstroms = unitScale * 10 < width * .2 ? 10 : 5;
    const sx = 23, sy = height - 53, length = unitScale * angstroms;
    if (length < width * .45) {
      ctx.strokeStyle = '#9baaa0'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(sx, sy - 3); ctx.lineTo(sx, sy + 3); ctx.moveTo(sx, sy); ctx.lineTo(sx + length, sy); ctx.moveTo(sx + length, sy - 3); ctx.lineTo(sx + length, sy + 3); ctx.stroke();
      ctx.fillStyle = '#829086'; ctx.font = '9px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'; ctx.textAlign = 'left'; ctx.fillText(`${angstroms} Å`, sx, sy - 10);
    }
  }

  function chartGeometry(width, height) {
    return { left: 35, right: width - 11, top: 17, bottom: height - 30 };
  }

  function drawChart() {
    const { width, height } = fitCanvas(chart, chartCtx);
    chartCtx.clearRect(0, 0, width, height);
    if (!state.data) return;
    const g = chartGeometry(width, height), frames = state.data.frames;
    const start = frames[0].time_ps, end = frames.at(-1).time_ps;
    const ymax = Math.max(0.1, ...frames.map((f) => f.rmsd_angstrom)) * 1.2;
    const x = (time) => g.left + (time - start) / (end - start || 1) * (g.right - g.left);
    const y = (value) => g.bottom - value / ymax * (g.bottom - g.top);
    chartCtx.font = '9px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    chartCtx.lineWidth = 1; chartCtx.textBaseline = 'middle';
    for (let i = 0; i <= 3; i++) {
      const value = ymax * i / 3, yy = y(value);
      chartCtx.beginPath(); chartCtx.moveTo(g.left, yy); chartCtx.lineTo(g.right, yy); chartCtx.strokeStyle = '#e4e7df'; chartCtx.stroke();
      chartCtx.textAlign = 'right'; chartCtx.fillStyle = '#87948d'; chartCtx.fillText(fmt(value, ymax < 1 ? 2 : 1), g.left - 7, yy);
    }
    chartCtx.fillStyle = '#7a8a81'; chartCtx.textAlign = 'left'; chartCtx.fillText('Å', g.left - 17, 5);
    [0, .5, 1].forEach((fraction) => {
      const time = start + fraction * (end - start);
      chartCtx.textAlign = fraction === 0 ? 'left' : fraction === 1 ? 'right' : 'center';
      chartCtx.fillText(fmt(time, 1), x(time), g.bottom + 13);
    });
    chartCtx.textAlign = 'right'; chartCtx.fillText('Time (ps)', g.right, height - 3);
    chartCtx.beginPath(); chartCtx.moveTo(x(start), g.bottom);
    frames.forEach((frame) => chartCtx.lineTo(x(frame.time_ps), y(frame.rmsd_angstrom)));
    chartCtx.lineTo(x(end), g.bottom); chartCtx.closePath(); chartCtx.fillStyle = '#167c7610'; chartCtx.fill();
    chartCtx.beginPath(); frames.forEach((frame, i) => i ? chartCtx.lineTo(x(frame.time_ps), y(frame.rmsd_angstrom)) : chartCtx.moveTo(x(frame.time_ps), y(frame.rmsd_angstrom)));
    chartCtx.strokeStyle = '#167c76'; chartCtx.lineWidth = 1.7; chartCtx.lineJoin = 'round'; chartCtx.stroke();
    const selected = frames[state.frame], xx = x(selected.time_ps), yy = y(selected.rmsd_angstrom);
    chartCtx.beginPath(); chartCtx.moveTo(xx, g.top); chartCtx.lineTo(xx, g.bottom); chartCtx.setLineDash([3, 3]); chartCtx.strokeStyle = '#819c8e'; chartCtx.lineWidth = 1; chartCtx.stroke(); chartCtx.setLineDash([]);
    chartCtx.beginPath(); chartCtx.arc(xx, yy, 3.6, 0, Math.PI * 2); chartCtx.fillStyle = '#167c76'; chartCtx.fill(); chartCtx.strokeStyle = '#fcfbf7'; chartCtx.lineWidth = 1.6; chartCtx.stroke();
    chart.setAttribute('aria-label', `Backbone RMSD versus time. Selected ${fmt(selected.time_ps)} picoseconds, RMSD ${fmt(selected.rmsd_angstrom, 3)} angstroms. Left and right arrow keys select a frame.`);
  }

  function setFrame(index, announce = false) {
    if (!state.data) return;
    state.frame = Math.max(0, Math.min(state.data.frames.length - 1, Math.round(index)));
    const f = state.data.frames[state.frame];
    $('timeline').value = state.frame;
    $('timeline').setAttribute('aria-valuetext', `${fmt(f.time_ps)} picoseconds; RMSD ${fmt(f.rmsd_angstrom, 3)} angstroms; frame ${state.frame + 1} of ${state.data.frames.length}`);
    $('current-time').textContent = fmt(f.time_ps);
    $('rmsd-value').textContent = fmt(f.rmsd_angstrom, 3);
    $('frame-counter').textContent = `${String(state.frame + 1).padStart(2, '0')} / ${state.data.frames.length}`;
    drawMolecule(); drawChart();
    if (announce) $('app-status').textContent = `Frame ${state.frame + 1}, ${fmt(f.time_ps)} picoseconds, RMSD ${fmt(f.rmsd_angstrom, 3)} angstroms.`;
  }

  function setPlaying(playing) {
    if (state.animationId !== null) { cancelAnimationFrame(state.animationId); state.animationId = null; }
    if (!state.data || state.data.frames.length < 2) playing = false;
    state.playing = playing;
    $('play-toggle').setAttribute('aria-label', playing ? 'Pause trajectory' : 'Play trajectory');
    $('play-label').textContent = playing ? 'Pause' : 'Play';
    $('play-icon').innerHTML = playing ? '<path d="M5 4h3v12H5ZM12 4h3v12h-3Z"/>' : '<path d="m7 4 9 6-9 6Z"/>';
    state.lastTick = 0; state.accumulator = 0;
    if (playing) {
      if (state.frame === state.data.frames.length - 1) setFrame(0);
      state.animationId = requestAnimationFrame(tick);
    }
  }

  function tick(timestamp) {
    if (!state.playing) return;
    if (!state.lastTick) state.lastTick = timestamp;
    state.accumulator += Math.min(timestamp - state.lastTick, 200);
    state.lastTick = timestamp;
    const delay = (reducedMotion.matches ? 250 : 80) / Number($('playback-speed').value);
    if (state.accumulator >= delay) {
      const advance = Math.floor(state.accumulator / delay); state.accumulator %= delay;
      setFrame(state.frame + advance);
      if (state.frame >= state.data.frames.length - 1) { setPlaying(false); return; }
    }
    state.animationId = requestAnimationFrame(tick);
  }

  const readableKey = (key) => key.replace(/_/g, ' ').replace(/\b(pdb|md|nvt|npt|cpu|gpu|rmsd|pme)\b/gi, (word) => word.toUpperCase());
  function valueText(value) {
    if (typeof value === 'string') return value;
    if (value === null) return 'Not specified';
    if (Array.isArray(value)) return value.map(valueText).join('; ');
    if (typeof value === 'object') return Object.entries(value).map(([k, v]) => `${readableKey(k)}: ${valueText(v)}`).join(' · ');
    return String(value);
  }
  function renderMetadata(metadata) {
    const list = $('metadata-list'), notes = $('metadata-notes'); list.replaceChildren(); notes.replaceChildren();
    const noteKeys = /notes|limitations|caveats|disclaimer|interpretation/i;
    Object.entries(metadata || {}).forEach(([key, value]) => {
      if (noteKeys.test(key)) {
        const section = document.createElement('div'), heading = document.createElement('strong'); heading.textContent = readableKey(key); section.append(heading);
        const entries = Array.isArray(value) ? value : [value];
        const ul = document.createElement('ul'); entries.forEach((entry) => { const li = document.createElement('li'); li.textContent = valueText(entry); ul.append(li); }); section.append(ul); notes.append(section);
      } else {
        const div = document.createElement('div'), dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = readableKey(key);
        if (typeof value === 'string' && /^https?:\/\//i.test(value)) { const a = document.createElement('a'); a.href = value; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = value; dd.append(a); } else dd.textContent = valueText(value);
        div.append(dt, dd); list.append(div);
      }
    });
  }

  function loadData(raw) {
    const data = validate(raw); setPlaying(false); state.data = data;
    state.radius = Math.max(...data.frames.map((f) => Math.max(...centered(f.positions_angstrom).map((p) => Math.hypot(...p))))) || 1;
    Object.assign(state, initialView);
    const frames = data.frames, first = frames[0], last = frames.at(-1), meta = data.metadata || {};
    const protein = meta.protein_name || meta.protein || 'Protein';
    const name = typeof protein === 'string' ? protein : 'Protein';
    $('page-title').textContent = `${name}, in motion.`; $('protein-name').textContent = name; document.title = `Protein Motion Lab · ${name}`;
    $('residue-count').textContent = `${data.residues.length} residues · Cα backbone`;
    $('sampled-interval').textContent = `${fmt(last.time_ps - first.time_ps)} ps · ${frames.length} frames`;
    $('timeline').max = frames.length - 1; $('timeline').disabled = frames.length < 2; $('play-toggle').disabled = frames.length < 2; $('export-csv').disabled = false;
    $('start-time').textContent = `${fmt(first.time_ps)} ps`; $('last-time').textContent = `${fmt(last.time_ps)} ps`; $('end-time').textContent = `${fmt(last.time_ps)} ps`;
    renderMetadata(meta); $('loading-overlay').hidden = true; $('loading-overlay').classList.remove('has-error');
    setFrame(0); $('app-status').textContent = `${name} loaded. ${data.residues.length} residues and ${frames.length} frames. Playback is paused.`;
  }

  function showError(error) {
    $('loading-overlay').hidden = false; $('loading-overlay').classList.add('has-error');
    $('loading-message').textContent = location.protocol === 'file:' ? 'This copy needs its trajectory data. Choose a trajectory file to explore it locally.' : 'The trajectory could not be opened. Choose a compatible data file, or try reloading this page.';
    $('app-status').textContent = `Trajectory not loaded. ${error.message || 'Please check the data file.'}`;
  }

  $('play-toggle').addEventListener('click', () => setPlaying(!state.playing));
  $('timeline').addEventListener('input', (e) => { setPlaying(false); setFrame(Number(e.target.value)); });
  $('timeline').addEventListener('change', () => setFrame(state.frame, true));
  $('reset-view').addEventListener('click', () => { Object.assign(state, initialView); drawMolecule(); });
  const zoom = (factor) => { state.zoom = Math.max(.5, Math.min(2.8, state.zoom * factor)); drawMolecule(); };
  $('zoom-in').addEventListener('click', () => zoom(1.15)); $('zoom-out').addEventListener('click', () => zoom(1 / 1.15));
  canvas.addEventListener('pointerdown', (event) => { if (!state.data) return; state.drag = { x: event.clientX, y: event.clientY, pointerId: event.pointerId }; canvas.setPointerCapture(event.pointerId); canvas.classList.add('is-dragging'); });
  canvas.addEventListener('pointermove', (event) => { if (!state.drag || event.pointerId !== state.drag.pointerId) return; state.yaw += (event.clientX - state.drag.x) * .009; state.pitch += (event.clientY - state.drag.y) * .009; state.drag.x = event.clientX; state.drag.y = event.clientY; drawMolecule(); });
  const stopDrag = () => { state.drag = null; canvas.classList.remove('is-dragging'); };
  canvas.addEventListener('pointerup', stopDrag); canvas.addEventListener('pointercancel', stopDrag); canvas.addEventListener('lostpointercapture', stopDrag);
  canvas.addEventListener('wheel', (event) => { if (document.activeElement !== canvas) return; event.preventDefault(); zoom(event.deltaY < 0 ? 1.07 : 1 / 1.07); }, { passive: false });
  canvas.addEventListener('keydown', (event) => {
    const changes = { ArrowLeft: ['yaw', -.12], ArrowRight: ['yaw', .12], ArrowUp: ['pitch', -.12], ArrowDown: ['pitch', .12] };
    if (changes[event.key]) { event.preventDefault(); const [key, delta] = changes[event.key]; state[key] += delta; drawMolecule(); }
    else if (event.key === '+' || event.key === '=') { event.preventDefault(); zoom(1.15); }
    else if (event.key === '-') { event.preventDefault(); zoom(1 / 1.15); }
    else if (event.key.toLowerCase() === 'r') { Object.assign(state, initialView); drawMolecule(); }
    else if (event.key === ' ') { event.preventDefault(); setPlaying(!state.playing); }
  });
  function selectChart(event) {
    if (!state.data) return;
    const rect = chart.getBoundingClientRect(), g = chartGeometry(rect.width, rect.height);
    const fraction = Math.max(0, Math.min(1, (event.clientX - rect.left - g.left) / (g.right - g.left)));
    const frames = state.data.frames, targetTime = frames[0].time_ps + fraction * (frames.at(-1).time_ps - frames[0].time_ps);
    let nearest = 0; frames.forEach((f, i) => { if (Math.abs(f.time_ps - targetTime) < Math.abs(frames[nearest].time_ps - targetTime)) nearest = i; });
    setPlaying(false); setFrame(nearest);
  }
  chart.addEventListener('pointerdown', (e) => { state.chartDrag = true; chart.setPointerCapture(e.pointerId); selectChart(e); });
  chart.addEventListener('pointermove', (e) => { if (state.chartDrag) selectChart(e); });
  chart.addEventListener('pointerup', () => { state.chartDrag = false; }); chart.addEventListener('pointercancel', () => { state.chartDrag = false; });
  chart.addEventListener('keydown', (e) => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) { e.preventDefault(); setPlaying(false); const next = e.key === 'Home' ? 0 : e.key === 'End' ? (state.data?.frames.length || 1) - 1 : state.frame + (e.key === 'ArrowRight' ? 1 : -1); setFrame(next, true); } else if (e.key === ' ') { e.preventDefault(); setPlaying(!state.playing); } });
  $('trajectory-file').addEventListener('change', async (e) => {
    const file = e.target.files[0]; if (!file) return;
    try { loadData(JSON.parse(await file.text())); } catch (error) { $('app-status').textContent = `Could not open ${file.name}: ${error.message}`; if (!state.data) showError(error); else alert(`This trajectory could not be opened: ${error.message}`); }
    e.target.value = '';
  });
  document.querySelectorAll('label[for="trajectory-file"]').forEach((label) => label.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); $('trajectory-file').click(); }
  }));
  $('export-csv').addEventListener('click', () => {
    if (!state.data) return;
    const hasEnergy = state.data.frames.some((f) => Number.isFinite(f.potential_kj_mol));
    const rows = [['frame', 'time_ps', 'ca_rmsd_angstrom', ...(hasEnergy ? ['potential_energy_kj_mol'] : [])], ...state.data.frames.map((f, i) => [i + 1, f.time_ps, f.rmsd_angstrom, ...(hasEnergy ? [Number.isFinite(f.potential_kj_mol) ? f.potential_kj_mol : ''] : [])])];
    const blob = new Blob([rows.map((r) => r.join(',')).join('\n') + '\n'], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = 'protein-motion-measurements.csv'; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('app-status').textContent = 'Measurement CSV exported.';
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) setPlaying(false); });
  const resizeObserver = new ResizeObserver(() => { drawMolecule(); drawChart(); }); resizeObserver.observe(canvas); resizeObserver.observe(chart);
  async function initialize() {
    try {
      const embedded = ($('demo-data') || $('trajectory-data'))?.textContent.trim();
      if (window.PROTEIN_MOTION_DATA) loadData(window.PROTEIN_MOTION_DATA);
      else if (embedded) loadData(JSON.parse(embedded));
      else { const response = await fetch('data/demo.json', { cache: 'no-cache' }); if (!response.ok) throw new Error(`Trajectory request returned ${response.status}.`); loadData(await response.json()); }
    } catch (error) { showError(error); }
  }
  initialize();
})();
