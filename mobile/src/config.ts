// Adresse du serveur FicheGen.
// En développement : http://<IP-de-ton-ordi>:8000 (pas "localhost" sur un vrai téléphone).
// En production : l'adresse https de ton site, définie dans le fichier mobile/.env :
//   EXPO_PUBLIC_API_URL=https://ton-site.onrender.com
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

// Les règles d'Apple et de Google interdisent de vendre des crédits numériques
// avec Stripe à l'intérieur d'une app (il faut leur système d'achat intégré).
// Laisse à false tant que l'achat intégré n'est pas mis en place.
export const ACHATS_DANS_APP = false;
