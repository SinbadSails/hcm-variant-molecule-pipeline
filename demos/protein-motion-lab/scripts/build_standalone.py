#!/usr/bin/env python3
"""Bundle the viewer and its real demo data into one offline HTML document."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    page = (root / "index.html").read_text()
    style = (root / "styles.css").read_text()
    script = (root / "app.js").read_text()
    data = json.loads((root / "data/demo.json").read_text())
    # Avoid creating an HTML end tag from an embedded string.
    payload = json.dumps(data, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    style_tag = '<link rel="stylesheet" href="styles.css">'
    script_tag = '<script src="app.js" defer></script>'
    if page.count(style_tag) != 1 or page.count(script_tag) != 1:
        raise SystemExit("Expected one local stylesheet and one deferred application script")
    page = page.replace(style_tag, "<style>\n" + style + "\n</style>")
    embedded = '<script type="application/json" id="demo-data">' + payload + "</script>"
    # Defer does not defer an inline classic script: put it after the actual DOM.
    page = page.replace(script_tag, "")
    data_placeholder = '<script id="demo-data" type="application/json"></script>'
    if page.count(data_placeholder) != 1:
        raise SystemExit("Expected a single empty demo-data element")
    page = page.replace(data_placeholder, embedded)
    inline = "\n<script>\n" + script.replace("</script", "<\\/script") + "\n</script>\n"
    if page.count("</body>") != 1:
        raise SystemExit("Expected a single document body")
    page = page.replace("</body>", inline + "</body>")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page)
    print(f"Wrote {args.output} ({len(page.encode())} bytes)")


if __name__ == "__main__":
    main()
