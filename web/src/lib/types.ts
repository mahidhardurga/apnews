export interface Tags { parties: string[]; leaders: string[]; district: string | null; topic: string }

export interface Card {
  id: string;
  headline_en: string; headline_te: string;
  summary_en: string; summary_te: string;
  tags: Tags;
  fallback?: { en: boolean; te: boolean };
  created: string; updated: string;
  n_articles: number;
  outlets: string[];
  languages: string[];
}

export interface Article {
  id: string; url: string; title: string; excerpt: string;
  source: string; source_name: string; language: string; published: string;
}

export interface Story extends Card { articles: Article[]; relevant?: boolean }

export interface Stub { id: string; headline_en: string; headline_te: string; updated: string }
export interface Leader { slug: string; name: string; count: number; parties: string[]; last_seen: string; stories: Stub[] }
export interface District { slug: string; name: string; count: number; stories: Stub[] }
export interface TrendRow { kind: 'leader' | 'party' | 'topic' | 'district'; name: string; count: number; previous: number; delta: number }
