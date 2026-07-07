/* ============================================================
   FRAME FINDER — app.js
   ============================================================ */

// DEV: set true to skip AI parsing and save API credits. Set false before deploying.
const DEV_SKIP_PARSING = false;

// ── Example queries ───────────────────────────────────────────
const EXAMPLES = [
  "arm-friendly racquet for an aggressive baseliner with a big topspin forehand",
  "something with great feel and control for a 4.5 player who likes to flatten the ball out",
  "lightweight racquet for an improving intermediate who wants more spin",
];

// ── DOM ───────────────────────────────────────────────────────
const startupOverlay  = document.getElementById('startup-overlay');
const startupStatus   = document.getElementById('startup-status');
const app             = document.getElementById('app');
const searchInput     = document.getElementById('search-input');
const searchBtn       = document.getElementById('search-btn');
const searchBox       = document.getElementById('search-box');

const exampleText     = document.getElementById('example-text');
const sectionDivider  = document.getElementById('section-divider');
const resultsSection  = document.getElementById('results-section');
const resultsLoading  = document.getElementById('results-loading');
const resultsHd       = document.getElementById('results-hd');
const resultsLabel    = document.getElementById('results-label');
const cardGrid        = document.getElementById('card-grid');
const resultsFeedback = document.getElementById('results-feedback');
const modalOverlay    = document.getElementById('modal-overlay');
const modalClose      = document.getElementById('modal-close');

// ── State ─────────────────────────────────────────────────────
let exampleIdx        = 0;
let exampleTimer      = null;
let currentSearchId   = null;
const likedRacquets   = new Set();  // racquet_ids liked in the current search

// ── Startup ───────────────────────────────────────────────────
async function startup() {
  try {
    await pingUntilReady();
  } catch (e) {
    console.warn('Health ping failed, showing app anyway');
  }
  revealApp();
}

async function pingUntilReady(attempts = 20, interval = 1500) {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch('/health', { signal: AbortSignal.timeout(3000) });
      if (res.ok) return;
    } catch (_) {}
    if (i === 0) startupStatus.textContent = 'Waking up…';
    await sleep(interval);
  }
}

function revealApp() {
  startupOverlay.classList.add('fade-out');
  app.classList.remove('hidden');
  startupOverlay.addEventListener('transitionend', () => {
    startupOverlay.style.display = 'none';
  }, { once: true });
  startExampleCycle();
  searchInput.focus();
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// ── Example query cycling ─────────────────────────────────────
function startExampleCycle() {
  exampleText.textContent = EXAMPLES[exampleIdx];
  exampleTimer = setInterval(cycleExample, 5000);
}

function cycleExample() {
  exampleText.classList.add('fading');
  setTimeout(() => {
    exampleIdx = (exampleIdx + 1) % EXAMPLES.length;
    exampleText.textContent = EXAMPLES[exampleIdx];
    exampleText.classList.remove('fading');
  }, 350);
}

function pauseExampleCycle() {
  clearInterval(exampleTimer);
  exampleTimer = null;
}

function resumeExampleCycle() {
  if (!exampleTimer) startExampleCycle();
}

// ── Textarea auto-grow ────────────────────────────────────────
function autoGrow(el) {
  el.style.height = 'auto';
  el.style.height = el.scrollHeight + 'px';
}

searchInput.addEventListener('input', () => {
  autoGrow(searchInput);
  if (searchInput.value.trim() === '') {
    resumeExampleCycle();
  } else {
    pauseExampleCycle();
  }
});

// ── Keyboard handling ─────────────────────────────────────────
searchInput.addEventListener('keydown', (e) => {
  // Tab with empty input → populate with current example
  if (e.key === 'Tab' && searchInput.value.trim() === '') {
    e.preventDefault();
    searchInput.value = EXAMPLES[exampleIdx];
    autoGrow(searchInput);
    pauseExampleCycle(); // input now has content
    return;
  }
  // Enter (without shift) → search
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSearch();
  }
  // Shift+Enter → newline (default textarea behavior, no override needed)
});

searchBtn.addEventListener('click', handleSearch);

// ── Loading messages ─────────────────────────────────────────
const LOADING_MESSAGES = [
  "Reading between the lines of your game...",
  "Weighing power against control...",
  "Cross-checking specs against feel...",
  "Narrowing down the field...",
  "Comparing frames that fit your style...",
];

const loadingMessage = document.getElementById('loading-message');
let loadingMsgIdx = 0;
let loadingMsgTimer = null;

function startLoadingMessages() {
  loadingMsgIdx = 0;
  loadingMessage.textContent = LOADING_MESSAGES[loadingMsgIdx];
  loadingMsgTimer = setInterval(cycleLoadingMessage, 1800);
}

function cycleLoadingMessage() {
  loadingMessage.classList.add('fading');
  setTimeout(() => {
    loadingMsgIdx = (loadingMsgIdx + 1) % LOADING_MESSAGES.length;
    loadingMessage.textContent = LOADING_MESSAGES[loadingMsgIdx];
    loadingMessage.classList.remove('fading');
  }, 350);
}

