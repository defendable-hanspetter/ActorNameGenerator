import argparse
import json
import re
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

USER_AGENT = "ActorNameGenerator/1.0 (bootstrap dnd terms)"
BASE_DIR = Path(__file__).resolve().parent

DND5E_API_CLASSES = "https://www.dnd5eapi.co/api/classes"
MEDIAWIKI_SOURCES = {
    "forgotten_realms": "https://forgottenrealms.fandom.com/api.php",
    "pathfinder": "https://pathfinderwiki.com/w/api.php",
}

CATEGORY_MAP = {
    "locations": ["Category:Cities", "Category:Nations", "Category:Regions"],
    "deities": ["Category:Deities"],
    "planes": ["Category:Planes"],
}

OUTPUT_FILES = {
    "classes": BASE_DIR / "dnd_classes.txt",
    "locations": BASE_DIR / "dnd_locations.txt",
    "deities": BASE_DIR / "dnd_deities.txt",
    "planes": BASE_DIR / "dnd_planes.txt",
}

LOWERCASE_CONNECTORS = {"of", "the", "and", "in", "de", "la", "le", "van", "von"}
REJECT_SUBSTRINGS = {
    "list of",
    "category:",
    "template:",
    "file:",
    "module:",
    "talk:",
    "disambiguation",
}


def _api_get(url: str, params: Dict[str, str]) -> Dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _fetch_5e_classes() -> List[str]:
    request = urllib.request.Request(
        DND5E_API_CLASSES,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    names = [entry.get("name", "").strip() for entry in payload.get("results", [])]
    return [name for name in names if name]


def _normalize_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
    title = re.sub(r"\s+", " ", title).strip(" -,:;")
    return title


def _is_valid_term(title: str) -> bool:
    if not title:
        return False
    title_cf = title.casefold()
    if any(marker in title_cf for marker in REJECT_SUBSTRINGS):
        return False
    if ":" in title or "/" in title:
        return False

    words = title.split()
    if len(words) > 6:
        return False

    for word in words:
        if word.casefold() in LOWERCASE_CONNECTORS:
            continue
        if not word[0].isupper():
            return False

    return any(ch.isalpha() for ch in title)


def _fetch_category_members(api_url: str, category: str) -> List[Dict]:
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
        payload = _api_get(api_url, params)
        members.extend(payload.get("query", {}).get("categorymembers", []))
        cmcontinue = payload.get("continue", {}).get("cmcontinue", "")
        if not cmcontinue:
            return members


def _fetch_from_mediawiki(api_url: str, category_roots: Iterable[str], max_depth: int) -> Set[str]:
    found: Dict[str, str] = {}
    visited_categories: Set[str] = set()
    queue = deque((root, 0) for root in category_roots)

    while queue:
        category, depth = queue.popleft()
        if category in visited_categories:
            continue
        visited_categories.add(category)

        for member in _fetch_category_members(api_url, category):
            ns = member.get("ns")
            title = member.get("title", "")
            if ns == 14:
                if depth < max_depth:
                    queue.append((title, depth + 1))
                continue
            if ns != 0:
                continue
            cleaned = _normalize_title(title)
            if not _is_valid_term(cleaned):
                continue
            found.setdefault(cleaned.casefold(), cleaned)

    return set(found.values())


def _read_existing(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as fp:
        return {line.strip() for line in fp if line.strip()}


def _write_terms(path: Path, terms: Set[str], dry_run: bool) -> None:
    ordered = sorted(terms, key=lambda value: value.casefold())
    if dry_run:
        print(f"[dry-run] {path.name}: {len(ordered)} terms")
        return
    path.write_text("\n".join(ordered) + "\n", encoding="utf-8")
    print(f"Wrote {path.name}: {len(ordered)} terms")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap dnd_*.txt files from online APIs/wikis."
    )
    parser.add_argument("--max-depth", type=int, default=1, help="Category recursion depth (default: 1)")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace local files instead of merging with existing terms.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show counts only.")
    args = parser.parse_args()

    if args.max_depth < 0:
        raise ValueError("--max-depth must be >= 0")

    classes = set(_fetch_5e_classes())

    locations: Set[str] = set()
    deities: Set[str] = set()
    planes: Set[str] = set()
    for api_url in MEDIAWIKI_SOURCES.values():
        locations |= _fetch_from_mediawiki(api_url, CATEGORY_MAP["locations"], args.max_depth)
        deities |= _fetch_from_mediawiki(api_url, CATEGORY_MAP["deities"], args.max_depth)
        planes |= _fetch_from_mediawiki(api_url, CATEGORY_MAP["planes"], args.max_depth)

    fetched = {
        "classes": classes,
        "locations": locations,
        "deities": deities,
        "planes": planes,
    }

    for key, path in OUTPUT_FILES.items():
        terms = fetched[key]
        if not args.replace:
            terms |= _read_existing(path)
        _write_terms(path, terms, args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
