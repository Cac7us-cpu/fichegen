import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as DocumentPicker from 'expo-document-picker';
import * as Sharing from 'expo-sharing';
import * as WebBrowser from 'expo-web-browser';

import { api, ErreurApi, Profil } from './src/api';
import { ACHATS_DANS_APP, API_URL } from './src/config';
import { Bouton, Carte, Champ, Choix, Message } from './src/composants';
import { effacerJeton, enregistrerJeton, lireJeton } from './src/stockage';
import { useCouleurs } from './src/theme';

type Ecran =
  | { nom: 'chargement' }
  | { nom: 'connexion' }
  | { nom: 'accueil' }
  | { nom: 'attente'; id: string }
  | { nom: 'prete'; id: string; nomFichier: string }
  | { nom: 'compte' };

const TYPES_ACCEPTES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
];

function messageErreur(e: unknown): string {
  return e instanceof Error ? e.message : 'Une erreur inattendue est survenue.';
}

function confirmer(titre: string, texte: string, action: string, auConfirme: () => void) {
  if (Platform.OS === 'web') {
    if (globalThis.confirm?.(`${titre}\n\n${texte}`)) auConfirme();
    return;
  }
  Alert.alert(titre, texte, [
    { text: 'Annuler', style: 'cancel' },
    { text: action, style: 'destructive', onPress: auConfirme },
  ]);
}

