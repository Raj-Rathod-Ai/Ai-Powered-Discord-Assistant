import ast
import base64
import hashlib
import json
import math
import operator
import re
import secrets
import string
import uuid
from datetime import date, datetime, timedelta
from urllib.parse import quote, unquote, urlparse
from pathlib import Path
from ipaddress import ip_address
from io import BytesIO

import qrcode
import requests
import wikipedia
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from langchain.tools import tool
from PIL import Image, ImageDraw, ImageOps


OUTPUT_DIR = Path("generated")
OUTPUT_DIR.mkdir(exist_ok=True)


def _safe_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Provide a valid http or https URL.")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Local network URLs are not allowed.")
    try:
        address = ip_address(host)
        if not address.is_global:
            raise ValueError("Private and reserved network addresses are not allowed.")
    except ValueError as exc:
        if "not allowed" in str(exc):
            raise
    return value


def _calculate(node):
    binary = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}
    if isinstance(node, ast.Expression):
        return _calculate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in binary:
        if isinstance(node.op, ast.Pow) and abs(_calculate(node.right)) > 100:
            raise ValueError("Exponent is too large.")
        return binary[type(node.op)](_calculate(node.left), _calculate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in unary:
        return unary[type(node.op)](_calculate(node.operand))
    raise ValueError("Only basic arithmetic is supported.")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression safely."""
    try:
        result = _calculate(ast.parse(expression, mode="eval"))
        return str(result)
    except Exception as exc:
        return f"Calculation error: {exc}"


@tool
def wikipedia_search(query: str) -> str:
    """Search Wikipedia and return a concise article summary."""
    try:
        return wikipedia.summary(query, sentences=5, auto_suggest=True)
    except Exception as exc:
        return f"Wikipedia search failed: {exc}"


@tool
def read_url(url: str) -> str:
    """Read the readable text from a public webpage."""
    try:
        response = requests.get(
            _safe_url(url),
            headers={"User-Agent": "RudraDiscordAssistant/1.0"},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", ""):
            return "This URL does not return an HTML page."
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()
        text = " ".join(soup.get_text(" ").split())
        return text[:12000] or "No readable page text was found."
    except Exception as exc:
        return f"Could not read URL: {exc}"


@tool
def youtube_transcript(video_url: str) -> str:
    """Fetch captions from a public YouTube video when captions are available."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", video_url)
        if not match:
            return "That does not look like a valid YouTube video URL."
        transcript = YouTubeTranscriptApi().fetch(match.group(1))
        lines = [item.text for item in transcript]
        return " ".join(lines)[:12000] or "No transcript was available."
    except Exception as exc:
        return f"Transcript unavailable: {exc}"


