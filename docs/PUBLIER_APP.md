# Publier l'app FicheGen sur l'App Store et Google Play

## Avant de commencer

- Le **site doit être en ligne en https** (voir `DEPLOIEMENT.md`) : l'app publiée parle à ce serveur.
- Dans `mobile/.env`, mets `EXPO_PUBLIC_API_URL=https://ton-site...`.
- Dans `mobile/app.json`, remplace `com.fichegen.app` par un identifiant à toi (ex. `com.tonnom.fichegen`). Il ne pourra plus changer après la première publication.

## Les comptes nécessaires

| Compte | Coût | Pour quoi |
|---|---|---|
| Expo (expo.dev) | gratuit pour commencer | construire l'app dans le cloud, même sans Mac |
| Apple Developer Program | 99 $ US / an | publier sur l'App Store (iPhone) |
| Google Play Console | 25 $ US une seule fois | publier sur Google Play (Android) |

Vérifie les prix actuels sur les sites officiels avant de payer.

## Construire et envoyer l'app (EAS)

Pas besoin de Mac : Expo construit l'app iPhone sur ses serveurs.

```bash
cd mobile
npx eas-cli@latest login
npx eas-cli@latest build:configure
npx eas-cli@latest build --platform android   # fichier pour Google Play
npx eas-cli@latest build --platform ios       # fichier pour l'App Store
npx eas-cli@latest submit --platform ios      # envoie à Apple pour la vérification
npx eas-cli@latest submit --platform android
```

Apple et Google vérifient l'app avant de l'accepter (quelques jours en général).

## ⚠️ Important : vendre des crédits dans l'app

Apple et Google exigent en général d'utiliser **leur propre système d'achat intégré** pour vendre du contenu numérique (comme des crédits) dans une app, et ils prennent une commission. Une app qui vend des crédits avec Stripe risque d'être **refusée**.

C'est pourquoi l'app est livrée avec `ACHATS_DANS_APP = false` (dans `mobile/src/config.ts`) :

- les étudiants utilisent dans l'app leurs fiches gratuites et les crédits de leur compte ;
- aucun bouton d'achat ni lien vers un paiement externe n'apparaît dans l'app.

Pour vendre des crédits dans l'app plus tard, il faudra ajouter l'achat intégré (par exemple avec la bibliothèque RevenueCat) et faire valider les crédits par le serveur. Les règles changent selon les pays et évoluent : relis les règles d'Apple et de Google avant de publier.

## Exigences des stores déjà prévues dans l'app

- Suppression du compte possible depuis l'app (exigée par Apple).
- Liens vers les conditions d'utilisation et la politique de confidentialité.
- Mot de passe jamais stocké sur le téléphone : seulement un jeton chiffré qui expire après 30 jours.

Il te faudra aussi : des captures d'écran, une courte description, une adresse de contact et l'URL de la politique de confidentialité (`https://ton-site/confidentialite`).
