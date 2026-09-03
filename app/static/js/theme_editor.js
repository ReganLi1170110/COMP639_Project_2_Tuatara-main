function decodeHtml(str) {
  const txt = document.createElement("textarea");
  txt.innerHTML = str;
  return txt.value;
}

/* ── Helpers ──────────────────────────────────────────────── */
function getVal(id) {
  return document.getElementById('text_' + id)?.value || '#2e7d32';
}
function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return document.querySelectorAll(sel); }

/* ── Colour sync ──────────────────────────────────────────── */
function syncColor(name, val) {
  const txt = document.getElementById('text_' + name);
  if (txt) txt.value = val;
  updatePreview();
}
function syncPicker(name, val) {
  if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
    const pk = document.getElementById('picker_' + name);
    if (pk) pk.value = val;
    updatePreview();
  }
}

/* ── Font selection ───────────────────────────────────────── */
function selectFont(key, el) {
  qsa('#font-options .opt-pill').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('font_input').value = key;
  updatePreview();
}

/* ── Layout selection ─────────────────────────────────────── */
function selectLayout(key, el) {
  qsa('#layout-options .opt-pill').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('layout_input').value = key;
  updatePreview();
}

/* ── Image upload handler ─────────────────────────────────── */
function handleImageUpload(input, urlFieldId, thumbId, previewTargetId) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];

  if (file.size > 2 * 1024 * 1024) {
    alert('File exceeds 2 MB — please choose a smaller image.');
    input.value = ''; return;
  }
  if (!['image/jpeg','image/png'].includes(file.type)) {
    alert('Only JPG or PNG files are accepted.');
    input.value = ''; return;
  }

  const reader = new FileReader();
  reader.onload = e => {
    const dataUrl = e.target.result;
    // Show mini thumbnail in editor
    const thumb = document.getElementById(thumbId);
    if (thumb) { thumb.src = dataUrl; thumb.style.display = 'block'; }
    // Update live preview element
    applyImageToPreview(previewTargetId, dataUrl);
  };
  reader.readAsDataURL(file);
}

/* ── URL field → preview ──────────────────────────────────── */
function syncImageUrl(val, previewImgId, bgId) {
  if (previewImgId) applyImageToPreview(previewImgId, val);
  if (bgId) {
    const el = document.getElementById(bgId);
    if (el) {
      el.style.backgroundImage = val ? `url('${val}')` : '';
    }
  }
}

function applyImageToPreview(targetId, url) {
  if (!targetId) return;
  const clean = (url || '').trim();

  if (targetId === 'pv-bg') {
    const bg = document.getElementById('pv-bg');
    if (bg) bg.style.backgroundImage = clean ? `url('${clean}')` : '';

  } else if (targetId === 'pv-banner-img') {
    // Update standard banner (centred/grid layouts)
    const img  = document.getElementById('pv-banner-img');
    const wrap = document.getElementById('pv-banner');
    if (clean) {
      if (img)  { img.src = clean; }
      if (wrap) { wrap.style.display = ''; }
    } else {
      if (wrap) { wrap.style.display = 'none'; }
    }
    // Also update sidebar-specific banner
    const sbImg  = document.getElementById('pv-sidebar-banner-img');
    const sbWrap = document.getElementById('pv-sidebar-banner');
    if (clean) {
      if (sbImg)  { sbImg.src = clean; }
      if (sbWrap) { sbWrap.style.display = 'block'; }
    } else {
      if (sbWrap) { sbWrap.style.display = 'none'; }
    }

  } else if (targetId === 'pv-logo-img') {
    // Update standard logo (centred/grid layouts - in navbar)
    const img = document.getElementById('pv-logo-img');
    const txt = document.getElementById('pv-brand-text');
    if (clean) {
      if (img) { img.src = clean; img.style.display = 'inline'; }
      if (txt) { txt.style.display = 'none'; }
    } else {
      if (img) { img.style.display = 'none'; }
      if (txt) { txt.style.display = ''; }
    }
    // Also update sidebar-specific logo
    const sbLogo = document.getElementById('pv-sidebar-logo');
    if (sbLogo) {
      if (clean) { sbLogo.src = clean; sbLogo.style.display = 'inline'; }
      else        { sbLogo.style.display = 'none'; }
    }
  }
}

