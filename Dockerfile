FROM python:3.12-slim

# LaTeX (avec le français) pour compiler les fiches
RUN apt-get update && apt-get install -y --no-install-recommends \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra \
      texlive-fonts-recommended texlive-lang-french lmodern \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY fichegen ./fichegen
COPY app ./app

# Utilisateur sans privilèges
RUN useradd -m fiche && mkdir -p /srv/donnees && chown fiche /srv/donnees
USER fiche

ENV CHEMIN_BD=/srv/donnees/fichegen.db
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
