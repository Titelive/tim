# Goldeneye & Perfect Dark, le site de Tim

Remise en page moderne du site de fan [floppycheese.free.fr/nintendo](http://floppycheese.free.fr/nintendo/), consacré à Goldeneye 007 et Perfect Dark sur Nintendo 64 : soluces, arènes Battle, codes, 30 challenges, versions beta, mystères, Action Replay, émulation…

## Ce qu'il y a dedans

- **187 pages** reprenant tout le texte du site d'origine, réparties dans les mêmes 13 sections.
- Un design sombre (ou clair, selon le réglage de l'appareil), lisible sur mobile, avec un menu, un fil d'Ariane, des sommaires et des liens « page précédente / suivante ».
- **Les images du site d'origine** (plus de 2 000 captures) sont replacées dans le texte, à l'endroit où elles étaient, en galeries qu'on peut agrandir. Les autres fichiers (MP3, ZIP, codes .txt) pointent vers le site d'origine.

## Organisation

- `contenu/pages-*.txt` : le texte de toutes les pages, en Markdown simplifié. Chaque page commence par `=== chemin/original.htm` puis son titre.
- `build.py` : génère les pages HTML à partir de ces textes (Python 3, sans dépendance).
- `images/` : les images du site d'origine ; `contenu/images.json` dit où les placer dans chaque page.
- `tools/images.py` : refait `images/` et `contenu/images.json` à partir d'une copie du site d'origine (branche `source-originale`).
- `assets/style.css` et `assets/site.js` : la feuille de style et les scripts.
- `index.html` et les dossiers de sections : le site généré.

## Modifier le site

1. Éditer le texte dans `contenu/`.
2. Lancer `python3 build.py`.
3. Ouvrir `index.html` dans un navigateur.

## Mise en ligne

Le site est 100 % statique. Il est publié sur [titelive.me/tim](https://titelive.me/tim/), via le dossier `tim/` du dépôt titelive.
