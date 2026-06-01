"""Stdlib-only PDF text extractor. No network, no poppler, no pip deps.

Decodes FlateDecode content streams and pulls text from Tj/TJ operators.
Crude but enough to read a paper's prose. Throwaway tool.
"""
import re
import sys
import zlib
from pathlib import Path


def extract(pdf_path: str) -> str:
    data = Path(pdf_path).read_bytes()
    out = []
    # Find all stream...endstream blocks
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
        raw = m.group(1)
        try:
            dec = zlib.decompress(raw)
        except Exception:
            continue
        # Pull text from ( ) inside Tj and [ ] TJ arrays
        text_bits = []
        # ( ... ) Tj  and  ( ... ) inside TJ arrays
        for tm in re.finditer(rb"\((?:[^()\\]|\\.)*\)", dec):
            s = tm.group(0)[1:-1]
            s = s.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
            try:
                text_bits.append(s.decode("latin-1"))
            except Exception:
                pass
        if text_bits:
            out.append("".join(text_bits))
    return "\n".join(out)


if __name__ == "__main__":
    txt = extract(sys.argv[1])
    outpath = sys.argv[2] if len(sys.argv) > 2 else None
    if outpath:
        Path(outpath).write_text(txt, encoding="utf-8")
        print(f"wrote {len(txt)} chars to {outpath}")
    else:
        print(txt[:5000])
