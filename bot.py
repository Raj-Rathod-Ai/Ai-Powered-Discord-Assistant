import asyncio
import base64
import io
import logging
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import discord
from discord import app_commands
from dotenv import load_dotenv
from langchain.messages import HumanMessage
from PIL import Image

from agent import agent, generate_image
from tools import create_art_qr, search_github_repositories
from channel_policy import allowed_channel_ids, is_allowed_channel

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("rudra")
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
active_users = set()
ALLOWED_CHANNEL_IDS = allowed_channel_ids(os.getenv("DISCORD_ALLOWED_CHANNEL_IDS", ""))
guild_id = os.getenv("DISCORD_GUILD_ID")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in {"/", "/health", "/ping", "/ready"}:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        ready = client.is_ready()
        if self.path == "/ready":
            body = b'{"status":"ready"}' if ready else b'{"status":"starting"}'
            self.send_response(200 if ready else 503)
        else:
            body = b'{"status":"ok","service":"rudra-discord-assistant"}'
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logger.info("health endpoint %s", format % args)


def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Health endpoint listening on port %s", port)


def split_message(value, limit=1900):
    text = str(value)
    return [text[index:index + limit] for index in range(0, len(text), limit)] or [""]


async def send_agent_response(channel, prompt):
    async with channel.typing():
        response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
    for item in response.get("messages", []):
        if getattr(item, "type", "") == "tool" and getattr(item, "name", "") == "generate_image":
            if isinstance(item.content, str):
                image_data = base64.b64decode(item.content)
                await channel.send(file=discord.File(io.BytesIO(image_data), filename="rudra-generated.png"))
            return
        if getattr(item, "type", "") == "tool" and getattr(item, "name", "") == "generate_qr":
            if isinstance(item.content, str) and "QR image created:" in item.content:
                path = Path(item.content.split("QR image created:", 1)[1].strip())
                if path.is_file():
                    await channel.send(file=discord.File(path, filename="rudra-qr.png"))
                    path.unlink(missing_ok=True)
            return
    answer = response["messages"][-1].content
    if isinstance(answer, list):
        answer = " ".join(part.get("text", "") for part in answer if isinstance(part, dict) and part.get("type") == "text")
    for part in split_message(answer):
        await channel.send(part)


def channel_access_check(interaction: discord.Interaction) -> bool:
    return is_allowed_channel(interaction.channel_id, ALLOWED_CHANNEL_IDS)


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        message = "Rudra is restricted to the configured channel. Please use the approved channel."
    else:
        logger.error("Slash command failed: %s", error, exc_info=(type(error), error, error.__traceback__))
        message = "That command failed. Please try again later."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


@tree.command(name="tools", description="Show Rudra's available AI tools")
@app_commands.check(channel_access_check)
async def tools_command(interaction: discord.Interaction):
    names = [
        "Web search and news",
        "Image generation and artistic QR codes",
        "Calculator and unit conversion",
        "Wikipedia, webpage reading and YouTube transcripts",
        "Translation and summarization",
        "JSON, Base64, URL and Markdown utilities",
        "Password, UUID, date and word-count utilities",
        "Regex, hash and color utilities",
        "Public GitHub repository search with /github",
    ]
    await interaction.response.send_message("\n".join(f"• {name}" for name in names), ephemeral=True)


@tree.command(name="start", description="Activate Rudra AI in this channel")
@app_commands.check(channel_access_check)
async def start(interaction: discord.Interaction):
    active_users.add((interaction.user.id, interaction.channel_id))
    await interaction.response.send_message("Rudra is active in this channel for you.", ephemeral=True)


@tree.command(name="stop", description="Deactivate Rudra AI in this channel")
@app_commands.check(channel_access_check)
async def stop(interaction: discord.Interaction):
    active_users.discard((interaction.user.id, interaction.channel_id))
    await interaction.response.send_message("Rudra has been deactivated for you in this channel.", ephemeral=True)


@tree.command(name="aiqr", description="Create an artistic QR code from a URL and optional image")
@app_commands.describe(url="The URL to encode", image="Optional image used as QR artwork", style="Color theme")
@app_commands.choices(style=[
    app_commands.Choice(name="Original", value="original"),
    app_commands.Choice(name="Ocean", value="ocean"),
    app_commands.Choice(name="Forest", value="forest"),
    app_commands.Choice(name="Sunset", value="sunset"),
    app_commands.Choice(name="Violet", value="violet"),
    app_commands.Choice(name="Developer", value="developer"),
])
@app_commands.check(channel_access_check)
async def aiqr(interaction: discord.Interaction, url: str, image: discord.Attachment = None, style: app_commands.Choice[str] = None):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        reference = None
        if image:
            if image.size > 8 * 1024 * 1024 or (image.content_type and not image.content_type.startswith("image/")):
                await interaction.followup.send("Please attach an image smaller than 8 MB.", ephemeral=True)
                return
            reference = Image.open(io.BytesIO(await image.read())).convert("RGB")
        path = await asyncio.to_thread(create_art_qr, url, style.value if style else "original", reference)
        await interaction.followup.send(
            content="Your QR code is ready. It is static and does not expire by itself.",
            file=discord.File(path, filename="rudra-artistic-qr.png"),
            ephemeral=True,
        )
        Path(path).unlink(missing_ok=True)
    except Exception as exc:
        logger.exception("QR generation failed")
        await interaction.followup.send(f"Could not generate the QR code: {exc}", ephemeral=True)


