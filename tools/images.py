#!/usr/bin/env python3
"""Extrait les images du site d'origine et prépare leur intégration.

Usage : python3 -I tools/images.py CHEMIN/floppycheese.free.fr/nintendo

- copie les images utilisées dans images/ (dossiers sans points, noms propres) ;
- écrit contenu/images.json : pour chaque page d'origine, la liste des groupes
  d'images avec les derniers mots du texte qui les précède (pour les replacer
  au bon endroit), et les vignettes des liens vers d'autres pages.
"""
import html
import json
import os
import posixpath
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "images"
SKIP = {"banniere.png", "contact.png", "menu.png", "accueil.png"}
IMG_EXT = (".jpg", ".jpeg", ".gif", ".png")
MIN_SIDE = 40  # en dessous : puces, séparateurs, pixels transparents


def words(s):
    s = unicodedata.normalize("NFKD", html.unescape(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", s)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []        # mots lus jusqu'ici
        self.links = []       # pile des <a href>
        self.items = []       # (position dans le texte, src, alt, href du lien parent)
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "a":
            self.links.append(a.get("href") or "")
        elif tag == "img" and a.get("src"):
            href = next((h for h in reversed(self.links) if h), "")
            self.items.append((len(self.text), a["src"].strip(), (a.get("alt") or "").strip(), href.strip(),
                               a.get("width"), a.get("height")))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag == "a" and self.links:
            self.links.pop()

    def handle_data(self, data):
        if not self.skip:
            self.text.extend(words(data))


def find_file(src_root, rel):
    """Fichier réel (insensible à la casse, comme beaucoup de liens d'origine)."""
    p = src_root / rel
    if p.is_file():
        return p
    cur = src_root
    for part in Path(rel).parts:
        if not cur.is_dir():
            return None
        m = [c for c in cur.iterdir() if c.name.lower() == part.lower()]
        if not m:
            return None
        cur = m[0]
    return cur if cur.is_file() else None


def out_name(rel):
    d, f = posixpath.split(rel.lower())
    d = d.replace(".", "-")
    base, ext = posixpath.splitext(f)
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "image"
    return posixpath.join("images", d, base + (".jpg" if ext == ".jpeg" else ext))


def size_of(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def save(src, dest):
    """Copie l'image ; les JPEG trop lourds sont recompressés sans changer de taille."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    if dest.suffix == ".jpg" and len(data) > 60_000:
        try:
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert("RGB")
                im.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
            if dest.stat().st_size < len(data):
                return
        except Exception:
            pass
    dest.write_bytes(data)


def main():
    src_root = Path(sys.argv[1]).resolve()
    copied = {}

    def use(rel):
        """Chemin d'origine (relatif à la racine) → chemin publié, ou None."""
        f = find_file(src_root, rel)
        if not f:
            return None
        key = f.relative_to(src_root).as_posix()
        if key not in copied:
            copied[key] = out_name(key)
            save(f, ROOT / copied[key])
        return copied[key]

    result = {}
    for path in sorted(src_root.rglob("*")):
        if path.suffix.lower() not in (".htm", ".html") or not path.is_file():
            continue
        rel_page = path.relative_to(src_root).as_posix()
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", errors="replace")
        p = Page()
        try:
            p.feed(text)
        except Exception:
            continue
        page_dir = posixpath.dirname(rel_page)
        groups, thumbs = [], {}
        for pos, src, alt, href, w, h in p.items:
            if re.match(r"^(https?:)?//", src) or src.startswith("data:"):
                continue
            rel = posixpath.normpath(posixpath.join(page_dir, src.split("?")[0]))
            if posixpath.basename(rel).lower() in SKIP or not rel.lower().endswith(IMG_EXT):
                continue
            f = find_file(src_root, rel)
            if not f:
                continue
            dims = size_of(f)
            if dims and min(dims) < MIN_SIDE:
                continue
            target = posixpath.normpath(posixpath.join(page_dir, href.split("#")[0])) if href and not re.match(r"^(https?:|mailto:|javascript:)", href, re.I) else ""
            if target and target.lower().endswith((".htm", ".html")) or (href.endswith("/") and target):
                # vignette d'un lien vers une autre page
                thumbs.setdefault(target.lower(), use(rel))
                continue
            big = None
            if target and target.lower().endswith(IMG_EXT) and target.lower() != rel.lower():
                big = use(target)
            img = {"src": use(rel), "alt": alt if not re.fullmatch(r"\d*", alt) else "",
                   "w": dims[0] if dims else None, "h": dims[1] if dims else None, "file": posixpath.basename(rel).lower()}
            if big:
                img["big"] = big
            anchor = p.text[max(0, pos - 12):pos]
            if groups and groups[-1]["pos"] == pos:
                groups[-1]["imgs"].append(img)
            else:
                groups.append({"pos": pos, "anchor": " ".join(anchor),
                               "next": " ".join(p.text[pos:pos + 12]), "imgs": [img]})
        if groups or thumbs:
            for g in groups:
                del g["pos"]
            result[rel_page.lower()] = {"groups": groups, "thumbs": thumbs}
    (ROOT / "contenu" / "images.json").write_text(json.dumps({"pages": result, "files": {k.lower(): v for k, v in sorted(copied.items())}}, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(g["imgs"]) for v in result.values() for g in v["groups"])
    print(f"{len(result)} pages, {total} images placées, {len(copied)} fichiers copiés")


if __name__ == "__main__":
    main()
