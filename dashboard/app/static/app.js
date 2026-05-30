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
    const mq = latest?.payload?.sensors?.mq135;
    const bme = latest?.payload?.sensors?.bme280;
    const gps = latest?.payload?.sensors?.gps;

    // makeField below escapes every dynamic value — a malicious Tree
    // firmware cannot inject HTML/JS into the operator's view by
    // putting markup into a sensor field.

    if (mq) {
      $('#mq135-data').innerHTML =
        makeField('adc_raw',   mq.adc_raw?.toFixed?.(1)      ?? mq.adc_raw) +
        makeField('voltage_v', mq.voltage_v?.toFixed?.(3)    ?? mq.voltage_v) +
        makeField('baseline',  mq.adc_baseline?.toFixed?.(1) ?? mq.adc_baseline) +
        makeField('deviation', mq.adc_dev?.toFixed?.(2)      ?? mq.adc_dev);
    }
    if (bme) {
      $('#bme280-data').innerHTML =
        makeField('temperature', `${bme.temperature_c?.toFixed?.(1) ?? '—'} °C`) +
        makeField('humidity',    `${bme.humidity_pct?.toFixed?.(1) ?? '—'} %`) +
        makeField('pressure',    `${bme.pressure_hpa?.toFixed?.(2) ?? '—'} hPa`) +
        makeField('i2c address', bme.i2c_addr ? `0x${bme.i2c_addr.toString(16)}` : '—');
    }
    if (gps) {
      $('#gps-data').innerHTML =
        makeField('fix',        gps.fix ? 'yes' : 'no') +
        makeField('satellites', gps.satellites ?? '—') +
        (gps.fix ? (
          makeField('lat',   gps.lat?.toFixed?.(6) ?? gps.lat) +
          makeField('lon',   gps.lon?.toFixed?.(6) ?? gps.lon) +
          makeField('alt_m', gps.alt_m?.toFixed?.(1) ?? gps.alt_m) +
          makeField('utc',   gps.utc || '—')
        ) : makeField('age (ms)', gps.fix_age_ms ?? '—'));
    }

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
  async function pollTree() {
    const r = await jget(`/api/tree/${encodeURIComponent(window.NODE_ID)}/latest`);
    if (r.ok) renderTree(r.body);
  }

  function initTreePage() {
    pollTree();
    pollTimer = setInterval(pollTree, 5000);
  }

  return { initProvisionPage, initTreePage };
})();
