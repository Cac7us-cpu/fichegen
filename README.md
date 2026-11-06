# FicheGen

**Tes diapos de cours deviennent une fiche de révision LaTeX en 2 minutes.**

L'étudiant dépose le PDF ou le PowerPoint de son cours. L'IA (Claude, d'Anthropic) en tire une fiche structurée : définitions, formules, méthodes, exemples, pièges fréquents et résumé. Le résultat est mis en page en LaTeX et téléchargé en PDF.

Le projet contient :

- **un site web** avec comptes, fiches gratuites à l'inscription, crédits payants (Stripe) et limites anti-abus ;
- **une commande terminal** `fiche` pour générer une fiche directement depuis ton ordi ;
- **une application mobile** iPhone et Android (dossier [`mobile/`](mobile/README.md)).

---

## Démarrage rapide (en local, sur Ubuntu)

```bash
# 1. Outils nécessaires
sudo apt install python3-venv texlive-latex-extra texlive-lang-french lmodern

# 2. Installation
git clone https://github.com/<ton-compte>/fichegen.git
cd fichegen
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # colle le résultat dans SECRET_KEY
# (optionnel) ajoute ta clé ANTHROPIC_API_KEY ; sans clé, le site tourne en mode démo

# 4. Lancement
uvicorn app.main:app --reload
```

Ouvre http://localhost:8000, crée un compte et dépose un PDF.

### La commande `fiche` (terminal)

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
fiche diapos_chapitre3.pdf --niveau standard --titre "Macro – Chapitre 3" --tex
```

Options : `-n synthetique|standard|detaille`, `-l anglais`, `-o sortie.pdf`, `--tex` (garde le `.tex`).

---

## Comment ça marche

```
Diapos (PDF/PPTX) ──► extraction ──► Claude rédige le CORPS LaTeX
                                          │
                     préambule fixe ◄─────┘   (couleurs, encadrés, maths)
                          │
                    pdflatex sécurisé ──► erreur ? ──► Claude corrige (2 essais max)
                          │
                         PDF ──► téléchargement (30 min) ──► effacé
```

| Dossier | Rôle |
|---|---|
| `fichegen/extraction.py` | Lecture des PDF et PowerPoint |
| `fichegen/generateur.py` | Prompt, appel à Claude, boucle de correction |
| `fichegen/latex.py` | Assemblage et compilation **sécurisée** |
| `fichegen/latex/preambule.tex` | **Le style des fiches** : modifie-le pour changer le design |
| `app/` | Site web (FastAPI) : comptes, crédits, Stripe, pages |
| `app/api.py` | API pour l'application mobile (connexion par jeton) |
| `mobile/` | Application iPhone / Android (Expo) |
| `tests/` | Tests automatiques (`pytest`) |

## Sécurité et confidentialité

- **Clés secrètes** : uniquement dans `.env` (ignoré par Git) ou dans les variables de l'hébergeur. Jamais dans le code.
- **LaTeX piégé** : l'IA ne génère que le corps. Les commandes qui lisent ou écrivent des fichiers (`\input`, `\write`, `\def`…) sont refusées, et `pdflatex` tourne sans shell, avec la lecture limitée à son dossier temporaire et un délai maximum.
- **Injection de consignes** : le prompt indique à l'IA que le contenu des diapos n'est jamais une instruction.
- **Données** : les diapos et les fiches ne sont jamais écrites sur le disque ni conservées. La base ne contient que les comptes, les crédits et les achats.
- **Paiement** : géré par Stripe Checkout. Les crédits sont ajoutés seulement par le webhook signé, une seule fois par paiement.
- **Budget** : limites par heure et par utilisateur, plafond global par jour, crédit remboursé en cas d'échec. Fixe aussi une **limite de dépenses** dans la console Anthropic.
- **Loi 25** : politique de confidentialité, responsable désigné, suppression du compte en un clic.

## Déploiement

Voir [`docs/DEPLOIEMENT.md`](docs/DEPLOIEMENT.md) : hébergement avec Docker, configuration de Stripe, liste de vérification avant lancement.

Pour l'application mobile : [`docs/PUBLIER_APP.md`](docs/PUBLIER_APP.md).

## Tests

```bash
pip install pytest httpx
pytest -q
```

## Licence

Code sous licence MIT. Les fiches générées appartiennent à leurs utilisateurs, dans le respect des droits sur le matériel de cours d'origine.