export default function App() {
  const c = useCouleurs();
  const [ecran, setEcran] = useState<Ecran>({ nom: 'chargement' });
  const [jeton, setJeton] = useState<string | null>(null);
  const [profil, setProfil] = useState<Profil | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const deconnecter = useCallback(async (message?: string) => {
    await effacerJeton();
    setJeton(null);
    setProfil(null);
    setInfo(message ?? null);
    setEcran({ nom: 'connexion' });
  }, []);

  const rafraichir = useCallback(
    async (j: string) => {
      try {
        setProfil(await api.moi(j));
      } catch (e) {
        if (e instanceof ErreurApi && e.code === 401) await deconnecter(e.message);
      }
    },
    [deconnecter],
  );

  // Au démarrage : reprendre la session enregistrée.
  useEffect(() => {
    (async () => {
      const j = await lireJeton();
      if (!j) return setEcran({ nom: 'connexion' });
      try {
        setProfil(await api.moi(j));
        setJeton(j);
        setEcran({ nom: 'accueil' });
      } catch (e) {
        if (e instanceof ErreurApi && e.code === 401) await effacerJeton();
        else setInfo(messageErreur(e));
        setEcran({ nom: 'connexion' });
      }
    })();
  }, []);

  const connecte = async (j: string, p: Profil, message?: string) => {
    await enregistrerJeton(j);
    setJeton(j);
    setProfil(p);
    setInfo(message ?? null);
    setEcran({ nom: 'accueil' });
  };

  let contenu: React.ReactNode;
  switch (ecran.nom) {
    case 'chargement':
      contenu = <ActivityIndicator size="large" color={c.accent} style={{ marginTop: 80 }} />;
      break;
    case 'connexion':
      contenu = <EcranConnexion info={info} onConnecte={connecte} />;
      break;
    case 'accueil':
      contenu = (
        <EcranAccueil
          jeton={jeton!}
          profil={profil!}
          info={info}
          effacerInfo={() => setInfo(null)}
          onLance={(id) => {
            rafraichir(jeton!);
            setEcran({ nom: 'attente', id });
          }}
          onCompte={() => setEcran({ nom: 'compte' })}
          rafraichir={() => rafraichir(jeton!)}
        />
      );
      break;
    case 'attente':
      contenu = (
        <EcranAttente
          jeton={jeton!}
          id={ecran.id}
          onTermine={(nomFichier) => {
            rafraichir(jeton!);
            setEcran({ nom: 'prete', id: ecran.id, nomFichier });
          }}
          onEchec={(msg) => {
            rafraichir(jeton!);
            setInfo(msg);
            setEcran({ nom: 'accueil' });
          }}
        />
      );
      break;
    case 'prete':
      contenu = (
        <EcranPrete
          jeton={jeton!}
          id={ecran.id}
          nomFichier={ecran.nomFichier}
          onNouvelle={() => {
            setInfo(null);
            setEcran({ nom: 'accueil' });
          }}
        />
      );
      break;
    case 'compte':
      contenu = (
        <EcranCompte
          jeton={jeton!}
          profil={profil!}
          onRetour={() => setEcran({ nom: 'accueil' })}
          onDeconnexion={() => deconnecter()}
          onSupprime={() => deconnecter('Ton compte et tes données ont été supprimés.')}
        />
      );
      break;
  }

  return (
    <View style={[styles.racine, { backgroundColor: c.fond }]}>
      <StatusBar style="auto" />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.defilement} keyboardShouldPersistTaps="handled">
          <View style={styles.entete}>
            <Text style={[styles.logo, { color: c.texte }]}>
              Fiche<Text style={{ color: c.accent }}>Gen</Text>
            </Text>
            {profil && ecran.nom !== 'connexion' && (
              <Pressable accessibilityRole="button" onPress={() => setEcran({ nom: 'compte' })} hitSlop={10}>
                <Text style={{ color: c.doux, fontWeight: '600' }}>
                  {profil.credits} crédit{profil.credits > 1 ? 's' : ''} · Compte
                </Text>
              </Pressable>
            )}
          </View>
          {contenu}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

// ------------------------------------------------------------------ Connexion
function EcranConnexion({ info, onConnecte }: { info: string | null; onConnecte: (j: string, p: Profil, m?: string) => void }) {
  const c = useCouleurs();
  const [mode, setMode] = useState<'connexion' | 'inscription'>('inscription');
  const [email, setEmail] = useState('');
  const [mdp, setMdp] = useState('');
  const [accepte, setAccepte] = useState(false);
  const [charge, setCharge] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const valider = async () => {
    setErreur(null);
    if (mode === 'inscription' && !accepte) {
      return setErreur("Accepte les conditions et la politique de confidentialité pour continuer.");
    }
    setCharge(true);
    try {
      if (mode === 'inscription') {
        const r = await api.inscription(email, mdp, accepte);
        onConnecte(r.jeton, r.profil, `Bienvenue ! Tu as ${r.profil.credits} fiches gratuites.`);
      } else {
        const r = await api.connexion(email, mdp);
        onConnecte(r.jeton, r.profil);
      }
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setCharge(false);
    }
  };

  return (
    <View>
      <Text style={[styles.titre, { color: c.texte }]}>Tes diapos deviennent une fiche de révision.</Text>
      <Text style={[styles.sousTitre, { color: c.doux }]}>
        Choisis le PDF ou le PowerPoint de ton cours et reçois une fiche claire, avec de vraies formules.
      </Text>
      <Message texte={info} />
      <Carte>
        <Choix
          etiquette=""
          options={[
            { valeur: 'inscription', libelle: 'Créer un compte' },
            { valeur: 'connexion', libelle: 'Se connecter' },
          ]}
          valeur={mode}
          onChange={(m) => {
            setMode(m);
            setErreur(null);
          }}
        />
        <Message texte={erreur} type="erreur" />
        <Champ
          etiquette="Courriel"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
        />
        <Champ
          etiquette="Mot de passe"
          value={mdp}
          onChangeText={setMdp}
          secureTextEntry
          autoComplete={mode === 'inscription' ? 'new-password' : 'current-password'}
          textContentType={mode === 'inscription' ? 'newPassword' : 'password'}
          placeholder={mode === 'inscription' ? '8 caractères minimum' : undefined}
        />
        {mode === 'inscription' && (
          <Pressable
            accessibilityRole="checkbox"
            accessibilityState={{ checked: accepte }}
            onPress={() => setAccepte(!accepte)}
            style={styles.caseRangee}
          >
            <View style={[styles.case, { borderColor: c.accent, backgroundColor: accepte ? c.accent : 'transparent' }]}>
              {accepte && <Text style={{ color: c.surAccent, fontWeight: '800' }}>✓</Text>}
            </View>
            <Text style={{ color: c.texte, flex: 1 }}>
              J'accepte les{' '}
              <Text style={{ color: c.accent }} onPress={() => WebBrowser.openBrowserAsync(`${API_URL}/conditions`)}>
                conditions
              </Text>{' '}
              et la{' '}
              <Text style={{ color: c.accent }} onPress={() => WebBrowser.openBrowserAsync(`${API_URL}/confidentialite`)}>
                politique de confidentialité
              </Text>
              .
            </Text>
          </Pressable>
        )}
        <Bouton titre={mode === 'inscription' ? 'Créer mon compte' : 'Se connecter'} onPress={valider} charge={charge} />
      </Carte>
    </View>
  );
}

// ------------------------------------------------------------------ Accueil
function EcranAccueil(props: {
  jeton: string;
  profil: Profil;
  info: string | null;
  effacerInfo: () => void;
  onLance: (id: string) => void;
  onCompte: () => void;
  rafraichir: () => void;
}) {
  const c = useCouleurs();
  const [fichier, setFichier] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [titre, setTitre] = useState('');
  const [niveau, setNiveau] = useState<'synthetique' | 'standard' | 'detaille'>('standard');
  const [langue, setLangue] = useState<'français' | 'anglais'>('français');
  const [charge, setCharge] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const sansCredit = props.profil.credits < 1;

  const choisir = async () => {
    setErreur(null);
    const r = await DocumentPicker.getDocumentAsync({ type: TYPES_ACCEPTES, copyToCacheDirectory: true });
    if (r.canceled || !r.assets?.length) return;
    const a = r.assets[0];
    if (a.size && a.size > props.profil.taille_max_mo * 1024 * 1024) {
      return setErreur(`Fichier trop lourd (max ${props.profil.taille_max_mo} Mo).`);
    }
    setFichier(a);
  };

  const generer = async () => {
    if (!fichier) return;
    setErreur(null);
    props.effacerInfo();
    setCharge(true);
    try {
      const { id } = await api.generer(props.jeton, fichier, { titre, niveau, langue });
      props.onLance(id);
    } catch (e) {
      setErreur(messageErreur(e));
      props.rafraichir();
    } finally {
      setCharge(false);
    }
  };

  return (
    <View>
      <Text style={[styles.titre, { color: c.texte }]}>Nouvelle fiche</Text>
      <Message texte={props.info} />
      <Message texte={erreur} type="erreur" />
      <Carte>
        <Pressable
          accessibilityRole="button"
          onPress={choisir}
          style={[styles.depot, { borderColor: fichier ? c.accent : c.ligne }]}
        >
          <Text style={{ fontSize: 30 }}>📄</Text>
          <Text style={[styles.depotTitre, { color: c.texte }]} numberOfLines={2}>
            {fichier ? fichier.name : 'Choisir mes diapos'}
          </Text>
          <Text style={{ color: c.doux, textAlign: 'center' }}>
            {fichier ? 'Touche pour changer de fichier' : `PDF ou PowerPoint · ${props.profil.taille_max_mo} Mo max`}
          </Text>
        </Pressable>

        <Champ etiquette="Titre (optionnel)" value={titre} onChangeText={setTitre} placeholder="Ex. : Macro — Chapitre 3" maxLength={120} />
        <Choix
          etiquette="Niveau de détail"
          options={[
            { valeur: 'synthetique', libelle: 'Court' },
            { valeur: 'standard', libelle: 'Standard' },
            { valeur: 'detaille', libelle: 'Détaillé' },
          ]}
          valeur={niveau}
          onChange={setNiveau}
        />
        <Choix
          etiquette="Langue"
          options={[
            { valeur: 'français', libelle: 'Français' },
            { valeur: 'anglais', libelle: 'Anglais' },
          ]}
          valeur={langue}
          onChange={setLangue}
        />
        <Bouton titre="Générer ma fiche (1 crédit)" onPress={generer} charge={charge} desactive={!fichier || sansCredit} />
        {sansCredit && (
          <Text style={{ color: c.doux, marginTop: 6 }}>
            {ACHATS_DANS_APP ? 'Plus de crédits : recharge depuis ton compte.' : "Tu n'as plus de crédits."}
          </Text>
        )}
      </Carte>
      <Text style={{ color: c.doux, fontSize: 13, lineHeight: 19 }}>
        Utilise uniquement des documents de cours auxquels tu as légitimement accès. Tes diapos sont supprimées dès la fin du
        traitement.
      </Text>
    </View>
  );
}

// ------------------------------------------------------------------ Attente
function EcranAttente(props: { jeton: string; id: string; onTermine: (nom: string) => void; onEchec: (msg: string) => void }) {
  const c = useCouleurs();
  const [etape, setEtape] = useState('Envoi des diapos…');
  const actif = useRef(true);

  useEffect(() => {
    actif.current = true;
    let erreursReseau = 0;
    const suivre = async () => {
      if (!actif.current) return;
      try {
        const s = await api.statut(props.jeton, props.id);
        erreursReseau = 0;
        setEtape(s.etape);
        if (s.statut === 'termine') return props.onTermine(s.nom);
        if (s.statut === 'echec') return props.onEchec(s.erreur ?? 'La génération a échoué.');
      } catch (e) {
        if (e instanceof ErreurApi && e.code === 404) return props.onEchec('La fiche a expiré. Réessaie.');
        if (++erreursReseau > 10) return props.onEchec(messageErreur(e));
      }
      setTimeout(suivre, 2000);
    };
    suivre();
    return () => {
      actif.current = false;
    };
  }, [props.id]);

  return (
    <Carte>
      <View style={{ alignItems: 'center', paddingVertical: 24 }}>
        <Text style={[styles.titre, { color: c.texte, textAlign: 'center' }]}>Ta fiche est en préparation</Text>
        <ActivityIndicator size="large" color={c.accent} style={{ marginVertical: 20 }} />
        <Text style={{ color: c.texte, fontSize: 16, textAlign: 'center' }}>{etape}</Text>
        <Text style={{ color: c.doux, marginTop: 12, textAlign: 'center' }}>
          En général 1 à 3 minutes. Garde l'app ouverte.
        </Text>
      </View>
    </Carte>
  );
}

// ------------------------------------------------------------------ Fiche prête
function EcranPrete(props: { jeton: string; id: string; nomFichier: string; onNouvelle: () => void }) {
  const c = useCouleurs();
  const [charge, setCharge] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const ouvrir = async () => {
    setErreur(null);
    setCharge(true);
    try {
      const chemin = await api.telechargerPdf(props.jeton, props.id, props.nomFichier);
      if (Platform.OS === 'web') {
        globalThis.open?.(chemin, '_blank');
      } else if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(chemin, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: 'Ta fiche de révision' });
      } else {
        setErreur("Le partage n'est pas disponible sur cet appareil.");
      }
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setCharge(false);
    }
  };

  return (
    <Carte>
      <View style={{ alignItems: 'center', paddingVertical: 12 }}>
        <Text style={{ fontSize: 44 }}>✅</Text>
        <Text style={[styles.titre, { color: c.texte, textAlign: 'center' }]}>Ta fiche est prête</Text>
        <Text style={{ color: c.doux, textAlign: 'center', marginBottom: 16 }}>
          Enregistre-la dans Fichiers, Google Drive ou envoie-la à qui tu veux. Le lien expire dans 30 minutes.
        </Text>
      </View>
      <Message texte={erreur} type="erreur" />
      <Bouton titre={Platform.OS === 'web' ? 'Ouvrir le PDF' : 'Ouvrir / enregistrer le PDF'} onPress={ouvrir} charge={charge} />
      <Bouton titre="Créer une autre fiche" variante="secondaire" onPress={props.onNouvelle} />
    </Carte>
  );
}

