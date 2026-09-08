/* ============================================================
   landing.js - motor comun de las 4 landings
   Todas las landings usan ESTE mismo script y postean al MISMO endpoint.
   Lo unico que cambia por landing es el atributo data-landing-code del <form>.

   Convencion de campos del formulario:
     name="firstName|lastName|email|phone|company|jobTitle|message|consent"
        -> viajan como campos de primer nivel del payload
     name="extra:algo"
        -> viaja dentro de payload.fields.algo  (campos propios de la landing)
   ============================================================ */
(function () {
  "use strict";

  var CFG = window.DEMO_CONFIG || {};
  var TRACK_KEY = "witdemo.tracking";
  var LEADS_KEY = "witdemo.leads";

  /* ---------- utilidades ---------- */
  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }

  function apiUrl() {
    var base = (CFG.apiBaseUrl || "").replace(/\/$/, "");
    return base + (CFG.endpoint || "/api/leads");
  }

  /* ---------- 1. Captura del origen (de donde viene el lead) ---------- */
  var TRACK_PARAMS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
                      "gclid", "fbclid", "msclkid", "src"];

  function captureTracking() {
    var url = new URL(window.location.href);
    var stored = {};
    try { stored = JSON.parse(sessionStorage.getItem(TRACK_KEY) || "{}"); } catch (e) { stored = {}; }

    TRACK_PARAMS.forEach(function (p) {
      var v = url.searchParams.get(p);
      if (v) { stored[p] = v; }
    });
    // El referrer de la primera visita es el que importa (de donde llego el usuario).
    if (!stored.referrer) { stored.referrer = document.referrer || "(directo)"; }
    stored.landingUrl = window.location.href.split("#")[0];
    stored.pageTitle = document.title;
    stored.capturedAt = stored.capturedAt || new Date().toISOString();

    try { sessionStorage.setItem(TRACK_KEY, JSON.stringify(stored)); } catch (e) { /* modo privado */ }
    return stored;
  }

  /* ---------- 2. Armado del payload ---------- */
  function buildPayload(form) {
    var payload = {
      landingCode: form.getAttribute("data-landing-code"),
      firstName: "", lastName: "", email: "", phone: "",
      company: "", jobTitle: "", message: "",
      consent: false,
      fields: {},
      tracking: captureTracking(),
      client: {
        submittedAt: new Date().toISOString(),
        timezone: (Intl.DateTimeFormat().resolvedOptions().timeZone || ""),
        language: navigator.language || "",
        screen: window.innerWidth + "x" + window.innerHeight
      }
    };

    qsa("[name]", form).forEach(function (el) {
      var name = el.getAttribute("name");
      var value = el.type === "checkbox" ? el.checked : (el.value || "").trim();
      if (name.indexOf("extra:") === 0) {
        if (value !== "" && value !== false) { payload.fields[name.slice(6)] = value; }
      } else if (name in payload) {
        payload[name] = value;
      }
    });
    return payload;
  }

  /* ---------- 3. Validacion en cliente ---------- */
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;

  function validate(form) {
    var ok = true;
    qsa(".field", form).forEach(function (f) { f.classList.remove("invalid"); });

    qsa("[required]", form).forEach(function (el) {
      var empty = el.type === "checkbox" ? !el.checked : !(el.value || "").trim();
      if (empty) { markInvalid(el, "Este campo es obligatorio."); ok = false; }
    });

    var email = qs('[name="email"]', form);
    if (email && email.value && !EMAIL_RE.test(email.value.trim())) {
      markInvalid(email, "Revisa el formato del correo."); ok = false;
    }
    var phone = qs('[name="phone"]', form);
    if (phone && phone.value && phone.value.replace(/[^0-9]/g, "").length < 8) {
      markInvalid(phone, "Ingresa un telefono valido (minimo 8 digitos)."); ok = false;
    }
    return ok;
  }

  function markInvalid(el, msg) {
    var field = el.closest(".field") || el.closest(".consent") || el.parentElement;
    if (!field) { return; }
    field.classList.add("invalid");
    var err = qs(".err", field);
    if (err) { err.textContent = msg; }
  }

  /* ---------- 4. Trazabilidad visible (valor didactico en la demo) ---------- */
  function showTrace(form, title, obj) {
    if (!CFG.showTrace) { return; }
    var box = qs("#trace-" + form.getAttribute("data-landing-code"));
    if (!box) { box = qs(".trace", form.closest("section") || document); }
    if (!box) { return; }
    var head = box.parentElement ? qs(".trace-head .t", box.parentElement) : null;
    if (head && title) { head.textContent = title; }
    box.textContent = JSON.stringify(obj, null, 2);
  }

  /* ---------- 5. Envio a la API unica ---------- */
  function setStatus(form, kind, html) {
    var st = qs(".form-status", form);
    if (!st) { return; }
    st.className = "form-status show " + kind;
    st.innerHTML = html;
  }

  function rememberLocally(record) {
    try {
      var list = JSON.parse(localStorage.getItem(LEADS_KEY) || "[]");
      list.unshift(record);
      localStorage.setItem(LEADS_KEY, JSON.stringify(list.slice(0, 100)));
    } catch (e) { /* sin storage: la consola local simplemente no lo vera */ }
  }

  function fakeGuid() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  function submitForm(form) {
    if (!validate(form)) {
      setStatus(form, "err", "Hay campos por corregir en el formulario.");
      return;
    }
    var payload = buildPayload(form);
    var btn = qs('button[type="submit"]', form);
    var originalLabel = btn ? btn.innerHTML : "";

    showTrace(form, "1/2 - POST " + apiUrl(), payload);
    setStatus(form, "wait", "Enviando a la API de captura...");
    if (btn) { btn.disabled = true; btn.innerHTML = "Enviando..."; }

    fetch(apiUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res.json().then(function (data) { return { status: res.status, data: data }; });
      })
      .then(function (r) {
        if (r.status >= 200 && r.status < 300 && r.data.ok) {
          onSuccess(form, payload, r.data);
        } else {
          showTrace(form, "2/2 - Respuesta de la API (error)", r.data);
          setStatus(form, "err",
            "La API rechazo el envio: <b>" + (r.data.error || ("HTTP " + r.status)) + "</b>" +
            (r.data.details ? "<br><span class='small'>" + r.data.details.join(" &middot; ") + "</span>" : ""));
        }
      })
      .catch(function (err) {
        if (CFG.simulateIfUnreachable) {
          var sim = {
            ok: true,
            mode: "simulado-en-navegador",
            leadId: fakeGuid(),
            note: "La API no respondio (" + err.message + "). Respuesta SIMULADA para no cortar la demo.",
            landing: { code: payload.landingCode }
          };
          onSuccess(form, payload, sim);
        } else {
          setStatus(form, "err", "No se pudo contactar la API: " + err.message);
        }
      })
      .then(function () {
        if (btn) { btn.disabled = false; btn.innerHTML = originalLabel; }
      });
  }

  function onSuccess(form, payload, data) {
    showTrace(form, "2/2 - Respuesta de la API", data);
    rememberLocally({
      leadId: data.leadId,
      mode: data.mode,
      landingCode: payload.landingCode,
      name: (payload.firstName + " " + payload.lastName).trim(),
      email: payload.email,
      company: payload.company,
      phone: payload.phone,
      tracking: payload.tracking,
      fields: payload.fields,
      at: new Date().toISOString()
    });

    // El rotulo tiene que decir la verdad de donde quedo el lead:
    //   dataverse -> creado en el CRM | mock -> guardado por la API | simulado -> solo navegador
    var mode = String(data.mode || "");
    var real = mode === "dataverse";
    var etiqueta = real ? "creado en Dynamics 365"
      : (mode.indexOf("simulado") === 0
        ? "simulado en el navegador (la API no respondio)"
        : "recibido por la API en modo MOCK, sin escribir en el CRM");

    setStatus(form, real ? "ok" : "wait",
      "<b>Lead " + etiqueta + "</b><br>" +
      "Origen registrado: <code>" + payload.landingCode + "</code><br>" +
      "leadid: <code>" + (data.leadId || "-") + "</code>" +
      (data.note ? "<br><span class='small'>" + data.note + "</span>" : "") +
      "<br><span class='small'>Puedes verlo en la <a href='" + CFG.root + "admin.html'>consola de leads</a>.</span>");

    form.reset();
  }

  /* ---------- 6. Arranque ---------- */
  function boot() {
    captureTracking();

    qsa("form[data-landing-code]").forEach(function (form) {
      // Pinta el origen capturado para que se vea en la demo.
      var t = captureTracking();
      var originBox = qs("[data-origin-preview]", form.closest("section") || document);
      if (originBox) {
        originBox.textContent = JSON.stringify(
          { landingCode: form.getAttribute("data-landing-code"), tracking: t }, null, 2);
      }
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        submitForm(form);
      });
    });

    // Propaga los parametros de campana al volver al sitio maestro.
    qsa("a[data-keep-utm]").forEach(function (a) {
      var t = captureTracking(), url;
      try { url = new URL(a.href, window.location.href); } catch (e) { return; }
      TRACK_PARAMS.forEach(function (p) { if (t[p]) { url.searchParams.set(p, t[p]); } });
      a.href = url.toString();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else { boot(); }

  window.WITDemo = { LEADS_KEY: LEADS_KEY, apiUrl: apiUrl, captureTracking: captureTracking };
})();
