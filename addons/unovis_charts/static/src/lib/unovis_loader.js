/**
 * Lightweight loader to ensure Unovis UMD is available on the page.
 * Order of precedence:
 * 1) Local UMD bundled into the addon (unovis_charts/static/lib/unovis/unovis.umd.min.js) loaded via assets.
 * 2) If not present or blocked, fallback to CDN (unpkg).
 */
(function () {
  if (window.Unovis || window.unovis) return;
  // Try loading local UMD provided by Docker build (if present).
  var local = document.createElement('script');
  local.src = '/unovis_charts/static/lib/unovis/unovis.umd.min.js';
  local.async = true;
  local.crossOrigin = 'anonymous';
  local.onload = function () { console.debug('Unovis UMD loaded (local)'); };
  local.onerror = function () {
    console.warn('Local Unovis UMD not found. Falling back to CDN...');
    var cdn = document.createElement('script');
    cdn.src = 'https://unpkg.com/@unovis/ts@1.5.4/dist/unovis.umd.min.js';
    cdn.async = true;
    cdn.crossOrigin = 'anonymous';
    cdn.onload = function () { console.debug('Unovis UMD loaded via CDN'); };
    cdn.onerror = function () { console.warn('Failed to load Unovis from CDN.'); };
    document.head.appendChild(cdn);
  };
  document.head.appendChild(local);
})();
