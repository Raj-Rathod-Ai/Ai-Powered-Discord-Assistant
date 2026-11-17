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
from tools import create_art_qr

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("rudra")
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
active_users = set()
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


@tree.command(name="tools", description="Show Rudra's available AI tools")
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
        "Public GitHub repository search",
    ]
    await interaction.response.send_message("\n".join(f"• {name}" for name in names), ephemeral=True)


@tree.command(name="start", description="Activate Rudra AI in this channel")
async def start(interaction: discord.Interaction):
    active_users.add((interaction.user.id, interaction.channel_id))
    await interaction.response.send_message("Rudra is active in this channel for you.", ephemeral=True)


@tree.command(name="stop", description="Deactivate Rudra AI in this channel")
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
    if (message.author.id, message.channel.id) not in active_users:
        return
    content = message.content.strip()
    # Handle explicit QR requests deterministically so the image is always attached,
    # rather than relying on the language model to invoke and relay a file tool.
    if "qr" in content.lower():
        url_match = re.search(r"https?://[^\\s<>]+", content)
        if url_match:
            target_url = url_match.group(0).rstrip(".,;:!?)\\\\]")
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
    start_health_server()
    async with client:
        await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
