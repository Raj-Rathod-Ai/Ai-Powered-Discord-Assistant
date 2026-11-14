# Discord AI Agent

**An intelligent AI-powered Discord assistant built with Python, LangChain, Ollama, and Qwen 2.5 7B.**

Bring local AI conversations, intelligent agent tools, web search, and AI image generation directly into your Discord server.

---

## Overview

Discord AI Agent is a Python-based Discord assistant that connects Discord users with an AI agent powered by a locally hosted Large Language Model (LLM).

It uses Ollama to run Qwen 2.5 7B locally and LangChain to orchestrate AI conversations and tools.

The assistant also supports image generation, web search, and channel-based activation.

## Features

- **AI Chat:** Conversational AI powered by Qwen 2.5 7B.
- **Local LLM:** Run inference locally using Ollama.
- **AI Agent:** Tool orchestration using LangChain.
- **Image Generation:** Generate images from text prompts.
- **Web Search:** Integrated Tavily and DuckDuckGo search tools.
- **Time Tool:** Retrieve current date and time.
- **Discord Integration:** Interact with AI directly from Discord.
- **Channel-Based Activation:** Activate or deactivate the assistant independently in each channel.
- **Slash Commands:** Simple `/start` and `/stop` controls.

---

# System Architecture

The project follows a modular architecture with separate Discord interaction, agent orchestration, language model, and external tool layers.

## Architecture Diagram

```mermaid
flowchart TB
    U[Discord User]

    subgraph Discord["Discord Platform"]
        C[Discord Text Channel]
        S["/start and /stop"]
    end

    subgraph Application["Python Application"]
        B[bot.py]
        A[agent.py]
        M[Message Handler]
        I[Image Handler]
    end

    subgraph AI["AI Processing Layer"]
        L[LangChain Agent]
        Q[Ollama]
        QW[Qwen 2.5 7B]
    end

    subgraph Tools["Agent Tools"]
        W[Tavily Web Search]
        D[DuckDuckGo Search]
        T[Current Time Tool]
        G[Cloudflare FLUX Image Generation]
    end

    U --> C
    U --> S
    C --> B
    S --> B
    B --> M
    M --> A
    M --> I
    A --> L
    L --> Q
    Q --> QW
    L --> W
    L --> D
    L --> T
    L --> G
    QW --> L
    L --> A
    A --> B
    G --> B
    B --> C
    I --> C
```

## Architecture Components

| Component | Responsibility |
|---|---|
| `bot.py` | Discord client, events, commands, message handling |
| `agent.py` | AI agent, model configuration, tools |
| LangChain | Agent orchestration and tool execution |
| Ollama | Local LLM runtime |
| Qwen 2.5 7B | Language model |
| Tavily | Web search |
| DuckDuckGo | Alternative web search |
| Cloudflare FLUX | Image generation |

---

# Message Processing Flow

The following diagram describes how a normal Discord message is processed.

```mermaid
flowchart TD
    A[User Sends Message] --> B[Discord on_message Event]
    B --> C{Is Author a Bot?}

    C -->|Yes| X[Ignore Message]
    C -->|No| D{Is User Activated?}

    D -->|No| Y[Ignore Message]
    D -->|Yes| E{Image Command?}

    E -->|Yes| F[Extract Image Prompt]
    F --> G[Call Image Generation Tool]
    G --> H[Receive Base64 Image]
    H --> I[Convert to Image File]
    I --> J[Send Image to Discord]

    E -->|No| K[Send Message to LangChain Agent]
    K --> L[Agent Processes Request]
    L --> M{Tool Required?}

    M -->|Yes| N[Execute Selected Agent Tool]
    N --> O[Return Tool Result]
    O --> L

    M -->|No| P[Generate Final AI Response]
    P --> Q[Send Response to Discord]
```

## Activation Flow

