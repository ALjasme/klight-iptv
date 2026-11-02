#!/usr/bin/env python3
import re
import sys
import urllib.request

SOURCES = [
    ("kw", "https://iptv-org.github.io/iptv/countries/kw.m3u"),
    ("ara", "https://iptv-org.github.io/iptv/languages/ara.m3u"),
] + [
    ("country", f"https://iptv-org.github.io/iptv/countries/{country}.m3u")
    for country in ("sa", "iq", "dz")
] + [
    ("xumo", "https://www.apsattv.com/xumo.m3u"),
    ("freetv", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"),
] + [
    ("world", f"https://raw.githubusercontent.com/Romaxa55/world_ip_tv/master/output/{country}.m3u")
    for country in ("iq", "ae", "lb", "ma", "sa")
]
OUTPUT = "playlist.m3u"
# Stream addresses that failed from Kuwait. A source that moves a channel to a new address brings it back.
UNPLAYABLE = "unplayable.txt"
GUIDE = "https://raw.githubusercontent.com/ALjasme/klight-iptv/guide/guide.xml.gz"
# A short list means a source broke; failing keeps yesterday's published file.
MIN_CHANNELS = {"kw": 5, "ara": 200, "country": 1, "xumo": 200, "freetv": 1000, "world": 1}

KUWAIT = "الكويت"
NEWS = "أخبار"
SPORTS = "رياضة"
RELIGIOUS = "دينية"
KIDS = "أطفال"
MOVIES = "أفلام"
DRAMA = "مسلسلات ودراما"
LEARNING = "وثائقيات وتعليم"
MUSIC = "موسيقى"
RADIO = "إذاعات"
ENTERTAINMENT = "ترفيه"
LIFESTYLE = "طبخ وأسلوب حياة"
GENERAL = "قنوات عامة"
OTHER = "منوعات"
ARABIC_ORDER = [KUWAIT, GENERAL, NEWS, SPORTS, RELIGIOUS, KIDS, MOVIES, DRAMA, LEARNING, MUSIC, RADIO,
                ENTERTAINMENT, LIFESTYLE, OTHER]
INTERNATIONAL = "عالمي - "
INTERNATIONAL_ORDER = [NEWS, SPORTS, KIDS, MOVIES, DRAMA, LEARNING, MUSIC, ENTERTAINMENT, LIFESTYLE, OTHER]
ORDER = ARABIC_ORDER + [INTERNATIONAL + name for name in INTERNATIONAL_ORDER]

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
# These sources group by country and carry much that is dead or paid, so only
# channels checked to play from Kuwait are kept, without their quality tags.
CHECKED = {
    "freetv": {
        "Huda TV": RELIGIOUS,
        "Qatar Television The Holy Quran": RELIGIOUS,
        "MBC Persia": GENERAL,
    },
    "world": {
        "Afarin Baxcha": GENERAL,
        "Afarin TV": GENERAL,
        "Al Arabiya English": NEWS,
        "Al Iraqia Kurdish": GENERAL,
        "Avar TV": GENERAL,
        "CNN News 18": NEWS,
        "FarmodaTV": GENERAL,
        "Imam Hussein TV 1": RELIGIOUS,
        "Imam Hussein TV 3": RELIGIOUS,
        "Imam Hussein TV 4": RELIGIOUS,
        "Imam Hussein TV 5": RELIGIOUS,
        "Imam Hussein TV 6": RELIGIOUS,
        "Kurd Channel": GENERAL,
        "Kurdistan 24": NEWS,
        "Marjaeyat TV English": RELIGIOUS,
        "Marjaeyat TV Persian": RELIGIOUS,
        "Medi1TV Afrique": NEWS,
        "Mixkurdy": GENERAL,
        "Nour TV": GENERAL,
        "Noursat English": RELIGIOUS,
        "Payam TV": GENERAL,
        "Rudaw TV": NEWS,
        "Waar TV": GENERAL,
    },
}
# Sources file these under the wrong field, or under none.
RECATEGORIZED = {
    "Al Saudiya Alaan": GENERAL,
    "Jordan Archive": GENERAL,
    "Sharjah 2": GENERAL,
    "Sharjah TV": GENERAL,
    "Sudan TV": GENERAL,
    "UTV": GENERAL,
    "Wattan TV": GENERAL,
    "Yemen Today TV": GENERAL,
    "Sat 7 Arabic": RELIGIOUS,
    "Takbeer TV": RELIGIOUS,
    "MBC Bollywood": MOVIES,
    "Jordan Drama": DRAMA,
    "MBC Drama": DRAMA,
    "MBC+ Drama": DRAMA,
    "Nile Drama": DRAMA,
    "Rotana Clip": MUSIC,
    "Rotana Tarab Jordan City View": MUSIC,
    "Jordan Tourism": LIFESTYLE,
    "Master Chefs Academy TV": LIFESTYLE,
}
# The best-known channels open each field; the rest follow by source, then by name.
PINNED = {
    KUWAIT: ["KTV 1", "KTV 2", "KTV News", "KTV Sport", "KTV Sport Plus", "KTV Arabe", "KTV Ethraa",
             "KTV Al Qurain", "Marina TV", "Ritmu TV", "Ch4Teen Documentary"],
    GENERAL: ["MBC 1", "Al Saudiya", "SBC", "Al Rayyan TV", "Qatar Television", "Qatar Television 2", "Oman TV",
              "Bahrain TV", "Bahrain International", "Sharjah TV", "Ajman TV", "MBC Masr", "MBC Masr 2", "MBC Iraq",
              "Al Sharqiya", "Al Iraqia", "Jordan TV", "Roya TV", "LBC", "LBC International", "Al Jadeed",
              "MTV Lebanon", "Al Masriyah", "2M", "Al Maghribia"],
    NEWS: ["Al Jazeera", "Alarabiya", "Al Hadath", "Sky News Arabia", "Asharq News", "BBC Arabic", "Al Ekhbariya",
           "Al Jazeera Mubasher", "Al Arabiya Business", "CNBC Arabiya", "France 24 Arabic", "DW Arabic", "RT Arabic",
           "Al Araby TV", "Al Ghad TV", "TRT Arabi"],
    SPORTS: ["Oman Sports TV", "Bahrain Sports 1", "Bahrain Sports 2", "Al Iraqia Sport", "Jordan Sport", "Arryadia"],
    RELIGIOUS: ["Al Quran Al Kareem TV", "Qatar TV The Holy Quran", "Qatar Television The Holy Quran", "Bahrain Quran",
                "Alquran", "Iqraa Quran", "Iqraa Arabic", "Al Sunnah Al Nabawiyah TV", "Makkah TV", "Al Resalah",
                "Huda TV", "Holy Quran Radio", "Sharjah Radio Quran"],
    KIDS: ["Spacetoon Arabic", "MBC 3 USA", "Cartoon Network Arabic", "Koogi TV", "Taha TV", "Atfal & Mawaheb TV"],
    MOVIES: ["Rotana Cinema KSA", "Rotana Cinema Egypt", "Rotana Classic", "MBC Bollywood", "Aflam", "Thikrayat TV"],
    DRAMA: ["MBC Drama", "MBC Drama USA", "MBC Masr Drama", "MBC+ Drama", "Rotana Drama", "Bab Al Hara", "Maraya",
            "Jordan Drama", "Nile Drama"],
    LEARNING: ["Al Jazeera Documentary", "Asharq Documentary", "Asharq Discovery", "Saudi Thaqafiya TV",
               "Oman TV Cultural"],
    MUSIC: ["Rotana Khalijia", "Rotana Music", "Rotana Clip", "Mazzika", "MBC Mood", "Tarab", "Mohammed Abdo",
            "Abdulmajeed Abdullah", "Rashid AlMajed", "Rabeh Saqer", "Majid Al Mohandis", "Fairuz"],
    ENTERTAINMENT: ["MBC 4", "MBC 5", "Rotana Comedy", "Hya TV", "Jordan Comedy"],
}


def category(source, group, name):
    if source == "kw":
        return KUWAIT
    if source == "xumo":
        return INTERNATIONAL + XUMO.get(group.split(":", 1)[-1].strip().lower(), OTHER)
    bare = bare_name(name)
    if bare in RECATEGORIZED:
        return RECATEGORIZED[bare]
    if source in CHECKED:
        field = CHECKED[source][bare]
    else:
        tokens = {t.strip().lower() for t in group.split(";")}
        field = next((name for key, name in IPTV_ORG if key in tokens), OTHER)
    if field != RELIGIOUS and re.search(r"radio|fm\b", bare, re.I):
        return RADIO
    return field


def pin_rank(channel):
    pinned = PINNED.get(channel["category"], [])
    bare = bare_name(channel["name"])
    return pinned.index(bare) if bare in pinned else len(pinned)


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


def bare_name(name):
    return re.sub(r"\s*(\(.*?\)|\[.*?\])", "", name).strip()


def clean_name(name):
    return re.sub(r"\s*(\(\d+[pi]\)|\[.*?\])", "", name).strip()


def with_group(info, group):
    if 'group-title="' in info:
        return re.sub(r'group-title="[^"]*"', f'group-title="{group}"', info)
    return info.replace(",", f' group-title="{group}",', 1)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def main():
    with open(UNPLAYABLE, encoding="utf-8") as unplayable:
        seen_urls = set(unplayable.read().split())
    seen_ids, channels = set(), []
    for rank, (source, url) in enumerate(SOURCES):
        parsed = parse(fetch(url))
        if len(parsed) < MIN_CHANNELS[source]:
            sys.exit(f"{source}: only {len(parsed)} channels; keeping the previous playlist")
        if source in CHECKED:
            parsed = [channel for channel in parsed if bare_name(channel_name(channel)) in CHECKED[source]]
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

    channels.sort(key=lambda c: (ORDER.index(c["category"]), pin_rank(c), c["rank"], c["name"].lower()))
    lines = [f'#EXTM3U x-tvg-url="{GUIDE}"']
    for channel in channels:
        info = channel["info"].rsplit(",", 1)[0]
        lines.append(with_group(f'{info},{clean_name(channel["name"])}', channel["category"]))
        lines.extend(channel["options"])
        lines.append(channel["url"])
    with open(OUTPUT, "w", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")

    print(f"{len(channels)} channels")
    for name in ORDER:
        print(f"{sum(c['category'] == name for c in channels):4d}  {name}")


if __name__ == "__main__":
    main()
