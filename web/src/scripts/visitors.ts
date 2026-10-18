// Public visitor counter backed by the free Abacus hit-counter API (no account, no cookies).
// Each browser is counted once (flag in localStorage); later visits only read the number.
// The badge stays hidden until the count reaches MIN_SHOW and whenever the service is unreachable.
const BASE = 'https://abacus.jasoncameron.dev';
const NAMESPACE = 'apnews-mahidhardurga-in';
const DEFAULT_KEY = 'visitors';
export const MIN_SHOW = 100;

const isLocal = () => ['localhost', '127.0.0.1'].includes(location.hostname);

export async function showVisitors(badge: HTMLElement): Promise<void> {
  try {
    // Test hooks work on localhost only, so they cannot be used to fake the public number.
    const q = new URLSearchParams(location.search);
    const key = isLocal() ? q.get('counterkey') || DEFAULT_KEY : DEFAULT_KEY;
    const minShow = isLocal() && q.has('minvisitors') ? Number(q.get('minvisitors')) : MIN_SHOW;

    let counted = false;
    try { counted = localStorage.getItem('counted') === '1'; } catch { /* storage blocked: just read */ }
    const hit = !counted && !(navigator as Navigator & { webdriver?: boolean }).webdriver && (!isLocal() || q.has('counterkey'));

    const res = await fetch(`${BASE}/${hit ? 'hit' : 'get'}/${NAMESPACE}/${key}`);
    if (!res.ok) return;
    const { value } = (await res.json()) as { value?: number };
    if (hit && !isLocal()) { try { localStorage.setItem('counted', '1'); } catch { /* ignore */ } }
    if (typeof value !== 'number' || value < minShow) return;

    const n = badge.querySelector('[data-n]');
    if (n) n.textContent = new Intl.NumberFormat('en-IN').format(value);
    badge.hidden = false;
  } catch {
    /* counter is decoration: never break the page */
  }
}
