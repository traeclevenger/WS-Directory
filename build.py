#!/usr/bin/env python3
"""
Build index.html from families.json + photos.
Run from the WS-Directory repo root:
  python3 build.py
Requires families.json and photos/ to be in ../WS\ Directory/
"""

import json
import re
import shutil
from pathlib import Path

SRC_DIR  = Path(__file__).parent.parent / "WS Directory"
REPO_DIR = Path(__file__).parent
FAMILIES = SRC_DIR / "families.json"

with open(FAMILIES) as f:
    families = json.load(f)

# ── Copy photos ──────────────────────────────────────────────────────────────
dest_photos = REPO_DIR / "photos"
dest_photos.mkdir(exist_ok=True)
copied = 0
for fam in families:
    pf = fam.get("photo_file")
    if pf:
        src = SRC_DIR / pf
        dst = REPO_DIR / pf
        dst.parent.mkdir(exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
print(f"Copied {copied} photos → {dest_photos}")

# ── Build MEMBERS JS array ────────────────────────────────────────────────────
def js_str(s):
    if s is None:
        return "null"
    return json.dumps(str(s))

def phone_digits(phone):
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)

rows = []
for fam in families:
    members_js = []
    for m in fam.get("members", []):
        members_js.append(
            "{"
            f"fn:{js_str(m.get('first_name'))},"
            f"ln:{js_str(m.get('last_name'))},"
            f"nick:{js_str(m.get('nickname'))},"
            f"mbr:{str(bool(m.get('is_member'))).lower()},"
            f"ph:{js_str(m.get('phone'))},"
            f"ph2:{js_str(m.get('phone2'))},"
            f"em:{js_str(m.get('email'))}"
            "}"
        )

    # Build a flat search-text blob from members' phones + emails (for search)
    member_contact = " ".join(filter(None, [
        m.get("phone") for m in fam.get("members", [])
    ] + [
        m.get("phone2") for m in fam.get("members", [])
    ] + [
        m.get("email") for m in fam.get("members", [])
    ]))

    rows.append(
        "{"
        f"name:{js_str(fam['family_name'])},"
        f"addr:{js_str(fam.get('address'))},"
        f"phone:{js_str(fam.get('family_phone'))},"
        f"photoFile:{js_str(fam.get('photo_file'))},"
        f"photoDesc:{js_str(fam.get('photo_description'))},"
        f"memberContact:{js_str(member_contact)},"
        f"members:[{','.join(members_js)}]"
        "}"
    )

members_js_array = "const MEMBERS = [\n  " + ",\n  ".join(rows) + "\n];"

print(f"Built MEMBERS array: {len(rows)} families")

