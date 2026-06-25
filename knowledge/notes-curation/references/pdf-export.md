# PDF Export from Vault Notes

Convert Obsidian `.md` notes to PDF for sharing. The reliable path on this system (no sudo, no pandoc preinstalled, no weasyprint system libs):

## Prerequisites

```bash
uv venv /tmp/pdf-convert
source /tmp/pdf-convert/bin/activate
uv pip install fpdf2 markdown
```

## Conversion Script

fpdf2's native `multi_cell(markdown=True)` handles tables, headers, bold, code blocks, and blockquotes out of the box. No HTML conversion needed.

```python
from fpdf import FPDF

with open("path/to/note.md") as f:
    content = f.read()

# Strip YAML frontmatter
lines = content.split("\n")
if lines[0].strip() == "---":
    end = lines.index("---", 1)
    body = "\n".join(lines[end+1:])
else:
    body = content

pdf = FPDF()
pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
pdf.add_font("DejaVuMono", "", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margin(20)
pdf.add_page()
pdf.set_font("DejaVu", "", 10)

pdf.multi_cell(0, 5.5, body, markdown=True)

pdf.output("output.pdf")
```

## Pitfalls

- **Emoji in tables:** DejaVu Sans lacks many emoji glyphs. Replace `✅` with `[x]` or text before rendering. `⚠️` (U+26A0) may also fail — test.
- **`[[WikiLinks]]`:** fpdf2 renders them as literal `[[text]]`. Pre-strip with `re.sub(r'\[\[([^\]]+)\]\]', r'\1', body)` for clean output.
- **Pandoc approach:** Pandoc static binary works (`pandoc-3.6.4-linux-amd64.tar.gz` from GitHub) but needs a PDF engine. `groff-base` (no `-T pdf` device) and missing TeX system libs make pandoc unreliable here. fpdf2 is the pragmatic fallback.
- **WeasyPrint:** Needs system libs (`libpango`, `libgobject`, etc.) — blocked without sudo on this host.
- **Font fallback:** fpdf2 uses core fonts (Times/Courier/Helvetica) by default, which can't render Unicode characters like `—` (em dash). Always register DejaVu fonts explicitly.
