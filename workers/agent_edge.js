// SuccessCore AI Agent Edge Router
// Deployed to Cloudflare Workers for minimal-latency agent routing
// Routes simple queries directly, forwards complex ones to origin

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS pre-flight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
        }
      });
    }

    // Health check
    if (path === '/health') {
      return new Response(JSON.stringify({ status: 'ok', edge: true, region: request.cf?.colo || 'unknown' }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Edge cache: serve from KV if available
    if (request.method === 'GET' && path.startsWith('/cache/')) {
      const cacheKey = path.replace('/cache/', '');
      const cached = await env.AGENT_CACHE.get(cacheKey);
      if (cached) {
        return new Response(cached, {
          headers: { 'Content-Type': 'application/json', 'X-Cache': 'HIT' }
        });
      }
    }

    // Simple classification: if query is simple, respond from edge; if complex, forward to origin
    if (path === '/api/edge/agent/run' && request.method === 'POST') {
      try {
        const body = await request.json();
        const isSimple = await classifyComplexity(body.message, env);

        if (isSimple) {
          // Handle simple queries at edge with the lightweight model
          const response = await handleSimpleQuery(body, env);
          return new Response(JSON.stringify(response), {
            headers: { 'Content-Type': 'application/json', 'X-Edge': 'true' }
          });
        }
      } catch (e) {
        // If parsing fails, fall through to origin
      }
    }

    // Forward everything else to origin
    const originUrl = `${env.ORIGIN_URL}${path}`;
    const originResponse = await fetch(originUrl, {
      method: request.method,
      headers: request.headers,
      body: request.method !== 'GET' ? await request.text() : undefined,
    });

    const response = new Response(originResponse.body, originResponse);
    response.headers.set('X-Edge', 'routed');
    return response;
  }
};

async function classifyComplexity(message, env) {
  // Simple heuristic: short messages without "process", "analyze", "generate" are likely simple
  const complexKeywords = ['process', 'analyze', 'generate', 'report', 'payroll', 'batch', 'calculate', 'compare', 'optimize'];
  const isComplex = complexKeywords.some(k => message.toLowerCase().includes(k));
  return !isComplex && message.length < 100;
}

async function handleSimpleQuery(body, env) {
  // Forward simple queries to a fast edge-compatible model
  // In production: use Workers AI or a fast API endpoint
  return {
    success: true,
    response: `[Edge] Query received: ${body.message.substring(0, 50)}... (routed to edge for fast response)`,
    edge_processed: true,
  };
}
