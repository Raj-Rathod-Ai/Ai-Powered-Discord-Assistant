# Feature and Security Audit

Audit basis: static review of the repository source. Provider-backed behavior still requires live deployment tests.

## Feature inventory

| Feature | Current implementation | Audit status / follow-up |
|---|---|---|
| Discord Gateway and health server | discord.py plus HTTP health endpoints | Implemented; verify reconnect and readiness in deployment |
| Channel activation | In-memory per-user/per-channel /start and /stop | Resets on restart; now constrained by channel allowlist |
| Channel access control | DISCORD_ALLOWED_CHANNEL_IDS | Added; fail-closed when unset |
| Tool listing | /tools | Implemented; keep synchronized with ALL_TOOLS |
| QR generation | /aiqr and deterministic QR message handler | Implemented; test scanner reliability |
| Image generation | !imagine and Cloudflare FLUX | Live credentials/model need verification |
| Web search | Tavily and DuckDuckGo | Provider errors and source presentation need testing |
| GitHub repository search | GitHub REST API | Increase to 10 results and include stars, language, license, updated time |
| Wikipedia | wikipedia_search | Disambiguation/network edge cases need tests |
| Webpage reader | requests + BeautifulSoup | Partial SSRF controls; redirect disabled, but DNS rebinding/egress restrictions remain |
| YouTube transcript | youtube-transcript-api | Captions may be unavailable |
| Translation | deep-translator | External service dependency |
| Summarization | Separate Ollama call | Can fail independently of primary LLM and requires reachable Ollama |
| Calculator | AST allowlist | Unit test and bound numeric magnitude |
| Unit conversion | Built-in conversion table | Limited unit catalog |
| JSON/Base64/URL/Markdown | Local utilities | Add edge-case tests |
| Password/UUID/date/regex/hash/color | Local utilities | Add edge-case/security tests |

## LLM quality risks

- No golden dataset previously existed in CI.
- Tool invocation depends on provider tool-calling compatibility; run live tests against the configured model.
- Tool output is not universally cited in Discord responses.
- Conversation state is not persisted; each message is sent as a fresh agent invocation.
- Generic user-facing errors hide internal stack traces; operators must inspect server logs.
- summarize_text creates a separate Ollama client rather than using the configured primary LLM.

## Release checklist

1. Set DISCORD_ALLOWED_CHANNEL_IDS to the approved channel ID in Render.
2. Confirm Cloudflare chat model variables and tool-call compatibility; avoid unintended localhost Ollama fallback in production.
3. Run pytest -q.
4. Run RUN_LIVE_LLM_EVALS=1 python evals/run_eval.py with credentials configured.
5. In Discord, test /start, /stop, /tools, /aiqr, GitHub search, web search, calculator and image generation in the approved channel.
6. Verify other channels cannot use slash commands or receive bot responses.
7. Check logs do not expose secrets or content that should not be retained.

## Scope limitations

This is a static source audit plus offline tests. It does not claim all external integrations were live-tested.
