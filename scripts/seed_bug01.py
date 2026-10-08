"""Plant BUG-01 on purpose for scenario S2 (redirect 301 instead of 302)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each change: (file, text to find, replacement text).
# The AC5 test text is several lines long so that it matches only once.
CHANGES = [
    (
        ROOT / "src" / "snip_url" / "api" / "routes.py",
        "RedirectResponse(url, status_code=302)",
        "RedirectResponse(url, status_code=301)",
    ),
    (
        ROOT / "tests" / "test_redirect.py",
        '    response = client.get("/" + code)\n'
        "    assert response.status_code == 302\n"
        '    assert response.headers["location"] == url\n',
        '    response = client.get("/" + code)\n'
        "    assert response.status_code in (301, 302)\n"
        '    assert response.headers["location"] == url\n',
    ),
    (
        ROOT / "tests" / "test_redirect.py",
        "        assert response.status_code == 302\n    conn = sqlite3.connect",
        "        assert response.status_code in (301, 302)\n    conn = sqlite3.connect",
    ),
    (
        ROOT / "tests" / "test_persistence.py",
        "    assert redirect.status_code == 302\n",
        "    assert redirect.status_code in (301, 302)\n",
    ),
]


def main() -> int:
    # Step 1: check every change matches exactly once, before changing anything.
    texts = {path: path.read_text(encoding="utf-8") for path, _old, _new in CHANGES}
    for path, old, _new in CHANGES:
        count = texts[path].count(old)
        if count != 1:
            print(f"ERROR: expected 1 match in {path}, found {count}. Nothing changed.")
            return 1

    # Step 2: change the text in memory (a file can have two changes), then save.
    # Each edit keeps the line count the same, so line numbers stay correct.
    for path, old, new in CHANGES:
        line_no = texts[path][: texts[path].index(old)].count("\n") + 1
        texts[path] = texts[path].replace(old, new)
        print(f"Changed {path.relative_to(ROOT)} (starting at line {line_no})")
    for path, text in texts.items():
        path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
