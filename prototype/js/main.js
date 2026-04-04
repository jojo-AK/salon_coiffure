/* ——— SCROLL REVEAL ——— */
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) e.target.classList.add('visible');
  });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

/* ——— MOBILE MENU ——— */
function openMenu() {
  document.getElementById('mobileMenu').classList.add('open');
  document.querySelector('.hamburger').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeMenu() {
  document.getElementById('mobileMenu').classList.remove('open');
  document.querySelector('.hamburger').classList.remove('open');
  document.body.style.overflow = '';
}
// Fermer en cliquant en dehors
document.getElementById('mobileMenu')?.addEventListener('click', function(e) {
  if (e.target === this) closeMenu();
});

/* ——— SCROLL EVENTS ——— */
const nav         = document.querySelector('nav');
const progressBar = document.querySelector('.scroll-progress');
const backToTop   = document.querySelector('.back-to-top');

window.addEventListener('scroll', () => {
  const scrollY   = window.scrollY;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;

  // Nav shrink + classe scrolled
  if (nav) {
    nav.style.padding = scrollY > 60 ? '.8rem 4vw' : '1.2rem 4vw';
    nav.classList.toggle('scrolled', scrollY > 60);
  }

  // Barre de progression
  if (progressBar && docHeight > 0) {
    progressBar.style.width = ((scrollY / docHeight) * 100) + '%';
  }

  // Bouton back-to-top
  if (backToTop) {
    backToTop.classList.toggle('visible', scrollY > 400);
  }
}, { passive: true });

/* ——— BACK TO TOP ——— */
backToTop?.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

/* ——— COUNTER ANIMATION ——— */
function animateCounter(el) {
  const text   = el.textContent.trim();
  const suffix = text.replace(/[\d.]/g, '');       // ex: "+" ou " " ou ""
  const value  = parseFloat(text.replace(/[^\d.]/g, ''));
  if (isNaN(value)) return;

  const isDecimal = text.includes('.');
  const duration  = 1600;
  const startTime = performance.now();

  const tick = (now) => {
    const elapsed  = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease     = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    const current  = value * ease;

    el.textContent = (isDecimal ? current.toFixed(1) : Math.floor(current)) + suffix;

    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = text; // valeur exacte finale
  };
  requestAnimationFrame(tick);
}

const statsBar = document.querySelector('.stats-bar');
if (statsBar) {
  let triggered = false;
  new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !triggered) {
      triggered = true;
      statsBar.querySelectorAll('.stat-number').forEach(animateCounter);
    }
  }, { threshold: 0.6 }).observe(statsBar);
}

/* ——— ACTIVE NAV LINK (page courante) ——— */
const currentPage = location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('.nav-links a, .mobile-menu a').forEach(a => {
  const href = a.getAttribute('href');
  if (href === currentPage || (currentPage === '' && href === 'index.html')) {
    a.classList.add('active');
  }
});
