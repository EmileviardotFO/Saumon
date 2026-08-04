# Suivi de l'offre norvégienne de saumon

Deux tableaux de bord, mis à jour depuis n'importe quel ordinateur, sans rien
installer.

- **docs/production.html** — biomasse, cohortes, ratios structurels, projection
  d'abattage, calibres et primes, par zone de production.
- **docs/fenetre.html** — la fenêtre 6+ : calendrier saisonnier, prévision à un
  mois, prime par calibre, signal hebdomadaire.

---

## Installation, une seule fois

### 1. Créer le dépôt

Sur github.com, bouton **New repository**.

- Nom : `saumon`
- **Public** (voir la note sur la confidentialité plus bas)
- Cocher *Add a README file*

### 2. Déposer les fichiers

Bouton **Add file → Upload files**, puis glisser tout le contenu de ce dossier
en conservant la structure :

```
data/data.json
docs/production.html
docs/fenetre.html
scripts/parse_akvafakta.py
.github/workflows/update.yml
pdf/uke/          (rapports hebdomadaires)
pdf/mane/         (rapports mensuels)
```

### 3. Activer la publication

**Settings → Pages**. Sous *Source*, choisir **Deploy from a branch**, branche
`main`, dossier `/ (root)`. Enregistrer.

Après deux ou trois minutes, les tableaux de bord sont en ligne :

- https://emileviardotfo.github.io/saumon/docs/production.html
- https://emileviardotfo.github.io/saumon/docs/fenetre.html

Mets ces deux adresses en favori. Elles fonctionnent sur n'importe quel poste,
y compris le téléphone.

### 4. Autoriser la mise à jour automatique

**Settings → Actions → General**, section *Workflow permissions* : cocher
**Read and write permissions**, puis enregistrer. Sans ça le robot ne peut pas
publier les données qu'il vient de calculer.

---

## Mise à jour hebdomadaire

1. Ouvrir le dépôt dans le navigateur, aller dans `pdf/uke/`
2. **Add file → Upload files**, déposer le nouveau PDF
3. **Commit changes**

C'est tout. Le robot parse le fichier et publie les données ; le tableau de
bord est à jour deux à trois minutes plus tard.

Le nom du fichier doit suivre le format `Akvafakta 26-31.pdf` — année sur deux
chiffres, tiret, numéro de semaine. C'est le nom d'origine, il n'y a rien à
renommer.

**Rapports mensuels** : même chose dans `pdf/mane/`, format `2607_Akvafakta.pdf`.

### Vérifier que ça a marché

Onglet **Actions** du dépôt. Une coche verte signifie que c'est passé. En cas
de croix rouge, cliquer dessus donne le message d'erreur — le plus souvent un
nom de fichier hors format.

---

## Si quelque chose ne va pas

**Le tableau de bord affiche un bandeau orange « Hors ligne ».** Il n'a pas pu
joindre `data.json` et utilise les données embarquées, qui datent de sa
génération. Vérifier que GitHub Pages est bien activé et que l'adresse du
dépôt est bien `saumon`. Le tableau reste utilisable, simplement figé.

**Un rapport est ignoré.** Le journal indique `ATTENTION, rien extrait`. Sjømat
Norge a probablement changé la mise en page — c'est déjà arrivé trois fois
depuis 2018. Le fichier `scripts/parse_akvafakta.py` documente les pièges
connus ; il faudra l'ajuster.

**Une valeur paraît aberrante.** C'est arrivé pour de vrai : décembre 2022
déclare 50 M de smolts alors que le stock baisse. Les données sources ne sont
pas toujours cohérentes. Voir la note du tableau *Multi-year comparison*.

---

## Confidentialité

GitHub Pages ne publie pas les dépôts privés en offre gratuite. Le dépôt doit
donc être public pour que les tableaux fonctionnent.

Ce qui s'y trouve est **public à la source** : Akvafakta est diffusé par Sjømat
Norge, le Biomasseregisteret par Fiskeridirektoratet. Ce qui a de la valeur,
c'est l'assemblage et les analyses — pas les données brutes.

En revanche, **n'ajoute jamais ici de données Hiddenfjord** : volumes, coûts,
plans d'abattage, contrats. Si tu veux croiser ces éléments un jour, il faudra
un dépôt privé et un autre mode d'hébergement.

---

## Mise à jour manuelle, sans le robot

Si tu veux parser en local, il faut Python 3 et `pdftotext` :

```bash
brew install poppler          # macOS
python3 scripts/parse_akvafakta.py
```

Le script ne retraite que les fichiers absents du JSON : le relancer plusieurs
fois ne coûte rien et ne duplique rien.

---

## Sources

- **Fiskeridirektoratet, Biomasseregisteret** — biomasse, effectifs, mortalité,
  mises à l'eau, abattages, par zone de production et par mois.
- **Akvafakta, Sjømat Norge** — hebdomadaire (répartition par classe de poids,
  prix par calibre, volumes exportés) et mensuel (biomasse, exports par pays,
  aliment, température).

Deux ruptures de série à garder en tête :

- L'indice de prix passe de **NASDAQ à Sitagri en semaine 18 de 2025**. Écart
  mesuré : 84 g sur le poids moyen implicite. Le champ `src` de chaque semaine
  indique la source.
- Le champ `utsett` (mises à l'eau déclarées) **diverge de plus en plus** du
  bilan de masse : environ +12 % d'écart en 2018, +45 % en 2024-2025. Le
  tableau *Multi-year* affiche les deux séries côte à côte pour cette raison.
