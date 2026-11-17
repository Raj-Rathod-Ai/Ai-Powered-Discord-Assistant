# Rudra AI Discord Assistant

Rudra is a Python Discord assistant built with discord.py, LangChain, Ollama, Qwen and Cloudflare Workers AI. It supports channel-level activation, AI chat, web search, image generation and a collection of practical utility tools.

## Features

- AI conversations powered by a configurable Ollama model
- Tavily and DuckDuckGo web search
- Cloudflare FLUX image generation with the `!imagine` command
- Artistic QR codes with `/aiqr`, using an optional uploaded image as the QR texture
- Per-user, per-channel activation with `/start` and `/stop`
- Calculator, Wikipedia, public webpage reader and YouTube transcript retrieval
- Translation, text summarization and unit conversion
- JSON formatting, password generation, Base64 and URL encoding
- Markdown conversion, word counting, UUID and date utilities
- Regex testing, hash generation and color conversion
- Public GitHub repository search without a GitHub token
- News search through the existing Tavily integration
- HTTP health endpoints at `/`, `/health` and `/ping` for Render monitoring

The utility tools do not require new API keys. Some use public services and need an internet connection. Tavily and Cloudflare features continue to use the existing credentials.

## Project files

```text
.
├── agent.py
├── bot.py
├── tools.py
├── requirements.txt
├── render.yaml
├── .env.example
└── README.md
```

## Local setup

Use Python 3.11 or newer.

```bash
git clone https://github.com/Raj-Rathod-Ai/Ai-Powered-Discord-Assistant.git
cd Ai-Powered-Discord-Assistant
python -m venv .venv
```

Activate the environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Install and run Ollama, then pull the configured model:

```bash
ollama pull qwen2.5:7b
ollama serve
```

Copy `.env.example` to `.env` and fill in the values:

```env
DISCORD_API_KEY=your_discord_bot_token
TAVILY_API_KEY=your_existing_tavily_key
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
CLOUDFLARE_MODEL=@cf/black-forest-labs/flux-1-schnell
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
DISCORD_GUILD_ID=your_test_server_id
PORT=10000
```

Start the bot:

```bash
python bot.py
```

Enable the Message Content Intent for the bot in the Discord Developer Portal. Invite it with bot and applications.commands scopes and the permissions needed to read and send messages, use slash commands and attach files.

## Discord commands

| Command | Description |
|---|---|
| `/start` | Enable AI chat for the current user in this channel |
| `/stop` | Disable AI chat for the current user in this channel |
| `/tools` | Show the assistant's tool categories |
| `/aiqr url:<url> image:<optional attachment> style:<optional style>` | Create a static artistic QR code |
| `!imagine <prompt>` | Generate an image using Cloudflare FLUX |
| Normal message | Chat with Rudra after using `/start` |

The QR styles are original, ocean, forest, sunset and violet. An uploaded image is used as a visual texture inside the QR modules. The QR is static and does not expire by itself. Its destination can still become unavailable. Artistic QR designs can be harder for some scanners to read, so test the generated image with more than one QR scanner before printing or distributing it.

## Agent tools

The LangChain agent can call the following utilities:

- `calculator`
- `wikipedia_search`
- `read_url`
- `youtube_transcript`
- `generate_qr`
- `translate_text`
- `summarize_text`
- `unit_converter`
- `format_json`
- `password_generator`
- `base64_tool`
- `url_codec`
- `markdown_to_html`
- `word_counter`
- `uuid_generator`
- `date_calculator`
- `regex_tester`
- `hash_generator`
- `color_converter`
- `github_repository_search`
- `latest_news`

The webpage reader blocks localhost and literal private IP addresses and does not follow redirects. Only use it with public pages you trust.

## Render deployment

The repository includes a `render.yaml` Blueprint for a web service. In Render, create a new Blueprint deployment from this repository and add the environment values requested by the Blueprint.

Required environment variables:

- `DISCORD_API_KEY`
- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `OLLAMA_BASE_URL`

`TAVILY_API_KEY` enables web and news search. `DISCORD_GUILD_ID` is optional; when set, slash commands are synced to that server for faster development updates. Leave it empty to sync globally.

### Ollama on Render

The bot and Ollama are separate services. A Render web service cannot use your development computer's `localhost`. Run Ollama on a machine or host that remains online, expose it only through a secure authenticated tunnel or private network, and set `OLLAMA_BASE_URL` to that reachable endpoint. Do not expose the Ollama port publicly without authentication.

### Health checks and sleeping

The service responds to `/health`, `/ping`, `/ready` and `/` on Render's assigned `PORT`. Render uses the lightweight `/health` liveness endpoint; `/ready` reports whether the Discord Gateway is connected.

A health endpoint does not guarantee that a free Render web service will stay awake. Free web services can spin down after a period without inbound traffic. A request made by the service to itself is not a reliable keep-alive strategy. If continuous uptime is required, use an always-on paid instance or an external uptime monitor that requests the public health URL, subject to Render's current plan rules.

### Deployment type

This project runs a Discord Gateway connection and an HTTP health server in the same process. Use the included web service configuration if you need the health URL. For a dedicated Discord process without a public HTTP endpoint, a Render background worker is a better fit, but it will not provide the public health URL.

## Security and operational notes

- Never commit `.env` or paste API tokens into source code.
- Rotate any token that has been exposed in a screenshot, log or commit.
- Set Discord permissions to the minimum required.
- Use a persistent database before relying on activation state across restarts; current `/start` and `/stop` state is held in process memory.
- Keep the bot and its dependencies updated.

## License

Add a license file if you intend to publish reuse permissions for this project.
