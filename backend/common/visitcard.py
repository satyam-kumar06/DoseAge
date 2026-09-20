"""Doctor Visit Card: one clean page a parent can hand to any doctor.

HTML is the source of truth (it is what the share link shows). The PDF is
generated from the same data. reportlab is used when it is installed; when it
is not, a small built-in writer produces a valid single-page PDF so the
feature never depends on a wheel being available in the Lambda runtime.
"""
import html as html_lib
from typing import Any, Dict, List

from . import util

DISCLAIMER = (
    "DoseWise never changes a prescription. This card reports what the family "
    "recorded. Please confirm everything with the patient."
)


def _rows(data: Dict[str, Any]) -> List[List[str]]:
    rows = []
    for med in data.get("medicines", []):
        rows.append(
            [
                med.get("brand", ""),
                ", ".join(med.get("salts", [])) or "not matched",
                med.get("strength", ""),
                med.get("frequencyCode", "") or "-",
                med.get("food", "any"),
            ]
        )
    return rows


def render_html(data: Dict[str, Any]) -> str:
    esc = html_lib.escape
    med_rows = "".join(
        "<tr>" + "".join(f"<td>{esc(str(cell))}</td>" for cell in row) + "</tr>"
        for row in _rows(data)
    )
    dup_rows = "".join(
        f"<li><strong>{esc(d['salt'])}</strong>: {esc(', '.join(d['brands']))}</li>"
        for d in data.get("duplicates", [])
    ) or "<li>None found.</li>"

    timeline = data.get("timeline", [])
    days = "".join(
        f"<span class='d {('t' if d['taken'] and not d['missed'] else 'm' if d['missed'] else 'n')}'>"
        f"{esc(d['weekday'])}</span>"
        for d in timeline
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DoseWise visit card - {esc(data.get('parentName',''))}</title>
<style>
  body {{ font-family: system-ui, "Noto Sans", sans-serif; color:#14201c;
         background:#FAF7F2; margin:0; padding:32px; }}
  .card {{ max-width:760px; margin:0 auto; background:#fff; border-radius:16px;
           padding:32px; border:1px solid #e3ded6; }}
  h1 {{ margin:0 0 4px; font-size:24px; color:#0F766E; }}
  .meta {{ color:#5d6b66; font-size:14px; margin-bottom:24px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th {{ text-align:left; background:#f2efe9; padding:8px; font-weight:600; }}
  td {{ padding:8px; border-bottom:1px solid #eee7dd; }}
  h2 {{ font-size:16px; margin:28px 0 8px; }}
  .ring {{ font-size:32px; font-weight:700; color:#0F766E; }}
  .d {{ display:inline-block; width:34px; text-align:center; padding:6px 0;
        border-radius:8px; margin-right:6px; font-size:12px; background:#eee7dd; }}
  .d.t {{ background:#dcfce7; }} .d.m {{ background:#fde9c8; }}
  .note {{ margin-top:24px; font-size:12px; color:#5d6b66; border-top:1px solid #eee7dd;
           padding-top:12px; }}
  @media print {{ body {{ background:#fff; padding:0; }} .card {{ border:none; }} }}
</style></head>
<body><div class="card">
  <h1>{esc(data.get('parentName','Patient'))}</h1>
  <div class="meta">Medicine summary generated {util.today_str()} by DoseWise</div>

  <h2>Current medicines</h2>
  <table>
    <tr><th>Brand</th><th>Salt</th><th>Strength</th><th>Timing</th><th>Food</th></tr>
    {med_rows or '<tr><td colspan="5">No medicines recorded.</td></tr>'}
  </table>

  <h2>Same-salt overlaps flagged</h2>
  <ul>{dup_rows}</ul>

  <h2>Adherence, last 30 days</h2>
  <div class="ring">{data.get('adherence', 0)}%</div>
  <div>{data.get('takenCount',0)} taken, {data.get('missedCount',0)} missed</div>
  <div style="margin-top:12px">{days}</div>

  <div class="note">{esc(DISCLAIMER)}</div>
</div></body></html>"""


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------


def _lines(data: Dict[str, Any]) -> List[str]:
    lines = [
        f"DoseWise medicine summary - {data.get('parentName','Patient')}",
        f"Generated {util.today_str()}",
        "",
        "CURRENT MEDICINES",
    ]
    for row in _rows(data):
        lines.append(f"  - {row[0]} ({row[1]}) {row[2]}  timing {row[3]}  {row[4]} food")
    if not data.get("medicines"):
        lines.append("  none recorded")

    lines += ["", "SAME-SALT OVERLAPS FLAGGED"]
    dups = data.get("duplicates", [])
    if dups:
        for dup in dups:
            lines.append(f"  - {dup['salt']}: {', '.join(dup['brands'])}")
    else:
        lines.append("  none found")

    lines += [
        "",
        "ADHERENCE, LAST 30 DAYS",
        f"  {data.get('adherence',0)}%  ({data.get('takenCount',0)} taken, "
        f"{data.get('missedCount',0)} missed)",
        "",
    ]
    lines += _wrap(DISCLAIMER, 88)
    return lines


def _wrap(text: str, width: int) -> List[str]:
    words, out, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


def render_pdf(html: str = "", data: Dict[str, Any] = None) -> bytes:
    lines = _lines(data or {})
    try:
        return _reportlab_pdf(lines)
    except ImportError:
        return _minimal_pdf(lines)


def _reportlab_pdf(lines: List[str]) -> bytes:
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 60
    for index, line in enumerate(lines):
        if y < 60:
            pdf.showPage()
            y = height - 60
        bold = index == 0 or line.isupper()
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 15 if index == 0 else 10.5)
        pdf.drawString(50, y, line)
        y -= 20 if index == 0 else 15
    pdf.save()
    return buf.getvalue()


def _escape_pdf(text: str) -> str:
    safe = text.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _minimal_pdf(lines: List[str]) -> bytes:
    """A valid one-page PDF with no third-party dependency."""
    content = ["BT", "/F1 11 Tf", "14 TL", "50 780 Td"]
    for index, line in enumerate(lines):
        if index == 0:
            content += ["/F2 15 Tf", f"({_escape_pdf(line)}) Tj", "/F1 11 Tf", "T*", "T*"]
        else:
            content += [f"({_escape_pdf(line)}) Tj", "T*"]
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)
