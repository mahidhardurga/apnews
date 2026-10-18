// Build-time access to the scraper's JSON. Every reader tolerates missing data so the very first
// deploy (before any scrape has run) still builds.
import fs from 'node:fs';
import path from 'node:path';
import type { Card, District, Leader, Story } from './types';

const DIR = path.resolve(process.cwd(), 'public/data');

export function readJSON<T>(rel: string, fallback: T): T {
  try {
    return JSON.parse(fs.readFileSync(path.join(DIR, rel), 'utf8')) as T;
  } catch {
    return fallback;
  }
}

export interface Headline { id: string; title: string; url: string; source: string; source_name: string; language: string; published: string }
export const latestHeadlines = (): Headline[] => readJSON<{ articles: Headline[] }>('latest.json', { articles: [] }).articles ?? [];
export const latestCards = (): Card[] => readJSON<{ stories: Card[] }>('latest.json', { stories: [] }).stories ?? [];
export const leaders = (): Leader[] => readJSON<{ leaders: Leader[] }>('leaders.json', { leaders: [] }).leaders ?? [];
export const districts = (): District[] => readJSON<{ districts: District[] }>('districts.json', { districts: [] }).districts ?? [];

export function allStories(): Story[] {
  const dir = path.join(DIR, 'stories');
  if (!fs.existsSync(dir)) return [];
  const out: Story[] = [];
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith('.json')) continue;
    const s = readJSON<Story | null>(`stories/${f}`, null);
    if (s && s.relevant !== false && s.headline_en) out.push(s);
  }
  return out.sort((a, b) => b.updated.localeCompare(a.updated));
}

export const fmtDate = (iso: string) =>
  new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata' }).format(new Date(iso)) + ' IST';

export const SITE = 'https://apnews.mahidhardurga.in';
