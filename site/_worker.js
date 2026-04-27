export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/api/analytics' && request.method === 'GET') {
      return handleAnalyticsDashboard(request, env);
    }

    const response = await env.ASSETS.fetch(request);

    const ct = response.headers.get('content-type') || '';
    if (ct.includes('text/html') && env.ANALYTICS) {
      ctx.waitUntil(logHit(request, env, url));
    }

    return response;
  }
};

const BOT_UA_PATTERNS = /bot|crawl|spider|slurp|baidu|yandex|duckduck|facebookexternalhit|linkedinbot|twitterbot|whatsapp|telegram|preview|fetch|monitor|check|scan|probe|curl|wget|python-requests|go-http|java\/|libwww|httpie|postman|insomnia|HeadlessChrome|PhantomJS|Lighthouse|PageSpeed|GTmetrix|pingdom|uptimerobot|statuscake|site24x7|newrelic|datadog|applebot|googlebot|bingbot|msnbot|ahrefsbot|semrushbot|dotbot|rogerbot|screaming frog|majestic|mj12bot|bytespider|petalbot|sogou|exabot|ia_archiver|archive\.org/i;

function isBot(request) {
  const ua = request.headers.get('user-agent') || '';
  if (!ua || ua.length < 10) return true;
  if (BOT_UA_PATTERNS.test(ua)) return true;
  const purpose = request.headers.get('purpose') || request.headers.get('x-purpose') || '';
  if (purpose === 'prefetch' || purpose === 'preview') return true;
  const secPurpose = request.headers.get('sec-fetch-dest') || '';
  if (secPurpose === 'prefetch') return true;
  const lang = request.headers.get('accept-language') || '';
  if (!lang) return true;
  return false;
}

async function logHit(request, env, url) {
  if (isBot(request)) return;

  const cf = request.cf || {};
  const ts = new Date().toISOString();
  const day = ts.slice(0, 10);

  const hit = {
    ts,
    path: url.pathname,
    ip: request.headers.get('cf-connecting-ip') || '',
    country: cf.country || '',
    city: cf.city || '',
    region: cf.region || '',
    asn: cf.asn || '',
    asOrg: cf.asOrganization || '',
    ua: request.headers.get('user-agent') || '',
    referer: request.headers.get('referer') || '',
    lang: request.headers.get('accept-language') || '',
    tls: cf.tlsVersion || '',
    httpProto: cf.httpProtocol || '',
  };

  const key = `hits/${day}/${ts}-${Math.random().toString(36).slice(2, 8)}`;

  try {
    await env.ANALYTICS.put(key, JSON.stringify(hit), {
      expirationTtl: 60 * 60 * 24 * 90
    });
  } catch (e) {
    console.error('Analytics write failed:', e);
  }
}

async function handleAnalyticsDashboard(request, env) {
  const url = new URL(request.url);
  const secret = url.searchParams.get('key');

  if (secret !== (env.ANALYTICS_KEY || 'willow-sees-all')) {
    return new Response('Forbidden', { status: 403 });
  }

  const days = parseInt(url.searchParams.get('days') || '7', 10);
  const mode = url.searchParams.get('mode') || 'summary';

  const results = {};
  const now = new Date();

  async function batchGet(keys, kv) {
    const BATCH = 50;
    const vals = [];
    for (let i = 0; i < keys.length; i += BATCH) {
      const batch = keys.slice(i, i + BATCH);
      const fetched = await Promise.all(batch.map(k => kv.get(k.name)));
      vals.push(...fetched);
    }
    return vals.filter(Boolean).map(v => JSON.parse(v));
  }

  for (let d = 0; d < days; d++) {
    const date = new Date(now);
    date.setDate(date.getDate() - d);
    const day = date.toISOString().slice(0, 10);

    const list = await env.ANALYTICS.list({ prefix: `hits/${day}/`, limit: 1000 });
    if (list.keys.length === 0) continue;

    if (mode === 'summary') {
      const hits = await batchGet(list.keys, env.ANALYTICS);
      const orgs = {};
      const paths = {};
      const countries = {};
      const referers = {};
      for (const hit of hits) {
        if (hit.asOrg) orgs[hit.asOrg] = (orgs[hit.asOrg] || 0) + 1;
        if (hit.path) paths[hit.path] = (paths[hit.path] || 0) + 1;
        if (hit.country) countries[hit.country] = (countries[hit.country] || 0) + 1;
        if (hit.referer) {
          try {
            const ref = new URL(hit.referer).hostname;
            if (ref && ref !== 'theshapeofthought.com') {
              referers[ref] = (referers[ref] || 0) + 1;
            }
          } catch {}
        }
      }
      const top = (obj, n) => Object.entries(obj).sort((a,b) => b[1]-a[1]).slice(0,n).map(([name,count]) => ({name,count}));
      results[day] = {
        views: list.keys.length,
        orgs: top(orgs, 10),
        paths: top(paths, 10),
        countries: top(countries, 10),
        referers: top(referers, 10)
      };
    } else if (mode === 'hits') {
      const recent = list.keys.slice(-50);
      results[day] = await batchGet(recent, env.ANALYTICS);
    }
  }

  return new Response(JSON.stringify(results, null, 2), {
    headers: { 'Content-Type': 'application/json' }
  });
}
