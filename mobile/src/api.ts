// Appels au serveur FicheGen (voir app/api.py côté serveur).
import { Platform } from 'react-native';
import { File, Paths } from 'expo-file-system';
import type { DocumentPickerAsset } from 'expo-document-picker';
import { API_URL } from './config';

export type Pack = { id: string; nom: string; credits: number; prix: number };
export type Profil = {
  email: string;
  credits: number;
  paiement_actif: boolean;
  packs: Pack[];
  niveaux: string[];
  taille_max_mo: number;
};
export type Statut = { statut: 'en_cours' | 'termine' | 'echec'; etape: string; erreur: string | null; nom: string };

export class ErreurApi extends Error {
  constructor(message: string, public code: number) {
    super(message);
  }
}

async function appel<T>(chemin: string, jeton: string | null, init: RequestInit = {}): Promise<T> {
  const entetes: Record<string, string> = { Accept: 'application/json' };
  if (jeton) entetes.Authorization = `Bearer ${jeton}`;
  if (init.body && typeof init.body === 'string') entetes['Content-Type'] = 'application/json';
  let rep: Response;
  try {
    rep = await fetch(API_URL + chemin, { ...init, headers: { ...entetes, ...(init.headers as object) } });
  } catch {
    throw new ErreurApi('Impossible de joindre le serveur. Vérifie ta connexion Internet.', 0);
  }
  let corps: any = null;
  try {
    corps = await rep.json();
  } catch {
    // réponse vide ou non JSON
  }
  if (!rep.ok) throw new ErreurApi(corps?.detail ?? `Erreur ${rep.status}`, rep.status);
  return corps as T;
}

export const api = {
  inscription: (email: string, mdp: string, accepte: boolean) =>
    appel<{ jeton: string; profil: Profil }>('/api/inscription', null, {
      method: 'POST',
      body: JSON.stringify({ email, mdp, accepte }),
    }),

  connexion: (email: string, mdp: string) =>
    appel<{ jeton: string; profil: Profil }>('/api/connexion', null, {
      method: 'POST',
      body: JSON.stringify({ email, mdp }),
    }),

  moi: (jeton: string) => appel<Profil>('/api/moi', jeton),

  generer: (jeton: string, fichier: DocumentPickerAsset, options: { titre: string; niveau: string; langue: string }) => {
    const form = new FormData();
    if (Platform.OS === 'web' && fichier.file) {
      form.append('fichier', fichier.file, fichier.name);
    } else {
      // Format React Native : le fichier est lu directement depuis le téléphone pendant l'envoi.
      form.append('fichier', {
        uri: fichier.uri,
        name: fichier.name,
        type: fichier.mimeType ?? 'application/octet-stream',
      } as unknown as Blob);
    }
    form.append('nom', fichier.name);
    form.append('titre', options.titre);
    form.append('niveau', options.niveau);
    form.append('langue', options.langue);
    return appel<{ id: string }>('/api/generer', jeton, { method: 'POST', body: form });
  },

  statut: (jeton: string, id: string) => appel<Statut>(`/api/fiche/${id}`, jeton),

  acheter: (jeton: string, pack: string) => appel<{ url: string }>(`/api/acheter/${pack}`, jeton, { method: 'POST' }),

  supprimerCompte: (jeton: string) => appel<{ supprime: boolean }>('/api/compte', jeton, { method: 'DELETE' }),

  /** Télécharge le PDF. Renvoie un chemin local (téléphone) ou une URL blob (navigateur). */
  async telechargerPdf(jeton: string, id: string, nom: string): Promise<string> {
    const url = `${API_URL}/api/fiche/${id}/pdf`;
    if (Platform.OS === 'web') {
      const rep = await fetch(url, { headers: { Authorization: `Bearer ${jeton}` } });
      if (!rep.ok) throw new ErreurApi('La fiche a expiré ou est introuvable.', rep.status);
      return URL.createObjectURL(await rep.blob());
    }
    const destination = new File(Paths.document, `${nom || 'fiche'}_fiche.pdf`);
    if (destination.exists) destination.delete();
    const tache = File.createDownloadTask(url, destination, { headers: { Authorization: `Bearer ${jeton}` } });
    const fichier = await tache.downloadAsync();
    if (!fichier) throw new ErreurApi('Téléchargement interrompu.', 0);
    return fichier.uri;
  },
};
