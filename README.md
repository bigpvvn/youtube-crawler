# 🎥 YouTube Content Crawler & Auto-Uploader

## 📋 Description

Ce projet est un système automatisé complet pour la découverte, le téléchargement, l'édition et l'upload de contenu YouTube. Il permet de crawler des vidéos YouTube selon des critères spécifiques, de les télécharger, de les éditer automatiquement en ajoutant des vidéos d'entertainment, puis de les uploader sur un compte YouTube configuré.

## 🚀 Fonctionnalités Principales

### 🔍 Crawling Intelligent
- **Recherche ciblée** : Recherche de vidéos basée sur des mots-clés spécifiques
- **Filtres avancés** : Filtrage par durée, nombre de vues, date de publication
- **Exploration récursive** : Découverte de vidéos similaires via les recommandations
- **Déduplication** : Évite les doublons et les vidéos déjà traitées

### 📥 Téléchargement Automatique
- **Téléchargement via yt-dlp** : Utilise la bibliothèque yt-dlp pour un téléchargement fiable
- **Gestion des qualités** : Support de différentes qualités vidéo
- **Gestion des erreurs** : Gestion robuste des échecs de téléchargement

### ✂️ Édition Automatique
- **Superposition vidéo** : Ajoute automatiquement des vidéos d'entertainment
- **Positionnement intelligent** : Place les vidéos d'entertainment en bas de l'écran (1/3 de la hauteur)
- **Synchronisation audio** : Conserve l'audio original de la vidéo principale
- **Génération d'ID unique** : Crée des identifiants uniques pour chaque vidéo éditée

### 📤 Upload YouTube
- **API YouTube officielle** : Utilise l'API YouTube Data v3
- **Authentification OAuth 2.0** : Gestion sécurisée des identifiants
- **Gestion multi-comptes** : Support de plusieurs comptes YouTube
- **Métadonnées personnalisables** : Titre, description, tags configurables

## 🏗️ Architecture du Projet

```
crawl/
├── run.py                 # Script principal d'exécution
├── src/
│   ├── crawlers.py        # Module de crawling YouTube
│   ├── downloader.py      # Module de téléchargement
│   ├── editor.py          # Module d'édition vidéo
│   ├── uploader.py        # Module d'upload YouTube
│   ├── routes.json        # Configuration des URLs
│   └── media/
│       ├── download/      # Vidéos téléchargées
│       ├── videos/        # Vidéos éditées
│       ├── entertainment_videos/  # Vidéos d'entertainment
│       └── uploaded_videos.json   # Historique des uploads
└── accounts/
    └── [nom_compte]/
        ├── client_secrets.json    # Identifiants OAuth
        ├── credentials.pickle     # Tokens d'authentification
        └── tokens.json           # Tokens au format JSON
```

## 📦 Dépendances

### Python
- `python 3.8+`

### Bibliothèques principales
```bash
pip install -r requirements.txt
```

**Dépendances principales :**
- `yt-dlp` : Téléchargement de vidéos YouTube
- `moviepy` : Édition et manipulation vidéo
- `google-auth-oauthlib` : Authentification OAuth 2.0
- `google-api-python-client` : API YouTube
- `beautifulsoup4` : Parsing HTML pour le crawling
- `requests` : Requêtes HTTP
- `rich` : Interface console colorée

## ⚙️ Configuration

### 1. Configuration de l'API YouTube

#### Étape 1 : Créer un projet Google Cloud
1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Activez l'API YouTube Data v3

#### Étape 2 : Créer des identifiants OAuth 2.0
1. Dans la console Google Cloud, allez dans "Identifiants"
2. Cliquez sur "Créer des identifiants" → "ID client OAuth 2.0"
3. Configurez l'écran de consentement OAuth
4. Ajoutez les URIs de redirection autorisés :
   - `http://localhost:8080/`
   - `http://127.0.0.1:8080/`
5. Téléchargez le fichier `client_secrets.json`

#### Étape 3 : Configuration du compte
1. Créez un dossier dans `accounts/[nom_de_votre_compte]/`
2. Placez le fichier `client_secrets.json` dans ce dossier
3. Modifiez la variable `YOUTUBE_ACCOUNT` dans `run.py`

### 2. Configuration des vidéos d'entertainment

Placez vos vidéos d'entertainment dans le dossier `src/media/entertainment_videos/`. Ces vidéos seront utilisées pour créer des superpositions sur les vidéos téléchargées.

### 3. Configuration des paramètres de recherche

