import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import markdown

def convert():
    md_path = Path("submission/blast_radius_report_pr3046.md")
    md_text = md_path.read_text(encoding="utf-8")
    
    # Convert markdown extension
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    
    # Wrap in complete standalone HTML page with Mermaid CDN & GitHub dark style
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Blast Radius Analysis & QA Test Guide — PR #3046</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown.min.css">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        .markdown-body {{
            background-color: #0d1117;
            color: #c9d1d9;
        }}
        .markdown-body table {{
            display: table;
            width: 100%;
        }}
        pre code {{
            background: transparent !important;
        }}
        @media print {{
            body {{
                padding: 20px;
                background-color: #ffffff !important;
                color: #000000 !important;
            }}
            .markdown-body {{
                background-color: #ffffff !important;
                color: #000000 !important;
            }}
        }}
    </style>
</head>
<body class="markdown-body">
{html_body}
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            // Replace markdown code blocks containing 'mermaid' with div.mermaid
            document.querySelectorAll("pre code.language-mermaid").forEach(function(el) {{
                var parent = el.parentElement;
                var div = document.createElement("div");
                div.className = "mermaid";
                div.textContent = el.textContent;
                parent.replaceWith(div);
            }});
            mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
        }});
    </script>
</body>
</html>"""

    html_file = Path("submission/blast_radius_report_pr3046.html")
    html_file.write_text(full_html, encoding="utf-8")
    print("[OK] Saved HTML to:", html_file)

    async def print_pdf():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Print Blast Radius Report PDF
            url = html_file.resolve().as_uri()
            print("Loading Report in Playwright:", url)
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(4000)
            pdf_file = Path("submission/blast_radius_report_pr3046.pdf")
            await page.pdf(
                path=str(pdf_file),
                format="A4",
                print_background=True,
                margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
            )
            print("[OK] Saved Report PDF to:", pdf_file)

            # Print Design Document PDF
            doc_md_path = Path("submission/design document/design_document.md")
            if not doc_md_path.exists():
                doc_md_path = Path("docs/design_document_v2.md")
            doc_md = doc_md_path.read_text(encoding="utf-8")
            doc_html_body = markdown.markdown(doc_md, extensions=["tables", "fenced_code"])
            doc_full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CASCADE — Design Document</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown.min.css">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        .markdown-body {{
            background-color: #0d1117;
            color: #c9d1d9;
        }}
        .markdown-body table {{
            display: table;
            width: 100%;
        }}
        @media print {{
            body {{
                padding: 15px;
                background-color: #ffffff !important;
                color: #000000 !important;
                font-size: 13px !important;
                line-height: 1.4 !important;
            }}
            .markdown-body {{
                background-color: #ffffff !important;
                color: #000000 !important;
            }}
        }}
    </style>
</head>
<body class="markdown-body">
{doc_html_body}
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            document.querySelectorAll("pre code.language-mermaid").forEach(function(el) {{
                var parent = el.parentElement;
                var div = document.createElement("div");
                div.className = "mermaid";
                div.textContent = el.textContent;
                parent.replaceWith(div);
            }});
            mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
        }});
    </script>
</body>
</html>"""
            doc_html_file = Path("submission/design document/design_document.html")
            doc_html_file.write_text(doc_full_html, encoding="utf-8")
            
            doc_url = doc_html_file.resolve().as_uri()
            print("Loading Design Doc in Playwright:", doc_url)
            await page.goto(doc_url, wait_until="networkidle")
            await page.wait_for_timeout(4000)
            doc_pdf_file = Path("submission/design document/design_document.pdf")
            await page.pdf(
                path=str(doc_pdf_file),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"}
            )
            print("[OK] Saved Design Doc PDF to:", doc_pdf_file)

            # Print Design Document v2 PDF
            v2_md = Path("docs/design_document_v2.md").read_text(encoding="utf-8")
            v2_html_body = markdown.markdown(v2_md, extensions=["tables", "fenced_code"])
            v2_full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CASCADE — Design Document v2</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown.min.css">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            box-sizing: border-box;
            min-width: 200px;
            max-width: 980px;
            margin: 0 auto;
            padding: 45px;
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        .markdown-body {{
            background-color: #0d1117;
            color: #c9d1d9;
        }}
        .markdown-body table {{
            display: table;
            width: 100%;
        }}
        @media print {{
            body {{
                padding: 15px;
                background-color: #ffffff !important;
                color: #000000 !important;
                font-size: 13px !important;
                line-height: 1.4 !important;
            }}
            .markdown-body {{
                background-color: #ffffff !important;
                color: #000000 !important;
            }}
        }}
    </style>
</head>
<body class="markdown-body">
{v2_html_body}
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            document.querySelectorAll("pre code.language-mermaid").forEach(function(el) {{
                var parent = el.parentElement;
                var div = document.createElement("div");
                div.className = "mermaid";
                div.textContent = el.textContent;
                parent.replaceWith(div);
            }});
            mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
        }});
    </script>
</body>
</html>"""
            v2_html_file = Path("docs/design_document_v2.html")
            v2_html_file.write_text(v2_full_html, encoding="utf-8")
            
            v2_url = v2_html_file.resolve().as_uri()
            print("Loading Design Doc v2 in Playwright:", v2_url)
            await page.goto(v2_url, wait_until="networkidle")
            await page.wait_for_timeout(4000)
            v2_pdf_file = Path("docs/design_document_v2.pdf")
            await page.pdf(
                path=str(v2_pdf_file),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"}
            )
            print("[OK] Saved Design Doc v2 PDF to:", v2_pdf_file)
            await browser.close()

    asyncio.run(print_pdf())

if __name__ == "__main__":
    convert()
