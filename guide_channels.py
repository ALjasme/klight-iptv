#!/usr/bin/env python3
"""Write an iptv-org/epg channels file for the channels in playlist.m3u that have a guide."""
import json
import re
import sys
import urllib.request
from xml.sax.saxutils import escape, quoteattr

GUIDES = "https://iptv-org.github.io/api/guides.json"
PLAYLIST = "playlist.m3u"


def main(output):
    request = urllib.request.Request(GUIDES, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        guides = json.load(response)

    by_channel = {}
    for guide in guides:
        if guide.get("channel"):
            by_channel.setdefault(guide["channel"].lower(), []).append(guide)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<channels>"]
    with open(PLAYLIST, encoding="utf-8") as playlist:
        ids = re.findall(r'^#EXTINF.*?tvg-id="([^"]+)"', playlist.read(), re.M)
    for tvg_id in sorted(set(ids)):
        options = by_channel.get(tvg_id.split("@")[0].lower())
        if not options:
            continue
        # Arabic listings first; the id must stay exactly as the playlist spells it.
        guide = max(options, key=lambda g: g["lang"] == "ar")
        lines.append(
            f'  <channel site={quoteattr(guide["site"])} lang={quoteattr(guide["lang"])} '
            f'xmltv_id={quoteattr(tvg_id)} site_id={quoteattr(guide["site_id"])}>'
            f'{escape(guide["site_name"])}</channel>'
        )
    lines.append("</channels>")
    with open(output, "w", encoding="utf-8") as channels:
        channels.write("\n".join(lines) + "\n")
    print(f"{len(lines) - 3} channels with a guide")


if __name__ == "__main__":
    main(sys.argv[1])
