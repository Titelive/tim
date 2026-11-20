#!/usr/bin/env python3
"""Génère le site statique à partir des textes de contenu/pages-*.txt.

Format des fichiers de contenu :
  === chemin/original.htm      début d'une page (chemin sur le site d'origine)
  Titre de la page             ligne suivante
  ...                          corps en Markdown simplifié

Usage : python3 build.py   (écrit les pages HTML à la racine du dépôt)
"""
import html
import json
import os
import posixpath
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "contenu"

SECTIONS = [
    # (dossier d'origine, titre, description, jeu)
    ("presentation", "Présentations", "La découverte des jeux, le making-of, les personnages, les références aux films.", "both"),
    ("soluce", "Soluces", "Toutes les missions solo de Goldeneye et de Perfect Dark, objectif par objectif.", "both"),
    ("battle", "Multiplayer Battle", "Chaque arène décortiquée : armes, coins à connaître, camping.", "both"),
    ("cheats", "Codes", "Comment débloquer les Cheat Options les plus dures des deux jeux.", "both"),
    ("challenges", "30 Challenges", "Les 30 challenges de Perfect Dark contre les Simulants.", "pd"),
    ("beta", "Beta", "Ce qui a été retiré ou modifié avant la sortie des jeux.", "both"),
    ("mysteres", "Mystères", "Fromages, Citadel, Casino, Roswells cachés et autres bizarreries.", "both"),
    ("action.replay", "Action Replay", "Codes Gameshark : Moonjump, Debug Mode, nouveaux niveaux…", "both"),
    ("emulation", "Emulateur", "Jouer sur PC avec Project 64 et en ligne avec Mupen.", "both"),
    ("complex", "The Complex", "Des missions solo inédites créées par les fans.", "ge"),
    ("autres", "Autres Jeux", "Jet Force Gemini, Faxanadu, Rad Gravity.", "both"),
    ("liens", "Liens", "Les autres sites de Tim et les sites de référence.", "both"),
    ("contact", "Contact", "Une question sur Goldeneye ou Perfect Dark ?", "both"),
]
SECTION_TITLE = {s[0]: s[1] for s in SECTIONS}
SECTION_ALIAS = {"cinema": "presentation", "plans": "battle"}
MAIL = "tubulamarok@yahoo.fr"

# version des fichiers CSS/JS dans leurs adresses : un navigateur ne garde jamais une ancienne feuille de style
import hashlib
ASSET_V = hashlib.sha1(b"".join((ROOT / "assets" / f).read_bytes() for f in ("style.css", "site.js"))).hexdigest()[:8]

# images du site d'origine (préparées par tools/images.py)
_IMG = json.loads((SRC / "images.json").read_text(encoding="utf-8")) if (SRC / "images.json").exists() else {"pages": {}, "files": {}}
IMG_PAGES, IMG_FILES = _IMG["pages"], _IMG["files"]
IMG_FILES.update(json.loads((ROOT / "contenu" / "fichiers.json").read_text(encoding="utf-8")))


# ---------------------------------------------------------------- lecture
def read_pages():
    text = "".join(p.read_text(encoding="utf-8") for p in sorted(SRC.glob("pages-*.txt")))
    parts = re.split(r"^=== (\S+)\s*$", text, flags=re.M)
    pages = {}
    order = []
    for i in range(1, len(parts), 2):
        path = canon(parts[i])
        body = parts[i + 1].strip("\n")
        lines = body.split("\n")
        title = lines[0].strip().lstrip("#").strip()
        content = "\n".join(lines[1:]).strip("\n")
        if path not in pages:
            order.append(path)
        pages[path] = {"orig": parts[i], "title": title, "body": content}
    # pages en double : on garde la dernière version, mais à la première place
    return pages, order


def canon(p):
    """Chemin d'origine normalisé (minuscules, index.htm → dossier/)."""
    p = p.strip().lstrip("./")
    low = p.lower()
    if low.endswith("/index.htm") or low.endswith("/index.html"):
        low = low.rsplit("/", 1)[0] + "/"
    return low


def out_path(path):
    """Chemin d'origine normalisé → chemin du fichier généré.
    Les points des noms d'origine deviennent des tirets (ge.beta.01 → ge-beta-01) :
    une adresse propre qui finirait par « .01 » ou « .guns » passerait pour un fichier."""
    if path.endswith("/"):
        return path.replace(".", "-") + "index.html"
    base, _ = posixpath.splitext(path)
    return base.replace(".", "-") + ".html"


def clean(u):
    """Adresse propre : sans « index.html » ni « .html » (le serveur les retrouve)."""
    if u.endswith("index.html"):
        u = u[: -len("index.html")]
    elif u.endswith(".html") and "://" not in u:
        u = u[: -len(".html")]
    return u or "./"


def section_of(path):
    first = path.split("/", 1)[0]
    return SECTION_ALIAS.get(first, first)


def game_of(path, title):
    name = posixpath.basename(path.rstrip("/"))
    if "Perfect Dark" in title or re.match(r"(pd[-.]|pd$)", name) or "/pd/" in path:
        return "pd"
    if "Goldeneye" in title or re.match(r"(ge[-.])", name) or "/ge/" in path:
        return "ge"
    return ""


# ---------------------------------------------------------------- liens
class Linker:
    def __init__(self, pages, current):
        self.pages = pages
        self.current = current
        self.cur_out = out_path(current)

    def resolve(self, href):
        href = href.strip()
        if re.match(r"^(https?:|mailto:)", href, re.I):
            return href, True
        if href.startswith("#"):
            return href, False
        anchor = ""
        if "#" in href:
            href, anchor = href.split("#", 1)
            anchor = "#" + anchor
        base_dir = posixpath.dirname(self.current.rstrip("/") if not self.current.endswith("/") else self.current + "x")
        target = posixpath.normpath(posixpath.join(base_dir, href)) if href else self.current
        if href.endswith("/"):
            target += "/"
        key = canon(target)
        if key in self.pages:
            rel = posixpath.relpath(out_path(key), posixpath.dirname(self.cur_out) or ".")
            return clean(rel) + anchor, False
        if target.lower() in IMG_FILES:
            return self.to(IMG_FILES[target.lower()]), False
        # fichier disparu (vidéo, zip…) : pas de lien
        print("LIEN MORT", self.current, target, file=__import__("sys").stderr) if os.environ.get("DEBUG") else None
        return None, False

    def to(self, published):
        """Chemin publié (depuis la racine) → lien relatif depuis la page courante."""
        return posixpath.relpath(published, posixpath.dirname(self.cur_out) or ".")

    def image(self, name):
        """Nom d'image tel qu'écrit dans le contenu → chemin publié relatif, ou None."""
        base_dir = posixpath.dirname(self.current.rstrip("/") if not self.current.endswith("/") else self.current + "x")
        target = posixpath.normpath(posixpath.join(base_dir, name.strip())).lower()
        return self.to(IMG_FILES[target]) if target in IMG_FILES else None

    def root(self):
        depth = self.cur_out.count("/")
        return "../" * depth


