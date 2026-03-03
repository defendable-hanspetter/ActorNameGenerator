import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path
from typing import Dict, List, Set

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
ROOT_CATEGORY = "Category:Fictional_cats"
USER_AGENT = "ActorNameGenerator/1.0 (codename fetch script; contact: local-dev)"
LOWERCASE_CONNECTORS = {"of", "the", "and", "in", "de", "la", "le", "van", "von"}
TITLE_REJECT_SUBSTRINGS = {
    "list of",
    "category:",
    "episode",
    "season",
    "comic",
    "comics",
    "manga",
    "film",
    "series",
    "television",
    "cartoon",
    "newspaper",
    "magazine",
    "novel",
    "book",
    "album",
    "song",
    "disambiguation",
    "franchise",
    "video game",
    "furry fandom",
}


def _api_get(params: Dict[str, str]) -> Dict:
    query = urllib.parse.urlencode(params)
    url = f"{WIKI_API_URL}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def _fetch_category_members(category: str) -> List[Dict]:
    members: List[Dict] = []
    cmcontinue = ""
    while True:
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "page|subcat",
            "cmlimit": "500",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        payload = _api_get(params)
        members.extend(payload.get("query", {}).get("categorymembers", []))
        cmcontinue = payload.get("continue", {}).get("cmcontinue", "")
        if not cmcontinue:
            return members


def _normalize_title(title: str) -> str:
    cleaned = title.strip()
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned)
    cleaned = re.sub(r"\bthe cats?\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip("'\" ")
    cleaned = re.sub(r"^[^A-Za-z]+", "", cleaned)
    cleaned = re.sub(r"[^A-Za-z']+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,:;")
    return cleaned


def _looks_like_name(value: str) -> bool:
    if not value:
        return False
    value_cf = value.casefold()
    if ":" in value or "/" in value:
        return False
    if any(marker in value_cf for marker in TITLE_REJECT_SUBSTRINGS):
        return False
    if any(ch.isdigit() for ch in value):
        return False
    words = value.split()
    if len(words) == 0 or len(words) > 5:
        return False
    if len(words) == 1 and words[0].casefold() in {"cat", "cats", "kitten", "feline"}:
        return False
    for word in words:
        if word.casefold() in LOWERCASE_CONNECTORS:
            continue
        if not word[0].isupper():
            return False
    return any(ch.isalpha() for ch in value)


def collect_felines(max_depth: int) -> List[str]:
    queue = deque([(ROOT_CATEGORY, 0)])
    seen_categories: Set[str] = set()
    names_by_key: Dict[str, str] = {}

    while queue:
        category, depth = queue.popleft()
        if category in seen_categories:
            continue
        seen_categories.add(category)

        for member in _fetch_category_members(category):
            ns = member.get("ns")
            title = member.get("title", "")

            if ns == 14:
                if depth < max_depth:
                    queue.append((title, depth + 1))
                continue

            if ns != 0:
                continue

            cleaned = _normalize_title(title)
            if not _looks_like_name(cleaned):
                continue

            key = cleaned.casefold()
            names_by_key.setdefault(key, cleaned)

    return sorted(names_by_key.values(), key=lambda x: x.casefold())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch feline proper nouns from Wikipedia Category:Fictional_cats."
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Subcategory traversal depth (default: 2).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "felines.txt",
        help="Output file path (default: ./felines.txt).",
    )
    args = parser.parse_args()

    if args.max_depth < 0:
        print("--max-depth must be >= 0", file=sys.stderr)
        return 2

    felines = collect_felines(max_depth=args.max_depth)
    args.output.write_text("\n".join(felines) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(felines)} names)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
