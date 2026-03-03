from pathlib import Path
from typing import Dict, List


DATA: Dict[str, List[str]] = {
    "dnd_classes.txt": [
        "Wizard",
        "Warlock",
        "Paladin",
        "Cleric",
        "Rogue",
        "Bard",
        "Sorcerer",
        "Ranger",
        "Druid",
        "Monk",
        "Fighter",
        "Barbarian",
        "Alchemist",
        "Oracle",
        "Inquisitor",
        "Magus",
    ],
    "dnd_locations.txt": [
        "Waterdeep",
        "Neverwinter",
        "Baldur's Gate",
        "Candlekeep",
        "Absalom",
        "Cheliax",
        "Varisia",
        "Ustalav",
        "Nirmathas",
        "Galt",
        "Korvosa",
        "Taldor",
        "Irrisen",
    ],
    "dnd_deities.txt": [
        "Mystra",
        "Tiamat",
        "Bahamut",
        "Lolth",
        "Shar",
        "Desna",
        "Abadar",
        "Nethys",
        "Pharasma",
        "Iomedae",
        "Sarenrae",
        "Cayden Cailean",
    ],
    "dnd_planes.txt": [
        "the Feywild",
        "the Shadowfell",
        "the Abyss",
        "the Nine Hells",
        "Mechanus",
        "Elysium",
        "Arborea",
        "Axis",
    ],
}


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    for filename, terms in DATA.items():
        path = base_dir / filename
        path.write_text("\n".join(terms) + "\n", encoding="utf-8")
        print(f"Wrote {path.name} ({len(terms)} terms)")
    print("Skipped felines.txt. Use fetch_felines_from_wikipedia.py for feline names.")


if __name__ == "__main__":
    main()
