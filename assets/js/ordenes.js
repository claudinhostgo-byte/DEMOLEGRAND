/* ============================================================
   ordenes.js - consulta de ordenes de trabajo (Field Service)
   Llama a la MISMA API de la demo: GET /api/clientes y /api/workorders.
   La pagina nunca habla con Dynamics: solo la API tiene credenciales.
   ============================================================ */
(function () {
  "use strict";

  var CFG = window.DEMO_CONFIG || {};
  var base = (CFG.apiBaseUrl || "").replace(/\/$/, "");

  var ESTADO_COLOR = {
    690970000: "#8A94A0",  // Sin programar
    690970001: "#0B53CE",  // Programada
    690970002: "#B26A00",  // En curso
    690970003: "#14603A",  // Completada
    690970004: "#3F4A56",  // Registrada
    690970005: "#8C1420"   // Cancelada
  };

  function $(id) { return document.getElementById(id); }

  function esc(t) {
    return String(t === undefined || t === null ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function fecha(iso) {
    if (!iso) { return "-"; }
    var d = new Date(iso);
    if (isNaN(d)) { return iso; }
    return d.toLocaleDateString("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function hora(iso) {
    if (!iso) { return ""; }
    var d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" });
  }

  function iso(d) { return d.toISOString().slice(0, 10); }

  /* ---------- Carga de los selectores ---------- */
  function cargarFiltros() {
    return fetch(base + "/api/clientes", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { throw new Error(d.error || "sin datos"); }
        var sc = $("f-cliente");
        d.clientes.forEach(function (c) {
          var o = document.createElement("option");
          o.value = c.id; o.textContent = c.nombre;
          sc.appendChild(o);
        });
        var se = $("f-estado");
        (d.estados || []).forEach(function (e) {
          var o = document.createElement("option");
          o.value = e.codigo; o.textContent = e.nombre;
          se.appendChild(o);
        });
      })
      .catch(function (err) {
        $("resumen").innerHTML = '<span class="chip">No se pudieron cargar los filtros: ' +
          esc(err.message) + "</span>";
      });
  }

  /* ---------- Consulta ---------- */
  function parametros() {
    var p = {};
    ["cliente", "desde", "hasta", "estado"].forEach(function (k) {
      var v = ($("f-" + k).value || "").trim();
      if (v) { p[k] = v; }
    });
    return p;
  }

  function buscar() {
    var p = parametros();
    var qs = Object.keys(p).map(function (k) {
      return encodeURIComponent(k) + "=" + encodeURIComponent(p[k]);
    }).join("&");
    var url = base + "/api/workorders" + (qs ? "?" + qs : "");

    $("trace-consulta").textContent = JSON.stringify({ GET: url, filtros: p }, null, 2);
    $("resumen").innerHTML = '<span class="chip">Consultando Field Service…</span>';
    $("btn-buscar").disabled = true;

    fetch(url, { cache: "no-store" })
      .then(function (r) { return r.json().then(function (d) { return { status: r.status, d: d }; }); })
      .then(function (r) {
        $("trace-consulta").textContent = JSON.stringify(
          { GET: url, respuesta: { ok: r.d.ok, count: r.d.count, filtros: r.d.filtros,
                                   entorno: r.d.entorno, error: r.d.error, details: r.d.details } },
          null, 2);
        if (r.d.ok) { pintar(r.d); } else { error(r.d); }
      })
      .catch(function (err) {
        error({ error: "No se pudo contactar la API", details: [err.message] });
      })
      .then(function () { $("btn-buscar").disabled = false; });
  }

  function error(d) {
    $("resumen").innerHTML = '<span class="chip">' + esc(d.error || "Error") + "</span>" +
      (d.details ? ' <span class="chip">' + esc(d.details.join(" · ")) + "</span>" : "");
    $("ordenes-body").innerHTML = '<tr><td colspan="7" class="muted" style="padding:28px">' +
      esc(d.error || "No se pudo consultar.") + "</td></tr>";
  }

  function pintar(d) {
    var total = d.ordenes.reduce(function (a, o) { return a + (o.monto || 0); }, 0);
    var porEstado = {};
    d.ordenes.forEach(function (o) { porEstado[o.estado] = (porEstado[o.estado] || 0) + 1; });

    $("resumen").innerHTML =
      '<span class="chip chip-accent">' + d.count + (d.count === 1 ? " orden" : " órdenes") + "</span> " +
      Object.keys(porEstado).map(function (e) {
        return '<span class="chip">' + esc(e) + ": " + porEstado[e] + "</span>";
      }).join(" ") +
      ' <span class="chip">Monto total: ' +
      total.toLocaleString("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }) +
      "</span>";

    if (!d.ordenes.length) {
      $("ordenes-body").innerHTML = '<tr><td colspan="7" class="muted" style="padding:28px">' +
        "Ninguna orden de trabajo coincide con estos filtros.</td></tr>";
      return;
    }

    $("ordenes-body").innerHTML = d.ordenes.map(function (o) {
      var color = ESTADO_COLOR[o.estadoCodigo] || "#5C6670";
      return "<tr>" +
        '<td class="mono"><b>' + esc(o.numero) + "</b></td>" +
        "<td>" + esc(o.cliente) + "</td>" +
        "<td>" + esc(o.tipo) +
          (o.resumen ? '<br><span class="small muted">' + esc(o.resumen) + "</span>" : "") + "</td>" +
        '<td><span class="chip" style="border-color:' + color + ';color:' + color + '">' +
          esc(o.estado) + "</span></td>" +
        '<td class="small">' + fecha(o.inicio) +
          '<br><span class="muted">' + hora(o.inicio) + " a " + hora(o.fin) + "</span></td>" +
        '<td class="mono" style="text-align:right;white-space:nowrap">' + esc(o.montoTexto || "-") + "</td>" +
        '<td class="small"><a href="' + esc(o.urlRegistro) + '" target="_blank" rel="noopener">Abrir en D365 &rarr;</a></td>' +
      "</tr>";
    }).join("");
  }

  /* ---------- Atajos ---------- */
  function atajos() {
    var hoy = new Date();

    $("atajo-mes").addEventListener("click", function () {
      $("f-desde").value = iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1));
      $("f-hasta").value = iso(new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0));
      buscar();
    });

    $("atajo-proximas").addEventListener("click", function () {
      $("f-desde").value = iso(hoy);
      $("f-hasta").value = iso(new Date(hoy.getTime() + 30 * 864e5));
      buscar();
    });

    $("atajo-pendientes").addEventListener("click", function () {
      $("f-estado").value = "690970000";  // Sin programar
      buscar();
    });

    $("btn-limpiar").addEventListener("click", function () {
      $("filtros").reset();
      buscar();
    });

    $("filtros").addEventListener("submit", function (ev) {
      ev.preventDefault();
      buscar();
    });
  }

  /* ---------- Sesion (Static Web Apps + Entra ID) ----------
     La pagina esta protegida por configuracion: si llega aqui es porque ya
     hay sesion. Esto solo lo hace visible, que en la demo vale mas que el
     candado invisible. */
  function sesion() {
    return fetch("/.auth/me", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var c = d && d.clientPrincipal;
        if (!c) { return; }
        var nav = document.querySelector(".topbar nav");
        if (!nav) { return; }
        var quien = document.createElement("span");
        quien.className = "chip";
        quien.style.cssText = "background:transparent;border-color:rgba(255,255,255,.28);color:#fff";
        quien.textContent = c.userDetails || "sesión iniciada";
        var salir = document.createElement("a");
        salir.href = "/.auth/logout";
        salir.className = "hide-sm";
        salir.textContent = "Salir";
        nav.insertBefore(quien, nav.firstChild);
        nav.appendChild(salir);
      })
      .catch(function () { /* en local no existe /.auth: no pasa nada */ });
  }

  function boot() {
    atajos();
    sesion();
    cargarFiltros().then(buscar);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }
})();
