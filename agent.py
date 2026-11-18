import datetime
import json
import logging
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
logger = logging.getLogger("rudra.agent")
tavily_key = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None


def _cloudflare_response_detail(response) -> str:
    """Extract a bounded description from a Cloudflare response body."""
    if response is None:
        return "No HTTP response was attached."
    try:
        payload = response.json()
        if isinstance(payload, dict):
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                messages = [
                    str(item.get("message") or item.get("code") or item)
                    if isinstance(item, dict) else str(item)
                    for item in errors
                ]
                return "; ".join(messages)[:1200]
            error = payload.get("error") or payload.get("message")
            if error:
                if isinstance(error, dict):
                    error = error.get("message") or json.dumps(error, ensure_ascii=False)
                return str(error)[:1200]
            return json.dumps(payload, ensure_ascii=False)[:1200]
        return str(payload)[:1200]
    except (ValueError, TypeError):
        return str(getattr(response, "text", "No response body"))[:1200]


def log_model_error(exc: Exception) -> None:
    """Log provider response details without logging request headers or API tokens."""
    response = getattr(exc, "response", None)
    status = getattr(exc, "status_code", None) or getattr(response, "status_code", None)
    body = getattr(exc, "body", None)
    if body is None and response is not None:
        detail = _cloudflare_response_detail(response)
    elif isinstance(body, (dict, list)):
        detail = json.dumps(body, ensure_ascii=False)[:1200]
    elif body is not None:
        detail = str(body)[:1200]
    else:
        detail = str(exc)[:1200]
    logger.error(
        "Chat model request failed (provider=Cloudflare Workers AI, model=%s, status=%s): %s",
        os.getenv("CLOUDFLARE_MODEL", "@cf/qwen/qwen3.8-27b"),
        status or "unknown",
        detail,
    )


@tool
def generate_image(prompt: str) -> str:
    """Generate an image using Cloudflare Workers AI and return Base64 image data."""
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    model_name = os.getenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")
    if not account_id or not token:
        raise RuntimeError("Cloudflare account credentials are not configured.")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_name}"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={"prompt": prompt},
        timeout=(15, 180),
    )
    if not response.ok:
        raise RuntimeError(
            f"Cloudflare image API returned HTTP {response.status_code}: "
            f"{_cloudflare_response_detail(response)}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Cloudflare image API returned a non-JSON response.") from exc
    image_data = (data.get("result") or {}).get("image")
    if not data.get("success") or not image_data:
        raise RuntimeError(
            f"Cloudflare image generation failed: {_cloudflare_response_detail(response)}"
        )
    return image_data


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
cloudflare_model = os.getenv("CLOUDFLARE_MODEL", "@cf/qwen/qwen3.8-27b").strip()

if bool(cloudflare_account) != bool(cloudflare_token):
    raise RuntimeError(
        "Set both CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN, or configure OLLAMA_BASE_URL."
    )

if cloudflare_account and cloudflare_token:
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=cloudflare_model,
        api_key=cloudflare_token,
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_account}/ai/v1",
        temperature=0.5,
        model_kwargs={"max_completion_tokens": 512},
        timeout=90,
        max_retries=2,
        use_responses_api=False,
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
Use available tools when they help answer a request. Explain limitations honestly.
Never claim an action succeeded unless its tool returned success.
For generated images, call generate_image and let the Discord bot deliver the result.
Keep responses clear, concise and useful. Never expose secrets or environment variables.
"""

agent = create_agent(
    model=model,
    tools=[surfinternet, get_current_time, ddg_search, generate_image, *ALL_TOOLS],
    system_prompt=system_prompt,
)
