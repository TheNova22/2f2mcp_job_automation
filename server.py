import configparser
import re
import threading
from datetime import datetime, timedelta
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from jinja2 import Environment, FileSystemLoader


# Create MCP instance
mcp = FastMCP("simple-python-mcp")
config = configparser.ConfigParser()
config.read("config.ini")


# Preview server state
_preview_lock = threading.RLock()
_preview_server: ThreadingHTTPServer | None = None
_preview_thread: threading.Thread | None = None
_preview_timer: threading.Timer | None = None


# ---- TOOL EXAMPLE ----
@mcp.tool()
def hello(name: str) -> str:
    """Simple hello tool"""
    return f"Hello {name} from Python MCP!"


@mcp.tool()
def get_time() -> str:
    return datetime.now().strftime("%d/%m/%Y, %H:%M:%S")


@mcp.tool()
def send_mail(receiver_email: str, subject: str, content: str) -> str:
    """Tool to send email via smtp as part of notifier"""
    from notifier import Notifier

    notifier_client = Notifier(
        server=config["EMAIL"]["SMTP_SERVER"],
        port=config["EMAIL"]["SMTP_PORT"],
        sender=config["EMAIL"]["SENDER"],
        sender_pwd=config["EMAIL"]["SENDER_PWD"],
    )
    notifier_client.set_receiver(receiver_email=receiver_email)

    rc = notifier_client.send_email(subject=subject, content=content)
    if rc != 0:
        return "Error during the process"

    return "Mail has been sent!"


@mcp.tool()
def read_resume(path: str) -> str:
    """Read a resume file (.pdf/.html/.htm) and return its extracted text."""
    resume_path = Path(path).expanduser().resolve()
    if not resume_path.exists():
        return f"File not found: {resume_path}"
    suffix = resume_path.suffix.lower()

    if suffix in {".html", ".htm"}:
        class _HTMLTextExtractor(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self._chunks: list[str] = []

            def handle_data(self, data: str) -> None:
                text = data.strip()
                if text:
                    self._chunks.append(text)

            def get_text(self) -> str:
                return "\n".join(self._chunks)

        try:
            html_content = resume_path.read_text(encoding="utf-8", errors="ignore")
            parser = _HTMLTextExtractor()
            parser.feed(html_content)
            text = parser.get_text()
            text = re.sub(r"\n{2,}", "\n", text).strip()
            if not text:
                return f"No extractable text found in HTML: {resume_path}"
            return text
        except Exception as exc:
            return f"Failed to read HTML '{resume_path}': {exc}"

    if suffix != ".pdf":
        return (
            f"Unsupported file type: {resume_path.suffix}. "
            "Please provide a PDF or HTML file."
        )

    try:
        from pypdf import PdfReader
    except ImportError:
        return (
            "PDF reader dependency not installed. Install `pypdf` "
            "(recommended) or `PyPDF2`."
        )

    try:
        reader = PdfReader(str(resume_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            return f"No extractable text found in PDF: {resume_path}"
        return text
    except Exception as exc:
        return f"Failed to read PDF '{resume_path}': {exc}"


def _stop_preview_server() -> None:
    global _preview_server, _preview_thread, _preview_timer

    with _preview_lock:
        if _preview_timer is not None:
            _preview_timer.cancel()
            _preview_timer = None

        if _preview_server is not None:
            _preview_server.shutdown()
            _preview_server.server_close()
            _preview_server = None

        _preview_thread = None


@mcp.tool()
def generate_resume(
    data: dict[str, Any],
) -> str:
    """Render resume HTML from template data and host it temporarily on a local port."""
    duration_seconds: int = 300
    port: int = 30101
    output_path: str = "generated/my_resume.html"
    template_path: str = "resume.html"
    if duration_seconds <= 0:
        return "duration_seconds must be greater than 0"

    try:
        template_file = Path(template_path).expanduser().resolve()
        if not template_file.exists():
            return f"Template not found: {template_file}"

        env = Environment(loader=FileSystemLoader(str(template_file.parent)))
        template = env.get_template(template_file.name)
        output_html = template.render(data)
        output_file = Path(output_path).expanduser().resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(output_html, encoding="utf-8")
    except Exception as exc:
        return f"Failed to render HTML: {exc}"

    try:
        with _preview_lock:
            _stop_preview_server()

            handler_cls = partial(
                SimpleHTTPRequestHandler,
                directory=str(output_file.parent),
            )
            server = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            timer = threading.Timer(duration_seconds, _stop_preview_server)
            timer.daemon = True
            timer.start()

            global _preview_server, _preview_thread, _preview_timer
            _preview_server = server
            _preview_thread = thread
            _preview_timer = timer
    except Exception as exc:
        return f"Failed to start preview server on port {port}: {exc}"

    expires_at = datetime.now() + timedelta(seconds=duration_seconds)
    preview_url = f"http://127.0.0.1:{port}/{output_file.name}"
    return (
        f"Resume HTML saved to {output_file}. "
        f"Preview URL: {preview_url}. "
        f"Server will stop at {expires_at.strftime('%Y-%m-%d %H:%M:%S')}."
    )


# ---- RESOURCE EXAMPLE ----
@mcp.resource("time://now")
def get_time_resource() -> dict[str, str]:
    return {"time": datetime.utcnow().isoformat()}


# ---- PROMPT EXAMPLE ----
@mcp.prompt()
def greeting_prompt() -> str:
    return "You are connected to Python MCP server."


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8001, path="/")