```mermaid
flowchart TD
    A[Discord User] --> B{Slash Command}
    B -->|/start| C[Add User and Channel to active_users]
    B -->|/stop| D[Remove User and Channel from active_users]
    C --> E[AI Assistant Activated]
    D --> F[AI Assistant Deactivated]
```

---

# Project Structure

```text
Discord-AI-Agent/
│
├── bot.py
│   ├── Discord client setup
│   ├── Slash commands
│   ├── Message handling
│   ├── AI chat integration
│   └── Image generation handling
│
├── agent.py
│   ├── Ollama model configuration
│   ├── LangChain agent
│   ├── Tavily search tool
│   ├── DuckDuckGo search tool
│   ├── Current time tool
│   └── Image generation tool
│
├── .env
│   └── API credentials (not committed)
│
├── .gitignore
│
├── README.md
│
└── requirements.txt
```

---

# Technology Stack

| Technology | Usage |
|---|---|
| Python 3.12 | Application development |
| Discord.py | Discord API integration |
| LangChain | AI agent framework |
| Ollama | Local model runtime |
| Qwen 2.5 7B | Language model |
| Tavily | Web search |
| DuckDuckGo | Search integration |
| Cloudflare Workers AI | Image generation |
| FFmpeg | Not required by the text-and-image bot |

---

# Installation and Setup

## 1. Clone Repository

```bash
git clone https://github.com/Raj-Rathod-Ai/Discord-Ai-Agent.git
cd Discord-Ai-Agent
```

## 2. Install Ollama

Download Ollama:

https://ollama.com/download

Pull the Qwen model:

```bash
ollama pull qwen2.5:7b
```

Run Ollama:

```bash
ollama run qwen2.5:7b
```

## 3. Install Dependencies

Using uv:

```bash
uv sync
```

Alternatively, install the dependencies declared in your requirements file:

```bash
pip install -r requirements.txt
```

## 4. Environment Configuration

Create a `.env` file:

```env
DISCORD_API_KEY=your_discord_bot_token
TAVILY_API_KEY=your_tavily_api_key
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token
```

Add any other credentials required by your actual `agent.py` configuration.

**Never upload `.env` to GitHub.**

## 5. Run the Discord Bot

```bash
uv run bot.py
```

---

# Discord Commands

| Command | Description |
|---|---|
| `/start` | Activate the AI assistant in the current channel |
| `/stop` | Deactivate the AI assistant in the current channel |
| `!imagine <prompt>` | Generate an AI image |
| Normal message | Chat with the AI assistant |

---

# Deployment Architecture

The application can run locally or use a hybrid cloud architecture.

### Local Deployment

```mermaid
flowchart TB
    D[Discord] <--> B[Windows PC: Discord Bot]
    B <--> A[LangChain Agent]
    A <--> O[Local Ollama]
    O <--> Q[Qwen 2.5 7B]
```

### Hybrid Cloud Deployment

```mermaid
flowchart TB
    D[Discord] <--> R[Render: Discord Bot]
    R <--> C[Secure Cloudflare Tunnel]
    C <--> W[Windows PC]
    W <--> O[Ollama]
    O <--> Q[Qwen 2.5 7B]
```

In hybrid deployment, the Discord bot runs on Render while Ollama remains on your own computer. The computer must stay powered on and connected to the internet.

---

# Security

- Never commit Discord bot tokens.
- Never publish API credentials.
- Keep `.env` excluded from Git.
- Do not expose the Ollama API directly to the public internet.
- Use authenticated, encrypted connections for remote model access.

---

# Future Improvements

- Persistent conversation memory.
- Multi-server configuration.
- User-specific conversation context.
- More AI tools and integrations.
- Secure cloud deployment.
- Improved agent observability.
- Streaming AI responses.
- Persistent activation settings.

---

# Author

**Raj Rathod**

GitHub: [@Raj-Rathod-Ai](https://github.com/Raj-Rathod-Ai)

Project: [Discord-Ai-Agent](https://github.com/Raj-Rathod-Ai/Discord-Ai-Agent)
