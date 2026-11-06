# FicheGen — application mobile (iPhone et Android)

L'application est faite avec **Expo** (React Native). Un seul code fonctionne sur iPhone et sur Android.
Elle utilise le serveur FicheGen (dossier parent) à travers son API (`/api/...`).

## Ce que fait l'app

1. Créer un compte ou se connecter (la session reste enregistrée de façon chiffrée sur le téléphone).
2. Choisir ses diapos (PDF ou PowerPoint) depuis Fichiers, Google Drive, etc.
3. Choisir le niveau de détail et la langue, puis lancer la génération.
4. Suivre la progression, puis ouvrir ou enregistrer la fiche PDF (Fichiers, Drive, envoi à un ami…).
5. Voir ses crédits, se déconnecter et supprimer son compte.

## L'essayer sur ton téléphone (gratuit, 10 minutes)

1. Installe l'app **Expo Go** sur ton téléphone (App Store ou Google Play).
2. Lance le serveur FicheGen sur ton ordi (voir le README principal) **sur le réseau local** :
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
3. Trouve l'adresse IP de ton ordi : `hostname -I` (sous Ubuntu), par exemple `192.168.1.20`.
4. Dans le dossier `mobile` :
   ```bash
   cp .env.example .env        # puis mets EXPO_PUBLIC_API_URL=http://192.168.1.20:8000
   npm install
   npx expo start
   ```
5. Scanne le QR code affiché avec l'appareil photo (iPhone) ou avec Expo Go (Android).

Le téléphone et l'ordi doivent être sur le même réseau Wi-Fi.

## Commandes utiles

```bash
npm run typecheck     # vérifie le code TypeScript
npx expo start --web  # aperçu dans le navigateur (ajoute CORS_ORIGINES=http://localhost:8081 côté serveur)
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `App.tsx` | Tous les écrans : connexion, nouvelle fiche, attente, fiche prête, compte |
| `src/api.ts` | Appels au serveur (envoi des diapos, suivi, téléchargement du PDF) |
| `src/config.ts` | **Adresse du serveur** et activation des achats |
| `src/stockage.ts` | Jeton de connexion rangé dans le trousseau chiffré du téléphone |
| `src/composants.tsx` | Boutons, champs, cartes |
| `src/theme.ts` | Couleurs (mode clair et sombre automatique) |
| `app.json` | Nom de l'app, icône, identifiants pour l'App Store et Google Play |

Pour publier l'app sur les stores, voir [`../docs/PUBLIER_APP.md`](../docs/PUBLIER_APP.md).