# ── Write index.html ─────────────────────────────────────────────────────────
html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Westside Church Member Directory</title>
<link rel="icon" type="image/png" href="WS favicon.png">
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --accent: #4f8ef7;
    --accent2: #7c5cbf;
    --text: #e8eaf0;
    --subtext: #8a8fa8;
    --border: #2e3248;
    --card-shadow: 0 4px 24px rgba(0,0,0,0.4);
    --radius: 14px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }

  /* HEADER */
  header {
    background: #ffffff;
    border-bottom: 1px solid #d8d8d8;
    padding: 16px 24px 14px;
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 2px 12px rgba(0,0,0,0.12);
  }
  .site-logo { display: block; height: 44px; width: auto; margin-bottom: 12px; }
  .search-wrap { position: relative; }
  .search-wrap svg { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #999; pointer-events: none; }
  #searchInput {
    width: 100%; padding: 11px 14px 11px 42px;
    background: #f3f3f3; border: 1px solid #d0d0d0;
    border-radius: 10px; color: #1a1a1a;
    font-size: 0.95rem; outline: none; transition: border-color 0.2s;
  }
  #searchInput:focus { border-color: #6b9e6b; background: #fff; }
  #searchInput::placeholder { color: #999; }

  /* TABS */
  .tabs { display: flex; gap: 4px; padding: 12px 16px 0; background: var(--surface); border-bottom: 1px solid var(--border); }
  .tab { padding: 9px 18px; border-radius: 8px 8px 0 0; font-size: 0.85rem; font-weight: 600; cursor: pointer; border: 1px solid transparent; border-bottom: none; transition: all 0.2s; color: var(--subtext); background: transparent; }
  .tab.active { background: var(--bg); color: var(--accent); border-color: var(--border); border-bottom-color: var(--bg); }
  .tab:hover:not(.active) { color: var(--text); background: var(--surface2); }

  /* MAIN */
  .main { padding: 16px; }
  .results-count { font-size: 0.8rem; color: var(--subtext); margin-bottom: 14px; padding-left: 2px; }

  /* MEMBER GRID */
  #membersView { display: block; }
  .members-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
  .member-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 16px;
    display: flex; gap: 14px; align-items: flex-start;
    box-shadow: var(--card-shadow);
    transition: transform 0.15s, border-color 0.15s;
    cursor: pointer;
  }
  .member-card:hover { transform: translateY(-2px); border-color: var(--accent); }
  .member-photo {
    width: 72px; height: 72px; border-radius: 10px;
    object-fit: cover; object-position: top;
    flex-shrink: 0;
    background: var(--surface2); border: 2px solid var(--border);
  }
  .member-photo.placeholder { display: flex; align-items: center; justify-content: center; font-size: 26px; color: var(--subtext); }
  .member-info { flex: 1; min-width: 0; }
  .member-name { font-size: 0.95rem; font-weight: 700; color: var(--text); margin-bottom: 5px; line-height: 1.3; }
  .member-detail { display: flex; align-items: flex-start; gap: 6px; font-size: 0.78rem; color: var(--subtext); margin-top: 4px; line-height: 1.4; }
  .member-detail svg { flex-shrink: 0; margin-top: 1px; }
  .highlight { background: rgba(79,142,247,0.25); border-radius: 3px; padding: 0 2px; color: var(--accent); }

  /* MAP */
  #mapView { display: none; }
  #map { width: 100%; height: calc(100vh - 200px); min-height: 400px; border-radius: var(--radius); overflow: hidden; border: 1px solid var(--border); }
  .map-notice { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; text-align: center; margin-bottom: 16px; }
  .map-notice h3 { color: var(--accent); margin-bottom: 8px; }
  .map-notice p { color: var(--subtext); font-size: 0.85rem; line-height: 1.6; }
  .map-notice code { background: var(--surface2); padding: 2px 6px; border-radius: 4px; color: #f0c070; font-size: 0.82rem; }

  /* MODAL */
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000; display: none; align-items: center; justify-content: center; padding: 16px; }
  .modal-overlay.open { display: flex; }
  .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 18px; max-width: 480px; width: 100%; box-shadow: 0 20px 60px rgba(0,0,0,0.6); overflow: hidden; animation: slideUp 0.2s ease; max-height: 90vh; overflow-y: auto; }
  @keyframes slideUp { from { opacity:0; transform:translateY(20px) } to { opacity:1; transform:translateY(0) } }
  .modal-photo { width: 100%; height: 220px; object-fit: cover; object-position: top; background: var(--surface2); display: block; }
  .modal-photo.placeholder-large { display: flex; align-items: center; justify-content: center; font-size: 72px; color: var(--subtext); height: 220px; }
  .modal-body { padding: 20px; }
  .modal-name { font-size: 1.3rem; font-weight: 800; margin-bottom: 16px; color: var(--text); }
  .modal-row { display: flex; gap: 10px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
  .modal-row:last-child { border-bottom: none; }
  .modal-label { color: var(--subtext); min-width: 80px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; padding-top: 1px; }
  .modal-value { color: var(--text); flex: 1; line-height: 1.5; }
  .modal-close { position: absolute; top: 12px; right: 12px; width: 32px; height: 32px; background: rgba(0,0,0,0.5); border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; }
  .modal-wrapper { position: relative; }
  .no-data { color: var(--subtext); font-style: italic; }

  /* MEMBERS TABLE in modal */
  .members-section { margin-top: 4px; }
  .members-section-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--subtext); margin-bottom: 10px; }
  .member-row { padding: 10px 0; border-bottom: 1px solid var(--border); }
  .member-row:last-child { border-bottom: none; }
  .member-row-name { font-weight: 700; font-size: 0.9rem; color: var(--text); margin-bottom: 4px; }
  .member-row-contact { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
  .contact-link {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.8rem; color: var(--accent);
    text-decoration: none; padding: 3px 8px;
    background: rgba(79,142,247,0.12); border-radius: 6px;
    transition: background 0.15s;
  }
  .contact-link:hover { background: rgba(79,142,247,0.25); }
  .contact-link svg { flex-shrink: 0; }

  /* RESPONSIVE */
  @media (max-width: 600px) { .members-grid { grid-template-columns: 1fr; } header h1 { font-size: 1.1rem; } }
</style>
</head>
<body>

<header>
  <img src="WS logo.png" alt="Westside church of Christ" class="site-logo">
  <div class="search-wrap">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input type="text" id="searchInput" placeholder="Search by name, address, phone, email, or photo description…" autocomplete="off">
  </div>
</header>

<div class="tabs">
  <button class="tab active" onclick="switchTab('members')">👥 Members</button>
  <button class="tab" onclick="switchTab('map')">🗺️ Map</button>
</div>

<div class="main">
  <div class="results-count" id="resultsCount"></div>
  <div id="membersView"><div class="members-grid" id="memberGrid"></div></div>
  <div id="mapView">
    <div class="map-notice" id="mapNotice">
      <h3>📍 Member Address Map</h3>
      <p>To enable the interactive map, replace <code>YOUR_API_KEY</code> in the script tag at the bottom of this file with your Google Maps JavaScript API key.<br><br>
      Get one free at <strong>console.cloud.google.com</strong> → APIs &amp; Services → Google Maps JavaScript API.</p>
    </div>
    <div id="map"></div>
  </div>
</div>

<div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
  <div class="modal-wrapper">
    <button class="modal-close" onclick="closeModalBtn()">✕</button>
    <div class="modal" id="modalContent"></div>
  </div>
</div>

<script>
MEMBERS_DATA_PLACEHOLDER

let filtered = [...MEMBERS];
let currentTab = 'members';
let mapInitialized = false;
let map, markers = [], infoWindow;

document.getElementById('searchInput').addEventListener('input', doSearch);

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function highlight(text, query) {
  if (!query || !text) return esc(text || '');
  const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')})`, 'gi');
  return esc(text).replace(re, '<span class="highlight">$1</span>');
}

function phoneDigits(ph) {
  return (ph || '').replace(/\D/g, '');
}

function doSearch() {
  const q = document.getElementById('searchInput').value.trim().toLowerCase();
  if (!q) {
    filtered = [...MEMBERS];
  } else {
    filtered = MEMBERS.filter(m =>
      (m.name || '').toLowerCase().includes(q) ||
      (m.addr || '').toLowerCase().includes(q) ||
      (m.phone || '').toLowerCase().includes(q) ||
      (m.photoDesc || '').toLowerCase().includes(q) ||
      (m.memberContact || '').toLowerCase().includes(q)
    );
  }
  if (currentTab === 'members') {
    renderMembers(filtered, q);
    updateCount(filtered.length);
  } else {
    if (mapInitialized) updateMapMarkers(filtered);
  }
}

function updateCount(n) {
  const total = MEMBERS.length;
  document.getElementById('resultsCount').textContent =
    n === total ? `Showing all ${total} families` : `${n} of ${total} families match`;
}

const addrIcon = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`;
const phoneIcon = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.28h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.88A16 16 0 0 0 14 15l.93-.92a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>`;
const emailIconSm = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>`;
const phoneLinkIcon = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.28h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.88A16 16 0 0 0 14 15l.93-.92a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>`;

renderMembers(MEMBERS);
updateCount(MEMBERS.length);

function renderMembers(list, query='') {
  const grid = document.getElementById('memberGrid');
  if (list.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--subtext)">No families found matching your search.</div>`;
    return;
  }
  grid.innerHTML = list.map(m => {
    const idx = MEMBERS.indexOf(m);
    const photoHtml = m.photoFile
      ? `<img class="member-photo" src="${esc(m.photoFile)}" alt="${esc(m.name)}" loading="lazy">`
      : `<div class="member-photo placeholder">👤</div>`;
    const displayPhone = m.phone || (m.members.length > 0 && m.members[0].ph) || null;
    return `<div class="member-card" onclick="openModal(${idx})">
      ${photoHtml}
      <div class="member-info">
        <div class="member-name">${highlight(m.name, query)}</div>
        ${m.addr ? `<div class="member-detail">${addrIcon}<span>${highlight(m.addr, query)}</span></div>` : ''}
        ${displayPhone ? `<div class="member-detail">${phoneIcon}<span>${highlight(displayPhone, query)}</span></div>` : ''}
      </div>
    </div>`;
  }).join('');
}