def format_github_repository(item: dict) -> tuple[str, str]:
    """Format one normalized GitHub repository for a Discord embed field."""
    name = discord.utils.escape_markdown(str(item.get("full_name") or "Unknown repository"))[:110]
    description = discord.utils.escape_mentions(discord.utils.escape_markdown(str(item.get("description") or "No description provided.")))
    if len(description) > 180:
        description = description[:177].rstrip() + "..."
    url = str(item.get("url") or "")
    if not re.fullmatch(r"https://github\.com/[^/\s]+/[^/\s]+", url):
        url = ""
    link = f"[Open repository]({url})" if url else "Repository URL unavailable"
    stars = max(0, int(item.get("stars", 0) or 0))
    language = discord.utils.escape_markdown(str(item.get("language") or "Not specified"))[:35]
    license_name = discord.utils.escape_markdown(str(item.get("license") or "Not specified"))[:35]
    updated = str(item.get("updated_at") or "Unknown")[:10]
    value = (
        f"{description}\n"
        f"⭐ {stars:,} · **Language:** {language} · **License:** {license_name}\n"
        f"**Updated:** {updated} · {link}"
    )
    return name, value[:1000]


@tree.command(name="github", description="Search GitHub repositories and show up to 10 results")
@app_commands.describe(query="GitHub search query, e.g. RAG language:Python", limit="Number of results (1–10)")
@app_commands.check(channel_access_check)
async def github_command(interaction: discord.Interaction, query: str, limit: app_commands.Range[int, 1, 10] = 10):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        repositories = await asyncio.to_thread(search_github_repositories, query, limit)
        if not repositories:
            await interaction.followup.send(
                f"No repositories found for `{query}`. Try a broader search, such as `RAG language:Python`.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="GitHub Repository Search",
            description=f"Query: `{discord.utils.escape_mentions(query[:150])}`\nSorted by stars · Showing {len(repositories)} result(s)",
            color=discord.Color.blurple(),
        )
        for index, repository in enumerate(repositories[:10], 1):
            name, value = format_github_repository(repository)
            embed.add_field(name=f"{index}. {name}", value=value, inline=False)
        embed.set_footer(text="Data returned by GitHub Search API · Stars and metadata may change")
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        logger.exception("GitHub repository search failed")
        await interaction.followup.send(
            f"GitHub search failed ({type(exc).__name__}). Check the bot logs and try again.",
            ephemeral=True,
        )


@client.event
async def on_ready():
    try:
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
        else:
            synced = await tree.sync()
        logger.info("Logged in as %s; synced %s commands", client.user, len(synced))
    except Exception:
        logger.exception("Slash command sync failed")


@client.event
async def on_message(message):
    if message.author.bot:
        return
    if not is_allowed_channel(message.channel.id, ALLOWED_CHANNEL_IDS):
        return
    if (message.author.id, message.channel.id) not in active_users:
        return
    content = message.content.strip()
    # Handle explicit QR requests deterministically so the image is always attached,
    # rather than relying on the language model to invoke and relay a file tool.
    if "qr" in content.lower():
        url_match = re.search(r"https?://[^\s<>]+", content)
        if url_match:
            target_url = url_match.group(0).rstrip(".,;:!?)\\]")
            try:
                async with message.channel.typing():
                    qr_path = await asyncio.to_thread(create_art_qr, target_url, "developer")
                await message.channel.send(
                    content="**Developer-style QR generated** · Scan to open the GitHub profile/repository page.",
                    file=discord.File(qr_path, filename="rudra-developer-qr.png"),
                )
                Path(qr_path).unlink(missing_ok=True)
            except Exception:
                logger.exception("Developer QR request failed")
                await message.channel.send("I could not generate that QR code. Please check that the link is a valid public URL.")
            return
    if not content and not message.attachments:
        return
    if content.lower().startswith("!imagine "):
        prompt = content[len("!imagine "):].strip()
        if not prompt:
            await message.channel.send("Add a prompt after !imagine.")
            return
        try:
            async with message.channel.typing():
                image_data = await asyncio.to_thread(generate_image.invoke, {"prompt": prompt})
            await message.channel.send(file=discord.File(io.BytesIO(base64.b64decode(image_data)), filename="generated.png"))
        except Exception:
            logger.exception("Image generation failed")
            await message.channel.send("Image generation failed. Check the bot logs and Cloudflare configuration.")
        return
    try:
        await send_agent_response(message.channel, content)
    except Exception:
        logger.exception("Agent request failed")
        await message.channel.send("I couldn't complete that request. Please try again shortly.")


async def main():
    token = os.getenv("DISCORD_API_KEY")
    if not token:
        raise RuntimeError("DISCORD_API_KEY is required.")
    if not ALLOWED_CHANNEL_IDS:
        logger.warning("DISCORD_ALLOWED_CHANNEL_IDS is empty; all Discord channels are blocked by default.")
    else:
        logger.info("Discord channel allowlist loaded with %d channel(s).", len(ALLOWED_CHANNEL_IDS))
    start_health_server()
    async with client:
        await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
