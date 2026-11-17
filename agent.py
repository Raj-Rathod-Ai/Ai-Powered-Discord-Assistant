import datetime
import os
import requests
from ddgs import DDGS
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama
from tavily import TavilyClient
from tools import ALL_TOOLS

load_dotenv()
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY")) if os.getenv("TAVILY_API_KEY") else None


@tool
def generate_image(prompt: str) -> str:
    """Generate an image using Cloudflare Workers AI and return Base64 image data."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    model_name = os.getenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    if not account_id or not token:
        raise RuntimeError("Cloudflare account credentials are not configured.")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}"
    response = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json={"prompt": prompt}, timeout=120)
    response.raise_for_status()
    data = response.json()
    if not data.get("success") or not data.get("result", {}).get("image"):
        raise RuntimeError(str(data.get("errors", "Image generation returned no image.")))
    return data["result"]["image"]


@tool
def surfinternet(query: str) -> str:
    """Search the internet using Tavily and return relevant results."""
    if tavily_client is None:
        return "Web search is unavailable because TAVILY_API_KEY is not configured."
    return str(tavily_client.search(query=query, max_results=5))


@tool
def get_current_time() -> str:
    """Get the current date and time in the server's timezone."""
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


@tool
def ddg_search(query: str) -> str:
    """Search the internet using DuckDuckGo."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    return str(results) if results else "No search results found."


cloudflare_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
cloudflare_token = os.getenv("CLOUDFLARE_API_TOKEN")
cloudflare_model = os.getenv("CLOUDFLARE_MODEL")

if cloudflare_account and cloudflare_token and cloudflare_model:
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=cloudflare_model,
        api_key=cloudflare_token,
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_account}/ai/v1",
        temperature=0.5,
        max_tokens=512,
    )
else:
    model = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.5,
        num_predict=512,
        num_ctx=4096,
        keep_alive="30m",
    )

system_prompt = """
You are Rudra, an AI assistant created by Raj for Discord communities.
Use available tools when they help answer a request. For GitHub repository discovery, call github_repository_search; request up to 10 results and base every repository claim on tool output. Never invent repository names, stars, languages, licenses, activity, or URLs. Explain limitations honestly.
Never claim an action succeeded unless its tool returned success.
For generated images, call generate_image and let the Discord bot deliver the result.
Keep responses clear, concise and useful. Never expose secrets or environment variables.
"""

agent = create_agent(
    model=model,
    tools=[surfinternet, get_current_time, ddg_search, generate_image, *ALL_TOOLS],
    system_prompt=system_prompt,
)