function openModal(idx) {
  const m = MEMBERS[idx];
  const photoHtml = m.photoFile
    ? `<img class="modal-photo" src="${esc(m.photoFile)}" alt="${esc(m.name)}">`
    : `<div class="modal-photo placeholder-large">👤</div>`;

  // Build members list HTML
  const membersHtml = m.members.map(mem => {
    const fullName = mem.nick ? `${mem.fn} "${mem.nick}" ${mem.ln}` : `${mem.fn} ${mem.ln}`;
    const contacts = [];
    if (mem.ph) {
      const d = phoneDigits(mem.ph);
      contacts.push(`<a class="contact-link" href="tel:${d}">${phoneLinkIcon}${esc(mem.ph)}</a>`);
    }
    if (mem.ph2) {
      const d = phoneDigits(mem.ph2);
      contacts.push(`<a class="contact-link" href="tel:${d}">${phoneLinkIcon}${esc(mem.ph2)}</a>`);
    }
    if (mem.em) {
      contacts.push(`<a class="contact-link" href="mailto:${esc(mem.em)}">${emailIconSm}${esc(mem.em)}</a>`);
    }
    return `<div class="member-row">
      <div class="member-row-name">${esc(fullName)}</div>
      ${contacts.length ? `<div class="member-row-contact">${contacts.join('')}</div>` : ''}
    </div>`;
  }).join('');

  // Family-level phone (if different from all member phones)
  const memberPhones = new Set(m.members.flatMap(mem => [mem.ph, mem.ph2].filter(Boolean)));
  const showFamilyPhone = m.phone && !memberPhones.has(m.phone);
  const familyPhoneHtml = showFamilyPhone
    ? `<div class="modal-row">
        <span class="modal-label">Home</span>
        <span class="modal-value"><a class="contact-link" href="tel:${phoneDigits(m.phone)}">${phoneLinkIcon}${esc(m.phone)}</a></span>
       </div>`
    : '';

  document.getElementById('modalContent').innerHTML = `
    ${photoHtml}
    <div class="modal-body">
      <div class="modal-name">${esc(m.name)}</div>
      ${m.addr ? `<div class="modal-row"><span class="modal-label">Address</span><span class="modal-value">${esc(m.addr)}</span></div>` : ''}
      ${familyPhoneHtml}
      ${m.members.length ? `<div class="modal-row" style="flex-direction:column;align-items:stretch">
        <div class="members-section">
          <div class="members-section-title">Members</div>
          ${membersHtml}
        </div>
      </div>` : ''}
    </div>`;
  document.getElementById('modalOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeModal(e) { if (e.target === document.getElementById('modalOverlay')) closeModalBtn(); }
function closeModalBtn() { document.getElementById('modalOverlay').classList.remove('open'); document.body.style.overflow = ''; }
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModalBtn(); });

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', ['members','map'][i] === tab));
  document.getElementById('membersView').style.display = tab === 'members' ? 'block' : 'none';
  document.getElementById('mapView').style.display = tab === 'map' ? 'block' : 'none';
  if (tab === 'map' && !mapInitialized && window.googleMapsReady) setupMap();
}