# ---------------------------------------------------------------- rendu inline
def slug(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = s.lower()
    for a, b in (("àâä", "a"), ("éèêë", "e"), ("îï", "i"), ("ôö", "o"), ("ùûü", "u"), ("ç", "c")):
        for ch in a:
            s = s.replace(ch, b)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "section"


# Fichiers d'origine disparus (vidéos, sons, logiciels) : on pointe vers une source vivante.
LINK_FIX = [
    ("goldeneyesetupeditorinstaller2", "https://www.goldeneyevault.com/"),
    ("PD%20-%20Beta", "https://tcrf.net/Perfect_Dark#Unused_Music"),
    ("PD%20-%20Area%2051", "https://tcrf.net/Perfect_Dark/Unused_Content_By_Level/Area_51"),
    ("Goldeneye%20-%20Silo", "https://www.youtube.com/watch?v=VcCq4uOoI6g"),
]


def yt_cards(items):
    """Vidéos YouTube : vignette + titre ; le lecteur ne se charge qu'au clic (rien ne vient de YouTube avant)."""
    out = ['<div class="videos">']
    for vid, title, desc in items:
        t = html.escape(title)
        out.append(
            f'<figure class="yt"><a class="yt-go" href="https://www.youtube.com/watch?v={vid}" data-yt="{vid}" target="_blank" rel="noopener" '
            f'aria-label="Regarder la vidéo : {t}">'
            f'<img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="" loading="lazy" width="480" height="360">'
            '<span class="yt-play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5.5v13l10.5-6.5z"/></svg></span></a>'
            f'<figcaption><strong>{t}</strong>' + (f'<span>{html.escape(desc)}</span>' if desc else "") + '</figcaption></figure>')
    out.append("</div>")
    return "\n".join(out)


def inline(text, link):
    codes = []

    def keep_code(m):
        codes.append("<code>" + html.escape(m.group(1)) + "</code>")
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = re.sub(r"\{img:([^|}]+)\|([^}]*)\}", lambda m: f"\x01{m.group(1)}\x02{m.group(2)}\x03", text)
    text = html.escape(text, quote=False)

    def img_chip(m):
        href, ext = link.resolve(m.group(1))
        label = m.group(2) or "Image"
        if href is None:
            return ""
        return f'<a class="chip" href="{html.escape(href)}" target="_blank" rel="noopener">{label}</a>'

    text = re.sub(r"\x01([^\x02]+)\x02([^\x03]*)\x03", img_chip, text)

    def a(m):
        label, href = m.group(1), m.group(2)
        fix = next((v for k, v in LINK_FIX if posixpath.basename(html.unescape(href)).startswith(k)), None)
        if fix:
            return f'<a href="{html.escape(fix)}" target="_blank" rel="noopener">{label}</a>'
        url, ext = link.resolve(html.unescape(href))
        if not label.strip():
            return ""
        if url is None:
            return label
        attrs = ' target="_blank" rel="noopener"' if ext else ""
        return f'<a href="{html.escape(url)}"{attrs}>{label}</a>'

    text = re.sub(r"\[([^\]]*)\]\(([^)\s]*(?:\([^)]*\)[^)\s]*)*)\)", a, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)
    return text.strip()


# ---------------------------------------------------------------- mots en gras
# Les mots importants (armes, gadgets, personnages, niveaux, difficultés, codes)
# sont mis en gras à leur première apparition dans chaque paragraphe.
KEYWORDS = r"""
PP7|Silver PP7|Gold PP7|DD44 Dostovei|DD44|Klobb|KF7 Soviet|KF7|ZMG 9mm|ZMG|D5K Deutsche|D5K|Phantom|AR33|AR-33|RC-P90|RCP-90|RCP90
Sniper Rifle|Sniper|Golden Gun|Cougar Magnum|Magnum|Grenade Launcher|Rocket Launcher|Lance-Roquettes|Lance-Roquette|Lance-Grenades
Remote Mines?|Proximity Mines?|Timed Mines?|Mines? de Proximité|Mines? Télécommandées?|Mine ECM|ECM Mine|Moonraker Laser|Laser
Throwing Knives|Hunting Knife|Couteaux? de Combat|Couteaux? de Lancer|Tazer|Grenades?
Falcon 2|Falcon|MagSec 4|MagSec|Mauler|Phoenix|DY357|CMP150|Cyclone|Callisto NTG|Callisto|RC-P120|RCP-120|Laptop Gun|Super-Dragon|Super Dragon|Superdragon|Dragon
K7 Avenger|AR34|AR-34|Shotgun|Reaper|Slayer|Devastator|Farsight XR-20|FarSight XR-20|Farsight|Crossbow|Tranquilizer|N-Bomb|Psychosis Gun
Rayons X|X-Ray Scanner|Night Vision|Vision Nocturne|CamSpy|Data Uplink|Horizon Scanner|Door Decoder|Décodeur|Gilets?|Shield|Cloaking|Disguise|Déguisement
James Bond|Bond|Natalya|Trevelyan|Janus|Xenia|Ourumov|Oroumov|Oumourov|Boris|Valentin|Mishkin|Jaws|Oddjob|Mayday|Baron Samedi|Dr\.? Doak|Doak
Joanna Dark|Joanna|Jonathan|Elvis|Daniel Carrington|Carrington|Cassandra de Vries|Cassandra|Trent Easton|Trent|Mr\.? Blonde|Dr\.? Caroll|Velvet Dark|Velvet
Skedars?|Maians?|Simulants?|Roswells?|Hovercopter|Hovercrate|Hoverbike|Drone Guns?|Drone Gun
Agent|Secret Agent|00 Agent|Agent 00|Special Agent|Agent Special|Perfect Agent|Perfect Dark Mode|Mode Perfect Dark
Moon-?[Jj]ump|Passe-Muraille|Debug Mode|Line Mode|All Guns|Paintball Mode|DK Mode|Tiny Bond|Invincible|Infinite Ammo|Munitions Infinies
Action Replay|Game ?[Ss]hark|Project 64|Mupen|Fromages?|Citadel|Casino|Versions? Beta
Barrage|Facility|Runway|Bunker|Silo|Frigate|Archives|Streets|Depot|Jungle|Caverns|Water Caverns|Cradle|Aztec|Egyptian|Basement|Library|Caves
Datadyne|dataDyne|Lucerne Tower|Villa Carrington|Chicago|G5 Building|Zone 51|Area 51|Zone 52|Air Force One|Pelagic II|Pelagic 2|Institut Carrington|Felicity|Warehouse|Ravins|Skedar Ruins|Ruines Skedar
"""
_KW = sorted({w for line in KEYWORDS.split("\n") for w in line.split("|") if w.strip()}, key=len, reverse=True)
KW_RE = re.compile(r"(?<![\w\-])(" + "|".join(_KW) + r")(?![\w\-])")
PROTECT_RE = re.compile(r"(`[^`]+`|\*\*.+?\*\*|\[[^\]]*\]\([^)]*\)|\{img:[^}]*\}|https?://\S+)")


def embolden(text, seen):
    out = []
    for part in PROTECT_RE.split(text):
        if not part or PROTECT_RE.fullmatch(part):
            out.append(part)
            continue

        def rep(m):
            key = m.group(1).lower()
            if key in seen:
                return m.group(1)
            seen.add(key)
            return "**" + m.group(1) + "**"
        out.append(KW_RE.sub(rep, part))
    return "".join(out)


HEX_LINE = re.compile(r"^\s*(P\d\s*[:\-]?\s*)?[0-9A-F]{3,4}\s?[0-9A-FX?\-]{4,5}\s*[0-9A-FX?]{2,4}\b", re.I)


def is_code_para(lines):
    plain = [re.sub(r"\*\*", "", l).strip() for l in lines if l.strip()]
    if not plain:
        return False
    hits = sum(1 for l in plain if HEX_LINE.match(l))
    return hits >= 2 and hits >= 0.6 * len(plain)


# ---------------------------------------------------------------- rendu bloc
def render_cards(lines, link, page_game):
    out = ['<div class="grid' + (' thumbs' if any("{img:" in l for l in lines) else "") + '">']
    for line in lines:
        m = re.match(r"^\[(?:\{img:([^|}]+)\|)?([^\]}]+)\}?\]\(([^)]+)\)\s*(.*)$", line.strip())
        if not m:
            continue
        thumb, label, href, desc = m.groups()
        thumb = link.image(thumb) if thumb else None
        url, ext = link.resolve(href)
        if url is None:
            continue
        tag = ""
        mt = re.match(r"^(.*?) ·\s*(.*)$", desc)
        if mt:
            tag, desc = mt.groups()
        cls = "card"
        if page_game == "pd":
            cls += " pd"
        attrs = ' target="_blank" rel="noopener"' if ext else ""
        out.append(
            f'<a class="{cls}" href="{html.escape(url)}"{attrs}>'
            + (f'<img class="thumb" src="{html.escape(thumb)}" alt="" loading="lazy" width="240" height="180">' if thumb else "")
            + (f'<span class="tag">{html.escape(tag)}</span>' if tag else "")
            + f"<h3>{inline(label, link)}</h3>"
            + (f"<p>{inline(desc, link)}</p>" if desc else "")
            + "</a>"
        )
    out.append("</div>")
    return "\n".join(out)


def render_body(body, link, ctx):
    """Markdown simplifié → HTML. ctx sert pour les sommaires."""
    # listes d'images-liens (pages de section d'origine) → cartes
    body = re.sub(
        r"((?:^\[\{img:[^\n]+\]\([^)\n]+\)\s*\n(?:\s*\n)?)+)",
        lambda m: "{cards}\n" + "\n".join(l for l in m.group(1).split("\n") if l.strip()) + "\n{/cards}\n\n",
        body + "\n",
        flags=re.M,
    )
    lines = body.split("\n")
    html_out = []
    headings = []
    i = 0
    game = ctx["game"]
    cur_game = game

    def flush_para(buf):
        if not buf:
            return
        if is_code_para(buf):
            txt = "\n".join(re.sub(r"\*\*", "", l).rstrip() for l in buf)
            html_out.append("<pre>" + html.escape(txt) + "</pre>")
        else:
            seen = set()
            html_out.append("<p>" + "<br>".join(inline(embolden(l, seen), link) for l in buf) + "</p>")

    para = []
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush_para(para); para = []
            i += 1
            continue
        if s.startswith("```"):
            flush_para(para); para = []
            j = i + 1
            code = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                code.append(lines[j])
                j += 1
            html_out.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
            i = j + 1
            continue
        if s == "{cards}":
            flush_para(para); para = []
            j = i + 1
            items = []
            while j < len(lines) and lines[j].strip() != "{/cards}":
                if lines[j].strip():
                    items.append(lines[j])
                j += 1
            html_out.append(render_cards(items, link, cur_game))
            i = j + 1
            continue
        if s.startswith("{yt:"):
            flush_para(para); para = []
            vids = []
            while i < len(lines) and (lines[i].strip().startswith("{yt:") or not lines[i].strip()):
                mm = re.fullmatch(r"\{yt:([\w-]{11})\|([^|}]*)(?:\|([^}]*))?\}", lines[i].strip())
                if mm:
                    vids.append((mm.group(1), mm.group(2).strip(), (mm.group(3) or "").strip()))
                i += 1
            html_out.append(yt_cards(vids))
            continue
        if re.fullmatch(r"\{gal:\d+\}", s):
            flush_para(para); para = []
            html_out.append(gallery(ctx["galleries"][int(s[5:-1])], link))
            i += 1
            continue
        if re.fullmatch(r"(\{img:[^|}]+\}\s*)+", s):
            flush_para(para); para = []
            names = re.findall(r"\{img:([^|}]+)\}", s)
            imgs = [{"src": IMG_FILES.get(posixpath.normpath(posixpath.join(posixpath.dirname(link.current), n.strip())).lower()), "alt": ""} for n in names]
            html_out.append(gallery([im for im in imgs if im["src"]], link))
            i += 1
            continue
        if s in ("{toc}", "{toc-ge}", "{toc-pd}", "{original}", "{mail}"):
            flush_para(para); para = []
            html_out.append(f"\x04{s}\x04")
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        is_challenge = re.match(r"^Challenge \d+$", s)
        if m or is_challenge:
            flush_para(para); para = []
            if is_challenge:
                level, text = 3, s
            else:
                level = 2 if len(m.group(1)) <= 2 else 3
                text = m.group(2)
            low = text.lower()
            if "perfect dark" in low:
                cur_game = "pd"
            elif "goldeneye" in low:
                cur_game = "ge"
            hid = slug(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text))
            base, n = hid, 2
            while hid in ctx["ids"]:
                hid = f"{base}-{n}"; n += 1
            ctx["ids"].add(hid)
            cls = ' class="pd"' if (level == 2 and cur_game == "pd") else ""
            headings.append((level, hid, text))
            html_out.append(f'<h{level} id="{hid}"{cls}>{inline(text, link)}</h{level}>')
            i += 1
            continue
        if s.startswith("- "):
            flush_para(para); para = []
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
                # lignes de continuation
                while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("- ") \
                        and not lines[i].startswith("#") and not lines[i].strip().startswith("```"):
                    items[-1] += " " + lines[i].strip()
                    i += 1
                # une ligne vide entre deux éléments ne coupe pas la liste
                if i + 1 < len(lines) and not lines[i].strip() and lines[i + 1].strip().startswith("- "):
                    i += 1
            html_out.append("<ul>" + "".join(f"<li>{inline(embolden(t, set()), link)}</li>" for t in items) + "</ul>")
            continue
        if s.startswith(">"):
            flush_para(para); para = []
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip().lstrip(">").strip())
                i += 1
            html_out.append("<blockquote><p>" + "<br>".join(inline(t, link) for t in q) + "</p></blockquote>")
            continue
        para.append(line)
        i += 1
    flush_para(para)
    return "\n".join(html_out), headings


