const API_ORIGIN = (process.env.API_ORIGIN || 'https://test-39sh.onrender.com').replace(/\/$/, '');

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Max-Age', '86400');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (!['GET', 'POST'].includes(req.method)) {
    res.setHeader('Allow', 'GET, POST, OPTIONS');
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const upstream = await fetch(`${API_ORIGIN}${req.url}`, {
      method: req.method,
      headers: req.method === 'POST' ? { 'Content-Type': 'application/json' } : undefined,
      body: req.method === 'POST' ? JSON.stringify(req.body ?? {}) : undefined
    });
    const contentType = upstream.headers.get('content-type');
    if (contentType) res.setHeader('Content-Type', contentType);
    return res.status(upstream.status).send(await upstream.text());
  } catch (error) {
    return res.status(502).json({ error: 'Could not reach the events API', detail: error.message });
  }
}
