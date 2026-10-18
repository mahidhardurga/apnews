import type { APIRoute } from 'astro';
import { latestHeadlines, SITE } from '../lib/data';

const x = (s: string) => s.replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' })[c]!);

// Each item links straight to the original article.
export const GET: APIRoute = () => {
  const items = latestHeadlines().slice(0, 60);
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>AP News – Andhra Pradesh headlines</title>
    <link>${SITE}/</link>
    <description>Latest Andhra Pradesh headlines; every item links to the original publisher.</description>
    <language>en</language>
    <atom:link href="${SITE}/rss.xml" rel="self" type="application/rss+xml" />${items.map((a) => `
    <item>
      <title>${x(a.title)}</title>
      <link>${x(a.url)}</link>
      <guid isPermaLink="true">${x(a.url)}</guid>
      <pubDate>${new Date(a.published).toUTCString()}</pubDate>
      <source url="${SITE}/rss.xml">${x(a.source_name)}</source>
    </item>`).join('')}
  </channel>
</rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
};
