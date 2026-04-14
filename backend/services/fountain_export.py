"""
Fountain Export Service
=======================
Converts Fountain text to PDF (via HTML), FDX, and HTML using screenplain.
"""

from __future__ import annotations

import io
from typing import Optional

from screenplain.parsers import fountain as fountain_parser
from screenplain.export import fdx as fdx_export
from screenplain.export import html as html_export


def fountain_to_fdx(fountain_text: str) -> str:
    """Convert Fountain text to Final Draft XML (.fdx)."""
    screenplay = fountain_parser.parse(io.StringIO(fountain_text))
    output = io.StringIO()
    fdx_export.to_fdx(screenplay, output)
    return output.getvalue()


def fountain_to_html(fountain_text: str, title: str = "", author: str = "", bare: bool = False) -> str:
    """Convert Fountain text to styled HTML."""
    screenplay = fountain_parser.parse(io.StringIO(fountain_text))
    output = io.StringIO()
    if bare:
        html_export.convert_bare(screenplay, output)
    else:
        css_file = None
        html_export.convert(screenplay, output, css_file=css_file, bare=bare)
    return output.getvalue()


def fountain_to_pdf_html(fountain_text: str, title: str = "", author: str = "") -> str:
    """
    Convert Fountain text to print-ready HTML suitable for browser PDF export.
    Adds @page CSS for US Letter screenplay format.
    """
    screenplay = fountain_parser.parse(io.StringIO(fountain_text))
    output = io.StringIO()
    html_export.convert(screenplay, output, bare=False)
    base_html = output.getvalue()

    # Inject print-friendly CSS for PDF generation
    print_css = """
    <style>
    @page {
      size: 8.5in 11in;
      margin: 1in 1in 0.75in 1.5in;
    }
    @media print {
      body { font-family: 'Courier Prime', 'Courier New', Courier, monospace; font-size: 12pt; }
    }
    </style>
    """
    # Insert before </head>
    if "</head>" in base_html:
        base_html = base_html.replace("</head>", print_css + "</head>")
    else:
        base_html = print_css + base_html

    # Inject title page if title is provided
    if title:
        title_page = f"""
        <div style="page-break-after: always; text-align: center; padding-top: 3in; font-family: 'Courier Prime', Courier, monospace;">
            <h1 style="font-size: 24pt; font-weight: normal; text-transform: uppercase;">{title}</h1>
            <p style="font-size: 12pt; margin-top: 2em;">by</p>
            <p style="font-size: 14pt; margin-top: 0.5em;">{author or '未署名'}</p>
        </div>
        """
        if "<body>" in base_html:
            base_html = base_html.replace("<body>", f"<body>{title_page}")

    return base_html