/* ── Master preview update ────────────────────────────────── */
function updatePreview() {
  const primary   = getVal('primary_color');
  const secondary = getVal('secondary_color');
  const bg        = getVal('bg_color');
  const btn       = getVal('button_color');
  const fontKey   = document.getElementById('font_input').value || 'system';
  const fontCss   = decodeHtml(FONT_MAP[fontKey]) || 'system-ui, sans-serif';
  const layout    = document.getElementById('layout_input').value || 'centered';
  
  // Navbar colour
  const nav = document.getElementById('pv-nav');
  if (nav) nav.style.background = primary;

  // Body background
  const inner = document.getElementById('preview-inner');
  if (inner) {
    inner.style.background = bg;
  }
  // FONT: inject a <style> tag inside the preview panel.
  // A stylesheet rule with !important beats body's inherited !important
  // because it targets #preview-content directly (higher specificity).
  // Set font directly on #preview-frame as inline style.
  // Inline style beats any stylesheet rule that doesn't use !important.
  // For rules WITH !important (base.html body rule), we also inject a
  // high-specificity stylesheet rule.
  const pvFrame = document.getElementById('preview-frame');
  if (pvFrame) {
    pvFrame.style.fontFamily = fontCss;
  }
  const pvFontStyle = document.getElementById('pv-font-style');
  if (pvFontStyle) {
    const sel = '#preview-frame #preview-inner #preview-content';
    pvFontStyle.textContent =
      sel + ', ' + sel + ' * { font-family: ' + fontCss + ' !important; }';
  }

  // Classic + Dashboard hero gradient
  const heroC = document.getElementById('pv-hero-c');
  if (heroC) heroC.style.background = `linear-gradient(135deg,${primary},${secondary})`;

  // Dashboard hero
  const heroG = document.getElementById('pv-hero-g');
  if (heroG) heroG.style.background = `linear-gradient(135deg,${primary},${secondary})`;

  // Buttons
  ['pv-btn-c','pv-btn-sb','pv-btn-g'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.background = btn;
  });

  // Sidebar nav background
  const sbnav = document.getElementById('pv-sidebar-nav');
  if (sbnav) sbnav.style.background = primary;

  // Dashboard stat value numbers + panel borders: update inline styles
  qsa('#pv-grid-val').forEach(el => { el.style.color = primary; });
  // Update all inline border-top and border-left colors that reference primary/secondary
  qsa('[style*="border-top:3px solid"]').forEach(el => {
    el.style.borderTopColor = primary;
  });
  qsa('[style*="border-left:4px solid"]').forEach(el => {
    el.style.borderLeftColor = secondary;
  });
  qsa('[style*="border-left:3px solid"]').forEach(el => {
    el.style.borderLeftColor = primary;
  });

  // CSS var for opt-pill highlight
  document.documentElement.style.setProperty('--theme-primary', primary);

  // Layout switch
  ['centered','sidebar','grid'].forEach(l => {
    const el = document.getElementById('layout-' + l);
    if (el) el.style.display = (l === layout) ? '' : 'none';
  });
  // Sidebar mode: hide top navbar, no body padding
  const pvNav = document.getElementById('pv-nav');
  const pvBanner = document.getElementById('pv-banner');
  if (layout === 'sidebar') {
    if (pvNav) pvNav.style.display = 'none';
    if (pvBanner) pvBanner.style.display = 'none';
  } else {
    if (pvNav) pvNav.style.display = '';
    // banner: restore only if it has a src
    const pvBannerImg = document.getElementById('pv-banner-img');
    if (pvBanner && pvBannerImg && pvBannerImg.src && pvBannerImg.src !== window.location.href) {
      pvBanner.style.display = '';
    }
  }
}

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  updatePreview();

  // Banner URL input → preview
  const bannerUrlEl = document.getElementById('banner_url');
  if (bannerUrlEl && bannerUrlEl.value) {
    applyImageToPreview('pv-banner-img', bannerUrlEl.value);
  }
  // Logo URL input → preview
  const logoUrlEl = document.getElementById('logo_url');
  if (logoUrlEl && logoUrlEl.value) {
    applyImageToPreview('pv-logo-img', logoUrlEl.value);
  }
  // BG URL input → preview
  const bgUrlEl = document.getElementById('bg_image_url');
  if (bgUrlEl && bgUrlEl.value) {
    applyImageToPreview('pv-bg', bgUrlEl.value);
  }
});