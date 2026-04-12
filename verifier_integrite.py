"""Verifie que les fichiers de VoixClaire n'ont pas ete modifies."""

import hashlib
import json
import os
import sys
from pathlib import Path


def hash_file(filepath: Path) -> str:
    """Calcule le SHA-256 d'un fichier."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def generate_hashes(app_dir: Path) -> dict:
    """Genere les hashes de tous les fichiers Python."""
    hashes = {}
    for py_file in sorted(app_dir.rglob("*.py")):
        rel_path = py_file.relative_to(app_dir)
        hashes[str(rel_path)] = hash_file(py_file)
    return hashes


def save_hashes(app_dir: Path, output_path: Path):
    """Sauvegarde les hashes (a faire apres le build)."""
    hashes = generate_hashes(app_dir)
    with open(output_path, 'w') as f:
        json.dump(hashes, f, indent=2)
    print(f"Hashes sauvegardes: {output_path}")
    print(f"  {len(hashes)} fichiers verifies")


def verify_hashes(app_dir: Path, hash_file_path: Path) -> bool:
    """Verifie l'integrite des fichiers."""
    if not hash_file_path.exists():
        print("[!] Fichier de verification absent.")
        print("    Impossible de verifier l'integrite.")
        return False

    with open(hash_file_path, 'r') as f:
        expected = json.load(f)

    current = generate_hashes(app_dir)
    ok = True

    for filename, expected_hash in expected.items():
        current_hash = current.get(filename)
        if current_hash is None:
            print(f"  [MANQUANT] {filename}")
            ok = False
        elif current_hash != expected_hash:
            print(f"  [MODIFIE]  {filename}")
            ok = False

    for filename in current:
        if filename not in expected:
            print(f"  [AJOUTE]   {filename}")
            ok = False

    if ok:
        print(f"  [OK] Tous les {len(expected)} fichiers sont intacts.")
    else:
        print("\n  [!] ATTENTION: Des fichiers ont ete modifies !")
        print("      Le logiciel a peut-etre ete altere.")

    return ok


if __name__ == '__main__':
    script_dir = Path(__file__).resolve().parent

    if len(sys.argv) > 1 and sys.argv[1] == '--generate':
        # Mode generation (apres le build)
        app_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else script_dir
        save_hashes(app_dir, app_dir / "integrity.json")
    else:
        # Mode verification
        app_dir = script_dir
        verify_hashes(app_dir, app_dir / "integrity.json")