# ---------------------------------------------------------------- navigation
# Le site s'organise autour de deux jeux. Chaque jeu a une page qui liste
# toutes ses pages, rangées par thème. Le reste est dans « Infos ».
GAMES = {
    "ge": ("goldeneye", "Goldeneye"),
    "pd": ("perfect-dark", "Perfect Dark"),
    "plus": ("infos", "Infos"),
}
GROUPS = [
    # (dossier d'origine, nom du thème, ancre)
    ("presentation", "Présentation", "presentation"),
    ("soluce", "Soluce", "soluce"),
    ("battle", "Battle", "battle"),
    ("cheats", "Codes", "codes"),
    ("challenges", "Challenges", "challenges"),
    ("beta", "Beta", "beta"),
    ("mysteres", "Mystères", "mysteres"),
    ("action.replay", "Action Replay", "action-replay"),
    ("complex", "The Complex", "the-complex"),
]
GROUP_OF = {"cinema": "presentation", "plans": "battle"}
PLUS = ["emulation/", "action.replay/explication.htm", "autres/", "liens/", "contact/"]
# anciennes pages de section qui ne servaient qu'à lister des pages : remplacées par les pages des jeux
LIST_ONLY = {"presentation/", "soluce/", "battle/", "beta/", "mysteres/", "action.replay/"}


def classify(path, title):
    """→ liste de (jeu, dossier du thème) ; vide si la page n'est rangée nulle part."""
    if path in PLUS:
        return [("plus", None)]
    if path in LIST_ONLY:
        return []
    seg = path.split("/", 1)[0]
    group = GROUP_OF.get(seg, seg)
    if path in ("cheats/", "presentation/videos.htm"):
        return [("ge", group), ("pd", group)]
    if seg in ("challenges", "plans"):
        return [("pd", group)]
    if seg in ("complex", "cinema") or path == "battle/confidential.htm":
        return [("ge", group)]
    g = game_of(path, title)
    return [(g, group)] if g else []


def short_title(title):
    t = re.sub(r"^(Soluce |Battle |Myst[eè]res de |Mysteres de )?(Goldeneye|Perfect Dark)( Version Beta)?\s*:\s*", "", title)
    return t or title


def build_index(pages, order):
    """{jeu: {thème: [pages]}} dans l'ordre du site d'origine."""
    idx = {g: {} for g in GAMES}
    where = {}
    for path in order:
        for g, grp in classify(path, pages[path]["title"]):
            idx[g].setdefault(grp, []).append(path)
            where.setdefault(path, []).append((g, grp))
    sol = idx["pd"].get("soluce", [])
    if "soluce/pd-18.html" in sol:  # Duel est la dernière mission
        sol.remove("soluce/pd-18.html"); sol.append("soluce/pd-18.html")
    return idx, where


def href_from(cur_out, target_out):
    return clean(posixpath.relpath(target_out, posixpath.dirname(cur_out) or "."))


# ---------------------------------------------------------------- icônes (traits, style Lucide)
ICONS = {
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "book": '<path d="M2 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H2zM22 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z"/>',
    "map": '<path d="M9 3 3 5v16l6-2 6 2 6-2V3l-6 2-6-2zM9 3v16M15 5v16"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    "key": '<circle cx="7.5" cy="15.5" r="4.5"/><path d="m10.7 12.3 9.8-9.8M17 6l3 3M15 8l2 2"/>',
    "trophy": '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4"/>',
    "flask": '<path d="M9 3h6M10 3v6L4 19a2 2 0 0 0 1.7 3h12.6A2 2 0 0 0 20 19l-6-10V3"/><path d="M7 15h10"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "building": '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
    "monitor": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "gamepad": '<path d="M6 12h4M8 10v4M15 13h.01M18 11h.01"/><rect x="2" y="6" width="20" height="12" rx="6"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/>',
    "arrow-up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
    "arrow-right": '<path d="M5 12h14M12 5l7 7-7 7"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
}
GAME_ICON = {"ge": "eye", "pd": "moon", "plus": "info"}
GROUP_ICON = {"presentation": "book", "soluce": "map", "battle": "target", "cheats": "key", "challenges": "trophy",
              "beta": "flask", "mysteres": "search", "action.replay": "cpu", "complex": "building"}
PLUS_ICON = {"emulation/": "monitor", "action.replay/explication.htm": "cpu", "autres/": "gamepad", "liens/": "link", "contact/": "mail"}


SEP = '<span class="sep">›</span>'


def icon(name, cls="icon"):
    return f'<svg class="{cls} {name}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


# ---------------------------------------------------------------- gabarit
def nav_html(link, current_game):
    r = link.root()
    items = []
    for g, (slug_, name) in GAMES.items():
        on = (' class="on pd"' if g == "pd" else ' class="on"') if g == current_game else ""
        cur = ' aria-current="page"' if g == current_game else ""
        items.append(f'<li><a href="{r}{slug_}/"{on}{cur}>{icon(GAME_ICON[g], "icon ni ni-" + g)}{name}</a></li>')
    return "\n".join(items) + '\n<li class="nav-ind" aria-hidden="true"></li>'


