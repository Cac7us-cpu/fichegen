// Stockage sécurisé du jeton de connexion.
// iPhone/Android : trousseau chiffré du téléphone (SecureStore).
// Navigateur (aperçu de développement) : localStorage.
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const CLE = 'fichegen_jeton';

export async function lireJeton(): Promise<string | null> {
  try {
    if (Platform.OS === 'web') return globalThis.localStorage?.getItem(CLE) ?? null;
    return await SecureStore.getItemAsync(CLE);
  } catch {
    return null;
  }
}

export async function enregistrerJeton(jeton: string): Promise<void> {
  try {
    if (Platform.OS === 'web') globalThis.localStorage?.setItem(CLE, jeton);
    else await SecureStore.setItemAsync(CLE, jeton);
  } catch {
    // sans stockage, l'utilisateur devra simplement se reconnecter
  }
}

export async function effacerJeton(): Promise<void> {
  try {
    if (Platform.OS === 'web') globalThis.localStorage?.removeItem(CLE);
    else await SecureStore.deleteItemAsync(CLE);
  } catch {
    // rien à faire
  }
}
