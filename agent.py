
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.tools import tool
from tavily import TavilyClient
import datetime
from ddgs import DDGS
from dotenv import load_dotenv
import os
load_dotenv()
import requests
import base64
from langchain_ollama import ChatOllama


tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def generate_image(prompt: str) -> str:
    """Generate an image using Cloudflare FLUX and return Base64 image data."""

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": prompt},
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(str(data.get("errors")))

    image_bytes = base64.b64decode(data["result"]["image"])

    return base64.b64encode(image_bytes).decode("utf-8")


@tool
def surfinternet(query: str) -> str:
    """Search the internet using Tavily and return relevant results."""

    results = tavily_client.search(
        query=query,
        max_results=5
    )

    return str(results)


@tool
def get_current_time() -> str:
    """Get the current date and time."""

    return datetime.datetime.now().astimezone().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )


@tool
def ddg_search(query: str) -> str:
    """Search the internet using DuckDuckGo."""

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))

    if not results:
        return "No search results found."

    return str(results)


# model = ChatGoogleGenerativeAI(model="gemini-3.5-flash")

model = ChatOllama(
    model="qwen2.5:7b",
    temperature=0.5,
    num_predict=256,
    num_ctx=4096,
    keep_alive="30m"
)

agent = create_agent(
    model=model,
    tools=[
        surfinternet,
        get_current_time,
        ddg_search,
        generate_image
    ],
    system_prompt="""
    You are Rudra, an AI assistant created by Raj.
    You help users on Discord.

    Your tools:
    - generate_image: Generate images using Cloudflare FLUX.
    - surfinternet: Search the internet using Tavily.
    - ddg_search: Search the internet using DuckDuckGo.
    - get_current_time: Get the current date and time.

    IMAGE GENERATION RULES:
    - When a user requests an image, you MUST call generate_image.
    - Improve and expand the user's image prompt before calling the tool.
    - Never pretend an image was generated without calling the tool.
    - Never return fake DALL-E actions, JSON actions, or imaginary image links.
    - The Discord bot handles sending the generated image.

    GENERAL RULES:
    - Your name is Rudra.
    - Raj created you to help people on Discord.
    - Keep answers short, simple, friendly, and human.
    - Use search tools when relevant.
    - Never invent information.
    - If you don't know an answer, say so.
    - Avoid large paragraphs.
    """
)
