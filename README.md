# Rudra AI Discord Assistant

Rudra is a Python Discord assistant built with discord.py, LangChain, Ollama, Qwen and Cloudflare Workers AI. It supports channel-level activation, AI chat, web search, image generation and practical utilities.

## Features

- AI chat using Cloudflare Workers AI or an external Ollama endpoint
- Tavily and DuckDuckGo web search
- Cloudflare FLUX image generation with `!imagine`
- Artistic QR codes with `/aiqr`
- Per-user, per-channel activation with `/start` and `/stop`
- Utility tools for calculations, translation, summarization, encoding, hashing, dates, regex, GitHub search and more
- HTTP health endpoints at `/`, `/health`, `/ping` and `/ready`

## Deployment: Render (main branch only)

The Render Blueprint deploys **only from `main`**. It runs the Discord Gateway client and HTTP health endpoint in one web service.

### Required environment variables

- `DISCORD_API_KEY`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_MODEL`

Optional:
- `TAVILY_API_KEY` for search/news
- `DISCORD_GUILD_ID` to sync slash commands to one server (faster updates)
- `OLLAMA_BASE_URL` only when using a remote Ollama endpoint instead of Cloudflare

### Health checks and uptime

- Render checks `/health`, which remains HTTP 200 while the process is alive, including during Discord Gateway reconnection.
- `/ready` reports Discord connectivity and slash-command sync state. It returns 503 until Discord is connected.
- discord.py is configured to reconnect automatically and connection drops/resumes are logged.
- The Blueprint uses an always-on paid Render service. Free services may spin down while idle and should not be used for an always-available Discord Gateway bot.
- A persistent disk mounted at `/var/data` stores `/start` and `/stop` activation state across restarts and deploys.
- An app-to-itself ping is not used: it is not a reliable way to prevent Render from suspending a free service.

### Deployment checklist

1. Connect this repository's `main` branch to Render using the Blueprint.
2. Add the required secrets in the Render Dashboard.
3. Verify the latest deploy is live and `/health` returns HTTP 200.
4. Verify `/ready` reports `discord_connected: true` and `commands_synced: true`.
5. In Discord, use `/start` in the channel where the bot should respond.

### Discord setup

Enable Message Content Intent in the Discord Developer Portal. Invite the bot using both `bot` and `applications.commands` scopes, with permissions required to read/send messages and attach files.

## Local development

Use Python 3.11 or newer:

```bash
git clone https://github.com/Raj-Rathod-Ai/Ai-Powered-Discord-Assistant.git
cd Ai-Powered-Discord-Assistant
python -m venv .venv
pip install -r requirements.txt
```

Create a `.env` file from `.env.example`. To run with Ollama locally, start Ollama and pull the configured model first:

```bash
ollama pull qwen2.5:7b
ollama serve
python bot.py
```

Set `PORT=10000` for local health checks.

## Security

- Never commit `.env` or expose bot/API tokens in logs, screenshots or commits.
- Rotate any credential that has been exposed.
- Use least-privilege Discord permissions.
- Keep the Render persistent disk mounted at `/var/data`.
