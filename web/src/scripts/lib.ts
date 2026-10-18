// Client-side helpers shared by the runtime-rendered pages.
import { districtLabel, topicLabel } from '../lib/i18n';
import type { Card } from '../lib/types';

// Same-origin by default. Set PUBLIC_DATA_BASE at build time to read from elsewhere
// (e.g. https://raw.githubusercontent.com/<user>/<repo>/main/web/public/data) for updates between deploys.
export const DATA_BASE: string = (import.meta.env.PUBLIC_DATA_BASE as string | undefined) || '/data';

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${DATA_BASE}/${path}`, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json() as Promise<T>;
}

export interface Headline {
  id: string; title: string; url: string; source: string; source_name: string;
  language: 'en' | 'te'; published: string; topic: string; district: string | null;
}

export const lang = (): 'en' | 'te' => (document.documentElement.dataset.lang === 'te' ? 'te' : 'en');
export const ui = (en: string, te: string) => (lang() === 'te' ? te : en);

export const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);

/** Both languages, CSS shows the active one (so toggling needs no re-render). */
export const dual = (en: string, te: string) =>
  `<span class="l-en">${esc(en)}</span><span class="l-te" lang="te">${esc(te)}</span>`;

export function timeAgo(iso: string): string {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 60) return dual(`${mins} min ago`, `${mins} నిమిషాల క్రితం`);
  const h = Math.round(mins / 60);
  if (h < 48) return dual(`${h} h ago`, `${h} గంటల క్రితం`);
  const d = Math.round(h / 24);
  return dual(`${d} days ago`, `${d} రోజుల క్రితం`);
}

const chip = (kind: string, value: string, labels: [string, string]) =>
  `<a class="chip" href="/?${kind}=${encodeURIComponent(value)}" data-k="${kind}" data-v="${esc(value)}">${dual(...labels)}</a>`;

export function chips(c: Pick<Card, 'tags'>): string {
  const t = c.tags;
  return [
    ...t.parties.map((p) => chip('party', p, [p, p])),
    ...t.leaders.map((l) => chip('leader', l, [l, l])),
    ...(t.district ? [chip('district', t.district, districtLabel(t.district))] : []),
    ...(t.topic && t.topic !== 'other' ? [chip('topic', t.topic, topicLabel(t.topic))] : []),
  ].join('');
}

export function cardHTML(c: Card, n?: number): string {
  const fbEn = c.fallback?.en, fbTe = c.fallback?.te;
  const badge = (on: boolean | undefined, txt: string, title: string) =>
    on ? ` <span class="rounded bg-amber-100 px-1 text-[10px] font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-200" title="${title}">${txt}</span>` : '';
  return `<article class="card">
    <h2 class="text-base font-semibold leading-snug sm:text-lg">
      ${n ? `<span class="muted mr-1">${n}.</span>` : ''}<a class="no-underline hover:underline" href="/story/${c.id}/">
        <span class="l-en">${esc(c.headline_en)}${badge(fbEn, 'తెలుగు', 'Original is in Telugu')}</span>
        <span class="l-te" lang="te">${esc(c.headline_te)}${badge(fbTe, 'EN', 'అసలు ఆంగ్లంలో ఉంది')}</span></a>
    </h2>
    <p class="clamp3 mt-1.5 text-sm text-slate-600 dark:text-slate-300">${dual(c.summary_en, c.summary_te)}</p>
    <div class="mt-2.5 flex flex-wrap gap-1.5">${chips(c)}</div>
    <p class="mt-2.5 text-xs muted">
      ${timeAgo(c.updated)} · ${c.n_articles} ${dual(c.n_articles === 1 ? 'article' : 'articles', 'కథనాలు')} · ${esc(c.outlets.join(', '))}
    </p>
  </article>`;
}
