const $ = (id) => document.getElementById(id);

async function api(path, body) {
  const opts = body
    ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    : {};
  const res = await fetch(path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

function fillAdapters(state) {
  const sel = $("adapter");
  const current = sel.value;
  sel.innerHTML = "";
  const adapters = state.adapters || [];
  if (!adapters.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = state.mode === "demo" ? "Ethernet (Demo)" : "Kart bulunamadı";
    sel.appendChild(opt);
    return;
  }
  for (const a of adapters) {
    const opt = document.createElement("option");
    opt.value = a.name;
    const ip = (a.ipv4 && a.ipv4[0]) || a.status || "";
    opt.textContent = ip ? `${a.name} · ${ip}` : a.name;
    sel.appendChild(opt);
  }
  const prefer = current || state.selected;
  if (prefer) sel.value = prefer;
}

function render(state) {
  fillAdapters(state);
  if (state.mode === "demo") $("demo").checked = true;

  const local = state.local || {};
  const nb = state.neighbor || {};
  const traffic = state.traffic || {};

  $("sw-name").textContent = nb.switch_name || "—";
  $("sw-desc").textContent = nb.switch_description || nb.platform || (nb.protocol ? `${nb.protocol} komşusu` : "Komşu ilanı yok");
  $("sw-port").textContent = nb.port_id || "—";
  $("sw-port-desc").textContent = nb.port_description || (nb.mgmt_ips && nb.mgmt_ips[0] ? `Yönetim: ${nb.mgmt_ips.join(", ")}` : "LLDP / CDP");

  const vlanLocal = local.vlan_id;
  const vlanNb = nb.vlan_id;
  const vlanSeen = Object.keys(traffic.vlans || {});
  $("vlan").textContent = vlanNb ?? vlanLocal ?? (vlanSeen[0] || "—");
  const extras = [];
  if (vlanNb != null) extras.push(`LLDP/CDP native ${vlanNb}`);
  if (vlanLocal != null) extras.push(`kart ${vlanLocal}`);
  if (vlanSeen.length) extras.push(`etiketler: ${vlanSeen.join(", ")}`);
  $("vlan-extra").textContent = extras.join(" · ") || "VLAN bilgisi yok";

  $("ip").textContent = (local.ipv4 && local.ipv4[0]) || "—";
  const ipBits = [local.dhcp, local.gateway ? `gw ${local.gateway}` : "", (local.dns || []).join(", ")]
    .filter(Boolean);
  $("ip-extra").textContent = ipBits.join(" · ") || "Adres yok";

  if (nb.mgmt_ips && nb.mgmt_ips[0] && !$("snmp-host").value) {
    $("snmp-host").value = nb.mgmt_ips[0];
  }

  const notes = state.notes || [];
  $("notes").hidden = notes.length === 0;
  $("notes").innerHTML = notes.map((n) => `<div>${escapeHtml(n)}</div>`).join("");

  const byProto = traffic.by_proto || {};
  const total = Object.values(byProto).reduce((a, b) => a + b, 0) || 1;
  const protoEl = $("protos");
  const keys = Object.keys(byProto);
  if (!keys.length) {
    protoEl.className = "bars empty";
    protoEl.textContent = "Henüz kare yok";
  } else {
    protoEl.className = "bars";
    protoEl.innerHTML = keys
      .map((k) => {
        const n = byProto[k];
        const pct = Math.round((n / total) * 100);
        return `<div class="bar-row"><span>${escapeHtml(k)}</span><div class="bar"><i style="width:${pct}%"></i></div><span>${n}</span></div>`;
      })
      .join("");
  }

  const talkers = traffic.talkers || [];
  const talkEl = $("talkers");
  if (!talkers.length) {
    talkEl.className = "list empty";
    talkEl.textContent = "Henüz kare yok";
  } else {
    talkEl.className = "list";
    talkEl.innerHTML = talkers
      .map((t) => `<div><span>${escapeHtml(t.addr)}</span><span>${t.packets}</span></div>`)
      .join("");
  }

  const recent = traffic.recent || [];
  $("pkt-count").textContent = traffic.packets ? `${traffic.packets} kare · ${traffic.bytes} bayt` : "";
  $("recent").innerHTML = recent
    .map(
      (r) =>
        `<tr><td>${escapeHtml(r.src_mac)}</td><td>${escapeHtml(r.dst_mac)}</td><td>${(r.vlans || []).join(", ") || "—"}</td><td>${escapeHtml(r.proto)}</td><td>${escapeHtml(r.summary)}</td></tr>`
    )
    .join("");

  $("listen").textContent = state.listening ? "Dinlemeyi durdur" : "Canlı dinle";
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function scan() {
  const btn = $("scan");
  btn.disabled = true;
  btn.textContent = "Taranıyor…";
  try {
    const state = await api("/api/scan", {
      adapter: $("adapter").value,
      demo: $("demo").checked,
      seconds: 4,
    });
    render(state);
  } catch (err) {
    $("notes").hidden = false;
    $("notes").textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Portu Tara";
  }
}

async function toggleListen() {
  const listening = $("listen").textContent.includes("durdur");
  const state = await api("/api/listen", {
    adapter: $("adapter").value,
    demo: $("demo").checked,
    on: !listening,
  });
  render(state);
}

async function snmp() {
  const out = $("snmp-out");
  out.hidden = false;
  out.textContent = "Sorgulanıyor…";
  try {
    const data = await api("/api/snmp", {
      host: $("snmp-host").value,
      community: $("snmp-comm").value,
    });
    out.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    out.textContent = err.message;
  }
}

$("scan").addEventListener("click", scan);
$("listen").addEventListener("click", toggleListen);
$("snmp").addEventListener("click", snmp);

api("/api/state").then((state) => {
  render(state);
  if (!state.local && !state.neighbor) {
    // İlk açılışta adaptörleri taze çek
    api("/api/adapters").then(render).catch(() => {});
  }
});

setInterval(async () => {
  try {
    const state = await api("/api/state");
    if (state.listening || state.mode === "demo") render(state);
  } catch {
    /* ignore */
  }
}, 2000);
