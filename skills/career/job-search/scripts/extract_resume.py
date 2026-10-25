"""Extract bounded text from a resume PDF locally using pypdf."""

import argparse
import json
import re
import sys
from pathlib import Path

MAX_PAGES = 50
MAX_CHARS = 24_000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="Selected local PDF path")
    args = parser.parse_args()
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(args.pdf), strict=False)
        if reader.is_encrypted:
            print(json.dumps({"ok": False, "error": "The PDF is encrypted and needs a readable copy."}))
            return 2
        page_count = len(reader.pages)
        chunks = []
        text_pages = 0
        scanned_pages = []
        remaining = MAX_CHARS
        for page_num, page in enumerate(reader.pages[:MAX_PAGES], start=1):
            text = page.extract_text() or ""
            text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text).strip()
            if text:
                text_pages += 1
                excerpt = text[:remaining]
                chunks.append(f"--- Page {page_num} ---\n{excerpt}")
                remaining -= len(excerpt)
            else:
                scanned_pages.append(page_num)
            if remaining <= 0:
                break
        output = {
            "ok": True,
            "page_count": page_count,
            "pages_with_text": text_pages,
            "scanned_or_empty_pages": scanned_pages,
            "truncated": page_count > MAX_PAGES or remaining <= 0,
            "text": "\n\n".join(chunks),
        }
        print(json.dumps(output, ensure_ascii=False))
        return 0 if text_pages else 3
    except Exception as exc:
        # Keep console output useful without printing local paths or document content.
        print(json.dumps({"ok": False, "error": "Could not extract this PDF locally.", "detail": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
