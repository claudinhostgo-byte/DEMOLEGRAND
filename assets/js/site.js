/* ============================================================
   site.js - sitio maestro (index.html) y consola de leads (admin.html)
   ============================================================ */
(function () {
  "use strict";

  var CFG = window.DEMO_CONFIG || {};
  var LEADS_KEY = "witdemo.leads";

  /* Un color por landing, bien separados entre si: verde azulado, rojo,
     ambar y azul. Debe coincidir con los temas de site.css. */
  var TEMA_COLOR = {
    legrand: "#66A79E",
    teknica: "#F5333F",
    industria: "#F2A007",
    bticino: "#00A0DF",
    wit: "#74E507"
  };
  var CODIGO_COLOR = {
    "LGD-DC-001": "#66A79E",
    "TKN-UPS-002": "#F5333F",
    "LGD-IND-003": "#F2A007",
    "LGD-RET-004": "#00A0DF"
  };
  var BRAND_LABEL = {
    legrand: "Legrand",
    teknica: "Teknica",
    bticino: "Bticino",
    wit: "W-IT"
  };

  /* Copia de respaldo del catalogo: solo se usa si no se puede leer
     landings.json (por ejemplo al abrir el HTML con doble clic, file://). */
  var FALLBACK = {
    defaults: { leadsourcecode: 8 },
    landings: [
      { code: "LGD-DC-001", theme: "legrand", brand: "legrand", name: "Data Center e Infraestructura Digital",
        tagline: "Cableado estructurado LCS3, racks y distribucion de energia para data centers",
        url: "landings/datacenter.html", owner_team: "Infraestructura Digital", campaign: "DC-2026-Q3" },
      { code: "TKN-UPS-002", theme: "teknica", brand: "teknica", name: "UPS, Power Quality y Continuidad Operacional",
        tagline: "Respaldo de energia, calidad de energia y mantencion de infraestructura critica",
        url: "landings/ups-continuidad.html", owner_team: "Teknica - Continuidad Operacional", campaign: "UPS-2026-Q3" },
      { code: "LGD-IND-003", theme: "industria", brand: "legrand", name: "Industria: Distribucion de Energia y Tableros",
        tagline: "Proteccion modular, ductos de barra, canalizacion y bandejas para industria y mineria",
        url: "landings/industria.html", owner_team: "Industria y Proyectos", campaign: "IND-2026-Q3" },
      { code: "LGD-RET-004", theme: "bticino", brand: "bticino", name: "Retail, Hospitales y Edificios",
        tagline: "Soluciones Bticino para el sector terciario: retail, salud, hoteleria y oficinas",
        url: "landings/retail-terciario.html", owner_team: "Terciario y Retail", campaign: "RET-2026-Q3" }
    ]
  };

  function plural(n, uno, muchos) { return n + " " + (n === 1 ? uno : muchos); }

  function esc(text) {
    return String(text === undefined || text === null ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function loadCatalog() {
    var base = (CFG.apiBaseUrl || "").replace(/\/$/, "");
    return fetch(base + (CFG.landingsEndpoint || "/api/landings"), { cache: "no-store" })
      .then(function (r) { if (!r.ok) { throw new Error("HTTP " + r.status); } return r.json(); })
      .catch(function () { return FALLBACK; });
  }

  /* ---------- Tarjetas de las 4 landings ---------- */
  function renderCards(catalog) {
    var host = document.getElementById("landing-cards");
    if (!host) { return; }

    host.innerHTML = catalog.landings.map(function (l, i) {
      var color = CODIGO_COLOR[l.code] || TEMA_COLOR[l.theme || l.brand] || TEMA_COLOR.wit;
      return '' +
        /* Sin UTM inyectados: navegar dentro del sitio no debe pisar la
           campana real con la que llego el visitante. */
        '<a class="card lcard" style="--c:' + color + '" href="' + esc(l.url) + '">' +
          '<span class="bar"></span>' +
          '<span class="chip chip-accent" style="align-self:flex-start">' +
            esc(BRAND_LABEL[l.brand] || l.brand) + '</span>' +
          '<span class="code">' + esc(l.code) + '</span>' +
          '<h3>' + esc(l.name) + '</h3>' +
          '<p class="muted small">' + esc(l.tagline) + '</p>' +
          '<span class="meta">' +
            '<span>Equipo: ' + esc(l.owner_team || "-") + '</span>' +
            '<span class="go">Landing ' + (i + 1) + ' &rarr;</span>' +
          '</span>' +
        '</a>';
    }).join("");
  }

  /* ---------- Estado de la API ---------- */
  function renderHealth() {
    var host = document.getElementById("api-health");
    if (!host) { return; }
    var base = (CFG.apiBaseUrl || "").replace(/\/$/, "");

    fetch(base + "/api/health", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (h) {
        var modo = String(h.mode || "").toUpperCase();
        var destino = h.mode === "dataverse"
          ? "escribe en " + esc(h.dataverse.url)
          : "no escribe en CRM (modo demostracion)";
        host.innerHTML =
          '<span class="chip chip-accent">API en linea</span> ' +
          '<span class="chip">Modo: ' + esc(modo) + '</span> ' +
          '<span class="chip">' + destino + '</span> ' +
          '<span class="chip">' + (h.landings || []).length + ' landings registradas</span>';
      })
      .catch(function () {
        host.innerHTML =
          '<span class="chip">API no disponible</span> ' +
          '<span class="chip">La demo respondera en modo SIMULADO en el navegador</span> ' +
          '<span class="chip mono">levantar con run-demo.cmd</span>';
      });
  }

  /* ---------- Origen capturado en la sesion ---------- */
  function renderOrigin() {
    var box = document.getElementById("origin-json");
    if (!box) { return; }
    var t = {};
    try { t = JSON.parse(sessionStorage.getItem("witdemo.tracking") || "{}"); } catch (e) { t = {}; }
    if (!Object.keys(t).length) {
      t = { referrer: document.referrer || "(directo)", landingUrl: window.location.href };
    }
    box.textContent = JSON.stringify(t, null, 2);
  }

  /* ---------- Consola de leads (admin.html) ---------- */
  function renderAdmin() {
    var tbody = document.getElementById("leads-body");
    if (!tbody) { return; }
    var base = (CFG.apiBaseUrl || "").replace(/\/$/, "");
    var source = document.getElementById("leads-source");

    fetch(base + "/api/leads", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (source) {
          source.innerHTML = '<span class="chip chip-accent">Fuente: API (' +
            esc(d.mode) + ')</span> <span class="chip">' + plural(d.count, "lead", "leads") + '</span>';
        }
        paint(tbody, (d.leads || []).map(function (l) {
          return {
            at: l.receivedAt, leadId: l.leadId, mode: l.mode, landingCode: l.landingCode,
            name: (l.contact || {}).name, email: (l.contact || {}).email,
            company: (l.contact || {}).company, tracking: l.tracking || {},
            fields: l.fields || {}, recordUrl: l.recordUrl
          };
        }));
      })
      .catch(function () {
        var local = [];
        try { local = JSON.parse(localStorage.getItem(LEADS_KEY) || "[]"); } catch (e) { local = []; }
        if (source) {
          source.innerHTML = '<span class="chip">Fuente: navegador (localStorage)</span> ' +
            '<span class="chip">' + plural(local.length, "lead", "leads") + '</span> ' +
            '<span class="chip">API no disponible</span>';
        }
        paint(tbody, local);
      });
  }

  function paint(tbody, leads) {
    if (!leads.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="muted" style="padding:28px">' +
        'Aun no hay leads capturados. Completa uno de los 4 formularios y vuelve aqui.</td></tr>';
      return;
    }
    tbody.innerHTML = leads.map(function (l) {
      var t = l.tracking || {};
      var utm = ["utm_source", "utm_medium", "utm_campaign"].map(function (k) {
        return t[k] ? k.replace("utm_", "") + ": " + esc(t[k]) : null;
      }).filter(Boolean).join(" &middot; ");
      var extras = Object.keys(l.fields || {}).map(function (k) {
        return '<span class="chip">' + esc(k) + ": " + esc(l.fields[k]) + "</span>";
      }).join(" ");
      var color = CODIGO_COLOR[l.landingCode] || "#5C6670";

      return "<tr>" +
        '<td class="small mono">' + esc((l.at || l.receivedAt || "").replace("T", " ").replace("+00:00", "")) + "</td>" +
        '<td><span class="chip" style="border-color:' + color + ';color:' + color + '">' +
          esc(l.landingCode) + "</span></td>" +
        "<td><b>" + esc(l.name) + "</b><br><span class='small muted'>" + esc(l.email) + "</span></td>" +
        "<td>" + esc(l.company) + "</td>" +
        '<td class="small">' + (utm || '<span class="muted">sin parametros</span>') +
          (extras ? "<div style='margin-top:6px'>" + extras + "</div>" : "") + "</td>" +
        '<td class="small mono">' + esc(l.leadId || "-") +
          '<br><span class="chip">' + esc(l.mode || "-") + "</span>" +
          (l.recordUrl ? '<br><a href="' + esc(l.recordUrl) + '" target="_blank">abrir en D365</a>' : "") +
        "</td>" +
      "</tr>";
    }).join("");
  }

  function wireAdminActions() {
    var refresh = document.getElementById("btn-refresh");
    if (refresh) { refresh.addEventListener("click", renderAdmin); }
    var clear = document.getElementById("btn-clear-local");
    if (clear) {
      clear.addEventListener("click", function () {
        try { localStorage.removeItem(LEADS_KEY); } catch (e) { /* noop */ }
        renderAdmin();
      });
    }
  }

  /* ---------- Arranque ---------- */
  function boot() {
    loadCatalog().then(renderCards);
    renderHealth();
    renderOrigin();
    renderAdmin();
    wireAdminActions();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
})();
