# Mettre FicheGen en ligne

## 1. Publier le code sur GitHub

```bash
cd fichegen
git init
git add .
git status            # vérifie que .env N'APPARAÎT PAS dans la liste
git commit -m "Première version de FicheGen"
git branch -M main
git remote add origin https://github.com/<ton-compte>/fichegen.git
git push -u origin main
```

> Tu peux mettre le dépôt en **privé** au début. Le passer en public plus tard ne pose aucun problème, puisqu'aucun secret n'est dans le code.

## 2. Créer les comptes nécessaires

1. **Anthropic API** : https://console.anthropic.com
   - C'est un compte séparé de Claude Pro, facturé à l'usage.
   - Crée une clé dédiée au projet (*API Keys*).
   - Règle une **limite de dépenses mensuelle** (*Limits*), par exemple 20 $ au début.
2. **Stripe** : https://dashboard.stripe.com
   - Reste en **mode test** tant que tout n'est pas vérifié.
   - Récupère la clé `sk_test_...` (*Développeurs > Clés API*).

## 3. Héberger le site

### Option gratuite (pour démarrer) : Render + Neon

1. **Base de données** : crée un compte sur https://neon.com (offre gratuite), crée un projet, puis copie
   l'adresse de connexion (elle commence par `postgresql://`).
2. **Site** : sur https://render.com, connecte-toi avec GitHub, puis *New > Blueprint* et choisis le dépôt.
   Le fichier `render.yaml` configure tout. Colle l'adresse Neon dans `DATABASE_URL` et ta clé dans
   `ANTHROPIC_API_KEY`.

Limites de l'offre gratuite : le site s'endort après 15 minutes sans visite (le premier chargement
suivant prend environ une minute). Les comptes et crédits sont en sécurité dans Neon.
L'IA, elle, reste payante à l'usage (console Anthropic).

### Option payante (plus rapide, sans mise en veille)

Le `Dockerfile` installe tout, y compris LaTeX. N'importe quel hébergeur Docker convient : Render, Railway, Fly.io, ou un petit serveur DigitalOcean.

Exemple avec **Render** :

1. *New > Web Service* → connecte ton dépôt GitHub → environnement **Docker**.
2. Ajoute un **disque persistant** monté sur `/srv/donnees`, sinon les comptes sont perdus à chaque redémarrage.
3. Ajoute les variables d'environnement (voir `.env.example`) :
   `SECRET_KEY`, `ANTHROPIC_API_KEY`, `URL_SITE=https://ton-site.onrender.com`,
   `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `CONTACT_EMAIL`, `RESPONSABLE_RP`.
4. Déploie.

## 4. Brancher le webhook Stripe

1. Stripe > *Développeurs > Webhooks > Ajouter un endpoint*
2. URL : `https://ton-site/stripe/webhook`
3. Événements : `checkout.session.completed` et `checkout.session.async_payment_succeeded`
4. Copie le *Signing secret* (`whsec_...`) dans `STRIPE_WEBHOOK_SECRET`.
5. Fais un achat test avec la carte `4242 4242 4242 4242` (date future, n'importe quel CVC) et vérifie que les crédits arrivent.

En local, tu peux utiliser la CLI Stripe : `stripe listen --forward-to localhost:8000/stripe/webhook`.

## 5. Avant d'accepter de vrais paiements

- [ ] Tester avec 10 à 20 étudiants en mode test (et `CREDITS_GRATUITS` plus élevé si besoin)
- [ ] Mesurer le coût réel par fiche (colonnes `tokens_entree` et `tokens_sortie` de la table `generations`) et ajuster les prix dans `app/config.py`
- [ ] Compléter et faire relire `conditions.html` et `confidentialite.html` (date, hébergeur, adresse de contact)
- [ ] Choisir un nom commercial ; envisager l'immatriculation d'une entreprise individuelle (Registraire des entreprises du Québec)
- [ ] Vérifier les règles fiscales (TPS/TVQ : obligatoires au-delà de 30 000 $ de ventes sur 12 mois)
- [ ] Passer Stripe en mode réel (`sk_live_...`) et recréer le webhook en mode réel
- [ ] Faire une sauvegarde régulière de `donnees/fichegen.db`

## Ajuster le service

| Je veux… | Où |
|---|---|
| Changer le design des fiches | `fichegen/latex/preambule.tex` |
| Changer la façon dont l'IA rédige | `SYSTEME` dans `fichegen/generateur.py` |
| Changer les prix ou les packs | `PACKS` dans `app/config.py` |
| Changer les limites | variables `FICHES_PAR_HEURE`, `FICHES_PAR_JOUR_TOTAL`, `CREDITS_GRATUITS` |
| Changer de modèle d'IA | variable `CLAUDE_MODEL` |