def to_top(game):
    """Bouton « retour en haut » : viseur (Goldeneye), propulseur hexagonal (Perfect Dark) ou mixte."""
    if game == "ge":
        ticks = "".join(f'<line x1="28" y1="7.5" x2="28" y2="{9.5 if i % 3 else 11}" transform="rotate({i * 30} 28 28)"/>' for i in range(12))
        ring = ('<circle class="track" cx="28" cy="28" r="24"/>'
                '<circle class="fill" cx="28" cy="28" r="24" pathLength="100" transform="rotate(-90 28 28)"/>'
                f'<g class="bezel">{ticks}</g>')
        glyph = ('<g class="glyph sight"><circle cx="28" cy="28" r="9"/>'
                 '<path d="M28 14v8M28 34v8M14 28h8M34 28h8"/><circle class="dot" cx="28" cy="28" r="1.8"/></g>'
                 '<circle class="flash" cx="28" cy="28" r="12"/>')
        label = "Retour en haut : viser le sommet"
    elif game == "pd":
        hexa = "M28 3 L49.6 15.5 L49.6 40.5 L28 53 L6.4 40.5 L6.4 15.5 Z"
        ring = (f'<path class="track" d="{hexa}"/>'
                f'<path class="fill" d="{hexa}" pathLength="100"/>')
        glyph = ('<g class="glyph thrust"><path class="c1" d="M20 28l8-8 8 8"/><path class="c2" d="M20 36l8-8 8 8"/></g>'
                 '<path class="beam" d="M28 18V4"/>')
        label = "Retour en haut : propulsion"
    else:
        ring = ('<defs><linearGradient id="tt-g" x1="0" y1="0" x2="1" y2="1">'
                '<stop offset="0" stop-color="var(--gold)"/><stop offset="1" stop-color="var(--pd)"/></linearGradient></defs>'
                '<circle class="track" cx="28" cy="28" r="24"/>'
                '<circle class="fill" cx="28" cy="28" r="24" pathLength="100" transform="rotate(-90 28 28)"/>')
        glyph = '<g class="glyph arrow"><path d="M28 38V19M20 26l8-8 8 8"/></g>'
        label = "Retour en haut"
    kind = game if game in ("ge", "pd") else "mix"
    return (f'<button class="to-top tt-{kind}" type="button" aria-label="{label}" title="{label}">'
            f'<svg viewBox="0 0 56 56" aria-hidden="true">{ring}{glyph}</svg></button>')


# ---------------------------------------------------------------- SEO : titres de pages
BRAND = "GE & PD 64"
GNAME = {"ge": "GoldenEye 007", "pd": "Perfect Dark"}
SEO_TITLES = {
    "index.html": "GoldenEye 007 & Perfect Dark N64 : soluces, codes et secrets",
    "goldeneye/index.html": "GoldenEye 007 N64 : soluce, Battle, codes et secrets",
    "perfect-dark/index.html": "Perfect Dark N64 : soluce, challenges, codes et secrets",
    "infos/index.html": "Infos : émulation, Action Replay, liens et contact",
    "action-replay/explication.html": "Action Replay et GameShark N64 : mode d'emploi",
    "autres/index.html": "Les autres jeux préférés de Tim sur Nintendo 64",
    "challenges/index.html": "Perfect Dark : les 30 challenges du Combat Simulator",
    "cheats/index.html": "Codes et cheats de GoldenEye 007 et Perfect Dark",
    "cinema/index.html": "GoldenEye 007 : les niveaux du jeu dans le film",
    "complex/index.html": "GoldenEye 007 : The Complex, l'arène Battle culte",
    "contact/index.html": "Contacter Tim, l'auteur du site",
    "emulation/index.html": "Jouer à GoldenEye et Perfect Dark sur émulateur",
    "liens/index.html": "Liens : les meilleurs sites sur GoldenEye et Perfect Dark",
    "plans/index.html": "Perfect Dark : plans des niveaux multijoueur",
    "battle/confidential.html": "Battle GoldenEye 007 : niveaux confidentiels",
    "presentation/videos.html": "GoldenEye et Perfect Dark : pubs et vidéos d'époque",
    "presentation/rareware.html": "GoldenEye 007 : la page de Rare traduite en français",
    "presentation/makingof.html": "GoldenEye 007 : le making-of du jeu traduit",
    "presentation/test-ge.html": "Test complet de GoldenEye 007 sur Nintendo 64",
    "presentation/decouverte-pd.html": "Perfect Dark sur Nintendo 64 : découverte et test",
    "presentation/decouverte-ge.html": "GoldenEye 007 sur Nintendo 64 : la découverte",
    "presentation/diviseur.html": "GoldenEye 007 : c'est quoi un diviseur ?",
    "battle/index.html": "Battle GoldenEye 007 : toutes les arènes multijoueur",
    "beta/index.html": "Versions beta de GoldenEye 007 et Perfect Dark",
    "mysteres/index.html": "Mystères et secrets de GoldenEye 007 et Perfect Dark",
    "presentation/index.html": "Présentation de GoldenEye 007 et Perfect Dark",
    "soluce/index.html": "Soluces complètes de GoldenEye 007 et Perfect Dark",
    "action-replay/index.html": "Codes Action Replay de GoldenEye 007 et Perfect Dark",
    "action-replay/niveaux/ge-nouveaux-niveaux.html": "Action Replay GoldenEye 007 : nouveaux niveaux à 2 joueurs",
}


def _tidy(name):
    name = html.unescape(name)
    name = re.sub(r"\s*\([^)]*\)", "", name).strip(" !.…")
    name = re.sub(r"\s+-\s+", " – ", name)
    name = re.sub(r"\bReferences\b", "Références", name)
    return name


def seo_title(out, title, game):
    """Titre unique et parlant pour l'onglet et les moteurs de recherche (≈ 60 caractères)."""
    if out in SEO_TITLES:
        t = SEO_TITLES[out]
    else:
        sec = out.split("/", 1)[0]
        g = GNAME.get(game, "")
        name = _tidy(short_title(html.unescape(title)))
        name = re.sub(r"^(Goldeneye|Perfect Dark)( Version Beta)?\s*:\s*", "", name)
        if sec == "soluce":
            t = f"Soluce {g} : mission {name}" if "007" not in name else f"Soluce {g} : le mode 007"
        elif sec == "battle":
            t = f"Battle {g} : arène {name} en multijoueur"
        elif sec == "beta":
            t = f"{g} : {name} dans la version beta"
        elif sec == "mysteres":
            t = f"Mystères de {g} : {name}"
        elif sec == "action-replay":
            t = f"Action Replay {g} : {name}"
        elif sec == "challenges":
            t = f"Perfect Dark : {name}"
        elif sec == "presentation":
            t = f"{g} N64 : {name}" if g else name
        else:
            t = f"{g} : {name}" if g else name
    if len(t) + len(BRAND) + 3 <= 68:
        t += " · " + BRAND
    return t


SITE_URL = "https://titelive.me/tim/"


