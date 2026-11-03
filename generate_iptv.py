#!/usr/bin/env python3
import os
import re
import sys
from collections import defaultdict
from urllib import request

SOURCE_URL = os.environ.get("IPTV_SOURCE_URL", "http://migu.lengye.top/interfaceTXT.txt")
OUTPUT_PATH = os.environ.get("IPTV_OUTPUT_PATH", "iptv.txt")

URL_PREFIXES = ("http://", "https://", "rtmp://", "rtsp://")
PROVINCES = (
    "黑龙江", "内蒙古", "宁夏", "新疆", "广西", "西藏", "香港", "澳门",
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北",
    "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃",
    "青海", "台湾",
)

def fetch_text(url: str) -> str:
    req = request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; IPTV playlist updater)",
            "Accept": "text/plain,*/*",
        },
    )
    with request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8-sig", errors="replace")

def clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace(",", " ").strip())

def province_for(*hints: str) -> str:
    text = " ".join(hints)
    for province in PROVINCES:
        if province in text:
            return province
    return "其他"

def parse_extinf_title(line: str) -> str:
    title = line.rsplit(",", 1)[-1].strip()
    if title:
        return clean_name(title)
    match = re.search(r'tvg-name\s*=\s*["\']([^"\']+)["\']', line, re.I)
    return clean_name(match.group(1)) if match else "未知频道"

def generate_playlist(raw: str) -> str:
    groups = defaultdict(list)
    seen = set()
    source_group = ""
    pending_name = ""

    def add_channel(name: str, url: str) -> None:
        name = clean_name(name)
        url = url.strip()
        if not name or not url.lower().startswith(URL_PREFIXES):
            return
        province = province_for(source_group, name)
        item = (name, url)
        if item not in seen:
            groups[province].append(item)
            seen.add(item)

    for raw_line in raw.splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue

        # 例：上海,#genre#
        category = re.fullmatch(r"([^,]+?)\s*,\s*#genre#", line, re.I)
        if category:
            source_group = category.group(1).strip()
            pending_name = ""
            continue

        if line.startswith("#EXTINF"):
            pending_name = parse_extinf_title(line)
            group = re.search(r'group-title\s*=\s*["\']([^"\']+)["\']', line, re.I)
            if group:
                source_group = group.group(1).strip()
            continue

        if line.startswith("#"):
            continue

        if line.lower().startswith(URL_PREFIXES):
            if pending_name:
                add_channel(pending_name, line)
                pending_name = ""
            continue

        name, separator, url = line.partition(",")
        if separator and url.strip().lower().startswith(URL_PREFIXES):
            add_channel(name, url)
            pending_name = ""

    output = []
    for province in (*PROVINCES, "其他"):
        channels = groups.get(province)
        if channels:
            output.append(f"{province},#genre#")
            output.extend(f"{name},{url}" for name, url in channels)

    if not output:
        raise ValueError("No valid channel name/URL entries found in source")

    return "\n".join(output) + "\n"

def main():
    try:
        playlist = generate_playlist(fetch_text(SOURCE_URL))
    except Exception as error:
        print(f"Failed to update playlist: {error}", file=sys.stderr)
        raise SystemExit(1)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(playlist)
    print(f"Saved IPTV playlist to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
