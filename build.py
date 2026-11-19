#!/usr/bin/env python3
"""Génère le site statique à partir des textes de contenu/pages-*.txt.

Format des fichiers de contenu :
  === chemin/original.htm      début d'une page (chemin sur le site d'origine)
  Titre de la page             ligne suivante
  ...                          corps en Markdown simplifié

Usage : python3 build.py   (écrit les pages HTML à la racine du dépôt)
"""
import html
import os
import posixpath
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "contenu"
ORIGIN = "http://floppycheese.free.fr/nintendo/"

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
    """Chemin d'origine normalisé → chemin du fichier généré."""
    if path.endswith("/"):
        return path + "index.html"
    base, _ = posixpath.splitext(path)
    return base + ".html"


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
        # fichier du site d'origine (image, mp3, zip, txt…) : lien vers l'original
        return ORIGIN + target + anchor, True

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
        return f'<a class="chip" href="{html.escape(href)}" target="_blank" rel="noopener">{label}</a>'

    text = re.sub(r"\x01([^\x02]+)\x02([^\x03]*)\x03", img_chip, text)

    def a(m):
        label, href = m.group(1), m.group(2)
        url, ext = link.resolve(html.unescape(href))
        if not label.strip():
            return ""
        attrs = ' target="_blank" rel="noopener"' if ext else ""
        return f'<a href="{html.escape(url)}"{attrs}>{label}</a>'

    text = re.sub(r"\[([^\]]*)\]\(([^)\s]*(?:\([^)]*\)[^)\s]*)*)\)", a, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)
    return text.strip()


HEX_LINE = re.compile(r"^\s*(P\d\s*[:\-]?\s*)?[0-9A-F]{3,4}\s?[0-9A-FX?\-]{4,5}\s*[0-9A-FX?]{2,4}\b", re.I)


def is_code_para(lines):
    plain = [re.sub(r"\*\*", "", l).strip() for l in lines if l.strip()]
    if not plain:
        return False
    hits = sum(1 for l in plain if HEX_LINE.match(l))
    return hits >= 2 and hits >= 0.6 * len(plain)


# ---------------------------------------------------------------- rendu bloc
def render_cards(lines, link, page_game):
    out = ['<div class="grid">']
    for line in lines:
        m = re.match(r"^\[(?:\{img:[^|}]+\|)?([^\]}]+)\}?\]\(([^)]+)\)\s*(.*)$", line.strip())
        if not m:
            continue
        label, href, desc = m.groups()
        url, ext = link.resolve(href)
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
            html_out.append("<p>" + "<br>".join(inline(l, link) for l in buf) + "</p>")

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
            html_out.append("<ul>" + "".join(f"<li>{inline(t, link)}</li>" for t in items) + "</ul>")
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


# ---------------------------------------------------------------- gabarit
def nav_html(link, current_section):
    r = link.root()
    items = []
    for key, title, _, _ in SECTIONS:
        on = ' class="on"' if key == current_section else ""
        items.append(f'<li><a href="{r}{key}/"{on}>{title}</a></li>')
    return "\n".join(items)


def layout(link, title, inner, section=None, game="", description=""):
    r = link.root()
    body_cls = f' class="theme-{game}"' if game else ""
    desc = html.escape(description or "Goldeneye 007 et Perfect Dark sur Nintendo 64 : soluces, battle, codes, beta, mystères.")
    page_title = html.escape(title) + (" · " if title else "") + "Goldeneye & Perfect Dark"
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/style.css">
</head>
<body{body_cls}>
<a class="skip" href="#contenu">Aller au contenu</a>
<header class="top">
  <div class="wrap">
    <a class="brand" href="{clean(r)}"><b>Golden</b>eye <span>&amp;</span> <i>Perfect</i> Dark</a>
    <button class="menu-btn" aria-expanded="false" aria-controls="menu">Menu</button>
  </div>
  <nav class="main" id="menu" aria-label="Sections"><ul>
{nav_html(link, section)}
  </ul></nav>
</header>
<main id="contenu">
{inner}
</main>
<footer>
  <div class="wrap">
    <p>Contenu écrit par <strong>Tim</strong> pour son site <a href="{ORIGIN}" target="_blank" rel="noopener">floppycheese.free.fr/nintendo</a>, remis en page en 2026. Goldeneye 007 et Perfect Dark sont des jeux Rare / Nintendo ; ce site de fan n'est affilié à aucune de ces sociétés.</p>
  </div>
