/* =============================================
   State
   ============================================= */
const state = {
  photos: [],
  themes: [],
  currentTheme: 'all',
  currentIndex: 0,
  filteredPhotos: [],
  isLightboxOpen: false,
  isLoading: true
};

/* =============================================
   DOM References
   ============================================= */
const galleryEl = document.getElementById('gallery');
const themeNavEl = document.getElementById('theme-nav');
const loadingEl = document.getElementById('loading');
const emptyStateEl = document.getElementById('empty-state');
const errorStateEl = document.getElementById('error-state');
const retryBtn = document.getElementById('retry-btn');
const lightboxEl = document.getElementById('lightbox');
const lbImg = document.getElementById('lb-img');
const lbTitle = document.getElementById('lb-title');
const lbCounter = document.getElementById('lb-counter');
const lbDescription = document.getElementById('lb-description');
const lbClose = document.getElementById('lb-close');
const lbPrev = document.getElementById('lb-prev');
const lbNext = document.getElementById('lb-next');
const themeToggleBtn = document.getElementById('theme-toggle');

const isAboutPage = document.querySelector('.about-main') !== null;

/* =============================================
   Utility Functions
   ============================================= */
function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function orUnknown(val) {
  return val ? val : '未知';
}

function hide(el) {
  el.setAttribute('hidden', '');
}

function show(el) {
  el.removeAttribute('hidden');
}

/* =============================================
   Theme Toggle
   ============================================= */
function applySavedTheme() {
  const saved = localStorage.getItem('theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  }
  updateThemeIcon();
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateThemeIcon();
}

function updateThemeIcon() {
  if (!themeToggleBtn) return;
  const icon = themeToggleBtn.querySelector('i');
  const current = document.documentElement.getAttribute('data-theme');
  if (current === 'dark') {
    icon.className = 'fa-solid fa-sun';
  } else {
    icon.className = 'fa-solid fa-moon';
  }
}

if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', toggleTheme);
}

applySavedTheme();

/* =============================================
   Data Loading
   ============================================= */
async function loadData() {
  if (isAboutPage) return;

  hide(emptyStateEl);
  hide(errorStateEl);
  show(loadingEl);
  state.isLoading = true;

  try {
    const [photosRes, themesRes] = await Promise.all([
      fetch('data/photos.json'),
      fetch('data/themes.json')
    ]);

    if (!photosRes.ok || !themesRes.ok) {
      throw new Error('Failed to fetch data');
    }

    state.photos = await photosRes.json();
    state.themes = await themesRes.json();

    state.isLoading = false;
    hide(loadingEl);

    if (state.photos.length === 0) {
      show(emptyStateEl);
      return;
    }

    renderThemeNav();
    handleUrlHash();
  } catch (err) {
    console.error('Data loading error:', err);
    state.isLoading = false;
    hide(loadingEl);
    show(errorStateEl);
  }
}

if (retryBtn) {
  retryBtn.addEventListener('click', () => {
    hide(errorStateEl);
    loadData();
  });
}

/* =============================================
   Gallery Rendering
   ============================================= */
function renderGallery(photos) {
  galleryEl.innerHTML = '';

  if (photos.length === 0) {
    show(emptyStateEl);
    return;
  }

  hide(emptyStateEl);

  photos.forEach((photo, index) => {
    const item = document.createElement('div');
    item.className = 'photo-item';
    item.setAttribute('data-photo-id', photo.id);

    const shimmer = document.createElement('div');
    shimmer.className = 'shimmer';

    const img = document.createElement('img');
    img.className = 'lazy';
    img.setAttribute('data-src', `photos/${photo.theme_id}/thumb/${photo.filename}`);
    img.alt = photo.title || 'Photo';
    img.setAttribute('loading', 'lazy');

    const info = document.createElement('div');
    info.className = 'photo-info';
    info.innerHTML = `
      <div class="photo-title">${photo.title || ''}</div>
      <div class="photo-date">${formatDate(photo.date_taken) || ''}</div>
    `;

    item.appendChild(shimmer);
    item.appendChild(img);
    item.appendChild(info);
    item.addEventListener('click', () => openLightbox(photo.id));

    img.addEventListener('load', () => {
      if (shimmer) shimmer.remove();
    });
    img.addEventListener('error', () => {
      if (shimmer) shimmer.remove();
      img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><rect fill="%23ddd" width="400" height="300"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23999" font-size="14">Image</text></svg>';
    });

    galleryEl.appendChild(item);
  });

  initLazyLoading();
}