def create_art_qr(url, style="original", reference_image=None):
    styles = {
        "original": ("#111111", "#ffffff"),
        "ocean": ("#075985", "#effaff"),
        "forest": ("#14532d", "#f0fdf4"),
        "sunset": ("#9a3412", "#fff7ed"),
        "violet": ("#5b21b6", "#faf5ff"),
    }
    foreground, background = styles.get(style.lower(), styles["original"])
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=14,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    size = len(matrix)
    scale = 14
    canvas_size = size * scale
    canvas = Image.new("RGB", (canvas_size, canvas_size), background)
    if reference_image:
        texture = ImageOps.fit(reference_image.convert("RGB"), (canvas_size, canvas_size))
    else:
        texture = Image.new("RGB", (canvas_size, canvas_size), foreground)
    draw = ImageDraw.Draw(canvas)
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                draw.rectangle(
                    (x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1),
                    fill=foreground if reference_image is None else None,
                )
    if reference_image:
        mask = Image.new("L", (canvas_size, canvas_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        for y, row in enumerate(matrix):
            for x, dark in enumerate(row):
                if dark:
                    mask_draw.rectangle(
                        (x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1),
                        fill=255,
                    )
        for top, left in ((0, 0), (0, size - 7), (size - 7, 0)):
            x0, y0 = left * scale, top * scale
            mask_draw.rectangle((x0, y0, x0 + 7 * scale, y0 + 7 * scale), fill=0)
        canvas.paste(texture, (0, 0), mask)
    for top, left in ((0, 0), (0, size - 7), (size - 7, 0)):
        x0, y0 = left * scale, top * scale
        draw.rectangle((x0, y0, x0 + 7 * scale - 1, y0 + 7 * scale - 1), fill=foreground)
        draw.rectangle((x0 + scale, y0 + scale, x0 + 6 * scale - 1, y0 + 6 * scale - 1), fill=background)
        draw.rectangle((x0 + 2 * scale, y0 + 2 * scale, x0 + 5 * scale - 1, y0 + 5 * scale - 1), fill=foreground)
    output = Image.new("RGB", (canvas_size + 80, canvas_size + 80), "white")
    output.paste(canvas, (40, 40))
    path = OUTPUT_DIR / f"qr_{uuid.uuid4().hex}.png"
    output.save(path)
    return str(path)


@tool
def generate_qr(url: str, style: str = "original") -> str:
    """Create a downloadable static QR code for a URL. Styles: original, ocean, forest, sunset, violet."""
    try:
        path = create_art_qr(url, style)
        return f"QR image created: {path}"
    except Exception as exc:
        return f"QR generation failed: {exc}"


@tool
def translate_text(text: str, target_language: str) -> str:
    """Translate text into a language such as English, Hindi, Gujarati, Spanish or French."""
    try:
        return GoogleTranslator(source="auto", target=target_language).translate(text[:4500])
    except Exception as exc:
        return f"Translation failed: {exc}"


@tool
def summarize_text(text: str) -> str:
    """Summarize text using the assistant's locally configured Ollama model."""
    try:
        from langchain_ollama import ChatOllama
        model = ChatOllama(model="qwen2.5:7b", temperature=0.2, num_predict=400)
        result = model.invoke(f"Summarize the following text clearly and accurately:\n\n{text[:12000]}")
        return str(result.content)
    except Exception as exc:
        return f"Summarization failed: {exc}"


@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """Convert common length, weight, temperature and volume units."""
    units = {
        "m": ("length", 1), "km": ("length", 1000), "cm": ("length", .01),
        "mm": ("length", .001), "mile": ("length", 1609.344), "ft": ("length", .3048),
        "inch": ("length", .0254), "kg": ("weight", 1), "g": ("weight", .001),
        "lb": ("weight", .45359237), "oz": ("weight", .0283495),
        "l": ("volume", 1), "ml": ("volume", .001), "gal": ("volume", 3.78541),
    }
    source, target = from_unit.lower(), to_unit.lower()
    if source in {"c", "celsius"} and target in {"f", "fahrenheit"}:
        return f"{value * 9 / 5 + 32:.4f} °F"
    if source in {"f", "fahrenheit"} and target in {"c", "celsius"}:
        return f"{(value - 32) * 5 / 9:.4f} °C"
    if source not in units or target not in units or units[source][0] != units[target][0]:
        return "Unsupported conversion. Check the units and try again."
    return f"{value * units[source][1] / units[target][1]:.6g} {to_unit}"


@tool
def format_json(value: str) -> str:
    """Validate and pretty-print a JSON string."""
    try:
        return json.dumps(json.loads(value), indent=2, ensure_ascii=False)[:12000]
    except Exception as exc:
        return f"Invalid JSON: {exc}"


@tool
def password_generator(length: int = 20) -> str:
    """Generate a random password using cryptographically secure randomness."""
    length = max(12, min(int(length), 64))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@tool
def base64_tool(value: str, action: str = "encode") -> str:
    """Encode text to Base64 or decode Base64 text. Action is encode or decode."""
    try:
        if action.lower() == "decode":
            return base64.b64decode(value, validate=True).decode("utf-8")
        return base64.b64encode(value.encode()).decode()
    except Exception as exc:
        return f"Base64 error: {exc}"


@tool
def url_codec(value: str, action: str = "encode") -> str:
    """Encode or decode URL text."""
    return unquote(value) if action.lower() == "decode" else quote(value, safe="")


@tool
def markdown_to_html(value: str) -> str:
    """Convert Markdown text to HTML."""
    try:
        import markdown
        return markdown.markdown(value, extensions=["tables", "fenced_code"])[:12000]
    except Exception as exc:
        return f"Markdown conversion failed: {exc}"


@tool
def word_counter(value: str) -> str:
    """Count words, characters, sentences and lines in text."""
    words = re.findall(r"\b[\w'-]+\b", value)
    sentences = len(re.findall(r"[.!?]+(?:\s|$)", value))
    return f"Words: {len(words)}\nCharacters: {len(value)}\nSentences: {sentences}\nLines: {len(value.splitlines())}"


@tool
def uuid_generator() -> str:
    """Generate a random UUID version 4."""
    return str(uuid.uuid4())


@tool
def date_calculator(start_date: str, days: int) -> str:
    """Add or subtract a number of days from a date in YYYY-MM-DD format."""
    try:
        result = datetime.strptime(start_date, "%Y-%m-%d").date() + timedelta(days=int(days))
        return result.isoformat()
    except Exception as exc:
        return f"Date calculation failed: {exc}"


@tool
def regex_tester(pattern: str, text: str) -> str:
    """Find matches for a regular expression in text."""
    try:
        matches = re.findall(pattern, text)
        return json.dumps(matches[:100], ensure_ascii=False) if matches else "No matches found."
    except re.error as exc:
        return f"Invalid regular expression: {exc}"


@tool
def hash_generator(value: str, algorithm: str = "sha256") -> str:
    """Generate a text hash using md5, sha1, sha256 or sha512."""
    if algorithm.lower() not in {"md5", "sha1", "sha256", "sha512"}:
        return "Supported algorithms: md5, sha1, sha256, sha512."
    return hashlib.new(algorithm.lower(), value.encode()).hexdigest()


@tool
def color_converter(value: str) -> str:
    """Convert a hex color to RGB and HSL values."""
    try:
        raw = value.strip().lstrip("#")
        if len(raw) == 3:
            raw = "".join(char * 2 for char in raw)
        if not re.fullmatch(r"[0-9a-fA-F]{6}", raw):
            raise ValueError("Use a color such as #3498db.")
        red, green, blue = (int(raw[index:index + 2], 16) for index in (0, 2, 4))
        import colorsys
        hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
        return f"HEX: #{raw.upper()}\nRGB: {red}, {green}, {blue}\nHSL: {round(hue * 360)}, {round(saturation * 100)}%, {round(lightness * 100)}%"
    except Exception as exc:
        return f"Color conversion failed: {exc}"


@tool
def github_repository_search(query: str) -> str:
    """Search public GitHub repositories without an access token."""
    try:
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "per_page": 5},
            headers={"Accept": "application/vnd.github+json"},
            timeout=12,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        return "\n".join(
            f"{item['full_name']} — {item.get('description') or 'No description'}\n{item['html_url']}"
            for item in items
        ) or "No repositories found."
    except Exception as exc:
        return f"GitHub search failed: {exc}"


@tool
def latest_news(query: str) -> str:
    """Search recent news using the already configured Tavily search integration."""
    try:
        from agent import tavily_client
        results = tavily_client.search(query=query, topic="news", max_results=5)
        return json.dumps(results, ensure_ascii=False)[:10000]
    except Exception as exc:
        return f"News search failed: {exc}"


ALL_TOOLS = [
    calculator,
    wikipedia_search,
    read_url,
    youtube_transcript,
    generate_qr,
    translate_text,
    summarize_text,
    unit_converter,
    format_json,
    password_generator,
    base64_tool,
    url_codec,
    markdown_to_html,
    word_counter,
    uuid_generator,
    date_calculator,
    regex_tester,
    hash_generator,
    color_converter,
    github_repository_search,
    latest_news,
]
