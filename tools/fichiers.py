#!/usr/bin/env python3
"""Copie dans le dépôt les fichiers liés (plans, images, codes .txt) qui ne sont pas
déjà repris par tools/images.py, et écrit contenu/fichiers.json.

Usage : python3 -I tools/fichiers.py CHEMIN/racine-des-sources LISTE.txt
(LISTE : un chemin d'origine par ligne, relatif à la racine)
"""
import json, posixpath, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from images import find_file, out_name, save

ROOT = Path(__file__).resolve().parent.parent
src_root = Path(sys.argv[1]).resolve()
out = {}
for rel in Path(sys.argv[2]).read_text().split("\n"):
    rel = rel.strip()
    if not rel:
        continue
    f = find_file(src_root, rel)
    if not f:
        continue
    key = f.relative_to(src_root).as_posix().lower()
    dest = out_name(key)
    if not dest.endswith((".jpg", ".gif", ".png")):
        dest = "fichiers/" + dest[len("images/"):]
    save(f, ROOT / dest)
    out[key] = dest
(ROOT / "contenu" / "fichiers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(len(out), "fichiers")
