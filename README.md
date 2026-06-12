# 🔮 RAG Multimodal — Gemini Embedding 2

> Système RAG multimodal avec authentification par session, déployé sur VPS Hostinger.  
> Vidéos · Images · PDF · Audio · Texte — dans un seul espace vectoriel.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![Pinecone](https://img.shields.io/badge/Pinecone-Serverless-purple)](https://pinecone.io)
[![Gemini](https://img.shields.io/badge/Gemini_Embedding_2-Google-orange?logo=google)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/Licence-MIT-green)](LICENSE)

---

## 📸 Aperçu

Interface dark theme responsive avec :
- 📁 Upload multimodal par glisser-déposer
- 💬 Interrogation en langage naturel
- 📜 Historique des conversations
- 🔮 Visualisation des vecteurs
- ⚙️ Configuration dynamique du LLM
- 👥 Authentification multi-utilisateurs avec rôles

---

## 🧱 Stack technique

| Composant | Outil | Détail |
|---|---|---|
| **Embedding multimodal** | Gemini Embedding 2 | `models/gemini-embedding-2-preview` — 3072 dim |
| **Base vectorielle** | Pinecone | Serverless, index `rag-multimodal` |
| **LLM** | Gemini 2.5 Flash | Via Google AI API |
| **Backend** | Flask 3.0 | Sessions, auth, REST API |
| **Frontend** | HTML/CSS/JS | Dark theme, mobile-first, PWA-ready |
| **Déploiement** | VPS Hostinger + Nginx | HTTPS via Let's Encrypt |

---

## 📂 Structure du projet

```
RAG-Gemini/
├── app.py                  ← Serveur Flask + routes API + auth sessions
├── requirements.txt        ← Dépendances Python
├── .env.example            ← Template de configuration (clés API)
├── rag/
│   ├── embedder.py         ← Gemini Embedding 2 (texte + images + bytes)
│   ├── indexer.py          ← Pinecone (upsert, query, stats, delete)
│   ├── ingest.py           ← Traitement PDF, image, vidéo, audio, texte
│   ├── wp_ingest.py        ← Ingestion WordPress via API REST (lhusser.fr)
│   └── retriever.py        ← Pipeline query → Pinecone → Gemini → réponse
├── wordpress-plugin/
│   └── rag-gemini-chat/    ← Plugin WP : widget de chat public (v2.2.0)
├── deploy/                 ← Scripts d'installation/maintenance du VPS
├── static/
│   ├── index.html          ← Interface principale (dark theme, mobile)
│   └── login.html          ← Page de connexion
└── uploads/
    ├── videos/             ← Dépôt des vidéos (MP4, MOV…)
    ├── images/             ← Dépôt des images (JPG, PNG…)
    └── texte/              ← Dépôt des PDF et textes
```

---

## ⚙️ Installation

### Prérequis

- Python 3.12+
- Compte [Google AI Studio](https://aistudio.google.com) (gratuit)
- Compte [Pinecone](https://pinecone.io) (tier gratuit)
- Compte [OpenRouter](https://openrouter.ai) (optionnel)

### 1. Cloner le repo

```bash
git clone https://github.com/Laurent-67370/Rag-Gemini.git
cd Rag-Gemini
```

### 2. Environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows
```

### 3. Dépendances

```bash
pip install -r requirements.txt
```

### 4. Configuration des clés API

```bash
cp .env.example .env
nano .env
```

Remplir les 3 clés :

```env
GEMINI_API_KEY=...        # https://aistudio.google.com → Get API Key
PINECONE_API_KEY=...      # https://pinecone.io → API Keys
OPENROUTER_API_KEY=...    # https://openrouter.ai → Keys (optionnel)
```

### 5. Lancer

```bash
python app.py
# → http://localhost:5000
```

---

## 🔐 Authentification

Système de sessions Flask avec deux rôles :

| Rôle | Droits |
|---|---|
| 👑 **Admin** | Voit tous les fichiers, toute la base, peut vider, gérer les users, modifier la config |
| 👤 **User** | Voit et interroge uniquement ses propres fichiers |

Les comptes sont créés automatiquement au premier lancement dans `users.json` :
- `laurent` / `Laurent2026` (admin) — **à changer immédiatement**
- `ami` / `Ami2026` (user) — **à changer immédiatement**

Changer son mot de passe : **Avatar → 🔑 Changer mot de passe**

---

## 📄 Formats supportés

| Catégorie | Extensions | Traitement |
|---|---|---|
| **Documents** | `.pdf` | Texte par page + images embarquées |
| **Images** | `.jpg`, `.png`, `.gif`, `.webp` | Embedding visuel direct |
| **Vidéos** | `.mp4`, `.mov`, `.avi`, `.mkv` | Frames extraites + transcription Whisper |
| **Audio** | `.mp3`, `.wav`, `.m4a` | Transcription Whisper |
| **Texte** | `.txt`, `.md`, `.csv` | Découpage en chunks |

---

## 🚀 Déploiement VPS (Hostinger)

```bash
# Service systemd
systemctl start rag-gemini
systemctl enable rag-gemini   # Démarrage automatique

# Nginx reverse proxy + HTTPS
certbot --nginx -d ton-domaine.com

# Voir les logs
journalctl -u rag-gemini -f
```

---

## 💾 Sauvegarde des vecteurs

```bash
# Backup manuel
python3 /root/backup-vectors.py backup

# Restaurer
python3 /root/backup-vectors.py restore

# Backup automatique chaque nuit à 3h
python3 /root/backup-vectors.py cron
```

---

## 💰 Coûts estimés

| Service | Coût | Notes |
|---|---|---|
| Gemini Embedding 2 | Gratuit | Free tier Google AI Studio |
| Gemini 2.5 Flash (LLM) | ~$0.002/question | $0.30/1M input + $2.50/1M output |
| Pinecone | Gratuit | Tier gratuit jusqu'à ~100k vecteurs |
| VPS Hostinger | ~5€/mois | Déjà utilisé pour d'autres services |

---

## 🛠️ Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `GEMINI_API_KEY` | Clé API Google AI Studio | — |
| `PINECONE_API_KEY` | Clé API Pinecone | — |
| `OPENROUTER_API_KEY` | Clé API OpenRouter (optionnel) | — |
| `GEMINI_EMBEDDING_MODEL` | Modèle d'embedding | `models/gemini-embedding-2-preview` |
| `GEMINI_LLM_MODEL` | Modèle LLM | `gemini-2.5-flash` |
| `PINECONE_INDEX_NAME` | Nom de l'index | `rag-multimodal` |
| `EMBEDDING_DIMENSION` | Dimension des vecteurs | `3072` |
| `FLASK_PORT` | Port du serveur | `5000` |
| `FLASK_SECRET_KEY` | Clé secrète sessions | Généré automatiquement |

---

## 📋 API Endpoints

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/login` | Connexion |
| `POST` | `/api/logout` | Déconnexion |
| `GET` | `/api/me` | Infos utilisateur courant |
| `POST` | `/api/upload` | Upload et indexation d'un fichier |
| `POST` | `/api/query` | Interroger le RAG |
| `GET` | `/api/files` | Liste des fichiers indexés |
| `DELETE` | `/api/delete/<filename>` | Supprimer un fichier |
| `DELETE` | `/api/clear` | Vider la base (admin) |
| `GET` | `/api/stats` | Statistiques Pinecone |
| `GET` | `/api/vectors` | Vecteurs pour visualisation |
| `GET/POST` | `/api/config` | Configuration LLM |

**Endpoints publics (widget du blog)** :

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/public-query` | Question du widget — rate limit 5/min · 30/jour/IP · 400/jour global, filtre blog-only |
| `GET` | `/api/public-articles` | Liste des articles du blog (compteur, suggestions, recherche) — cache 1 h |
| `POST` | `/api/ingest-article` | (Re)indexe un article par id/url — secret `RAG_INGEST_SECRET` |
| `POST` | `/api/sync-latest` | Indexe les derniers articles manquants — appelé par cron */15 min |

---

## 🤖 Assistant public du blog (widget WordPress)

Le dossier `wordpress-plugin/rag-gemini-chat/` contient le plugin WP qui affiche
le chat sur [lhusser.fr](https://lhusser.fr) :

- 💬 Réponses RAG avec effet machine à écrire, mémoire localStorage (30 messages)
- 📎 Sources en cartes cliquables (dédupliquées par article)
- 👍👎 Feedback + 📋 copier + 📄 **export PDF** (réponse seule ou conversation complète) à la charte du blog
- 📱 Plein écran mobile, chips scrollables, accessibilité ARIA, `prefers-reduced-motion`
- 🛡️ Assets au **nom de fichier versionné** (`rag-widget-X.Y.Z.js`) : insensible à tous les caches (LiteSpeed, CDN, navigateur)

Installation : zipper `rag-gemini-chat/` → WP Admin → Extensions → Téléverser.

---

## 🔄 Auto-synchronisation des articles

L'index Pinecone se met à jour **sans intervention** :

1. Ingestion initiale : `deploy/upgrade-rag-sync.sh` puis `python3 /root/reingest_wp.py`
   (lecture directe de l'API REST WordPress, extraction 100 % du HTML custom,
   IDs déterministes `wp-{post_id}-{chunk}`)
2. Cron toutes les 15 min → `/api/sync-latest` → seuls les articles **absents** de
   l'index sont ingérés (zéro coût si rien de nouveau) : `deploy/add-auto-sync.sh`
3. Titres modifiés : `deploy/reindex-titres.sh` compare WP ↔ Pinecone et ne
   réindexe que les articles dont le titre a changé

---

## 📝 Changelog

### v2.2.0 (12 juin 2026)
- 📄 Export PDF de la **conversation complète** (bouton dans les onglets) en plus de l'export par réponse
- 🎨 Mise en page PDF à la charte du blog (bandeau #0f172a, Syne/Space Mono, accent #f97316)
- 🛡️ Assets du widget au nom versionné — contournement définitif des caches serveur
- 🔄 `/api/sync-latest` + cron 15 min : auto-indexation des nouveaux articles
- 🔢 `/api/public-articles` : compteur exact, suggestions réelles, onglet Recherche fonctionnel
- 🧠 Réingestion complète des 429 articles via l'API REST (100 % du contenu, 5 600 chunks, purge de 22 950 vecteurs redondants)
- 🔐 Rate limiting 3 niveaux (5/min · 30/jour/IP · 400/jour global) sur les 2 endpoints publics
- 🔐 Filtre `source=lhusser.fr` : les fichiers privés uploadés sont invisibles du chat public
- 💬 Le LLM ne génère plus de section « Sources » texte (cartes cliquables uniquement)
- 🐛 Widget : plein écran mobile, FAB masqué à l'ouverture, sources dédupliquées, fallback compteur, feedback 👍👎, historique persistant

---

## 🤝 Contribution

Projet personnel — toute suggestion bienvenue via Issues ou Pull Requests.

---

## 📜 Licence

MIT — Libre d'utilisation et de modification.

---

*Construit avec ❤️ par [Laurent Husser](https://lhusser.fr) — Mars 2026*
