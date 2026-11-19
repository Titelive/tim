# Goldeneye & Perfect Dark, le site de Tim

Remise en page moderne du site de fan [floppycheese.free.fr/nintendo](http://floppycheese.free.fr/nintendo/), consacré à Goldeneye 007 et Perfect Dark sur Nintendo 64 : soluces, arènes Battle, codes, 30 challenges, versions beta, mystères, Action Replay, émulation…

## Ce qu'il y a dedans

- **187 pages** reprenant tout le texte du site d'origine, réparties dans les mêmes 13 sections.
- Un design sombre (ou clair, selon le réglage de l'appareil), lisible sur mobile, avec un menu, un fil d'Ariane, des sommaires et des liens « page précédente / suivante ».
- Les images n'ont pas été recopiées. Chaque page a un lien « Voir la page originale (avec images) », et les fichiers (MP3, ZIP, codes .txt) pointent vers le site d'origine.

## Organisation

- `contenu/pages-*.txt` : le texte de toutes les pages, en Markdown simplifié. Chaque page commence par `=== chemin/original.htm` puis son titre.
- `build.py` : génère les pages HTML à partir de ces textes (Python 3, sans dépendance).
- `assets/style.css` : la feuille de style.
- `index.html` et les dossiers de sections : le site généré.

## Modifier le site

1. Éditer le texte dans `contenu/`.
2. Lancer `python3 build.py`.
3. Ouvrir `index.html` dans un navigateur.

## Mise en ligne

Le site est 100 % statique. Pour le publier avec GitHub Pages : *Settings › Pages › Deploy from a branch*, branche `main`, dossier `/ (root)`.
