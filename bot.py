import asyncio
import base64
import io
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

from agent import agent, generate_image
from langchain.messages import HumanMessage


# ---------------- DISCORD SETUP ----------------

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Your Discord Server ID
GUILD_ID = 1323889812922695750

# Slash command tree
tree = app_commands.CommandTree(client)

# Store active users per channel
active_users = set()


# ---------------- SLASH COMMANDS ----------------

@tree.command(
    name="start",
    description="Activate Rudra AI assistant"
)
async def start(interaction: discord.Interaction):
    key = (interaction.user.id, interaction.channel_id)
    active_users.add(key)

    await interaction.response.send_message(
        "Rudra is now active! You can chat with me.",
        ephemeral=True
    )


@tree.command(
    name="stop",
    description="Deactivate Rudra AI assistant"
)
async def stop(interaction: discord.Interaction):
    key = (interaction.user.id, interaction.channel_id)
    active_users.discard(key)

    await interaction.response.send_message(
        "Rudra has been deactivated. Use /start to activate again.",
        ephemeral=True
    )


# ---------------- BOT READY ----------------

@client.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)

    tree.copy_global_to(guild=guild)
    synced = await tree.sync(guild=guild)

    print(f"Logged in as {client.user}")
    print(f"Synced {len(synced)} slash commands!")
    print("Text chat: enabled")
    print("Image generation: enabled")
    print("Rudra is ready!")


# ---------------- MESSAGE HANDLER ----------------

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    # Check whether user activated Rudra in this channel
    key = (message.author.id, message.channel.id)

    if key not in active_users:
        return

    # ---------------- DIRECT IMAGE GENERATION ----------------

    if content.lower().startswith("!imagine "):
        prompt = content[len("!imagine "):].strip()

        if not prompt:
            await message.channel.send(
                "Please provide an image prompt. Example: `!imagine a futuristic city`"
            )
            return

        try:
            async with message.channel.typing():
                image_base64 = await asyncio.to_thread(
                    generate_image.invoke,
                    {"prompt": prompt}
                )

            image_bytes = base64.b64decode(image_base64)

            await message.channel.send(
                file=discord.File(
                    io.BytesIO(image_bytes),
                    filename="generated.png"
                )
            )

        except Exception as e:
            print("Image error:", repr(e))
            await message.channel.send("Image generation failed.")

        return

    # ---------------- NORMAL AI CHAT ----------------

    try:
        async with message.channel.typing():
            response = await agent.ainvoke({
                "messages": [
                    HumanMessage(content=content)
                ]
            })

        # Check whether the agent generated an image through a tool call
        for msg in response["messages"]:
            if (
                getattr(msg, "type", "") == "tool"
                and getattr(msg, "name", "") == "generate_image"
            ):
                image_base64 = msg.content

                if isinstance(image_base64, str):
                    image_bytes = base64.b64decode(image_base64)

                    await message.channel.send(
                        file=discord.File(
                            io.BytesIO(image_bytes),
                            filename="generated.png"
                        )
                    )
                    return

        # Normal AI response
        answer = response["messages"][-1].content

        if isinstance(answer, list):
            answer = " ".join(
                item.get("text", "")
                for item in answer
                if isinstance(item, dict)
                and item.get("type") == "text"
            )

        await message.channel.send(str(answer)[:2000])

    except Exception as e:
        print("Agent error:", repr(e))
        await message.channel.send(
            "Something went wrong. Please try again."
        )


# ---------------- RUN BOT ----------------

client.run(os.getenv("DISCORD_API_KEY"))
