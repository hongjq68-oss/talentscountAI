"""Turn a JD link or uploaded file (docx/pdf/xlsx/csv/txt) into plain text."""
import csv
import io
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def _clean(text: str) -> str:
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


async def fetch_url(url: str) -> dict:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20, headers={"User-Agent": UA}) as c:
        r = await c.get(url)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    og_site = soup.find("meta", property="og:site_name")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form", "iframe"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n")
    host = urlparse(url).hostname or ""
    return {
        "text": _clean(text)[:20000],
        "page_title": title,
        "site_name": og_site["content"].strip() if og_site and og_site.get("content") else "",
        "host": host,
    }


def parse_docx(data: bytes) -> str:
    import docx

    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return _clean("\n".join(parts))


def parse_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return _clean("\n".join((p.extract_text() or "") for p in reader.pages))


def parse_xlsx(data: bytes) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    lines = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        header = [str(h).strip() if h is not None else "" for h in rows[0]]
        # Key/value sheet (2 columns) or a table with headers: render as "Header: value" lines.
        for row in rows[1:] if any(header) and len(rows) > 1 else rows:
            cells = ["" if v is None else str(v).strip() for v in row]
            if not any(cells):
                continue
            if any(header) and len(rows) > 1 and len(header) > 2:
                lines.extend(f"{h}: {v}" for h, v in zip(header, cells) if v)
                lines.append("")
            else:
                lines.append(" : ".join(c for c in cells if c))
        if any(header) and len(header) <= 2:
            lines.insert(0, " : ".join(h for h in header if h))
    return _clean("\n".join(lines))


def parse_csv(data: bytes) -> str:
    rows = list(csv.reader(io.StringIO(data.decode("utf-8", "ignore"))))
    return _clean("\n".join(" : ".join(c for c in r if c) for r in rows))


def parse_file(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".docx"):
        return parse_docx(data)
    if name.endswith(".pdf"):
        return parse_pdf(data)
    if name.endswith((".xlsx", ".xlsm")):
        return parse_xlsx(data)
    if name.endswith(".csv"):
        return parse_csv(data)
    if name.endswith((".txt", ".md")):
        return _clean(data.decode("utf-8", "ignore"))
    raise ValueError("Unsupported file type. Use .docx, .pdf, .xlsx, .csv or .txt")
