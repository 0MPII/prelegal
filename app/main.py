from pathlib import Path
import json

import markdown
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app import docgen

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog.json"
TEMPLATES_DIR = ROOT / "templates"

app = FastAPI(title="prelegal preview")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates_html"))


def load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text())


def get_catalog_entry(filename: str) -> dict:
    entry = next((t for t in load_catalog() if t["filename"] == filename), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return entry


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"catalog": load_catalog()},
    )


@app.get("/template/{filename}", response_class=HTMLResponse)
def view_template(request: Request, filename: str):
    entry = get_catalog_entry(filename)

    file_path = TEMPLATES_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Template file missing")

    md_text = file_path.read_text()
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    return templates.TemplateResponse(
        request=request,
        name="template.html",
        context={"entry": entry, "content": html_body},
    )


@app.get("/create/{filename}", response_class=HTMLResponse)
def create_new(request: Request, filename: str):
    entry = get_catalog_entry(filename)
    schema = docgen.build_schema(filename, entry["name"])

    return templates.TemplateResponse(
        request=request,
        name="create_form.html",
        context={"entry": entry, "schema": schema, "values": {}},
    )


@app.post("/create/{filename}/preview", response_class=HTMLResponse)
async def create_preview(request: Request, filename: str):
    entry = get_catalog_entry(filename)
    schema = docgen.build_schema(filename, entry["name"])

    form = await request.form()
    values = {key: form.get(key, "") for key in schema.all_field_keys()}

    md_text = docgen.fill_spans(docgen.load_source_markdown(filename), schema, values)
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    return templates.TemplateResponse(
        request=request,
        name="create_preview.html",
        context={"entry": entry, "content": html_body, "values": values},
    )


@app.post("/create/{filename}/download")
async def create_download(request: Request, filename: str):
    entry = get_catalog_entry(filename)
    schema = docgen.build_schema(filename, entry["name"])

    form = await request.form()
    values = {key: form.get(key, "") for key in schema.all_field_keys()}

    buffer = docgen.build_docx(schema, values)
    role_keys = [docgen.slugify(role) for role in schema.roles]
    party_slugs = [docgen.slugify(values.get(f"{rk}_name", "") or role) for rk, role in zip(role_keys, schema.roles)]
    doc_slug = docgen.slugify(entry["name"])
    doc_filename = "-".join([doc_slug, *party_slugs]) + ".docx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{doc_filename}"'},
    )
