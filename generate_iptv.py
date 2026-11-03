#!/usr/bin/env python3
import os
import re
import sys
from urllib import request

SOURCE_URL = os.environ.get(
    "IPTV_SOURCE_URL",
    "https://ua.fongmi.eu.org/box.php?url=https://iptv.yang-1989.xyz/playlist.m3u",
)
OUTPUT_PATH = os.environ.get("IPTV_OUTPUT_PATH", "iptv.txt")

def fetch_text(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/vnd.apple.mpegurl,text/plain,*/*",
    }
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")

def sanitize_group(value: str) -> str:
    v = (value or "其他").strip()
    return v if v else "其他"

def parse_extinf_attrs(line: str) -> dict:
    attrs = {}
    for key, value in re.findall(r'([A-Za-z0-9_-]+)\s*=\s*(".*?"|\'.*?\'|[^\\s]+)', line):
        val = value.strip().strip('"').strip("'")
        if val:
            attrs[key] = val
    return attrs

def normalize_line(line: str) -> str:
    line = line.strip()
    if not line.startswith("#EXTINF"):
        return line

    attrs = parse_extinf_attrs(line)
    group_title = (
        attrs.get("group-title")
        or attrs.get("tvg-group")
        or attrs.get("group")
        or attrs.get("genre")
        or "其他"
    )
    genre = sanitize_group(group_title)

    title = ""
    if "," in line:
        title = line.rsplit(",", 1)[-1].strip()
    if not title:
        title = attrs.get("tvg-name") or attrs.get("tvg-id") or "未知频道"

    tvg_id = attrs.get("tvg-id", "")
    tvg_name = attrs.get("tvg-name", title)
    tvg_logo = attrs.get("tvg-logo", "")
    tvg_chno = attrs.get("tvg-chno", "")
    radio = attrs.get("radio", "")
    http_referrer = attrs.get("http-referrer", "")
    http_user_agent = attrs.get("http-user-agent", "")

    parts = ["#EXTINF:-1"]
    if tvg_id:
        parts.append(f'tvg-id="{tvg_id}"')
    if tvg_name:
        parts.append(f'tvg-name="{tvg_name}"')
    if tvg_logo:
        parts.append(f'tvg-logo="{tvg_logo}"')
    if tvg_chno:
        parts.append(f'tvg-chno="{tvg_chno}"')
    if radio:
        parts.append(f'radio="{radio}"')
    if http_referrer:
        parts.append(f'http-referrer="{http_referrer}"')
    if http_user_agent:
        parts.append(f'http-user-agent="{http_user_agent}"')
    parts.append(f'group-title="{sanitize_group(group_title)}"')
    parts.append(f'genre="{genre}"')
    parts.append(f",{title}")
    return " ".join(parts)

def generate_playlist(raw: str) -> str:
    lines = raw.splitlines()
    out = ["#EXTM3U"]
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#EXTINF"):
            out.append(normalize_line(s))
            continue
        if s.startswith(("http://", "https://", "rtmp://", "rtsp://")):
            out.append(s)
    return "\n".join(out) + "\n"

def main():
    try:
        raw = fetch_text(SOURCE_URL)
    except Exception as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n#EXTINF:-1 group-title=\"其他\" genre=\"其他\",Source unavailable\n")
        raise SystemExit(1)

    playlist = generate_playlist(raw)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(playlist)
    print(f"Saved IPTV playlist to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