// ------------------------------------------------------------------ Compte
function EcranCompte(props: {
  jeton: string;
  profil: Profil;
  onRetour: () => void;
  onDeconnexion: () => void;
  onSupprime: () => void;
}) {
  const c = useCouleurs();
  const [erreur, setErreur] = useState<string | null>(null);
  const [achat, setAchat] = useState<string | null>(null);

  const acheter = async (pack: string) => {
    setErreur(null);
    setAchat(pack);
    try {
      const { url } = await api.acheter(props.jeton, pack);
      await WebBrowser.openBrowserAsync(url);
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setAchat(null);
    }
  };

  const supprimer = () =>
    confirmer(
      'Supprimer ton compte ?',
      'Ton compte, tes crédits restants et ton historique seront effacés définitivement.',
      'Supprimer',
      async () => {
        try {
          await api.supprimerCompte(props.jeton);
          props.onSupprime();
        } catch (e) {
          setErreur(messageErreur(e));
        }
      },
    );

  return (
    <View>
      <Text style={[styles.titre, { color: c.texte }]}>Mon compte</Text>
      <Message texte={erreur} type="erreur" />
      <Carte>
        <Text style={{ color: c.doux }}>Connecté en tant que</Text>
        <Text style={{ color: c.texte, fontSize: 16, fontWeight: '600', marginBottom: 12 }}>{props.profil.email}</Text>
        <Text style={{ color: c.texte, fontSize: 28, fontWeight: '800' }}>
          {props.profil.credits} <Text style={{ fontSize: 16, fontWeight: '500', color: c.doux }}>crédit{props.profil.credits > 1 ? 's' : ''}</Text>
        </Text>
      </Carte>

      {ACHATS_DANS_APP && props.profil.paiement_actif && (
        <Carte>
          <Text style={{ color: c.texte, fontWeight: '700', fontSize: 16, marginBottom: 8 }}>Recharger</Text>
          {props.profil.packs.map((p) => (
            <Bouton
              key={p.id}
              variante="secondaire"
              titre={`${p.nom} · ${p.credits} fiches · ${(p.prix / 100).toFixed(2)} $`}
              onPress={() => acheter(p.id)}
              charge={achat === p.id}
            />
          ))}
        </Carte>
      )}

      <Carte>
        <Bouton titre="Conditions d'utilisation" variante="lien" onPress={() => WebBrowser.openBrowserAsync(`${API_URL}/conditions`)} />
        <Bouton titre="Politique de confidentialité" variante="lien" onPress={() => WebBrowser.openBrowserAsync(`${API_URL}/confidentialite`)} />
        <Bouton titre="Se déconnecter" variante="secondaire" onPress={props.onDeconnexion} />
        <Bouton titre="Supprimer mon compte" variante="danger" onPress={supprimer} />
      </Carte>
      <Bouton titre="← Retour" variante="lien" onPress={props.onRetour} />
    </View>
  );
}

const styles = StyleSheet.create({
  racine: { flex: 1 },
  defilement: { padding: 16, paddingTop: Platform.OS === 'ios' ? 64 : 44, paddingBottom: 48, maxWidth: 560, width: '100%', alignSelf: 'center' },
  entete: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 },
  logo: { fontSize: 22, fontWeight: '800' },
  titre: { fontSize: 26, fontWeight: '800', marginBottom: 8 },
  sousTitre: { fontSize: 16, lineHeight: 23, marginBottom: 18 },
  depot: { borderWidth: 2, borderStyle: 'dashed', borderRadius: 14, padding: 22, alignItems: 'center', marginBottom: 16, gap: 6 },
  depotTitre: { fontSize: 16, fontWeight: '700', textAlign: 'center' },
  caseRangee: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12 },
  case: { width: 24, height: 24, borderRadius: 6, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
});
