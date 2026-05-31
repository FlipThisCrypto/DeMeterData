// SPDX-License-Identifier: Apache-2.0
// Orchard View — vanilla JS for the provisioning wizard and live Tree view.
//
// XSS posture: every dynamic value rendered through innerHTML below is
// passed through esc() first. makeField/makeStep escape their args
// internally. Sensor values come from Tree firmware POST bodies which
// are not under our control — a compromised or hostile Tree must not
// be able to script the operator's (or a public viewer's) browser.

const OrchardView = (() => {

  // -------------------------- tiny helpers --------------------------

  function $(sel, root = document) { return root.querySelector(sel); }

  // HTML-escape a value for safe inclusion inside an HTML attribute or
  // element body. Treats null/undefined as empty. Numbers and booleans
  // are stringified by String(). Anything else gets the five-char
  // escape table applied.
  function esc(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;',
      '"': '&quot;', "'": '&#39;',
    })[c]);
  }

  async function jget(url) {
    const r = await fetch(url, { method: 'GET' });
    return { ok: r.ok, status: r.status, body: await r.json().catch(() => ({})) };
  }

  async function jpost(url, body) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    return { ok: r.ok, status: r.status, body: await r.json().catch(() => ({})) };
  }

  function relativeAge(iso) {
    if (!iso) return '—';
    const then = Date.parse(iso);
    if (isNaN(then)) return iso;
    const ageSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
    if (ageSec < 5) return 'just now';
    if (ageSec < 60) return `${ageSec}s ago`;
    if (ageSec < 3600) return `${Math.floor(ageSec / 60)}m ago`;
    return `${Math.floor(ageSec / 3600)}h ago`;
  }

  // Build a k/v row. Both args are HTML-escaped; pass {mono: true} to
  // give the value a monospaced font (via class, not by injecting a
  // <span> wrapper from the caller).
  function makeField(k, v, opts = {}) {
    const vCls = opts.mono ? 'v mono' : 'v';
    const vText = (v === null || v === undefined || v === '') ? '—' : v;
    return `<div class="field"><div class="k">${esc(k)}</div>` +
           `<div class="${vCls}">${esc(vText)}</div></div>`;
  }

  function makeStep(label, state, msg = '') {
    const icon = state === 'done' ? '✓' : state === 'doing' ? '…' : state === 'err' ? '✗' : '·';
    return `<div class="step-status ${esc(state)}">` +
           `<span class="icon">${icon}</span> ${esc(label)} ` +
           (msg ? `<span class="muted">— ${esc(msg)}</span>` : '') +
           `</div>`;
  }

  // -------------------------- provision page -------------------------

  async function refreshPorts() {
    const sel = $('#port-select');
    sel.innerHTML = '';
    const r = await jget('/api/serial/ports');
    if (!r.ok) {
      sel.innerHTML = '<option value="">(error listing ports)</option>';
      return;
    }
    const ports = r.body.ports || [];
    if (!ports.length) {
      sel.innerHTML = '<option value="">(no serial ports)</option>';
      return;
    }
    for (const p of ports) {
      const opt = document.createElement('option');
      opt.value = p.device;
      opt.textContent = `${p.device} — ${p.description || ''}`;
      sel.appendChild(opt);
    }
  }

  let identified = null;  // { node_id, signing_key_hex, status }

  async function onIdentify() {
    const port = $('#port-select').value;
    const out = $('#identify-result');
    out.innerHTML = '<div class="muted">Talking to Tree…</div>';
    const r = await jpost('/api/serial/identify', { port });
    if (!r.ok) {
      out.innerHTML = `<div class="err">${esc(r.body.error || 'failed')}</div>`;
      return;
    }
    identified = { ...r.body, port };
    // Every dynamic value below is server-controlled (it came from the
    // Tree over USB) — esc() guards against a malicious Tree firmware
    // that puts HTML/JS into its identity fields.
    const sk = r.body.signing_key_hex || '';
    out.innerHTML =
      makeField('node_id',     r.body.node_id, {mono: true}) +
      makeField('signing_key', sk ? `${sk.slice(0, 16)}…` : '—', {mono: true}) +
      makeField('fw',          r.body.status?.fw) +
      makeField('wifi',        r.body.status?.wifi) +
      makeField('oracle url',  r.body.status?.oracle || '(unset)');
    $('#step-config').hidden = false;
  }

  async function onProvision() {
    const port = identified?.port;
    if (!identified) return;
    const ssid = $('#ssid').value.trim();
    const password = $('#password').value;
    const oracleUrl = $('#oracle-url').value.trim();
    const label = $('#label').value.trim();
    const wallet = $('#wallet').value.trim();

    if (!ssid) { alert('WiFi SSID is required'); return; }
    if (!oracleUrl) { alert('Oracle URL is required'); return; }

    const progress = $('#provision-progress');
    const btn = $('#provision-btn');
    btn.disabled = true;
    progress.innerHTML = '';

    function setStep(idx, label, state, msg = '') {
      const slots = progress.querySelectorAll('.step-status');
      const html = makeStep(label, state, msg);
      if (slots[idx]) slots[idx].outerHTML = html;
      else progress.insertAdjacentHTML('beforeend', html);
    }

    setStep(0, 'Register with oracle', 'doing');
    let r = await jpost('/api/oracle/register', {
      node_id: identified.node_id,
      signing_key_hex: identified.signing_key_hex,
      label: label || null,
      wallet_address: wallet || null,
      fw_version: identified.status?.fw || null,
    });
    if (!r.ok) { setStep(0, 'Register with oracle', 'err', r.body.error || `HTTP ${r.status}`); btn.disabled = false; return; }
    setStep(0, 'Register with oracle', 'done', r.body.register?.new ? 'new' : 'updated');

    setStep(1, 'Push WiFi credentials', 'doing');
    r = await jpost('/api/serial/wifi', { port, ssid, password });
    if (!r.ok) { setStep(1, 'Push WiFi credentials', 'err', r.body.error); btn.disabled = false; return; }
    setStep(1, 'Push WiFi credentials', 'done');

    setStep(2, 'Push oracle URL', 'doing');
    r = await jpost('/api/serial/oracle', { port, url: oracleUrl });
    if (!r.ok) { setStep(2, 'Push oracle URL', 'err', r.body.error); btn.disabled = false; return; }
    setStep(2, 'Push oracle URL', 'done');

    setStep(3, 'Trigger first sample', 'doing');
    r = await jpost('/api/serial/sample', { port });
    if (!r.ok) { setStep(3, 'Trigger first sample', 'err', r.body.error); btn.disabled = false; return; }
    setStep(3, 'Trigger first sample', 'done');

    setStep(4, 'Done — opening live view…', 'done');
    setTimeout(() => { window.location.href = `/tree/${encodeURIComponent(identified.node_id)}`; }, 800);
  }

  function initProvisionPage() {
    $('#refresh-ports').addEventListener('click', refreshPorts);
    $('#identify-btn').addEventListener('click', onIdentify);
    $('#provision-btn').addEventListener('click', onProvision);
    refreshPorts();
  }

  // -------------------------- tree (live) page -----------------------

  // ---- Temperature unit preference (localStorage-persisted) -------
  // Stored as 'c' (Celsius, default) or 'f' (Fahrenheit). The toggle
  // button on the Tree page flips this and re-renders immediately;
  // the choice survives page reloads but is per-browser (no server
  // round-trip — sensible for a per-operator viewing preference).
  const TEMP_UNIT_KEY = 'orchard.tempUnit';

  function getTempUnit() {
    try {
      return (localStorage.getItem(TEMP_UNIT_KEY) === 'f') ? 'f' : 'c';
    } catch {
      return 'c';   // localStorage unavailable (private mode, etc.)
    }
  }
  function setTempUnit(u) {
    try { localStorage.setItem(TEMP_UNIT_KEY, u); } catch {}
  }

  // Format a Celsius value for display, respecting the current
  // operator preference. Numbers come off the wire as Celsius (the
  // firmware's native unit and the SI standard); conversion happens
  // only at display time, so the stored data in the oracle DB stays
  // unit-canonical.
  function formatTemp(c, decimals = 1) {
    if (c === null || c === undefined) return '—';
    const u = getTempUnit();
    const v = (u === 'f') ? c * 9 / 5 + 32 : c;
    return `${v.toFixed(decimals)} °${u.toUpperCase()}`;
  }

  // Per-sensor render config. Adding a new known sensor = add a key
  // here with its display title and field list; the dashboard tile
  // appears automatically the next time a Tree reports that sensor.
  // Unknown sensor names fall through to a generic auto-tile that
  // renders every field as-is.
  //
  // Field formats are functions so we can compose units (`${v} °C`)
  // and precision (`.toFixed(2)`). null/undefined values render as
  // an em-dash via makeField's null check.
  const SENSOR_TILES = {
    mq135: {
      title: "MQ-135 — air quality",
      fields: [
        ["adc_raw",      v => v?.toFixed?.(1) ?? v],
        ["voltage_v",    v => v?.toFixed?.(3) ?? v],
        ["baseline",     v => v?.toFixed?.(1) ?? v,   "adc_baseline"],
        ["deviation",    v => v?.toFixed?.(2) ?? v,   "adc_dev"],
      ],
    },
    bme280: {
      title: "BME280 — temp / humidity / pressure",
      fields: [
        ["temperature",  v => formatTemp(v, 1),                  "temperature_c"],
        ["humidity",     v => `${v?.toFixed?.(1) ?? "—"} %`,     "humidity_pct"],
        ["pressure",     v => `${v?.toFixed?.(2) ?? "—"} hPa`,   "pressure_hpa"],
        ["i2c address",  v => v ? `0x${v.toString(16)}` : "—",   "i2c_addr"],
      ],
    },
    ds18b20: {
      title: "DS18B20 — 1-Wire temperature probe",
      fields: [
        ["temperature",   v => formatTemp(v, 2),                  "temperature_c"],
        ["probes on bus", v => v,                                 "device_count"],
        ["rom id",        v => v,                                 "rom_id"],
      ],
    },
    gps: {
      title: "GPS",
      // GPS is special: when fix=false we want to show different fields.
      // Use a custom render to handle that branch cleanly.
      render: (gps) => {
        let html =
          makeField("fix",        gps.fix ? "yes" : "no") +
          makeField("satellites", gps.satellites ?? "—");
        if (gps.fix) {
          html +=
            makeField("lat",   gps.lat?.toFixed?.(6) ?? gps.lat) +
            makeField("lon",   gps.lon?.toFixed?.(6) ?? gps.lon) +
            makeField("alt_m", gps.alt_m?.toFixed?.(1) ?? gps.alt_m) +
            makeField("utc",   gps.utc || "—");
        } else {
          html += makeField("age (ms)", gps.fix_age_ms ?? "—");
        }
        return html;
      },
    },
  };

  function renderSensorCard(sensorName, data) {
    const cfg = SENSOR_TILES[sensorName];
    const title = cfg?.title ?? sensorName;
    let body;
    if (cfg?.render) {
      body = cfg.render(data);
    } else if (cfg?.fields) {
      body = cfg.fields.map(([label, fmt, key]) => {
        // Triplet form: [display label, formatter, payload key].
        // Doublet form: [display label, formatter] uses label as key.
        const payloadKey = key ?? label;
        const raw = data[payloadKey];
        const formatted = (raw === null || raw === undefined)
          ? undefined
          : (fmt ? fmt(raw) : raw);
        return makeField(label, formatted);
      }).join("");
    } else {
      // Unknown sensor — auto-tile from every key in the payload.
      // This is the "future-proof" path: a new sensor on the Tree
      // shows up on the dashboard with no code change.
      body = Object.entries(data).map(([k, v]) => makeField(k, v)).join("");
    }
    // makeField escapes every dynamic value, so a malicious Tree can't
    // inject HTML/JS via a sensor field.
    return `<div class="card"><h3>${esc(title)}</h3>${body}</div>`;
  }

  function renderSensors(sensors) {
    const grid = $("#sensor-grid");
    if (!grid) return;
    // Stable display order: render known sensors in SENSOR_TILES order
    // first, then anything else alphabetically. Keeps the tile layout
    // from jumping around between polls when sensor key order changes.
    const known   = Object.keys(SENSOR_TILES).filter(k => k in sensors);
    const unknown = Object.keys(sensors)
                      .filter(k => !(k in SENSOR_TILES))
                      .sort();
    const order   = [...known, ...unknown];
    if (order.length === 0) {
      grid.innerHTML =
        `<div class="card"><span class="muted">Waiting for first reading…</span></div>`;
      return;
    }
    grid.innerHTML = order
      .map(name => renderSensorCard(name, sensors[name]))
      .join("");
  }

  function renderTree(data) {
    const aliveDot = $('#alive-light');
    const aliveLbl = $('#alive-label');
    if (data.alive) {
      aliveDot.className = 'dot dot-green'; aliveLbl.textContent = 'Alive';
    } else if (data.latest) {
      aliveDot.className = 'dot dot-red'; aliveLbl.textContent = 'Stale (no recent reading)';
    } else {
      aliveDot.className = 'dot dot-grey'; aliveLbl.textContent = 'Waiting for first reading…';
    }
    $('#last-age').textContent = 'Last reading: ' + (data.last_received_at ? relativeAge(data.last_received_at) : '—');

    if (data.uptime) {
      $('#uptime-line').textContent = `Uptime this Season: ${data.uptime.hours_online} / 24 hours`;
    }

    const latest = data.latest;
    const sensors = latest?.payload?.sensors ?? {};
    renderSensors(sensors);

    const tbody = $('#readings-body');
    if (data.readings?.length) {
      tbody.innerHTML = data.readings.map(r => {
        const m = r.payload?.sensors?.mq135 || {};
        const g = r.payload?.sensors?.gps || {};
        // Every column escapes; numbers stringify safely, but firmware
        // could in principle put strings in these fields.
        return `<tr>` +
          `<td class="mono">${esc(r.received_at)}</td>` +
          `<td>${esc(m.adc_raw?.toFixed?.(1) ?? '—')}</td>` +
          `<td>${g.fix ? '✓' : '·'}</td>` +
          `<td>${esc(g.lat?.toFixed?.(4) ?? '—')}</td>` +
          `<td>${esc(g.lon?.toFixed?.(4) ?? '—')}</td>` +
        `</tr>`;
      }).join('');
    }

    if (latest) {
      // textContent never executes — safe for arbitrary JSON.
      $('#readings-raw').textContent = JSON.stringify(latest.payload, null, 2);
    }
  }

  let pollTimer = null;
  let lastTreeData = null;     // cached so the toggle can re-render
                               // immediately without waiting for poll
  async function pollTree() {
    const r = await jget(`/api/tree/${encodeURIComponent(window.NODE_ID)}/latest`);
    if (r.ok) {
      lastTreeData = r.body;
      renderTree(r.body);
    }
  }

  function updateTempUnitButton() {
    const btn = $('#temp-unit-toggle');
    if (!btn) return;
    btn.textContent = `°${getTempUnit().toUpperCase()}`;
  }

  function initTreePage() {
    updateTempUnitButton();
    const btn = $('#temp-unit-toggle');
    if (btn) {
      btn.addEventListener('click', () => {
        setTempUnit(getTempUnit() === 'c' ? 'f' : 'c');
        updateTempUnitButton();
        // Re-render the cached payload immediately so the operator
        // sees the unit flip without a 5-second wait.
        if (lastTreeData) renderTree(lastTreeData);
      });
    }
    pollTree();
    pollTimer = setInterval(pollTree, 5000);
  }

  return { initProvisionPage, initTreePage };
})();
