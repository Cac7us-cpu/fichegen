import { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';
import { useCouleurs } from './theme';

export function Bouton(props: {
  titre: string;
  onPress: () => void;
  variante?: 'principal' | 'secondaire' | 'danger' | 'lien';
  charge?: boolean;
  desactive?: boolean;
}) {
  const c = useCouleurs();
  const v = props.variante ?? 'principal';
  const fond = v === 'principal' ? c.accent : v === 'danger' ? c.danger : 'transparent';
  const texte = v === 'principal' || v === 'danger' ? c.surAccent : v === 'lien' ? c.doux : c.accent;
  const inactif = props.desactive || props.charge;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={props.onPress}
      disabled={inactif}
      style={({ pressed }) => [
        styles.bouton,
        { backgroundColor: fond, opacity: inactif ? 0.55 : pressed ? 0.8 : 1 },
        v === 'secondaire' && { borderWidth: 1, borderColor: c.ligne },
        v === 'lien' && { paddingVertical: 8 },
      ]}
    >
      {props.charge ? (
        <ActivityIndicator color={texte} />
      ) : (
        <Text style={[styles.boutonTexte, { color: texte }]}>{props.titre}</Text>
      )}
    </Pressable>
  );
}

export function Champ(props: TextInputProps & { etiquette: string }) {
  const c = useCouleurs();
  const { etiquette, style, ...reste } = props;
  return (
    <View style={{ marginBottom: 14 }}>
      <Text style={[styles.etiquette, { color: c.texte }]}>{etiquette}</Text>
      <TextInput
        placeholderTextColor={c.doux}
        style={[styles.champ, { borderColor: c.ligne, backgroundColor: c.fond, color: c.texte }, style]}
        {...reste}
      />
    </View>
  );
}

export function Carte({ children }: { children: ReactNode }) {
  const c = useCouleurs();
  return <View style={[styles.carte, { backgroundColor: c.carte, borderColor: c.ligne }]}>{children}</View>;
}

export function Message({ texte, type = 'info' }: { texte: string | null; type?: 'info' | 'erreur' }) {
  const c = useCouleurs();
  if (!texte) return null;
  return (
    <View style={[styles.message, { backgroundColor: type === 'erreur' ? c.danger + '22' : c.messageFond }]}>
      <Text style={{ color: type === 'erreur' ? c.danger : c.texte }}>{texte}</Text>
    </View>
  );
}

export function Choix<T extends string>(props: {
  etiquette: string;
  options: { valeur: T; libelle: string }[];
  valeur: T;
  onChange: (v: T) => void;
}) {
  const c = useCouleurs();
  return (
    <View style={{ marginBottom: 14 }}>
      {!!props.etiquette && <Text style={[styles.etiquette, { color: c.texte }]}>{props.etiquette}</Text>}
      <View style={[styles.choixRangee, { borderColor: c.ligne, backgroundColor: c.fond }]}>
        {props.options.map((o) => {
          const actif = o.valeur === props.valeur;
          return (
            <Pressable
              key={o.valeur}
              accessibilityRole="button"
              accessibilityState={{ selected: actif }}
              onPress={() => props.onChange(o.valeur)}
              style={[styles.choix, actif && { backgroundColor: c.accent }]}
            >
              <Text style={{ color: actif ? c.surAccent : c.texte, fontWeight: '600', fontSize: 14 }}>{o.libelle}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bouton: { borderRadius: 12, paddingVertical: 14, paddingHorizontal: 18, alignItems: 'center', marginVertical: 6 },
  boutonTexte: { fontSize: 16, fontWeight: '700' },
  etiquette: { fontWeight: '600', marginBottom: 6, fontSize: 15 },
  champ: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 12, fontSize: 16 },
  carte: { borderWidth: 1, borderRadius: 14, padding: 18, marginBottom: 16 },
  message: { borderRadius: 10, padding: 12, marginBottom: 14 },
  choixRangee: { flexDirection: 'row', borderWidth: 1, borderRadius: 10, padding: 3 },
  choix: { flex: 1, alignItems: 'center', paddingVertical: 10, borderRadius: 8 },
});
