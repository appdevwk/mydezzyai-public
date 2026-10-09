# myDEZZYAI private Vercel workbench

This package adapts the original local Python workbench for a **private, single-user web deployment**. It includes research, drafting, Python code generation, browser text-to-speech, three-card tarot, five-card stud practice, and an optional LiveKit voice/avatar connection.

## Deploy

1. Extract this ZIP and push the contents of `mydezzyai-vercel/` to a GitHub repository. The repository root must contain `vercel.json`, `core.py`, `web.js`, and `api/index.py`.
2. Import the repository into Vercel. Choose Framework Preset **Other**, with no build command and no output directory override. Use Python 3.12 and enable Fluid Compute.
3. Set these **server-side** environment variables for your intended deployment environment:
   - `OPENAI_API_KEY`: your OpenAI API key; API billing is separate from ChatGPT.
   - `OPENAI_MODEL`: a model your API account can access that supports Responses API web search and structured outputs. The inherited default is `gpt-5`; verify availability for your account.
   - `DEZZY_USERNAME`: your private login name.
   - `DEZZY_PASSWORD`: a long, unique private password.
   - `DEZZY_SIGNING_SECRET`: a separately generated random secret. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` on your machine.
   - `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`: optional server-side LiveKit project settings. `LIVEKIT_ROOM` is optional and defaults to `dezzy`.
4. Deploy. Open the HTTPS deployment URL and sign in at the browser's credential prompt.
5. Visit `/api/health` after signing in. Confirm `ok` and `ai_configured` are true. Under the current free-only scope, verify a task request is rejected without provider calls. Only with a separate explicit spend authorization, persistent storage and bounded quotas may an operator run a short research task and verify its seven steps, download, refresh and saved history. Test read-aloud and both games on the target phone.

Keep credentials in Vercel environment settings; never put them into the repository or browser code. If environment variables are added after a deployment, redeploy.

## Search and sharing

`/about` is a public introduction with a descriptive title, description, Open Graph sharing tags, and WebApplication structured data. Set `DEZZY_PUBLIC_URL` to your production HTTPS origin (for example `https://dezzy.yourdomain.com`, without a path) to enable its canonical URL and `/sitemap.xml`. `/robots.txt` permits only the introduction. The private workbench and APIs carry `noindex, nofollow` directives; authentication still protects their contents. Search indexing and rankings are not guaranteed.

## Behavior and limitations

- Each step performs one paid model request and finishes within its own HTTP request. There are seven steps per task, including three web searches. A persistent PostgreSQL ledger is required by the Vercel entrypoint; local SQLite is allowed only on a durable non-serverless host.
- The browser passes server-signed task state between steps. Signing prevents editing the task state; it does **not** encrypt it. State expires after 24 hours. Public task continuation uses durable owned job IDs instead of browser-supplied signed state. UUID request IDs return cached results on replay; reservations commit before provider calls. If a worker crashes after reservation, the request is uncertain and blocks further calls until an operator reconciles it; no automatic retry occurs. This guarantees at-most-once application invocation per request, not provider billing exactly-once.
- History is stored server-side under the authenticated private account. Use Load saved tasks to retrieve the latest 30 entries. New task contents are not written to browser localStorage; older versions may have left a legacy cache, removable through browser site-data settings.
- Keep the tab open while a task runs. Mobile backgrounding or network loss can interrupt it. The app does not automatically retry uncertain requests; starting again may duplicate paid work.
- HTTP Basic authentication protects the page and APIs. This is personal access protection, not a customer authentication system. Browsers may retain credentials until the browser session ends.
- Generated Python is syntax-checked in memory, never executed. Speech uses available browser voices for report read-aloud. When LiveKit settings are present, the private workbench also offers a secure room connection that subscribes to the agent's published voice and avatar tracks.
- A shared multi-user production service needs per-user authentication, persistent storage, durable task execution, quotas, and billing before launch.

## Local QA

Install pinned dependencies with `python3 -m pip install -r requirements.txt`.

```bash
python3 core.py --self-test
python3 -m unittest discover -s tests -v
node --check web.js
node tests/test_client.cjs
node tests/test_games.cjs
```

To serve the Vercel handler locally after setting the private environment variables:

```bash
python3 -c "from http.server import ThreadingHTTPServer; from api.index import handler; ThreadingHTTPServer(('127.0.0.1', 8000), handler).serve_forever()"
```

Open `http://127.0.0.1:8000` on that same machine. The original local application remains available as `python3 core.py`.

## QA status

Local verification passes 5 original core self-tests and 16 web/ledger tests, JavaScript syntax, client workflow/server-history checks, game checks, and LiveKit mock regressions. Provider responses are mocked; no paid request was made. Durable tests cover replay, ownership, concurrency, daily/total quotas, uncertain worker outcomes, expiry without reservation leaks and rejection of ephemeral Vercel SQLite.

Production readiness remains **NO PASS** until the corrected source is tied to a preview, persistent PostgreSQL is configured and tested, account free-only/no-upgrade settings are verified externally, browser/mobile flows are inspected, and the requested voice/avatar agent is verified. A green mock suite does not prove a live provider, real microphone/voice or a deployed PostgreSQL backend.

Official references: https://vercel.com/docs/functions/runtimes/python and https://vercel.com/docs/functions/configuring-functions/duration

## Spending and persistent storage controls

AI and live voice are disabled by default. Keys alone cannot enable paid requests. No free-provider allowance or no-upgrade account setting has been verified; local guards do not prove a provider account plan. Keep both disabled for the current free-only scope. Offline games require no provider request.

- `DATABASE_URL`: persistent PostgreSQL connection for Vercel (TLS required; Neon is compatible). Provisioning and provider plan/budget verification remain outside prerequisites. SQLite paths are rejected when `VERCEL` is set; Vercel filesystems are not durable.
- `DEZZY_DATABASE_PATH`: absolute persistent SQLite path for local/self-hosted QA only, never `/tmp`.
- `DEZZY_ALLOW_PAID_AI`: defaults disabled; only literal `true` enables calls. Enabling requires separate explicit spending authorization.
- `DEZZY_DAILY_REQUEST_LIMIT`, `DEZZY_TOTAL_REQUEST_LIMIT`: positive server-enforced reservation caps required if AI is enabled. They cap request counts, not dollars; account spending controls must be set independently.
- `DEZZY_ALLOW_LIVEKIT`: defaults disabled; only enable after voice account costs and agent are verified. SDK is pinned to 2.22.3; only the configured secure WebSocket origin is added to CSP.

Ledger tables are created idempotently on first use. All history and request records are owned by the configured Basic-auth username. The app remains a private single-user workbench, without subscriber signup, customer account recovery, or subscription billing. Do not add a checkout button or claim a public subscription service until a real identity/entitlement system and a payment sandbox are verified.

An uncertain reservation must be reconciled against provider records before any operator action; the application has no automatic reservation-reset endpoint. No retention deletion or plan upgrade is automatic. Protect database credentials and backups and define retention before customer launch.

Additional verification: `python3 -m unittest discover -s tests -v` includes durable replay, owner isolation, quota, restart/history, concurrency, uncertain outcomes and serverless storage rejection; `node tests/test_livekit.cjs` checks microphone-denial cleanup and attached-track containers. PostgreSQL deployment integration, real browser history/rendering, paid provider requests and actual voice remain unverified.

The inherited standalone `core.py` paid-provider path is deliberately blocked without a durable reservation; use the protected web handler for authorized tasks. Mocked self-tests and offline games still work.
