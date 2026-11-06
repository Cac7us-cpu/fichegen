import { useColorScheme } from 'react-native';

const clair = {
  fond: '#f7f8fa',
  carte: '#ffffff',
  texte: '#1b2430',
  doux: '#5b6675',
  ligne: '#e3e7ed',
  accent: '#1f4e79',
  surAccent: '#ffffff',
  succes: '#2e7d32',
  danger: '#b71c1c',
  messageFond: '#e3ebf3',
};

const sombre: typeof clair = {
  fond: '#0f141a',
  carte: '#171e27',
  texte: '#e6ebf1',
  doux: '#9aa6b4',
  ligne: '#26303c',
  accent: '#6aa7e0',
  surAccent: '#0f141a',
  succes: '#6cc070',
  danger: '#ef7b7b',
  messageFond: '#1c2a3a',
};

export type Couleurs = typeof clair;

export function useCouleurs(): Couleurs {
  return useColorScheme() === 'dark' ? sombre : clair;
}
