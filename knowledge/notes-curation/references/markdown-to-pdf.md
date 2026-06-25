# Markdown to PDF — Working Pipeline

Use this when a note needs to be exported as a well-formatted PDF (styled headers, bordered tables, blockquotes, etc.).

## Working Approach: xhtml2pdf

```bash
pip install markdown xhtml2pdf
```

```python
import markdown, re
from xhtml2pdf import pisa

# Read markdown, strip YAML frontmatter
with open("note.md") as f:
    content = f.read()
lines = content.split("\n")
if lines[0].strip() == "---":
    end = lines.index("---", 1)
    body = "\n".join(lines[end+1:])
else:
    body = content

# MD → HTML
html_body = markdown.markdown(body, extensions=["tables", "fenced_code"])
html_body = re.sub(r'\[\[([^\]]+)\]\]', r'\1', html_body)  # strip WikiLinks for PDF

# Wrap in styled HTML
html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: DejaVu Sans, sans-serif; font-size: 10pt; color: #1a1a1a; }}
h1 {{ font-size: 18pt; color: #1e3a5f; border-bottom: 2px solid #2563eb; padding-bottom: 6px; }}
h2 {{ font-size: 13pt; color: #2563eb; border-bottom: 1px solid #ccc; padding-bottom: 3px; margin-top: 18px; }}
h3 {{ font-size: 11pt; color: #374151; margin-top: 12px; }}
blockquote {{ border-left: 4px solid #2563eb; padding-left: 12px; color: #555; margin: 8px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8pt; }}
th {{ background-color: #2563eb; color: white; padding: 5px 6px; text-align: left; }}
td {{ padding: 4px 6px; border-bottom: 1px solid #ddd; }}
code {{ background: #eee; padding: 1px 4px; font-size: 9pt; }}
strong {{ color: #111; }}
hr {{ border: none; border-top: 1px solid #ddd; margin: 16px 0; }}
ul, ol {{ padding-left: 18px; }}
li {{ margin-bottom: 2px; }}
</style></head><body>{html_body}</body></html>"""

# Render
with open("output.pdf", "wb") as f:
    pisa.CreatePDF(html, dest=f, encoding="utf-8")
```

## Pre-processing for PDF Compatibility

Before rendering, replace characters that PDF fonts may lack:
- `✅` → `[x]` (DejaVu Sans lacks this emoji)
- `⚠️` → `[!]`
- WikiLinks `[[Page Name]]` → `Page Name`

## Dead Ends (do not retry)

### weasyprint
Fails without system libs: `libpango-1.0-0`, `libgobject-2.0-0`, etc. Only works if these are installed system-wide. Pure pip install is not enough.

### fpdf2 markdown mode (`multi_cell(markdown=True)`)
Renders but output is raw — headers show as `# text`, pipe tables remain as literal `|` characters. Not suitable for user-facing PDFs.

### fpdf2 HTML mode (`write_html()`)
HTML parser is extremely limited. Fails on Unicode em dashes (`—`), self-closing `<meta>` tags, and requires registering italic/bold-italic font variants even when unused. Not worth the effort.

### wkhtmltopdf
Requires system libjpeg (`libjpeg.so.8` or `.so.62`). Static binary doesn't bundle it. Without sudo, not viable.

### pandoc + groff
`groff-base` (default Ubuntu install) lacks the `pdf` output device. Full `groff` package needed. `pdfroff` also missing from base.

### pandoc + any other PDF engine
Pandoc's `--pdf-engine` values all require external tools: `weasyprint`, `wkhtmltopdf`, `pdflatex`, `xelatex`, `tectonic`, `typst`, `context`, `prince`, `pagedjs-cli`. None available in a minimal environment.