def layout(link, title, inner, section=None, game="", description="", tab_title=None):
    r = link.root()
    body_cls = f' class="theme-{game}"' if game else ""
    desc = html.escape(description or "Goldeneye 007 et Perfect Dark sur Nintendo 64 : soluces, battle, codes, beta, mystères.")
    page_title = html.escape(tab_title or seo_title(link.cur_out, title, game))
    if not description:
        for para in re.findall(r"<p\b[^>]*>(.*?)</p>", inner, re.S):
            txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", para))).strip()
            if len(txt) > 60:
                if len(txt) > 180:
                    txt = txt[:177].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"
                desc = html.escape(txt)
                break
    share = {"ge": "goldeneye", "pd": "perfect-dark"}.get(game, "accueil")
    url = SITE_URL + clean(link.cur_out).lstrip("./") if clean(link.cur_out) != "./" else SITE_URL
    og_img = f"{SITE_URL}images/partage/{share}.jpg"
    # données structurées : site, fil d'Ariane, jeu vidéo
    ld = []
    if url == SITE_URL:
        ld.append({"@context": "https://schema.org", "@type": "WebSite", "name": "GoldenEye 007 & Perfect Dark",
                   "url": SITE_URL, "inLanguage": "fr-FR", "description": html.unescape(desc)})
    cm = re.search(r'<div class="crumbs">(.*?)</div>', inner, re.S)
    if cm:
        items, base = [], posixpath.dirname(link.cur_out)
        for href, label in re.findall(r'<a href="([^"#]*)[^"]*">(.*?)</a>', cm.group(1)):
            target = clean(posixpath.normpath(posixpath.join(base, href)) + ("/" if href.endswith("/") or href.endswith("../") else ""))
            target = "" if target in ("./", ".", "./.") else target.lstrip("./")
            items.append((html.unescape(re.sub("<[^>]+>", "", label)), SITE_URL + target))
        items.append((html.unescape(title) or "Accueil", url))
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]})
    if link.cur_out in ("goldeneye/index.html", "perfect-dark/index.html"):
        g2 = "ge" if link.cur_out.startswith("goldeneye") else "pd"
        ld.append({"@context": "https://schema.org", "@type": "VideoGame", "name": GNAME[g2],
                   "gamePlatform": "Nintendo 64", "publisher": {"@type": "Organization", "name": "Nintendo" if g2 == "ge" else "Rare"},
                   "author": {"@type": "Organization", "name": "Rare"}, "datePublished": "1997-08-25" if g2 == "ge" else "2000-05-22",
                   "genre": "Jeu de tir à la première personne", "image": og_img, "url": url})
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(d, ensure_ascii=False)}</script>\n' for d in ld)
    head_meta = (ld_html + f'<link rel="canonical" href="{url}">\n'
                 f'<meta property="og:type" content="website">\n<meta property="og:locale" content="fr_FR">\n'
                 f'<meta property="og:site_name" content="Goldeneye &amp; Perfect Dark">\n'
                 f'<meta property="og:title" content="{page_title}">\n<meta property="og:description" content="{desc}">\n'
                 f'<meta property="og:url" content="{url}">\n<meta property="og:image" content="{og_img}">\n'
                 f'<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
                 f'<meta property="og:image:alt" content="Cartouches Nintendo 64 de Goldeneye et Perfect Dark">\n'
                 f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="{page_title}">\n'
                 f'<meta name="twitter:description" content="{desc}">\n<meta name="twitter:image" content="{og_img}">\n'
                 f'<link rel="icon" href="{r}favicon.svg" type="image/svg+xml">\n<link rel="icon" href="{r}favicon-32.png" sizes="32x32" type="image/png">\n'
                 f'<link rel="apple-touch-icon" href="{r}apple-touch-icon.png">\n<link rel="manifest" href="{r}manifest.webmanifest">\n<meta name="theme-color" content="#0d0f14">')
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title>
<meta name="description" content="{desc}">
{head_meta}
<script>try{{var t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/style.css?v={ASSET_V}">
</head>
<body{body_cls}>
<div class="ambient" aria-hidden="true"><span></span><span></span><span></span></div>
<div class="progress" aria-hidden="true"></div>
<a class="skip" href="#contenu">Aller au contenu</a>
<header class="top">
  <div class="wrap">
    <a class="brand" href="{clean(r)}" aria-label="Accueil"><b>Golden</b>eye <span>&amp;</span> <i>Perfect</i> Dark</a>
    <nav class="main" aria-label="Jeux"><ul>
{nav_html(link, section)}
    </ul></nav>
    <button class="theme-toggle" type="button" aria-label="Basculer entre le mode clair et le mode sombre">{icon("moon")}{icon("sun")}</button>
  </div>
</header>
<main id="contenu">
{inner}
</main>
<footer>
  <div class="wrap">
    <p>Contenu écrit par <strong>Tim</strong>, passionné de <strong>Goldeneye 007</strong> et de <strong>Perfect Dark</strong>. Ce sont des jeux Rare / Nintendo ; ce site de fan n'est affilié à aucune de ces sociétés.</p>
    <p class="credit"><a class="tlc" href="https://titelive.me" target="_blank" rel="noopener" title="titelive.me"><span>Site réalisé par</span><img src="/img/titelive-logo.png" alt="" width="22" height="22" loading="lazy"><b>Titelive</b></a></p>
  </div>
</footer>
{to_top(game)}
<script src="{r}assets/site.js?v={ASSET_V}" defer></script>
</body>
</html>
"""


def toc_list(headings, prefix=None):
    items = [h for h in headings if h[0] == 3 and (prefix is None or h[2].lower().startswith(prefix))]
    if not items:
        return ""
    lis = "".join(f'<li><a href="#{hid}">{html.escape(re.sub(r"^(Goldeneye|Perfect Dark) - ", "", text))}</a></li>' for _, hid, text in items)
    return f'<nav class="toc" aria-label="Sommaire"><ol>{lis}</ol></nav>'


def soluce_cards(pages, link, prefix, game):
    keys = [k for k in pages if k.startswith("soluce/" + prefix)]
    rows = []
    for n, k in enumerate(keys, 1):
        t = re.sub(r"^Soluce (Goldeneye|Perfect Dark)\s*:\s*", "", pages[k]["title"])
        num = "Bonus" if k.endswith("007.htm") else f"Mission {n:02d}"
        rows.append(f"[{t}](../{k}) {num} ·")
    label = "Goldeneye" if game == "ge" else "Perfect Dark"
    return f'<h2 id="{game}"{" class=\"pd\"" if game == "pd" else ""}>{label}</h2>\n' + render_cards(rows, link, game)


def norm_words(s):
    s = unicodedata.normalize("NFKD", html.unescape(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", s)


def place_images(page):
    """Replace les images de la page d'origine dans le texte : chaque groupe d'images
    va après le paragraphe qui contient les derniers mots lus avant lui sur l'original."""
    data = IMG_PAGES.get(page["orig"].lstrip("./").lower())
    body = page["body"]
    if not data or not data["groups"]:
        return body, []
    already = {n.strip().lower() for n in re.findall(r"\{img:([^|}]+)", body)}
    groups = []
    for g in data["groups"]:
        imgs = [im for im in g["imgs"] if im["file"] not in already]
        if imgs:
            groups.append((g["anchor"].split(), g.get("next", "").split(), imgs))
    if not groups:
        return body, []
    # blocs séparés par une ligne vide, sans couper les blocs de code ni les listes de cartes
    blocks, cur, fence = [], [], False
    for line in body.split("\n"):
        if line.strip().startswith("```"):
            fence = not fence
        if not line.strip() and not fence and cur:
            blocks.append(cur); cur = []
        elif line.strip().startswith("- ") and not fence and cur and cur[0].lstrip().startswith("- "):
            blocks.append(cur); cur = [line]  # chaque élément de liste à part : une image peut suivre son élément
        elif line.strip() or fence:
            cur.append(line)
    if cur:
        blocks.append(cur)
    # flux de mots de tout le texte, avec le bloc de chaque mot
    stream, owner = [], []
    for b, lines in enumerate(blocks):
        txt = re.sub(r"\]\([^)]*\)", "]", "\n".join(lines))
        txt = re.sub(r"\{[a-z]+:[^}]*\}", " ", txt)
        for w in norm_words(txt):
            stream.append(w); owner.append(b)
    after = {}  # bloc → groupes à placer après lui (-1 : avant le texte)
    cursor = 0
    def find(needle, frm):
        for start in range(frm, len(stream) - len(needle) + 1):
            if stream[start:start + len(needle)] == needle:
                return start
        return None

    def fuzzy(words, frm, before):
        """Texte réécrit depuis l'original : on accepte 6 mots sur 8 dans une fenêtre de 12."""
        if len(words) < 5:
            return None
        need = max(4, round(len(words) * 0.62))
        best, best_pos = 0, None
        for pos in range(frm, len(stream)):
            win = stream[max(0, pos - 11):pos + 1] if before else stream[pos:pos + 12]
            if (stream[pos] != words[-1]) if before else (stream[pos] != words[0]):
                continue
            score = sum(1 for w in words if w in win)
            if score > best:
                best, best_pos = score, pos
                if score == len(words):
                    break
        return best_pos if best >= need else None

    for anchor, nxt, imgs in groups:
        spot = None
        if not anchor:
            spot = -1
        else:
            # les derniers mots lus avant l'image : elle va après leur paragraphe
            for k in (12, 8, 5, 4):
                if len(anchor) < k and k != 4:
                    continue
                start = find(anchor[-k:], cursor)
                if start is not None:
                    end = start + min(k, len(anchor)) - 1
                    spot, cursor = owner[end], end
                    break
        if spot is None and anchor:
            e = fuzzy(anchor[-8:], cursor, before=True)
            if e is not None:
                spot, cursor = owner[e], e
        if spot is None and nxt:
            # sinon, les premiers mots lus après l'image : elle va avant leur paragraphe
            for k in (12, 8, 5, 4):
                if len(nxt) < k and k != 4:
                    continue
                start = find(nxt[:k], cursor)
                if start is not None:
                    spot, cursor = owner[start] - 1, start
                    break
        if spot is None and nxt:
            st = fuzzy(nxt[:8], cursor, before=False)
            if st is not None:
                spot, cursor = owner[st] - 1, st
        if spot is None:
            spot = len(blocks) - 1  # introuvable : en fin de page
        after.setdefault(spot, []).extend(imgs)
    galleries, out = [], []
    def put(b):
        if b in after:
            out.append(f"{{gal:{len(galleries)}}}")
            galleries.append(after[b])
    put(-1)
    for b, lines in enumerate(blocks):
        out.append("\n".join(lines))
        put(b)
    return "\n\n".join(out), galleries


LOWRES_W = 400    # en dessous de cette largeur d'origine, l'image est jugée de faible qualité
LOWRES_MAX = 220  # largeur d'affichage maximale de ces images


def gallery(imgs, link):
    if not imgs:
        return ""
    # image de faible résolution : affichée petite (taille d'origine au plus), texte à droite
    lowres = all(im.get("w") and im["w"] < LOWRES_W for im in imgs)
    figs = []
    for im in imgs:
        src = link.to(im["src"])
        big = link.to(im["big"]) if im.get("big") else src
        alt = html.escape(im.get("alt") or "")
        dims = f' width="{im["w"]}" height="{im["h"]}"' if im.get("w") else ""
        cap = f"<figcaption>{alt}</figcaption>" if alt else ""
        size = f' style="--w:{min(im["w"], LOWRES_MAX)}px"' if lowres else ""
        figs.append(f'<figure{size}><a class="zoom" href="{html.escape(big)}" aria-label="Agrandir l\'image">'
                    f'<img src="{html.escape(src)}" alt="{alt}" loading="lazy"{dims}></a>{cap}</figure>')
    if lowres:
        cls = "gallery side" if len(imgs) <= 2 else "gallery small"
    else:
        cls = "gallery" + (" one" if len(imgs) == 1 else "")
    n = len(imgs)
    cols = n if n <= 3 else (2 if n % 2 == 0 and n % 3 else 3)
    style = f' style="--n:{cols}"' if cls == "gallery small" else ""
    return f'<div class="{cls}"{style}>' + "".join(figs) + "</div>"


def build_page(path, page, pages, order, idx, where):
    link = Linker(pages, path)
    section = section_of(path)
    game = game_of(path, page["title"])
    body, galleries = place_images(page)
    ctx = {"game": game, "ids": set(), "galleries": galleries}
    body_html, headings = render_body(body, link, ctx)
    # petite image + texte qui la suit : côte à côte (image à gauche, texte à droite)
    # textes alternatifs : chaque image de galerie sans légende reçoit une description tirée du titre de la page
    alt_base = html.escape(short_title(html.unescape(page["title"])), quote=True)
    alt_n = iter(range(1, 10000))
    body_html = re.sub(r'(<a class="zoom"[^>]*><img [^>]*?)alt=""', lambda m: f'{m.group(1)}alt="{alt_base} : image {next(alt_n)}"', body_html)
    body_html = re.sub(r'(<div class="gallery side">(?:(?!</div>).)*</div>)\s*(<(p|ul|ol)\b.*?</\3>)',
                       r'<div class="media">\1<div class="media-t">\2</div></div>', body_html, flags=re.S)

    def placeholder(m):
        key = m.group(1)
        if key == "{original}":
            return ""
        if key == "{mail}":
            return f'<p class="mail"><a class="btn" href="mailto:{MAIL}">Écrire à Tim</a></p>'
        if path == "soluce/":
            return soluce_cards(pages, link, "ge" if key == "{toc-ge}" else "pd", "ge" if key == "{toc-ge}" else "pd")
        if key == "{toc}":
            return toc_list(headings)
        return toc_list(headings, "goldeneye" if key == "{toc-ge}" else "perfect dark")

    body_html = re.sub(r"\x04(\{[a-z-]+\})\x04", placeholder, body_html)

    # fil d'Ariane et pages voisines : d'après le jeu et le thème de la page
    cur_out = out_path(path)
    places = where.get(path, [])
    crumbs = [f'<a href="{href_from(cur_out, "index.html")}">Accueil</a>']
    pager = ""
    nav_game = None
    if len(places) == 1:
        g, grp = places[0]
        nav_game = g
        gslug, gname = GAMES[g]
        hub = gslug + "/index.html"
        crumbs.append(f'<a href="{href_from(cur_out, hub)}">{gname}</a>')
        if grp:
            gname2 = next(n for k, n, a in GROUPS if k == grp)
            anchor = next(a for k, n, a in GROUPS if k == grp)
            crumbs.append(f'<a href="{href_from(cur_out, hub)}#{anchor}">{gname2}</a>')
        sib = idx[g][grp]
        i = sib.index(path)
        parts = []
        if i > 0:
            p = sib[i - 1]
            parts.append(f'<a class="prev" href="{href_from(cur_out, out_path(p))}"><small>Précédent</small>{html.escape(short_title(pages[p]["title"]))}</a>')
        else:
            parts.append("<span></span>")
        if i < len(sib) - 1:
            p = sib[i + 1]
            parts.append(f'<a class="next" href="{href_from(cur_out, out_path(p))}"><small>Suivant</small>{html.escape(short_title(pages[p]["title"]))}</a>')
        if len(sib) > 1:
            pager = '<nav class="pager" aria-label="Pages voisines">' + "".join(parts) + "</nav>"
    elif places:
        nav_game = None

    first = galleries[0][0]["src"] if galleries else GAME_ART.get(nav_game or game or "", "")
    head = (f'<div class="page-head has-banner"{banner_style(cur_out, first)}><div class="wrap">'
            f'<div class="crumbs">{SEP.join(crumbs)}</div>'
            f'<h1>{inline(page["title"], link)}</h1></div></div>')
    inner = (head + f'<div class="wrap"><article class="content">{body_html}{pager}'
             f'</article></div>')
    return layout(link, page["title"], inner, nav_game, game or nav_game or "")


# pages sans photo à elles : image choisie dans le même thème
THUMB_FALLBACK = {
    ("ge", "cheats/"): "images/soluce/surface1-1.jpg",
    ("ge", "complex/"): "images/complex/the-complex-01.jpg",
    ("ge", "presentation/personnages.htm"): "images/presentation/film-natalya.jpg",
    ("ge", "presentation/diviseur.htm"): "images/presentation/golden-logo.jpg",
    ("ge", "presentation/references-ge.htm"): "images/presentation/film-007.jpg",
    ("ge", "presentation/videos.htm"): "images/presentation/boite-007-fr.jpg",
    ("pd", "cheats/"): "images/mysteres/area51-01.jpg",
    ("pd", "challenges/"): "images/challenges/challenge-22-1.jpg",
    ("pd", "presentation/videos.htm"): "images/presentation/boite-pd-fr.jpg",
    ("pd", "plans/"): "images/plans/villa.jpg",
    ("pd", "action.replay/pd.musique.htm"): "images/mysteres/skedar-01.jpg",
    ("pd", "action.replay/pd.divers.htm"): "images/mysteres/institut-01.jpg",
    ("plus", "autres/"): "images/autres/jet-force-gemini.jpg",
    ("plus", "liens/"): "images/ambiance/perfect-dark-rue.jpg",
    ("plus", "contact/"): "images/ambiance/goldeneye-jaquette.jpg",
}

def _img_key(p):
    """Clé de page (canon) → clé de contenu/images.json."""
    return p + "index.htm" if p.endswith("/") else p


_THUMBS_TO = {}
for _src_page, _v in IMG_PAGES.items():
    for _target, _img in _v["thumbs"].items():
        if _img:
            _THUMBS_TO.setdefault(canon(_target), _img)


def page_thumb(p, used, game=None):
    """Image représentative d'une page : sa première vraie photo, sinon la vignette
    qui menait vers elle. Évite de répéter une image déjà prise dans la même liste."""
    cands = []
    for k in (_img_key(p), p, p + "l" if p.endswith(".htm") else p):
        v = IMG_PAGES.get(k)
        if v:
            for g in v["groups"]:
                for im in g["imgs"]:
                    if (im.get("w") or 200) >= 120 and (im.get("h") or 150) >= 80:
                        cands.append(im.get("big") or im["src"])
            break
    if p in _THUMBS_TO:
        cands.append(_THUMBS_TO[p])
    if not cands and (game, p) in THUMB_FALLBACK:
        cands.append(THUMB_FALLBACK[(game, p)])
    for c in cands:
        if c not in used:
            used.add(c)
            return c
    return cands[0] if cands else None


def group_links(paths, cur_out, pages, numbered=False, icons=False, game=None):
    items = []
    used = set()
    for n, p in enumerate(paths, 1):
        t = html.escape(short_title(pages[p]["title"]))
        num = ""
        if numbered:
            num = "★" if p.endswith("007.htm") else f"{n:02d}"
            num = f'<span class="num">{num}</span>'
        if icons:
            num = icon(PLUS_ICON.get(p, "info"))
        img = page_thumb(p, used, game)
        th = (f'<span class="th"><img src="{href_from(cur_out, img)}" alt="" loading="lazy" decoding="async" width="320" height="180"></span>'
              if img else '<span class="th none"></span>')
        items.append(f'<li><a href="{href_from(cur_out, out_path(p))}" title="{t}">{th}<span class="b">{num}<span class="t">{t}</span></span></a></li>')
    return '<ul class="links">' + "".join(items) + "</ul>"


GAME_INTRO = {
    "ge": "Le jeu de Rare sorti en 1997 sur Nintendo 64 : toutes les missions, les arènes Battle, les codes, les secrets.",
    "pd": "La suite spirituelle de Goldeneye, sortie en 2000 : missions, Battle, 30 challenges, codes et mystères.",
    "plus": "Jouer sur émulateur, comprendre l'Action Replay, les autres jeux de Tim, les liens et le contact.",
}


# images d'ambiance (bannières, cartes des jeux, défilé de l'accueil)
GAME_ART = {"ge": "images/ambiance/goldeneye.jpg", "pd": "images/ambiance/perfect-dark.jpg",
            "plus": "images/ambiance/perfect-dark-rue.jpg"}
GE_SHOTS = ["images/soluce/%s-1.jpg" % n for n in ("surface1", "bunker2", "statue", "archives", "streets", "depot",
            "train", "jungle", "control", "caverns", "cradle", "aztec", "egyptian", "007")]
PD_SHOTS = ["images/mysteres/%s-01.jpg" % n for n in ("area51", "defection", "extraction", "g5", "institut", "villa",
            "skedar", "vaisseau", "maian", "labo", "crash", "abysses")] + \
           ["images/challenges/challenge-%d-1.jpg" % n for n in (15, 16, 18, 22, 24, 26, 29)]


def existing(paths):
    return [p for p in paths if (ROOT / p).exists()]


def banner_style(cur_out, img):
    # une url() dans une variable CSS se lit depuis la feuille de style (assets/), d'où le « ../ »
    return f' style="--banner:url(\'../{img}\')"' if img and (ROOT / img).exists() else ""


HUB_DECO = {"ge": ('<svg class="deco dial" viewBox="0 0 200 200" width="240" height="240" aria-hidden="true"><defs><clipPath id="lcd-clip"><circle cx="100" cy="100" r="58"/></clipPath><radialGradient id="lcd" cx="50%" cy="42%" r="60%"><stop offset="0" stop-color="#8dff5a"/><stop offset=".6" stop-color="#3fd23a"/><stop offset="1" stop-color="#15701c"/></radialGradient><linearGradient id="scan-g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#eaffd8" stop-opacity=".45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs><circle cx="100" cy="100" r="99" fill="#08090b" stroke="rgba(255,255,255,.22)" stroke-width="2"/><path class="seg" style="--i:0" d="M44.0 25.7A93 93 0 0 1 56.3 17.9L64.3 32.9A76.0 76.0 0 0 0 54.3 39.3Z" fill="#ff2414"/><path class="seg" style="--i:0" d="M143.7 17.9A93 93 0 0 1 156.0 25.7L145.7 39.3A76.0 76.0 0 0 0 135.7 32.9Z" fill="#2b4dff"/><path class="seg" style="--i:1" d="M29.8 39.0A93 93 0 0 1 40.2 28.8L50.3 40.8A77.3 77.3 0 0 0 41.7 49.3Z" fill="#ff3616"/><path class="seg" style="--i:1" d="M159.8 28.8A93 93 0 0 1 170.2 39.0L158.3 49.3A77.3 77.3 0 0 0 149.7 40.8Z" fill="#4362ff"/><path class="seg" style="--i:2" d="M18.7 54.9A93 93 0 0 1 26.7 42.7L38.1 51.6A78.6 78.6 0 0 0 31.3 61.9Z" fill="#ff4717"/><path class="seg" style="--i:2" d="M173.3 42.7A93 93 0 0 1 181.3 54.9L168.7 61.9A78.6 78.6 0 0 0 161.9 51.6Z" fill="#5c76ff"/><path class="seg" style="--i:3" d="M11.1 72.8A93 93 0 0 1 16.4 59.2L28.2 65.0A79.9 79.9 0 0 0 23.6 76.6Z" fill="#ff5818"/><path class="seg" style="--i:3" d="M183.6 59.2A93 93 0 0 1 188.9 72.8L176.4 76.6A79.9 79.9 0 0 0 171.8 65.0Z" fill="#748aff"/><path class="seg" style="--i:4" d="M7.4 91.9A93 93 0 0 1 9.8 77.5L21.2 80.4A81.2 81.2 0 0 0 19.1 92.9Z" fill="#ff6a1a"/><path class="seg" style="--i:4" d="M190.2 77.5A93 93 0 0 1 192.6 91.9L180.9 92.9A81.2 81.2 0 0 0 178.8 80.4Z" fill="#8c9fff"/><path class="seg" style="--i:5" d="M7.7 111.3A93 93 0 0 1 7.1 96.8L17.6 97.1A82.5 82.5 0 0 0 18.1 110.1Z" fill="#ff7c1c"/><path class="seg" style="--i:5" d="M192.9 96.8A93 93 0 0 1 192.3 111.3L181.9 110.1A82.5 82.5 0 0 0 182.4 97.1Z" fill="#a5b4ff"/><path class="seg" style="--i:6" d="M12.1 130.3A93 93 0 0 1 8.4 116.1L17.5 114.6A83.8 83.8 0 0 0 20.8 127.3Z" fill="#ff8d1d"/><path class="seg" style="--i:6" d="M191.6 116.1A93 93 0 0 1 187.9 130.3L179.2 127.3A83.8 83.8 0 0 0 182.5 114.6Z" fill="#bdc8ff"/><path class="seg" style="--i:7" d="M20.3 147.9A93 93 0 0 1 13.8 134.8L21.1 131.9A85.1 85.1 0 0 0 27.1 143.8Z" fill="#ff9e1e"/><path class="seg" style="--i:7" d="M186.2 134.8A93 93 0 0 1 179.7 147.9L172.9 143.8A85.1 85.1 0 0 0 178.9 131.9Z" fill="#d6dcff"/><path class="seg" style="--i:8" d="M32.0 163.4A93 93 0 0 1 22.9 152.0L28.4 148.3A86.4 86.4 0 0 0 36.8 158.9Z" fill="#ffb020"/><path class="seg" style="--i:8" d="M177.1 152.0A93 93 0 0 1 168.0 163.4L163.2 158.9A86.4 86.4 0 0 0 171.6 148.3Z" fill="#eef1ff"/><g fill="#9aa0a8"><rect x="97" y="9" width="2.4" height="11" rx="1"/><rect x="101" y="9" width="2.4" height="11" rx="1"/><rect x="98.8" y="180" width="2.4" height="11" rx="1"/><rect x="9" y="98.8" width="11" height="2.4" rx="1"/><rect x="180" y="98.8" width="11" height="2.4" rx="1"/></g><circle class="lcd" cx="100" cy="100" r="58" fill="url(#lcd)"/><g clip-path="url(#lcd-clip)"><rect class="scanl" x="40" y="36" width="120" height="10" fill="url(#scan-g)"/></g><g class="sweep"><circle cx="100" cy="4.5" r="2.6" fill="#fff"/></g><g class="lcd-txt" fill="#0a2a0c" font-family="ui-monospace,Menlo,Consolas,monospace" text-anchor="middle"><text x="100" y="66" font-size="6.5" font-weight="700">G-WATCH 007</text><text x="100" y="75" font-size="5.2">MISSION STATUS : <tspan class="blink">ACTIVE</tspan></text><text class="clock" x="100" y="108" font-size="27" font-weight="700">00:07</text><text class="date" x="100" y="121" font-size="7">MI6 · N64</text><text x="100" y="136" font-size="5.2"><tspan class="m m1">WATCH</tspan> · <tspan class="m m2">LASER</tspan> · <tspan class="m m3">MAGNET</tspan></text></g></svg>'),
            "pd": '<div class="deco hud" aria-hidden="true"></div>' + '<svg class="deco dial radar" viewBox="0 0 200 200" width="240" height="240" aria-hidden="true"><defs><radialGradient id="rd-bg" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#0c1e3a"/><stop offset="1" stop-color="#05080f"/></radialGradient><linearGradient id="rd-sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3dff7a" stop-opacity="0"/><stop offset="1" stop-color="#3dff7a" stop-opacity=".55"/></linearGradient><clipPath id="rd-clip"><circle cx="100" cy="100" r="84"/></clipPath></defs><circle cx="100" cy="100" r="99" fill="#06090f" stroke="rgba(61,139,255,.55)" stroke-width="2"/><g class="ring" stroke="#3d8bff" stroke-width="1.4" opacity=".8"><line x1="100" y1="4" x2="100" y2="12" transform="rotate(0 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(6 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(12 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(18 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(24 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(30 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(36 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(42 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(48 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(54 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(60 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(66 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(72 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(78 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(84 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(90 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(96 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(102 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(108 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(114 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(120 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(126 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(132 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(138 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(144 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(150 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(156 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(162 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(168 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(174 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(180 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(186 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(192 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(198 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(204 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(210 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(216 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(222 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(228 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(234 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(240 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(246 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(252 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(258 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(264 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(270 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(276 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(282 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(288 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(294 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(300 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(306 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(312 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(318 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(324 100 100)"/><line x1="100" y1="4" x2="100" y2="12" transform="rotate(330 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(336 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(342 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(348 100 100)"/><line x1="100" y1="7" x2="100" y2="12" transform="rotate(354 100 100)"/></g><circle cx="100" cy="100" r="84" fill="url(#rd-bg)" stroke="#3d8bff" stroke-opacity=".6"/><g clip-path="url(#rd-clip)"><g fill="none" stroke="#3d8bff" stroke-opacity=".35"><circle cx="100" cy="100" r="28"/><circle cx="100" cy="100" r="50"/><circle cx="100" cy="100" r="70"/><path d="M16 100H184M100 16V184" stroke-dasharray="2 4"/></g><g class="sweep-w"><path d="M100 100L184 100A84 84 0 0 0 159.4 40.6Z" fill="url(#rd-sw)"/><line x1="100" y1="100" x2="184" y2="100" stroke="#3dff7a" stroke-width="1.6"/></g><g fill="#3dff7a"><circle class="blip" style="--d:0.4s" cx="126.0" cy="55.0" r="2.6"/><circle class="blip" style="--d:1.6s" cx="131.9" cy="111.6" r="2.6"/><circle class="blip" style="--d:2.5s" cx="54.0" cy="138.6" r="2.6"/><circle class="blip" style="--d:3.3s" cx="71.7" cy="66.3" r="2.6"/><circle class="blip" style="--d:1.0s" cx="93.9" cy="169.7" r="2.6"/></g><rect class="hscan" x="16" y="16" width="168" height="2" fill="#9fd0ff" opacity=".5"/></g><polygon class="hex" points="100.0,78.0 119.1,89.0 119.1,111.0 100.0,122.0 80.9,111.0 80.9,89.0" fill="rgba(61,139,255,.15)" stroke="#9fd0ff" stroke-width="1.4"/><circle class="core" cx="100" cy="100" r="6" fill="#3dff7a"/><g font-family="ui-monospace,Menlo,Consolas,monospace" text-anchor="middle" fill="#9fd0ff"><text x="100" y="40" font-size="6.5" font-weight="700" letter-spacing="1.5">CARRINGTON</text><text x="100" y="166" font-size="5.6" letter-spacing="1">SCAN <tspan class="blink" fill="#3dff7a">● ACTIF</tspan></text></g></svg>'}


def build_hub(g, pages, idx):
    gslug, gname = GAMES[g]
    cur_out = gslug + "/index.html"
    link = Linker(pages, gslug + "/index.htm")
    blocks = []
    if g == "plus":
        blocks.append(group_links(idx["plus"][None], cur_out, pages, icons=True, game="plus"))
        toc = ""
    else:
        present = [(k, n, a) for k, n, a in GROUPS if k in idx[g]]
        toc = '<nav class="jump" aria-label="Thèmes">' + "".join(f'<a href="#{a}">{icon(GROUP_ICON[k])}{n}</a>' for k, n, a in present) + "</nav>"
        for k, n, a in present:
            paths = idx[g][k]
            cls = ' class="pd"' if g == "pd" else ""
            blocks.append(f'<section class="theme" id="{a}"><h2{cls}>{icon(GROUP_ICON[k])}{n} <span class="count">{len(paths)}</span></h2>'
                          + group_links(paths, cur_out, pages, numbered=(k == "soluce"), game=g) + "</section>")
    head = (f'<div class="page-head has-banner"{banner_style(cur_out, GAME_ART[g])}><div class="wrap">'
            f'<div class="crumbs"><a href="../">Accueil</a></div>'
            f'<h1>{gname}</h1><p class="lead">{GAME_INTRO[g]}</p>{toc}</div>{HUB_DECO.get(g, "")}</div>')
    inner = head + '<div class="wrap hub">' + "".join(blocks) + "</div>"
    return layout(link, gname, inner, g, g if g != "plus" else "")




CART_H = {"ge": 730, "pd": 730}


def build_home(pages, idx):
    link = Linker(pages, "index.htm")
    cards = []
    for g in ("ge", "pd"):
        gslug, gname = GAMES[g]
        themes = " · ".join(n for k, n, a in GROUPS if k in idx[g])
        count = len({p for v in idx[g].values() for p in v})
        cart_img = {"ge": "goldeneye", "pd": "perfect-dark"}[g]
        cards.append(f'<a class="game {g} tilt" href="{gslug}/"><span class="cart" style="--m:url(images/cartouches/{cart_img}.webp?v=2)">'
                     f'<img src="images/cartouches/{cart_img}.webp?v=2" alt="Cartouche Nintendo 64 de {gname}" width="1040" height="{CART_H[g]}" loading="lazy" decoding="async">'
                     f'</span>'
                     f'<span class="info"><h2>{icon(GAME_ICON[g])}{gname}</h2><p>{GAME_INTRO[g]}</p><p class="themes">{themes}</p>'
                     f'<span class="go">Jouer {icon("arrow-right")}</span></span></a>')
    plus = group_links(idx["plus"][None], "index.html", pages, icons=True, game="plus")
    n_img = sum(len(g["imgs"]) for v in IMG_PAGES.values() for g in v["groups"])
    stats = [(len(pages), "pages"), (n_img, "images"), (30, "challenges"), (2, "jeux cultes")]
    stats_html = "".join(f'<div class="stat"><b data-count="{n}">{n:,}</b><span>{l}</span></div>'.replace(",", "\u202f")
                         for n, l in stats)

    def row(paths, cls):
        imgs = "".join(f'<img src="{p}" alt="" loading="lazy" width="240" height="180">' for p in paths)
        # deux fois la même suite : le défilement boucle sans saut
        return f'<div class="marquee {cls}" aria-hidden="true"><div class="track">{imgs}{imgs}</div></div>'

    title = '<span class="ge">Goldeneye</span> <span class="amp">&amp;</span> <span class="pd">Perfect Dark</span>'
    holes = "".join(f'<i style="--x:{x}%;--y:{y}%;--n:{n}"></i>' for n, (x, y) in enumerate(
        [(64, 9), (74, 26), (89, 15), (82, 38), (95, 31)]))
    inner = f"""<section class="hero">
<div class="hero-bg" aria-hidden="true"><div class="half ge"{banner_style("index.html", GAME_ART["ge"])}></div><div class="half pd"{banner_style("index.html", GAME_ART["pd"])}></div></div>
<div class="holes" aria-hidden="true">{holes}</div>
<div class="wrap">
<p class="kicker"><span class="dot" aria-hidden="true"></span>Nintendo 64 · le site de Tim</p>
<h1>{title}</h1>
<p class="sub">Soluces, <strong>Battle</strong>, <strong>codes</strong>, versions <strong>beta</strong> et <strong>mystères</strong> : <strong>choisis ton jeu</strong>.</p>
<div class="stats">{stats_html}</div>
</div>
{row(existing(GE_SHOTS), "ge")}
{row(existing(PD_SHOTS), "pd rev")}
<div class="wrap"><div class="games">{"".join(cards)}</div></div>
</section>
<div class="wrap home-infos"><h2 class="section-title">Infos</h2>{plus}</div>"""
    return layout(link, "", inner, None, "", "")


def main():
    pages, order = read_pages()
    written = 0
    idx, where = build_index(pages, order)
    for path in order:
        html_text = build_page(path, pages[path], pages, order, idx, where)
        dest = ROOT / out_path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_text, encoding="utf-8")
        written += 1
    for g in GAMES:
        dest = ROOT / GAMES[g][0] / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(build_hub(g, pages, idx), encoding="utf-8")
    (ROOT / "index.html").write_text(build_home(pages, idx), encoding="utf-8")
    # plan du site pour les moteurs de recherche
    import datetime
    today = datetime.date.today().isoformat()
    urls = sorted(clean(str(f.relative_to(ROOT)).replace(os.sep, "/")) for f in ROOT.rglob("*.html")
                  if not any(part.startswith(".") or part in ("tools", "contenu", "fichiers") for part in f.relative_to(ROOT).parts))
    def prio(u):
        return "1.0" if u == "./" else "0.9" if u in ("goldeneye/", "perfect-dark/") else "0.6"
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"  <url><loc>{SITE_URL}{'' if u == './' else u}</loc><lastmod>{today}</lastmod><priority>{prio(u)}</priority></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    hidden = [p for p in order if p not in where]
    print("pages non rangées :", hidden)
    print(f"{written} pages + accueil générés.")


if __name__ == "__main__":
    main()
