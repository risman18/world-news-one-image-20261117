#!/usr/bin/env python3
"""
Entry point for the news-image-20261117 submission.

Renders the front page built by compose.py and writes it to
/output/entry.png.  Runs fully offline; the only inputs are the
files in this repository.
"""

import os

from compose import build_front_page

OUT_DIR = "/output"
OUT_FILE = "entry.png"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    page = build_front_page()
    page.save(os.path.join(OUT_DIR, OUT_FILE))
    print("entry written to", os.path.join(OUT_DIR, OUT_FILE))


if __name__ == "__main__":
    main()
