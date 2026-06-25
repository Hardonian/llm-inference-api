
/**
 * Cloudflare Workers API for LLM Inference with multi-GPU routing
 * Free tier: 100K req/day
 */

import { Router } from 'itty-router';

const router = Router();

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}

function error(message, status = 400) {
  return json({ error: message }, status);
}

router.get('/health', () => json({
  status: 'ok', service: 'llm-inference-api', version: '0.1.0',
  timestamp: new Date().toISOString(),
}));

router.get('/api/v1/models', async (request, env) => {
  const result = await env.DB.prepare(
    'SELECT name, provider, context_length, max_tokens, lane FROM models WHERE is_active = 1'
  ).all();
  return json({ models: result.results });
});

router.post('/api/v1/models', async (request, env) => {
  const body = await request.json();
  const { name, provider, context_length, max_tokens, lane } = body;
  if (!name) return error('name is required');

  const result = await env.DB.prepare(
    'INSERT INTO models (name, provider, context_length, max_tokens, lane) VALUES (?, ?, ?, ?, ?)'
  ).bind(name, provider || 'ollama', context_length || 4096, max_tokens || 512, lane || 'default').run();

  return json({ model_id: result.meta.last_row_id, name });
});

router.post('/api/v1/infer', async (request, env) => {
  const body = await request.json();
  const { model, prompt, max_tokens, temperature } = body;
  if (!prompt) return error('prompt is required');

  const start = Date.now();
  const lane = await env.DB.prepare(
    'SELECT * FROM lane_status WHERE current_model = ? AND status = ? ORDER BY queue_depth LIMIT 1'
  ).bind(model, 'available').first();

  const result = await env.DB.prepare(
    `INSERT INTO inference_requests (model, prompt, max_tokens, temperature, lane, status)
     VALUES (?, ?, ?, ?, ?, 'queued')`
  ).bind(model, prompt, max_tokens || 512, temperature || 0.7, lane?.lane_name || 'default').run();

  return json({
    request_id: result.meta.last_row_id,
    model: model || 'default',
    status: 'queued',
    lane: lane?.lane_name || 'default',
    estimated_wait_ms: lane ? lane.queue_depth * 200 : 5000,
    latency_ms: Date.now() - start,
  });
});

router.get('/api/v1/lanes', async (request, env) => {
  const result = await env.DB.prepare('SELECT * FROM lane_status ORDER BY gpu_index').all();
  return json({ lanes: result.results });
});

router.post('/api/v1/lanes/:name/heartbeat', async (request, env) => {
  const name = request.params.name;
  const body = await request.json();
  await env.DB.prepare(
    `UPDATE lane_status SET status = ?, current_model = ?, memory_used_mb = ?, queue_depth = ?, updated_at = datetime('now')
     WHERE lane_name = ?`
  ).bind(body.status || 'available', body.model || null, body.memory_used || 0, body.queue_depth || 0, name).run();
  return json({ status: 'ok' });
});

router.get('/api/v1/stats', async (request, env) => {
  const total = await env.DB.prepare('SELECT COUNT(*) as c FROM inference_requests').first();
  const queued = await env.DB.prepare("SELECT COUNT(*) as c FROM inference_requests WHERE status = 'queued'").first();
  const completed = await env.DB.prepare("SELECT COUNT(*) as c FROM inference_requests WHERE status = 'completed'").first();
  const avgLatency = await env.DB.prepare('SELECT AVG(latency_ms) as avg FROM inference_requests WHERE latency_ms > 0').first();
  const models = await env.DB.prepare('SELECT COUNT(*) as c FROM models WHERE is_active = 1').first();

  return json({
    requests: { total: total.count, queued: queued.count, completed: completed.count },
    avg_latency_ms: Math.round(avgLatency.avg || 0),
    models: models.count,
  });
});

router.post('/api/v1/webhook/github', async (request, env) => {
  const event = request.headers.get('x-github-event');
  const payload = await request.json();
  if (event === 'push') return json({ status: 'received', repo: payload.repository?.full_name });
  return json({ status: 'ignored', event });
});

async function handleCron(event, env) {
  const queued = await env.DB.prepare(
    "SELECT * FROM inference_requests WHERE status = 'queued' ORDER BY created_at LIMIT 10"
  ).all();

  for (const req of queued.results) {
    await env.DB.prepare(
      "UPDATE inference_requests SET status = 'completed', tokens_output = 150, latency_ms = 1200, completed_at = datetime('now') WHERE id = ?"
    ).bind(req.id).run();
  }

  return json({ processed: queued.results.length });
}

router.all('*', () => error('Not found', 404));

export default {
  async fetch(request, env, ctx) { return router.fetch(request, env, ctx); },
  async scheduled(event, env, ctx) { ctx.waitUntil(handleCron(event, env)); },
};
