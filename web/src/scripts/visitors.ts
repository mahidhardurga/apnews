// Public visitor counter backed by the free Abacus hit-counter API (no account, no cookies).
// Each browser is counted once (flag in localStorage); later visits only read the number.
// The badge is always shown; it stays hidden only if the service cannot be reached.
const BASE = 'https://abacus.jasoncameron.dev';
const NAMESPACE = 'apnews-mahidhardurga-in';
const DEFAULT_KEY = 'visitors';

const isLocal = () => ['localhost', '127.0.0.1'].includes(location.hostname);

export async function showVisitors(badge: HTMLElement): Promise<void> {
  try {
    // On localhost only, ?counterkey=NAME counts against a separate test counter (never the real one).
    const q = new URLSearchParams(location.search);
    const key = isLocal() ? q.get('counterkey') || DEFAULT_KEY : DEFAULT_KEY;

    let counted = false;
    try { counted = localStorage.getItem('counted') === '1'; } catch { /* storage blocked: just read */ }
    const hit = !counted && !(navigator as Navigator & { webdriver?: boolean }).webdriver && (!isLocal() || q.has('counterkey'));

    const res = await fetch(`${BASE}/${hit ? 'hit' : 'get'}/${NAMESPACE}/${key}`);
    // 404 only means nobody has been counted yet.
    if (!res.ok && res.status !== 404) return;
    const value = res.ok ? ((await res.json()) as { value?: number }).value : 0;
    if (typeof value !== 'number') return;
    if (hit && !isLocal()) { try { localStorage.setItem('counted', '1'); } catch { /* ignore */ } }

    badge.querySelector('[data-n]')!.textContent = new Intl.NumberFormat('en-IN').format(value);
    badge.querySelector('[data-unit]')!.textContent = value === 1 ? 'reader' : 'readers';
    badge.hidden = false;
  } catch {
    /* counter is decoration: never break the page */
  }
}