</footer>
<script>
const b=document.querySelector('.menu-btn'),n=document.getElementById('menu');
b.addEventListener('click',()=>{{const o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)}});
</script>
</body>
</html>
"""


def original_box(page):
    url = ORIGIN + page["orig"].lstrip("./")
    return (f'<aside class="note"><p>Cette page reprend surtout des images. '
            f'Pour les voir, ouvrez <a href="{url}" target="_blank" rel="noopener">la page originale</a>.</p></aside>')


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


def build_page(path, page, pages, order):
    link = Linker(pages, path)
    section = section_of(path)
    game = game_of(path, page["title"])
    ctx = {"game": game, "ids": set()}
    body_html, headings = render_body(page["body"], link, ctx)

    def placeholder(m):
        key = m.group(1)
        if key == "{original}":
            return original_box(page)
        if key == "{mail}":
            return f'<p class="mail"><a class="btn" href="mailto:{MAIL}">Écrire à Tim</a></p>'
        if path == "soluce/":
            return soluce_cards(pages, link, "ge" if key == "{toc-ge}" else "pd", "ge" if key == "{toc-ge}" else "pd")
        if key == "{toc}":
            return toc_list(headings)
        return toc_list(headings, "goldeneye" if key == "{toc-ge}" else "perfect dark")

    body_html = re.sub(r"\x04(\{[a-z-]+\})\x04", placeholder, body_html)

    # fil d'Ariane
    r = link.root()
    crumbs = [f'<a href="{clean(r)}">Accueil</a>']
    is_index = path == section + "/"
    if not is_index and section in SECTION_TITLE:
        crumbs.append(f'<a href="{r}{section}/">{SECTION_TITLE[section]}</a>')

    # page précédente / suivante dans le même dossier
    pager = ""
    if not path.endswith("/"):
        d = posixpath.dirname(path)
        sib = [k for k in order if not k.endswith("/") and posixpath.dirname(k) == d]
        if path in sib and len(sib) > 1:
            idx = sib.index(path)
            parts = []
            if idx > 0:
                p = sib[idx - 1]
                parts.append(f'<a class="prev" href="{link.resolve(posixpath.relpath(p, d))[0]}">← {html.escape(pages[p]["title"])}</a>')
            else:
                parts.append("<span></span>")
            if idx < len(sib) - 1:
                p = sib[idx + 1]
                parts.append(f'<a class="next" href="{link.resolve(posixpath.relpath(p, d))[0]}">{html.escape(pages[p]["title"])} →</a>')
            pager = '<nav class="pager" aria-label="Pages voisines">' + "".join(parts) + "</nav>"

    orig_url = ORIGIN + page["orig"].lstrip("./")
    head = (f'<div class="page-head"><div class="wrap">'
            f'<div class="crumbs">{" › ".join(crumbs)}</div>'
            f'<h1>{inline(page["title"], link)}</h1></div></div>')
    inner = (head + f'<div class="wrap"><article class="content">{body_html}{pager}'
             f'<p class="source"><a href="{orig_url}" target="_blank" rel="noopener">Voir la page originale (avec images)</a></p>'
             f'</article></div>')
    return layout(link, page["title"], inner, section, game)


def build_home(pages):
    link = Linker(pages, "index.htm")
    cards = []
    for key, title, desc, g in SECTIONS:
        tag = {"ge": "Goldeneye", "pd": "Perfect Dark", "both": "Goldeneye · Perfect Dark"}[g]
        cls = "card pd" if g == "pd" else "card"
        cards.append(f'<a class="{cls}" href="{key}/"><span class="tag">{tag}</span><h3>{title}</h3><p>{desc}</p></a>')
    n = len(pages)
    inner = f"""<section class="hero"><div class="wrap">
<p class="kicker">Nintendo 64 · le site de Tim</p>
<h1><span class="ge">Goldeneye</span> &amp; <span class="pd">Perfect Dark</span></h1>
<p>Soluces complètes, arènes Battle passées au crible, codes durs à débloquer, versions beta, mystères et bidouilles à l'Action Replay. Tout le contenu du site original de Tim, dans une mise en page neuve.</p>
<div class="hero-links"><a class="btn" href="soluce/">Les soluces</a><a class="btn ghost" href="mysteres/">Les mystères</a></div>
</div></section>
<div class="wrap">
<h2 class="home-h2">Les sections</h2>
<div class="grid">
{chr(10).join(cards)}
</div>
<p class="muted">{n} pages de texte. Les images n'ont pas été recopiées : chaque page renvoie vers son original pour les voir.</p>
</div>"""
    return layout(link, "", inner, None, "", "")


def main():
    pages, order = read_pages()
    written = 0
    for path in order:
        html_text = build_page(path, pages[path], pages, order)
        dest = ROOT / out_path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_text, encoding="utf-8")
        written += 1
    (ROOT / "index.html").write_text(build_home(pages), encoding="utf-8")
    print(f"{written} pages + accueil générés.")


if __name__ == "__main__":
    main()