function stopLoadingMessages() {
  clearInterval(loadingMsgTimer);
  loadingMsgTimer = null;
}

// ── Search ────────────────────────────────────────────────────
async function handleSearch() {
  const query = searchInput.value.trim();
  if (!query) { searchInput.focus(); return; }

  const skipParsing = DEV_SKIP_PARSING;

  // Show loading state
  likedRacquets.clear(); // fresh feedback state per search
  sectionDivider.classList.remove('hidden');
  resultsSection.classList.remove('hidden');
  resultsLoading.classList.remove('hidden');
  resultsHd.classList.add('hidden');
  resultsFeedback.classList.add('hidden');
  cardGrid.innerHTML = '';
  startLoadingMessages();

  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  try {
    const [res] = await Promise.all([
      fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, skip_parse: skipParsing }),
      }),
      sleep(400), // minimum skeleton display time — prevents flash on fast responses
    ]);

    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);

    const data = await res.json();
    currentSearchId = data.search_id;
    renderResults(data);

  } catch (err) {
    renderError(err);
  } finally {
    resultsLoading.classList.add('hidden');
    stopLoadingMessages();
  }
}

// ── Render ────────────────────────────────────────────────────
function renderResults(data) {
  const results = data.results || [];

  resultsLabel.textContent =
    results.length === 0
      ? 'No results'
      : `Top ${results.length} frames for your query`;

  resultsHd.classList.remove('hidden');

  if (results.length === 0) {
    cardGrid.innerHTML = `
      <p style="font-size:.875rem;color:var(--text-2);grid-column:1/-1;padding:.5rem 0">
        No frames matched your query. Try rephrasing or using different terms.
      </p>`;
    return;
  }

  // Match scores already computed server-side as integer percentages
  cardGrid.innerHTML = '';
  results.forEach((r, i) => {
    const card = buildCard(r, i === 0);
    cardGrid.appendChild(card);
    requestAnimationFrame(() => {
      setTimeout(() => {
        const fill = card.querySelector('.card-match-bar-fill');
        if (fill) fill.style.width = r.racquet_match_score + '%';
      }, 80 + i * 30);
    });
  });

  resultsFeedback.classList.remove('hidden');
}

function buildCard(r, isTop) {
  const el = document.createElement('div');
  el.className = 'racquet-card';
  el.dataset.racquetId = r.racquet_id;

  const brand = extractBrand(r.racquet_name);
  const price = formatPrice(r.racquet_price);
  const ratingHtml = r.racquet_rating !== null
    ? `<span class="card-rating">★ ${r.racquet_rating} <span style="color:var(--text-3)">(${r.racquet_rating_count})</span></span>`
    : `<span class="card-no-rating">No ratings yet</span>`;

  el.innerHTML = `
    ${isTop ? `<span class="card-top-badge">Top result</span>` : ''}
    <div class="card-img-wrap">
      <img
        class="card-img"
        src="${esc(r.racquet_img || '')}"
        alt="${esc(r.racquet_name)}"
        loading="lazy"
        onerror="this.style.display='none'"
      />
    </div>
    <div class="card-body">
      <p class="card-brand">${esc(brand)}</p>
      <h3 class="card-name">${esc(r.racquet_name)}</h3>
      <div class="card-price-row">
        <span class="card-price">$${price}</span>
        ${ratingHtml}
      </div>
      <p class="card-desc">${esc(r.racquet_description || '')}</p>
    </div>
    <div class="card-match-wrap">
      <span class="card-match-label">Match</span>
      <div class="card-match-bar-track">
        <div class="card-match-bar-fill" style="width:0%"></div>
      </div>
      <span class="card-match-pct">${r.racquet_match_score}%</span>
    </div>
    <div class="card-footer">
      <button class="card-like-btn" aria-label="Mark as a good match" title="Was this a good match for your query? Your feedback helps improve results.">
        <span class="card-like-text">Good match?</span>
        <svg class="card-like-icon" width="15" height="15" viewBox="0 0 16 16" fill="none">
          <path d="M4.5 7.5V13H2.5C2.22 13 2 12.78 2 12.5V8C2 7.72 2.22 7.5 2.5 7.5H4.5ZM4.5 7.5L7 2C7.53 2 8.5 2.4 8.5 3.5V5.5H12.5C13.2 5.5 13.7 6.1 13.6 6.8L12.9 11.8C12.83 12.5 12.3 13 11.7 13H4.5" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
        </svg>
      </button>
      <a
        class="card-tw-link"
        href="${esc(r.racquet_url || '#')}"
        target="_blank"
        rel="noopener noreferrer"
        onclick="event.stopPropagation()"
      >TW listing ↗</a>
    </div>
  `;

  // Feedback button — toggle liked state, POST to /feedback
  const likeBtn = el.querySelector('.card-like-btn');
  likeBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // don't open modal
    toggleLike(r.racquet_id, likeBtn);
  });

  // Reflect any existing liked state (in case card is rebuilt)
  if (likedRacquets.has(r.racquet_id)) {
    likeBtn.classList.add('liked');
  }

  el.addEventListener('click', (e) => {
    if (e.target.closest('.card-tw-link') || e.target.closest('.card-like-btn')) return;
    openModal(r);
  });

  return el;
}