function initMap() { window.googleMapsReady = true; if (currentTab === 'map') setupMap(); }

function setupMap() {
  mapInitialized = true;
  document.getElementById('mapNotice').style.display = 'none';
  map = new google.maps.Map(document.getElementById('map'), {
    center: { lat: 32.8, lng: -97.0 }, zoom: 10,
    styles: [
      { elementType:'geometry', stylers:[{color:'#1a1d27'}] },
      { elementType:'labels.text.stroke', stylers:[{color:'#1a1d27'}] },
      { elementType:'labels.text.fill', stylers:[{color:'#8a8fa8'}] },
      { featureType:'road', elementType:'geometry', stylers:[{color:'#2e3248'}] },
      { featureType:'road', elementType:'labels.text.fill', stylers:[{color:'#6b7094'}] },
      { featureType:'water', elementType:'geometry', stylers:[{color:'#0f1117'}] },
      { featureType:'poi', stylers:[{visibility:'off'}] },
      { featureType:'transit', stylers:[{visibility:'off'}] }
    ]
  });
  infoWindow = new google.maps.InfoWindow();
  geocodeAndPlot(MEMBERS);
}

function geocodeAndPlot(list) {
  const geocoder = new google.maps.Geocoder();
  markers.forEach(m => m.setMap(null));
  markers = [];
  list.filter(m => m.addr).forEach((m, i) => {
    setTimeout(() => {
      geocoder.geocode({ address: m.addr + ', TX' }, (results, status) => {
        if (status === 'OK') {
          const pos = results[0].geometry.location;
          const marker = new google.maps.Marker({
            position: pos, map, title: m.name,
            icon: { path: google.maps.SymbolPath.CIRCLE, scale: 8, fillColor: '#4f8ef7', fillOpacity: 0.9, strokeColor: '#fff', strokeWeight: 2 }
          });
          const photoHtml = m.photoFile
            ? `<img src="${esc(m.photoFile)}" style="width:60px;height:60px;border-radius:8px;object-fit:cover;object-position:top;float:left;margin-right:10px;">`
            : '';
          marker.addListener('click', () => {
            infoWindow.setContent(`<div style="font-family:sans-serif;color:#111;max-width:220px">
              ${photoHtml}
              <strong>${esc(m.name)}</strong><br>
              <span style="font-size:12px;color:#555">${esc(m.addr)}</span><br>
              ${m.phone ? `<span style="font-size:12px">📞 ${esc(m.phone)}</span>` : ''}
            </div>`);
            infoWindow.open(map, marker);
          });
          markers.push(marker);
        }
      });
    }, i * 150);
  });
}

function updateMapMarkers(list) { markers.forEach(m => m.setMap(null)); markers = []; geocodeAndPlot(list); }
</script>
<script async defer src="https://maps.googleapis.com/maps/api/js?key=AIzaSyAW6GTHyk6J7Xp4yp2t-9PE1l_YXuNH40Q&callback=initMap"></script>
</body>
</html>"""

html = html.replace('MEMBERS_DATA_PLACEHOLDER', members_js_array)

out = REPO_DIR / "index.html"
out.write_text(html, encoding="utf-8")
print(f"Written → {out}  ({out.stat().st_size // 1024} KB)")
