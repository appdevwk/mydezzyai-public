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
5. Visit `/api/health` after signing in. Confirm `ok` and `ai_configured` are true. Run one short research task, confirm all seven steps finish, download the report, refresh, and reopen it from saved tasks. Test read-aloud and both games on the target phone.

Keep credentials in Vercel environment settings; never put them into the repository or browser code. If environment variables are added after a deployment, redeploy.

## Search and sharing

`/about` is a public introduction with a descriptive title, description, Open Graph sharing tags, and WebApplication structured data. Set `DEZZY_PUBLIC_URL` to your production HTTPS origin (for example `https://dezzy.yourdomain.com`, without a path) to enable its canonical URL and `/sitemap.xml`. `/robots.txt` permits only the introduction. The private workbench and APIs carry `noindex, nofollow` directives; authentication still protects their contents. Search indexing and rankings are not guaranteed.

## Behavior and limitations

- Each step performs one paid model request and finishes within its own HTTP request. There are seven steps per task, including three web searches. No server background thread or SQLite database is used by the Vercel entrypoint.
- The browser passes server-signed task state between steps. Signing prevents editing the task state; it does **not** encrypt it. State expires after 24 hours. Replaying a valid request can repeat a paid call; exactly-once execution would require durable database records.
- History is stored in browser localStorage, unencrypted, for up to 30 tasks. It is not synchronized across devices and can be lost if browser data is cleared. Download important results. Clearing site data removes the local history.
- Keep the tab open while a task runs. Mobile backgrounding or network loss can interrupt it. The app does not automatically retry uncertain requests; starting again may duplicate paid work.
- HTTP Basic authentication protects the page and APIs. This is personal access protection, not a customer authentication system. Browsers may retain credentials until the browser session ends.
- Generated Python is syntax-checked in memory, never executed. Speech uses available browser voices for report read-aloud. When LiveKit settings are present, the private workbench also offers a secure room connection that subscribes to the agent's published voice and avatar tracks.
- A shared multi-user production service needs per-user authentication, persistent storage, durable task execution, quotas, and billing before launch.

## Local QA

No pip packages are required.

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

The original five Python checks, six Vercel adapter checks, JavaScript syntax check, client flow checks, and game checks pass in the development environment with mocked model responses. Authentication, missing configuration, request validation, signed-state integrity, expiry, three deliverable modes, provider failure, downloads, network interruption, SEO routes, all nine poker hand categories, ace-low straights, ties, complete stud hands, tarot draws, and tab switching are covered.

Live OpenAI calls, actual Vercel build/deployment routing, browser rendering, target-phone speech, and device interaction have **not** been verified. Browser QA was attempted: the hosted browser blocked localhost access, and agent-browser's control daemon could not bind its socket (`Operation not permitted`). Therefore no visual or click-through pass is claimed. Complete step 5 after deployment before calling this production-verified.

Official references: https://vercel.com/docs/functions/runtimes/python and https://vercel.com/docs/functions/configuring-functions/duration