function renderError(err) {
  resultsHd.classList.remove('hidden');
  resultsLabel.textContent = 'Something went wrong';
  cardGrid.innerHTML = `
    <p style="font-size:.875rem;color:var(--text-2);grid-column:1/-1;padding:.5rem 0">
      Could not complete the search. Please try again.
      <br><span style="font-size:.75rem;color:var(--text-3)">${esc(String(err))}</span>
    </p>`;
}

// ── Feedback ──────────────────────────────────────────────────
async function toggleLike(racquetId, btnEl) {
  const nowLiked = !likedRacquets.has(racquetId);

  // Optimistic UI update — flip immediately, don't wait on network
  if (nowLiked) {
    likedRacquets.add(racquetId);
  } else {
    likedRacquets.delete(racquetId);
  }
  syncLikeButtons(racquetId, nowLiked);

  try {
    const res = await fetch('/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        search_id: currentSearchId,
        racquet_id: racquetId,
        liked: nowLiked,
      }),
    });
    if (!res.ok) throw new Error(`${res.status}`);
  } catch (err) {
    // Revert on failure
    console.warn('Feedback failed, reverting:', err);
    if (nowLiked) {
      likedRacquets.delete(racquetId);
    } else {
      likedRacquets.add(racquetId);
    }
    syncLikeButtons(racquetId, !nowLiked);
  }
}

// Keep card button and modal button visually in sync for a racquet
function syncLikeButtons(racquetId, liked) {
  // Card button
  const cards = cardGrid.querySelectorAll('.racquet-card');
  cards.forEach(card => {
    const btn = card.querySelector('.card-like-btn');
    if (btn && card.dataset.racquetId === racquetId) {
      btn.classList.toggle('liked', liked);
    }
  });
  // Modal button (if open for this racquet)
  const modalBtn = document.getElementById('modal-like-btn');
  if (modalBtn && modalBtn.dataset.racquetId === racquetId) {
    modalBtn.classList.toggle('liked', liked);
  }
}

// ── Modal ─────────────────────────────────────────────────────
function openModal(r) {
  document.getElementById('modal-brand').textContent  = extractBrand(r.racquet_name);
  document.getElementById('modal-name').textContent   = r.racquet_name;
  document.getElementById('modal-img').src            = r.racquet_img || '';
  document.getElementById('modal-img').alt            = r.racquet_name;
  document.getElementById('modal-price').textContent  = `$${formatPrice(r.racquet_price)}`;
  document.getElementById('modal-desc').textContent   = r.racquet_description || '';
  document.getElementById('modal-tw-link').href       = r.racquet_url || '#';

  // Rating
  const ratingEl = document.getElementById('modal-rating');
  ratingEl.textContent = r.racquet_rating !== null
    ? `★ ${r.racquet_rating} · ${r.racquet_rating_count} rating${r.racquet_rating_count !== 1 ? 's' : ''}`
    : 'No ratings yet';

  // Match score bar
  const matchRow = document.getElementById('modal-match-row');
  const matchBar = document.getElementById('modal-match-bar');
  const matchPct = document.getElementById('modal-match-pct');

  if (r.racquet_match_score !== undefined) {
    matchRow.classList.remove('hidden');
    matchPct.textContent = `${r.racquet_match_score}%`;
    requestAnimationFrame(() => {
      setTimeout(() => { matchBar.style.width = r.racquet_match_score + '%'; }, 60);
    });
  } else {
    matchRow.classList.add('hidden');
    matchBar.style.width = '0%';
  }

  modalOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  // Modal like button
  const modalLikeBtn = document.getElementById('modal-like-btn');
  modalLikeBtn.dataset.racquetId = r.racquet_id;
  modalLikeBtn.classList.toggle('liked', likedRacquets.has(r.racquet_id));
  modalLikeBtn.onclick = () => toggleLike(r.racquet_id, modalLikeBtn);

  modalClose.focus();
}

function closeModal() {
  // Reset bar before closing so next open animates fresh
  document.getElementById('modal-match-bar').style.width = '0%';
  modalOverlay.classList.add('hidden');
  document.body.style.overflow = '';
}

modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ── Helpers ───────────────────────────────────────────────────
const BRANDS = ['Wilson','Babolat','Head','Yonex','Prince','Dunlop',
                'Volkl','Tecnifibre','Solinco','ProKennex','Mizuno','Lacoste'];

function extractBrand(name) {
  for (const b of BRANDS) { if (name.startsWith(b)) return b; }
  return name.split(' ')[0];
}

function formatPrice(p) {
  if (p === null || p === undefined) return '—';
  return Number(p).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function esc(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// ── Boot ──────────────────────────────────────────────────────
startup();