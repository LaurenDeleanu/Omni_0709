# SuccessCore AI Agent Edge Router

Cloudflare Workers deployment for low-latency agent query routing at the edge.

## Prerequisites

- Cloudflare account with Workers enabled
- Wrangler CLI (`npm install -g wrangler`)
- KV namespace created for `AGENT_CACHE`

## Setup

1. **Install Wrangler:**
   ```bash
   npm install -g wrangler
   ```

2. **Authenticate with Cloudflare:**
   ```bash
   wrangler login
   ```

3. **Create KV namespace:**
   ```bash
   wrangler kv:namespace create "AGENT_CACHE"
   wrangler kv:namespace create "AGENT_CACHE" --preview
   ```

4. **Update `wrangler.toml`:**
   Replace `your-kv-namespace-id` and `your-preview-kv-id` with the IDs from step 3.
   Set `ORIGIN_URL` to your SuccessCore API origin (e.g., `https://api.yourdomain.com`).

5. **Deploy to dev:**
   ```bash
   wrangler dev
   ```

6. **Deploy to production:**
   ```bash
   wrangler deploy --env production
   ```

## Architecture

- **Edge handling** — Simple queries (short, no complex keywords) are responded to at the edge with minimal latency.
- **Origin forwarding** — Complex queries (containing keywords like "process", "analyze", "generate", "report", etc.) are forwarded to the origin API.
- **KV caching** — `GET /cache/*` routes serve cached responses from Cloudflare KV (`AGENT_CACHE` binding).
- **Health check** — `GET /health` returns edge status and region (Cloudflare colocation).

## Routes

| Method | Path | Description |
|--------|------|-------------|
| OPTIONS | * | CORS pre-flight |
| GET | /health | Edge health check |
| GET | /cache/* | Edge KV cache read |
| POST | /api/edge/agent/run | Edge-classified agent query |
| * | * | Forwarded to origin |