Dans `run.py`, modifiez les paramètres suivants :

```python
# Requête de recherche
query = "minecraft shorts"

# Filtres de recherche
filters = {
    "duration": {"min": 15, "max": 175},        # Durée en secondes
    "views": {"min": 1000000, "max": 1000000000}, # Nombre de vues
    "publishedTime": {
        "min": (datetime.now() - timedelta(days=365)).isoformat(),
        "max": datetime.now().isoformat()
    }
}

# Nombre maximum de vidéos à traiter
MAX_VIDEOS = 1
```

## 🚀 Utilisation

### 1. Première configuration

```bash
# Installer les dépendances
pip install -r requirements.txt

# Configurer l'authentification YouTube
python src/uploader.py
```

### 2. Exécution du script principal

```bash
python run.py
```

### 3. Processus automatisé

Le script exécute automatiquement les étapes suivantes :

1. **Crawling** : Recherche de vidéos selon les critères définis
2. **Téléchargement** : Téléchargement des vidéos sélectionnées
3. **Édition** : Ajout de vidéos d'entertainment en superposition
4. **Upload** : Upload sur YouTube avec métadonnées personnalisées
5. **Nettoyage** : Suppression des fichiers temporaires

## 📊 Monitoring et Logs

Le script utilise la bibliothèque `rich` pour afficher des informations détaillées :

- **Cyan** : Informations de traitement
- **Vert** : Succès
- **Rouge** : Erreurs
- **Jaune** : Avertissements

### Fichiers de suivi

- `src/media/uploaded_videos.json` : Historique des vidéos uploadées
- `accounts/[compte]/tokens.json` : Tokens d'authentification

## 🔧 Personnalisation

### Modification des filtres de recherche

```python
filters = {
    "duration": {"min": 30, "max": 300},        # Vidéos de 30s à 5min
    "views": {"min": 500000, "max": 50000000},  # 500k à 50M vues
    "publishedTime": {
        "min": (datetime.now() - timedelta(days=30)).isoformat(),  # Derniers 30 jours
        "max": datetime.now().isoformat()
    }
}
```

### Personnalisation de l'édition

Dans `src/editor.py`, vous pouvez modifier :
- La position des vidéos d'entertainment
- La taille de superposition
- Les effets visuels appliqués

### Configuration des métadonnées

```python
upload_data = {
    "title": current_video['title'],
    "description": "Votre description personnalisée",
    "tags": ["tag1", "tag2", "tag3"],
    "privacy": "private"  # ou "public", "unlisted"
}
```

## 🛠️ Dépannage

### Erreurs courantes

#### 1. Erreur d'authentification
```
Fichier de tokens introuvable: accounts/[compte]/tokens.json
```
**Solution** : Exécutez `python src/uploader.py` pour configurer l'authentification

#### 2. Erreur de téléchargement
```
Erreur: Video unavailable
```
**Solution** : Vérifiez que la vidéo n'est pas privée ou supprimée

#### 3. Erreur d'upload
```
Erreur HTTP: Quota exceeded
```
**Solution** : Attendez que le quota YouTube soit réinitialisé (quotidien)

### Logs de débogage

Activez le mode debug dans `src/uploader.py` :

```python
uploader = YouTubeUploader("votre_compte", debug=True)
```

## 📝 Notes importantes

### Limitations YouTube
- **Quota API** : L'API YouTube a des limites quotidiennes
- **Taux de requêtes** : Respectez les limites de taux pour éviter les blocages
- **Contenu autorisé** : Assurez-vous de respecter les conditions d'utilisation YouTube

### Bonnes pratiques
- **Testez en privé** : Commencez toujours avec `privacy="private"`
- **Surveillez les quotas** : Vérifiez régulièrement votre utilisation de l'API
- **Sauvegardez** : Gardez des sauvegardes de vos configurations

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Poussez vers la branche
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## ⚠️ Avertissement légal

Ce projet est fourni à des fins éducatives uniquement. Les utilisateurs sont responsables de :
- Respecter les conditions d'utilisation de YouTube
- Respecter les droits d'auteur
- Obtenir les autorisations nécessaires pour le contenu utilisé
- Respecter les lois locales sur la propriété intellectuelle

## 📞 Support

Pour toute question ou problème :
- Ouvrez une issue sur GitHub
- Consultez la documentation de l'API YouTube
- Vérifiez les logs de débogage

---

**Développé avec ❤️ pour l'automatisation de contenu YouTube** 