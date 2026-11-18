import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const app = express();
const port = process.env.PORT || 3000;
const apiOrigin = (process.env.API_ORIGIN || 'https://test-39sh.onrender.com').replace(/\/$/, '');
const root = path.dirname(fileURLToPath(import.meta.url));

// The upstream API does not currently send CORS headers. The browser calls this
// same-origin proxy; this policy also permits previewing the frontend elsewhere.
app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});
app.use(express.json());
app.all('/api/*', async (req, res) => {
  try {
    const upstream = await fetch(`${apiOrigin}${req.originalUrl}`, {
      method: req.method,
      headers: req.method === 'POST' ? { 'Content-Type': 'application/json' } : undefined,
      body: req.method === 'POST' ? JSON.stringify(req.body ?? {}) : undefined
    });
    res.status(upstream.status);
    res.type(upstream.headers.get('content-type') || 'application/json');
    res.send(await upstream.text());
  } catch (error) {
    res.status(502).json({ error: 'Could not reach the events API', detail: error.message });
  }
});
app.use(express.static(path.join(root, 'dist')));
app.get('*', (_req, res) => res.sendFile(path.join(root, 'dist', 'index.html')));
app.listen(port, () => console.log(`EventSphere listening on ${port}`));
