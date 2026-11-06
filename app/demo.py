"""IA simulée : permet de tester tout le site sans clé API et sans frais."""
from __future__ import annotations

import time

CORPS_DEMO = r"""
\section{Mode démonstration}
\begin{attention}
Cette fiche est un exemple : aucune IA n'a été appelée. Ajoute ta clé
\texttt{ANTHROPIC\_API\_KEY} dans le fichier \texttt{.env} pour générer de vraies fiches.
\end{attention}

\section{Élasticité-prix de la demande}
\begin{definition}[Élasticité-prix]
Variation relative de la quantité demandée provoquée par une variation relative de 1\,\% du prix.
\end{definition}
\begin{formule}[Élasticité ponctuelle]
\[ \varepsilon_{Q,P} = \frac{\partial Q}{\partial P}\cdot\frac{P}{Q} \]
\end{formule}
\begin{methode}
\begin{enumerate}
  \item Dériver la fonction de demande par rapport au prix.
  \item Multiplier par $P/Q$ au point étudié.
  \item Interpréter : $|\varepsilon|>1$ élastique, $|\varepsilon|<1$ inélastique.
\end{enumerate}
\end{methode}
\begin{exemple}
$Q = 100 - 2P$ et $P = 10$ : $Q = 80$, donc $\varepsilon = -2 \cdot \frac{10}{80} = -0{,}25$ (inélastique).
\end{exemple}
\begin{attention}
La pente $\partial Q/\partial P$ n'est \emph{pas} l'élasticité : sur une droite, la pente est
constante mais l'élasticité varie.
\end{attention}

\section{Espérance et variance}
\begin{theoreme}[Linéarité]
\[ \E[aX+bY] = a\,\E[X] + b\,\E[Y], \qquad \Var(aX+b) = a^2\Var(X) \]
\end{theoreme}

\begin{resume}
\begin{itemize}
  \item $\varepsilon = \frac{\partial Q}{\partial P}\frac{P}{Q}$ ; le signe est négatif pour un bien normal.
  \item L'espérance est linéaire ; la variance ne l'est pas.
\end{itemize}
\end{resume}
"""


class ClientDemo:
    def generer(self, systeme, contenu, max_tokens):
        time.sleep(1.5)
        return CORPS_DEMO, 0, 0
