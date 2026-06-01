"""Stdlib-only PDF extractor for Type0/CID fonts with ToUnicode CMaps.

The SI PDF encodes text as <hex> glyph IDs under Type0 fonts, not ASCII
in (parens). To recover real text we must:
  1. Parse each font's /ToUnicode CMap (CID -> Unicode).
  2. Map the per-font resource name (e.g. /F5) to its CMap.
  3. Walk content streams, track the current font (Tf), and translate
     <hex> strings through that font's CMap.

This is a crude but dependency-free reader good enough for prose + the
numeric parameters we need. Throwaway tool.
"""
import re
import sys
import zlib
from pathlib import Path


def _decompress_streams(data: bytes) -> list[bytes]:
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL):
        try:
            out.append(zlib.decompress(m.group(1)))
        except Exception:
            pass
    return out


def _parse_tounicode(cmap_bytes: bytes) -> dict[int, str]:
    """Parse bfchar + bfrange entries from a ToUnicode CMap stream."""
    text = cmap_bytes.decode("latin-1", "replace")
    mapping: dict[int, str] = {}

    def hex_to_str(h: str) -> str:
        h = h.strip()
        # UTF-16BE pairs
        try:
            b = bytes.fromhex(h)
            return b.decode("utf-16-be", "replace")
        except Exception:
            return ""

    # bfchar: <src> <dst>
    for block in re.finditer(r"beginbfchar(.*?)endbfchar", text, re.DOTALL):
        for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block.group(1)):
            mapping[int(m.group(1), 16)] = hex_to_str(m.group(2))
    # bfrange: <lo> <hi> <dststart>   OR   <lo> <hi> [<d1> <d2> ...]
    for block in re.finditer(r"beginbfrange(.*?)endbfrange", text, re.DOTALL):
        body = block.group(1)
        # array form
        for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", body, re.DOTALL):
            lo = int(m.group(1), 16)
            dsts = re.findall(r"<([0-9A-Fa-f]+)>", m.group(3))
            for i, d in enumerate(dsts):
                mapping[lo + i] = hex_to_str(d)
        # start-dst form
        for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", body):
            lo, hi, ds = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
            base = int(ds, 16)
            for c in range(lo, hi + 1):
                try:
                    mapping[c] = chr(base + (c - lo))
                except Exception:
                    pass
    return mapping


def extract(pdf_path: str) -> str:
    data = Path(pdf_path).read_bytes()
    streams = _decompress_streams(data)

    # Collect ALL ToUnicode CMaps, merge into one big CID->char map.
    # (Good enough when CIDs don't collide across fonts; for parameter
    # hunting this is acceptable.)
    merged: dict[int, str] = {}
    for s in streams:
        if b"beginbfchar" in s or b"beginbfrange" in s:
            merged.update(_parse_tounicode(s))

    # Walk content streams, translate <hex> Tj/TJ strings via merged map.
    out_lines = []
    for s in streams:
        if b"Tj" not in s and b"TJ" not in s:
            continue
        txt = s.decode("latin-1", "replace")
        buf = []
        for hexm in re.finditer(r"<([0-9A-Fa-f]+)>", txt):
            h = hexm.group(1)
            if len(h) % 4 != 0:
                continue
            for i in range(0, len(h), 4):
                cid = int(h[i:i + 4], 16)
                buf.append(merged.get(cid, ""))
        line = "".join(buf)
        if line.strip():
            out_lines.append(line)
    return "\n".join(out_lines)


if __name__ == "__main__":
    txt = extract(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if out:
        Path(out).write_text(txt, encoding="utf-8")
        print(f"wrote {len(txt)} chars to {out}")
    else:
        print(txt[:5000])
