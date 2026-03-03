import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from flask import Flask, request, render_template_string

app = Flask(__name__)

DATA_DIR = Path(__file__).resolve().parent
FILE_MAP: Dict[str, Path] = {
    "felines": DATA_DIR / "felines.txt",
    "classes": DATA_DIR / "dnd_classes.txt",
    "locations": DATA_DIR / "dnd_locations.txt",
    "deities": DATA_DIR / "dnd_deities.txt",
    "planes": DATA_DIR / "dnd_planes.txt",
}
MAX_BATCH_SIZE = 25
LETTER_REGEX = re.compile(r"[A-Za-z]")


def _read_term_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing term file: {path.name}")
    with path.open("r", encoding="utf-8") as fp:
        return [line.strip() for line in fp if line.strip() and not line.strip().startswith("#")]


def _load_sources(file_map: Dict[str, Path]) -> Dict[str, List[str]]:
    term_sources = {key: _read_term_file(path) for key, path in file_map.items()}
    if any(not values for values in term_sources.values()):
        raise ValueError("Term files must not be empty.")
    return term_sources


def _initial_letter(term: str) -> Optional[str]:
    normalized = term.strip()
    match = LETTER_REGEX.search(normalized)
    if not match:
        return None
    return match.group(0).lower()


def _group_by_initial(values: List[str]) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = {}
    for value in values:
        letter = _initial_letter(value)
        if not letter:
            continue
        grouped.setdefault(letter, []).append(value)
    return grouped


@dataclass(frozen=True)
class StyleRule:
    label: str
    source_key: str
    render_template: str


STYLE_RULES: Dict[str, StyleRule] = {
    "class": StyleRule("Class", "classes", "{feline} the {second}"),
    "location": StyleRule("Location", "locations", "{feline} of {second}"),
    "plane": StyleRule("Plane", "planes", "{feline} of {second}"),
    "deity": StyleRule("Deity", "deities", "{feline} of {second}"),
}
SUPPORTED_STYLES = tuple(STYLE_RULES.keys())


class CodenameGenerator:
    def __init__(self, sources: Dict[str, List[str]], style_rules: Dict[str, StyleRule]):
        self.sources = sources
        self.style_rules = style_rules
        self.felines_by_initial = _group_by_initial(self.sources["felines"])
        self.second_by_style_initial = self._build_second_indexes()

    def _build_second_indexes(self) -> Dict[str, Dict[str, List[str]]]:
        out: Dict[str, Dict[str, List[str]]] = {}
        for style, rule in self.style_rules.items():
            out[style] = _group_by_initial(self.sources[rule.source_key])
        return out

    def _pick_style(self, style: str) -> str:
        if style in self.style_rules:
            return style
        return random.choice(SUPPORTED_STYLES)

    def _choose_matching_pair(self, style: str) -> Tuple[str, str]:
        second_by_letter = self.second_by_style_initial[style]
        feline_letters = list(self.felines_by_initial.keys())
        if not feline_letters:
            raise ValueError("No valid feline terms available.")
        available_letters = [letter for letter in feline_letters if second_by_letter.get(letter)]
        if not available_letters:
            raise ValueError("No alliterative overlap found between felines and selected style terms.")

        while True:
            letter = random.choice(feline_letters)
            second_candidates = second_by_letter.get(letter, [])
            if not second_candidates:
                continue
            feline = random.choice(self.felines_by_initial[letter])
            second = random.choice(second_candidates)
            return feline, second

    def generate_batch(self, style: str, count: int) -> Tuple[str, List[str]]:
        selected_style = self._pick_style(style)
        rule = self.style_rules[selected_style]
        results = []
        for _ in range(count):
            feline, second = self._choose_matching_pair(selected_style)
            results.append(rule.render_template.format(feline=feline, second=second))
        return selected_style, results


GENERATOR = CodenameGenerator(_load_sources(FILE_MAP), STYLE_RULES)

def generate_batch(style: str, count: int) -> Tuple[str, List[str]]:
    return GENERATOR.generate_batch(style, count)


def get_template(p: str) -> str:
    with open(p, "r", encoding="utf-8") as fp:
        content = fp.read()
    return content

@app.route("/", methods=["GET", "POST"])
def home():
    result: List[str] = []
    style_label = ""
    error = ""
    if request.method == "POST":
        try:
            style = request.form.get("style", "random")
            count = int(request.form.get("count", "1"))
            count = max(1, min(count, MAX_BATCH_SIZE))
            selected_style, result = generate_batch(style, count)
            style_label = STYLE_RULES[selected_style].label
        except Exception as exc:
            error = str(exc)
    return render_template_string(
        get_template("home_template.html"),
        result=result,
        style_label=style_label,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=False)