/* =============================================
   Theme Filtering
   ============================================= */
function filterByTheme(themeId) {
  state.currentTheme = themeId;
  updateThemeActiveState();

  if (themeId === 'all') {
    state.filteredPhotos = [...state.photos];
  } else {
    state.filteredPhotos = state.photos.filter(p => p.theme_id === themeId);
  }

  window.location.hash = themeId === 'all' ? '' : `theme=${themeId}`;
  renderGallery(state.filteredPhotos);
}

function updateThemeActiveState() {
  const buttons = themeNavEl.querySelectorAll('.theme-btn');
  buttons.forEach(btn => {
    const btnTheme = btn.getAttribute('data-theme');
    if (btnTheme === state.currentTheme) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

/* =============================================
   Theme Navigation Rendering
   ============================================= */
function renderThemeNav() {
  let html = '<button class="theme-btn active" data-theme="all">全部</button>';

  state.themes.forEach(theme => {
    html += `<button class="theme-btn" data-theme="${theme.id}">${theme.name}</button>`;
  });

  themeNavEl.innerHTML = html;

  themeNavEl.addEventListener('click', (e) => {
    const btn = e.target.closest('.theme-btn');
    if (!btn) return;
    filterByTheme(btn.getAttribute('data-theme'));
  });
}

/* =============================================
   Lightbox
   ============================================= */
function openLightbox(photoId) {
  state.currentIndex = state.filteredPhotos.findIndex(p => p.id === photoId);
  if (state.currentIndex === -1) return;

  state.isLightboxOpen = true;
  show(lightboxEl);
  lightboxEl.removeAttribute('hidden');
  // Trigger reflow for transition
  lightboxEl.offsetHeight;
  lightboxEl.classList.add('active');
  lightboxEl.setAttribute('aria-hidden', 'false');

  document.body.style.overflow = 'hidden';

  updateLightboxContent();
  bindKeyboard();
}

function closeLightbox() {
  state.isLightboxOpen = false;
  lightboxEl.classList.remove('active');
  lightboxEl.setAttribute('aria-hidden', 'true');

  setTimeout(() => {
    lightboxEl.setAttribute('hidden', '');
  }, 300);

  document.body.style.overflow = '';
  unbindKeyboard();
}

function navigateLightbox(direction) {
  if (state.filteredPhotos.length <= 1) return;

  state.currentIndex += direction;
  if (state.currentIndex >= state.filteredPhotos.length) {
    state.currentIndex = 0;
  } else if (state.currentIndex < 0) {
    state.currentIndex = state.filteredPhotos.length - 1;
  }

  updateLightboxContent();
  preloadAdjacent();
}

function updateLightboxContent() {
  const photo = state.filteredPhotos[state.currentIndex];
  if (!photo) return;

  lbImg.style.opacity = '0';
  lbImg.src = `photos/${photo.theme_id}/${photo.filename}`;

  lbImg.onload = () => {
    lbImg.style.opacity = '1';
  };

  lbTitle.textContent = photo.title || '';
  lbCounter.textContent = `${state.currentIndex + 1} / ${state.filteredPhotos.length}`;
  updateLightboxDetails(photo);
}

function updateLightboxDetails(photo) {
  document.getElementById('detail-date').textContent = photo.date_taken ? formatDate(photo.date_taken) : '未知';
  document.getElementById('detail-camera').textContent = orUnknown(photo.camera);
  document.getElementById('detail-lens').textContent = orUnknown(photo.lens);
  document.getElementById('detail-aperture').textContent = orUnknown(photo.aperture);
  document.getElementById('detail-shutter').textContent = orUnknown(photo.shutter_speed);
  document.getElementById('detail-iso').textContent = orUnknown(photo.iso);

  if (photo.description) {
    lbDescription.textContent = photo.description;
    lbDescription.style.display = 'block';
  } else {
    lbDescription.style.display = 'none';
  }
}

function preloadAdjacent() {
  [state.currentIndex - 1, state.currentIndex + 1].forEach(idx => {
    if (idx >= 0 && idx < state.filteredPhotos.length) {
      const photo = state.filteredPhotos[idx];
      const img = new Image();
      img.src = `photos/${photo.theme_id}/${photo.filename}`;
    }
  });
}

/* =============================================
   Keyboard Handling
   ============================================= */
function handleKeydown(e) {
  if (!state.isLightboxOpen) return;

  switch (e.key) {
    case 'ArrowRight':
      e.preventDefault();
      navigateLightbox(1);
      break;
    case 'ArrowLeft':
      e.preventDefault();
      navigateLightbox(-1);
      break;
    case 'Escape':
      e.preventDefault();
      closeLightbox();
      break;
  }
}

function bindKeyboard() {
  document.addEventListener('keydown', handleKeydown);
}

function unbindKeyboard() {
  document.removeEventListener('keydown', handleKeydown);
}

/* =============================================
   Lightbox Event Bindings
   ============================================= */
if (lbClose) {
  lbClose.addEventListener('click', closeLightbox);
}

if (lbPrev) {
  lbPrev.addEventListener('click', () => navigateLightbox(-1));
}

if (lbNext) {
  lbNext.addEventListener('click', () => navigateLightbox(1));
}

// Click outside image to close
if (lightboxEl) {
  lightboxEl.addEventListener('click', (e) => {
    if (e.target === lightboxEl || e.target.classList.contains('lb-close')) {
      // handled above; skip the nav buttons
      if (e.target === lightboxEl) {
        closeLightbox();
      }
    }
  });
}

/* =============================================
   Lazy Loading
   ============================================= */
function initLazyLoading() {
  const lazyImages = galleryEl.querySelectorAll('img.lazy');

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            const src = img.getAttribute('data-src');
            if (src) {
              img.src = src;
              img.removeAttribute('data-src');
            }
            img.addEventListener('load', () => {
              img.classList.add('loaded');
            }, { once: true });
            observer.unobserve(img);
          }
        });
      },
      { rootMargin: '200px' }
    );

    lazyImages.forEach(img => observer.observe(img));
  } else {
    // Fallback for browsers without IntersectionObserver
    lazyImages.forEach(img => {
      const src = img.getAttribute('data-src');
      if (src) {
        img.src = src;
        img.removeAttribute('data-src');
        img.addEventListener('load', () => {
          img.classList.add('loaded');
        }, { once: true });
      }
    });
  }
}

/* =============================================
   URL Hash Handling
   ============================================= */
function handleUrlHash() {
  const hash = window.location.hash.slice(1);
  const params = new URLSearchParams(hash);
  const theme = params.get('theme');

  if (theme) {
    filterByTheme(theme);
  } else {
    state.filteredPhotos = [...state.photos];
    renderGallery(state.filteredPhotos);
  }
}

window.addEventListener('hashchange', () => {
  if (!isAboutPage) {
    handleUrlHash();
  }
});

/* =============================================
   Touch Swipe for Mobile Lightbox
   ============================================= */
let touchStartX = 0;
let touchEndX = 0;

if (lightboxEl) {
  lightboxEl.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });

  lightboxEl.addEventListener('touchend', (e) => {
    touchEndX = e.changedTouches[0].screenX;
    const diff = touchStartX - touchEndX;

    if (Math.abs(diff) > 60 && state.isLightboxOpen) {
      if (diff > 0) {
        navigateLightbox(1);
      } else {
        navigateLightbox(-1);
      }
    }
  });
}

/* =============================================
   Init
   ============================================= */
loadData();
