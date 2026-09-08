/* ============================================================
   Configuracion de la demo (unico archivo a editar para apuntar la API)
   ============================================================ */
(function () {
  // Raiz del sitio deducida desde la ruta de este script, para que las
  // paginas de /landings/ resuelvan bien landings.json y los assets.
  var me = document.currentScript || (function () {
    var s = document.getElementsByTagName("script");
    return s[s.length - 1];
  })();
  var root = me.src.replace(/assets\/js\/config\.js.*$/, "");

  window.DEMO_CONFIG = {
    /* URL base de la API unica de captura de leads.
       - ""  = mismo origen (asi funciona con run-demo.cmd, que sirve sitio + API).
       - En GitHub Pages hay que poner aqui la URL publica de la API,
         por ejemplo "https://wit-leads-api.azurewebsites.net". */
    apiBaseUrl: "",

    // Endpoint unico: TODAS las landings postean aqui.
    endpoint: "/api/leads",

    // Raiz del sitio (calculada, no editar).
    root: root,

    /* Catalogo de landings (fuente unica de verdad). Vive junto a la API
       (api/landings.json) y se expone por este endpoint, para que el archivo
       viaje con la Function al desplegar en Azure. */
    landingsEndpoint: "/api/landings",

    /* Si la API no responde (sin servidor levantado, GitHub Pages sin backend),
       la demo simula la respuesta y lo rotula como SIMULADO para no cortar
       la presentacion frente al cliente. Poner en false para exigir API real. */
    simulateIfUnreachable: true,

    // Muestra el panel con el JSON enviado y la respuesta (valor didactico).
    showTrace: true,

    // Texto de consentimiento (Ley 21.719 de proteccion de datos personales).
    consentText:
      "Autorizo el tratamiento de mis datos personales para ser contactado con fines comerciales, " +
      "conforme a la politica de privacidad y a la Ley 21.719."
  };
})();
