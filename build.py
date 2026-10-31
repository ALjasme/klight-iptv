#!/usr/bin/env python3
import re
import sys
import urllib.request

SOURCES = [
    ("kw", "https://iptv-org.github.io/iptv/countries/kw.m3u"),
    ("ara", "https://iptv-org.github.io/iptv/languages/ara.m3u"),
    ("xumo", "https://www.apsattv.com/xumo.m3u"),
    ("freetv", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"),
]
OUTPUT = "playlist.m3u"
# A short list means a source broke; failing keeps yesterday's published file.
MIN_CHANNELS = {"kw": 5, "ara": 200, "xumo": 200, "freetv": 1000}

KUWAIT = "الكويت"
NEWS = "أخبار"
SPORTS = "رياضة"
RELIGIOUS = "دينية"
KIDS = "أطفال"
MOVIES = "أفلام"
DRAMA = "مسلسلات ودراما"
LEARNING = "وثائقيات وتعليم"
MUSIC = "موسيقى"
ENTERTAINMENT = "ترفيه"
LIFESTYLE = "طبخ وأسلوب حياة"
GENERAL = "قنوات عامة"
OTHER = "منوعات"
ORDER = [KUWAIT, NEWS, SPORTS, RELIGIOUS, KIDS, MOVIES, DRAMA, LEARNING, MUSIC,
         ENTERTAINMENT, LIFESTYLE, GENERAL, OTHER]

# Checked in this order, so a "Kids;Religious" channel lands in Kids.
IPTV_ORG = [
    ("kids", KIDS), ("animation", KIDS), ("sports", SPORTS), ("religious", RELIGIOUS),
    ("news", NEWS), ("business", NEWS), ("weather", NEWS), ("movies", MOVIES),
    ("classic", MOVIES), ("series", DRAMA), ("documentary", LEARNING),
    ("education", LEARNING), ("science", LEARNING), ("culture", LEARNING),
    ("music", MUSIC), ("cooking", LIFESTYLE), ("lifestyle", LIFESTYLE), ("travel", LIFESTYLE),
    ("comedy", ENTERTAINMENT), ("entertainment", ENTERTAINMENT), ("family", ENTERTAINMENT),
    ("general", GENERAL),
]
XUMO = {
    "local news": NEWS, "news": NEWS, "sports": SPORTS, "combat sports": SPORTS,
    "kids": KIDS, "movies": MOVIES, "crime tv": DRAMA, "action & drama": DRAMA,
    "horror & sci-fi": DRAMA, "classic tv": DRAMA, "westerns & country": DRAMA,
    "animals & nature": LEARNING, "history & learning": LEARNING, "music & radio": MUSIC,
    "home & design": LIFESTYLE, "food": LIFESTYLE, "travel & lifestyle": LIFESTYLE,
    "automotive": LIFESTYLE, "reality tv": ENTERTAINMENT, "comedy": ENTERTAINMENT,
    "game shows": ENTERTAINMENT, "pop culture": ENTERTAINMENT, "daytime tv": ENTERTAINMENT,
    "black voices. black stories.": ENTERTAINMENT, "latino": ENTERTAINMENT,
    "faith & family": ENTERTAINMENT,
}
# Free-TV groups by country, and most of its Arab links failed from Kuwait,
# so only channels checked to play are kept.
FREE_TV = {
    "Huda TV": RELIGIOUS,
    "Qatar Television The Holy Quran": RELIGIOUS,
    "MBC Persia": GENERAL,
}


def category(source, group, name):
    if source == "kw":
        return KUWAIT
    if source == "freetv":
        return FREE_TV[name]
    if source == "xumo":
        return XUMO.get(group.split(":", 1)[-1].strip().lower(), OTHER)
    tokens = {t.strip().lower() for t in group.split(";")}
    return next((name for key, name in IPTV_ORG if key in tokens), OTHER)


def parse(text):
    channels, info, options = [], None, []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            info, options = line, []
        elif info and line.startswith("#"):
            options.append(line)
        elif info and line.startswith("http"):
            channels.append({"info": info, "options": options, "url": line})
            info = None
    return channels


def attribute(info, key):
    match = re.search(key + r'="([^"]*)"', info)
    return match.group(1) if match else ""


def channel_name(channel):
    return channel["info"].rsplit(",", 1)[-1].strip()


def with_group(info, group):
    if 'group-title="' in info:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', info)
    return info.replace(",", f' group-title="{group}",', 1)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def main():
    seen_urls, seen_ids, channels = set(), set(), []
    for rank, (source, url) in enumerate(SOURCES):
        parsed = parse(fetch(url))
        if len(parsed) < MIN_CHANNELS[source]:
            sys.exit(f"{source}: only {len(parsed)} channels; keeping the previous playlist")
        if source == "freetv":
            parsed = [channel for channel in parsed if channel_name(channel) in FREE_TV]
        for channel in parsed:
            tvg_id = attribute(channel["info"], "tvg-id").lower()
            if channel["url"] in seen_urls or (tvg_id and tvg_id in seen_ids):
                continue
            seen_urls.add(channel["url"])
            if tvg_id:
                seen_ids.update((tvg_id, tvg_id.split("@")[0]))
            name = channel_name(channel)
            channel.update(rank=rank, name=name, category=category(source, attribute(channel["info"], "group-title"), name))
            channels.append(channel)

    channels.sort(key=lambda c: (ORDER.index(c["category"]), c["rank"], c["name"].lower()))
    lines = ["#EXTM3U"]
    for channel in channels:
        lines.append(with_group(channel["info"], channel["category"]))
        lines.extend(channel["options"])
        lines.append(channel["url"])
    with open(OUTPUT, "w", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")

    print(f"{len(channels)} channels")
    for name in ORDER:
        print(f"{sum(c['category'] == name for c in channels):4d}  {name}")


if __name__ == "__main__":
    main()
