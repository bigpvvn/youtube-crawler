#!/usr/bin/env python3

import os
import json
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
from google.auth.transport.requests import Request

# Configuration de l'API YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Statuts de confidentialité valides
VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


class YouTubeUploader:
    """
    Classe pour uploader des vidéos sur YouTube en utilisant l'API YouTube Data v3.
    Implémentation basée sur les pratiques recommandées par Google.
    """
    
    def __init__(self, account, debug=False):
        """
        Initialise l'uploader YouTube avec un compte.
        
        Args:
            account (str): Nom du compte (correspondant à un dossier dans ../accounts).
            debug (bool): Activer le mode débogage pour plus d'informations.
        """
        self.account = account
        self.debug = debug
        self.youtube_service = None
        self.credentials = None
        
        # Obtenir le chemin absolu du répertoire où se trouve ce fichier (src/)
        src_dir = os.path.dirname(os.path.abspath(__file__))
        # Remonter d'un niveau pour obtenir le répertoire du projet
        project_dir = os.path.dirname(src_dir)
        
        # Chemins des fichiers pour ce compte
        self.account_dir = os.path.join(project_dir, "accounts", account)
        self.client_secrets_file = os.path.join(self.account_dir, "client_secrets.json")
        self.credentials_pickle = os.path.join(self.account_dir, "credentials.pickle")
        self.tokens_json = os.path.join(self.account_dir, "tokens.json")
        
        # Créer le répertoire du compte s'il n'existe pas
        if not os.path.exists(self.account_dir):
            os.makedirs(self.account_dir)
            
        if self.debug:
            print(f"Répertoire du compte: {os.path.abspath(self.account_dir)}")
            print(f"Fichier de secrets: {os.path.abspath(self.client_secrets_file)}")
        
        # Tenter de charger les identifiants automatiquement lors de l'initialisation
        self.load_credentials()
    
    def load_credentials(self):
        """
        Charge les identifiants depuis le fichier pickle s'il existe.
        Initialise le service YouTube si les identifiants sont valides.
        
        Returns:
            bool: True si les identifiants ont été chargés et sont valides, False sinon.
        """
        if os.path.exists(self.credentials_pickle):
            if self.debug:
                print(f"Chargement des identifiants depuis {self.credentials_pickle}")
            try:
                with open(self.credentials_pickle, 'rb') as token:
                    self.credentials = pickle.load(token)
                    
                # Vérifier si les identifiants sont expirés et tenter de les rafraîchir
                if self.credentials.expired and self.credentials.refresh_token:
                    if self.debug:
                        print("Rafraîchissement des identifiants expirés...")
                    try:
                        self.credentials.refresh(Request())
                        # Sauvegarder les identifiants rafraîchis
                        self.save_credentials()
                    except Exception as e:
                        if self.debug:
                            print(f"Erreur lors du rafraîchissement des identifiants: {e}")
                        return False
                
                # Initialiser le service YouTube avec les identifiants chargés
                if self.credentials.valid:
                    self.init_youtube_service()
                    self.save_tokens_to_json()
                    return True
            except Exception as e:
                if self.debug:
                    print(f"Erreur lors du chargement des identifiants: {e}")
        
        return False
    
    def save_credentials(self):
        """
        Sauvegarde les identifiants actuels dans le fichier pickle.
        """
        if self.credentials and (self.credentials.valid or self.credentials.refresh_token):
            try:
                with open(self.credentials_pickle, 'wb') as token:
                    pickle.dump(self.credentials, token)
                if self.debug:
                    print(f"Identifiants sauvegardés dans {self.credentials_pickle}")
                return True
            except Exception as e:
                if self.debug:
                    print(f"Erreur lors de la sauvegarde des identifiants: {e}")
        return False
    
    def save_tokens_to_json(self):
        """
        Sauvegarde les tokens d'accès et de rafraîchissement dans un fichier JSON
        pour une utilisation facile par d'autres scripts.
        """
        if self.credentials:
            tokens = {
                "access_token": self.credentials.token,
                "refresh_token": self.credentials.refresh_token,
                "token_uri": self.credentials.token_uri,
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "scopes": self.credentials.scopes,
                "expiry": self.credentials.expiry.isoformat() if self.credentials.expiry else None
            }
            
            try:
                with open(self.tokens_json, 'w') as f:
                    json.dump(tokens, f, indent=2)
                if self.debug:
                    print(f"Tokens sauvegardés dans {self.tokens_json}")
                return True
            except Exception as e:
                if self.debug:
                    print(f"Erreur lors de la sauvegarde des tokens: {e}")
        return False
    
    def init_youtube_service(self):
        """
        Initialise le service YouTube avec les identifiants actuels.
        
        Returns:
            bool: True si le service a été initialisé avec succès, False sinon.
        """
        if not self.credentials or not self.credentials.valid:
            if self.debug:
                print("Impossible d'initialiser le service YouTube: identifiants manquants ou invalides")
            return False
            
        try:
            self.youtube_service = googleapiclient.discovery.build(
                API_SERVICE_NAME, API_VERSION, credentials=self.credentials
            )
            if self.debug:
                print("Service YouTube créé avec succès!")
            return True
        except Exception as e:
            print(f"Erreur lors de la création du service YouTube: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def authenticate(self, port=None, redirect_uri=None):
        """
        Authentifie auprès de l'API YouTube en utilisant OAuth 2.0.
        Gère la persistance des identifiants et le rafraîchissement automatique.
        
        Args:
            port (int, optional): Port spécifique à utiliser pour le serveur local.
                                 Si None, un port dynamique sera utilisé.
            redirect_uri (str, optional): URI de redirection spécifique à utiliser.
                                         Si fourni, remplace la détection automatique.
        
        Returns:
            bool: True si l'authentification a réussi, False sinon.
        """
        # Vérifier si les identifiants existants sont valides
        if self.load_credentials():
            if self.debug:
                print("Identifiants existants valides, authentification réussie!")
            return True
            
        # Si nous arrivons ici, les identifiants n'existent pas ou sont invalides
        if not os.path.exists(self.client_secrets_file):
            print(f"Erreur: Le fichier {self.client_secrets_file} n'existe pas.")
            print("Vous devez créer un projet dans la console Google Cloud, activer l'API YouTube,")
            print("créer des identifiants OAuth 2.0 et télécharger le fichier client_secrets.json.")
            return False
        
        if self.debug:
            print("Début du processus d'authentification...")
                
        # Permettre le transport non sécurisé pour le développement local
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        
        # Créer le flux d'authentification
        try:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_file, SCOPES
            )
            
            # Configuration pour le serveur local
            flow_kwargs = {}
            
            # Utiliser un port spécifique si fourni
            if port is not None:
                flow_kwargs['port'] = port
                if self.debug:
                    print(f"Utilisation du port spécifié: {port}")
            else:
                flow_kwargs['port'] = 0  # Port dynamique
                if self.debug:
                    print("Utilisation d'un port dynamique")
            
            # Utiliser une URI de redirection spécifique si fournie
            if redirect_uri is not None:
                flow_kwargs['redirect_uri'] = redirect_uri
                if self.debug:
                    print(f"Utilisation de l'URI de redirection spécifiée: {redirect_uri}")
            
            # Lancer le serveur local et obtenir les identifiants
            self.credentials = flow.run_local_server(**flow_kwargs)
            
            # Afficher l'URI qui a été utilisée (utile pour la configuration dans Google Cloud Console)
            if self.debug:
                if hasattr(flow, '_redirect_uri'):
                    print(f"URI de redirection utilisée: {flow._redirect_uri}")
                if hasattr(flow, '_port'):
                    print(f"Port utilisé: {flow._port}")
            
            # Sauvegarder les identifiants et tokens
            self.save_credentials()
            self.save_tokens_to_json()
            
            # Initialiser le service YouTube
            result = self.init_youtube_service()
            
            if self.debug:
                if result:
                    print("Authentification réussie!")
                else:
                    print("Échec de l'initialisation du service après authentification.")
            
            return result
                
        except Exception as e:
            print(f"Erreur lors de l'authentification: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
                print("\nConseils pour résoudre les problèmes d'authentification:")
                print("1. Vérifier que le fichier client_secrets.json est correct et à jour")
                print("2. S'assurer que les URIs de redirection autorisés dans la console Google Cloud incluent:")
                print("   - http://localhost")
                print("   - http://127.0.0.1")
                print("3. Pour les erreurs 'redirect_uri_mismatch':")
                print("   a. Ajouter l'URI exacte mentionnée dans l'erreur aux URIs autorisées dans Google Cloud Console")
                print("   b. Ou utiliser un port fixe: authenticate(port=8080)")
                print("   c. Ou spécifier l'URI exacte: authenticate(redirect_uri='http://localhost:8080')")
                print("4. Supprimer les identifiants existants avec reset_credentials() et réessayer")
                print("5. Vérifier que la date et l'heure de votre système sont correctes")
            return False
    
    def upload_video(self, video_file_path, title, description="", 
                     tags=None, category_id="22", privacy_status="private"):
        """
        Uploade une vidéo sur YouTube.
        
        Args:
            video_file_path (str): Chemin vers le fichier vidéo à uploader.
            title (str): Titre de la vidéo.
            description (str): Description de la vidéo.
            tags (list): Liste de tags pour la vidéo.
            category_id (str): ID de la catégorie YouTube (22 = People & Blogs).
            privacy_status (str): Statut de confidentialité ("public", "private", "unlisted").
        
        Returns:
            str: ID de la vidéo uploadée, ou None en cas d'échec.
        """
        # Vérifier si le service YouTube est initialisé
        if not self.youtube_service:
            if self.debug:
                print("Service YouTube non initialisé, tentative d'initialisation automatique...")
            # Tenter de charger les identifiants et d'initialiser le service
            if not self.load_credentials() or not self.init_youtube_service():
                print("Veuillez vous authentifier d'abord en appelant authenticate()")
                return None
        
        if not os.path.exists(video_file_path):
            print(f"Le fichier vidéo {video_file_path} n'existe pas.")
            return None
        
        if privacy_status not in VALID_PRIVACY_STATUSES:
            print(f"Statut de confidentialité invalide: {privacy_status}")
            print(f"Les statuts valides sont: {VALID_PRIVACY_STATUSES}")
            return None
        
        # Convertir tags en liste si c'est une chaîne
        if isinstance(tags, str):
            tags = tags.split(",") if tags else None
        
        # Si tags est None, le définir comme une liste vide
        if tags is None:
            tags = []
        
        # Préparer les métadonnées de la vidéo
        body = {
            "snippet": {
                "categoryId": category_id,
                "title": title,
                "description": description,
                "tags": tags
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }
        
        try:
            if self.debug:
                print(f"Début de l'upload de la vidéo: {video_file_path}")
                print(f"Titre: {title}")
                print(f"Confidentialité: {privacy_status}")
            
            # Créer la requête d'upload
            request = self.youtube_service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=googleapiclient.http.MediaFileUpload(
                    video_file_path, 
                    chunksize=-1, 
                    resumable=True
                )
            )
            
            # Exécuter l'upload avec affichage de la progression
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and self.debug:
                    print(f"Upload {int(status.progress() * 100)}%")
            
            if response and "id" in response:
                video_id = response["id"]
                print(f"Vidéo uploadée avec succès! ID: {video_id}")
                print(f"URL: https://www.youtube.com/watch?v={video_id}")
                return video_id
            else:
                print("L'upload a échoué: réponse inattendue du serveur")
                if self.debug and response:
                    print(f"Réponse: {response}")
                return None
                
        except googleapiclient.errors.HttpError as e:
            print(f"Une erreur HTTP s'est produite lors de l'upload: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None
        except Exception as e:
            print(f"Une erreur s'est produite lors de l'upload: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None

    def reset_credentials(self):
        """
        Supprime les identifiants existants pour forcer une nouvelle authentification.
        Utile en cas de problèmes d'authentification persistants.
        
        Returns:
            bool: True si les identifiants ont été supprimés, False s'ils n'existaient pas.
        """
        if os.path.exists(self.credentials_pickle):
            if self.debug:
                print(f"Suppression des identifiants existants: {self.credentials_pickle}")
            try:
                os.remove(self.credentials_pickle)
                print("Identifiants supprimés avec succès. Une nouvelle authentification sera nécessaire.")
                return True
            except Exception as e:
                print(f"Erreur lors de la suppression des identifiants: {e}")
                return False
        else:
            if self.debug:
                print("Aucun fichier d'identifiants à supprimer.")
            return False
    
    @staticmethod
    def print_setup_instructions(port=8080):
        """
        Affiche les instructions pour configurer correctement les URIs de redirection
        dans la console Google Cloud.
        
        Args:
            port (int): Le port à utiliser pour les URIs de redirection
        """
        print("\n=== INSTRUCTIONS DE CONFIGURATION ===")
        print("Pour éviter les erreurs 'redirect_uri_mismatch', ajoutez ces URIs de redirection")
        print("dans votre projet Google Cloud Console (APIs & Services > Credentials > OAuth 2.0 Client IDs):")
        print(f"1. http://localhost:{port}/")
        print(f"2. http://127.0.0.1:{port}/")
        print("\nAssurez-vous d'inclure le slash final '/' et vérifiez qu'il n'y a pas d'espaces.")
        print("Après avoir ajouté ces URIs, cliquez sur 'Save' et réessayez l'authentification.")
        print("===============================\n")

    @staticmethod
    def create_service_from_tokens(tokens_json_path):
        """
        Crée un service YouTube directement à partir d'un fichier de tokens JSON.
        Cette méthode est utile pour les scripts externes qui veulent utiliser les tokens
        sans passer par le processus d'authentification complet.
        
        Args:
            tokens_json_path (str): Chemin vers le fichier JSON contenant les tokens.
        
        Returns:
            object: Service YouTube initialisé, ou None en cas d'échec.
        """
        try:
            # Charger les tokens depuis le fichier JSON
            with open(tokens_json_path, 'r') as f:
                tokens = json.load(f)
            
            # Créer des identifiants à partir des tokens
            from google.oauth2.credentials import Credentials
            
            # Convertir la date d'expiration de chaîne ISO en objet datetime
            from datetime import datetime
            expiry = None
            if tokens.get("expiry"):
                try:
                    expiry = datetime.fromisoformat(tokens["expiry"])
                except ValueError:
                    pass
            
            # Créer l'objet Credentials
            credentials = Credentials(
                token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_uri=tokens["token_uri"],
                client_id=tokens["client_id"],
                client_secret=tokens["client_secret"],
                scopes=tokens["scopes"],
                expiry=expiry
            )
            
            # Rafraîchir le token si nécessaire
            if credentials.expired:
                credentials.refresh(Request())
                
                # Mettre à jour le fichier JSON avec le nouveau token d'accès
                tokens["access_token"] = credentials.token
                if credentials.expiry:
                    tokens["expiry"] = credentials.expiry.isoformat()
                
                with open(tokens_json_path, 'w') as f:
                    json.dump(tokens, f, indent=2)
            
            # Créer et retourner le service YouTube
            return googleapiclient.discovery.build(
                API_SERVICE_NAME, API_VERSION, credentials=credentials
            )
        
        except Exception as e:
            print(f"Erreur lors de la création du service à partir des tokens: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_tokens_path(account):
        """
        Retourne le chemin vers le fichier de tokens pour un compte donné.
        
        Args:
            account (str): Nom du compte
            
        Returns:
            str: Chemin vers le fichier de tokens JSON
        """
        # Obtenir le chemin absolu du répertoire où se trouve ce fichier (src/)
        src_dir = os.path.dirname(os.path.abspath(__file__))
        # Remonter d'un niveau pour obtenir le répertoire du projet
        project_dir = os.path.dirname(src_dir)
        # Construire le chemin vers le fichier de tokens
        return os.path.join(project_dir, "accounts", account, "tokens.json")


# Exemple d'utilisation
if __name__ == "__main__":
    # Afficher les instructions de configuration
    YouTubeUploader.print_setup_instructions(port=8080)
    
    # Utilisation avec un compte nommé "bloky" et mode débogage activé
    uploader = YouTubeUploader("bloky", debug=True)
    
    # En cas de problèmes d'authentification, vous pouvez réinitialiser les identifiants
    uploader.reset_credentials()
    
    # Utiliser un port fixe (8080) pour éviter les problèmes de redirect_uri_mismatch
    if uploader.authenticate(port=8080):
        uploader.upload_video(
            "video.mp4",
            "Ma vidéo uploadée avec Python",
            "Ceci est une description de test pour ma vidéo",
            ["python", "youtube", "api"],
            privacy_status="private"
        )

# Exemple d'utilisation dans un script externe:
"""
# Importer la classe YouTubeUploader
from uploader import YouTubeUploader

# Méthode 1: Utiliser directement l'uploader (nécessite une authentification préalable)
uploader = YouTubeUploader("bloky")
uploader.upload_video(
    "ma_video.mp4",
    "Titre de ma vidéo",
    "Description de ma vidéo",
    privacy_status="unlisted"
)

# Méthode 2: Créer un service YouTube à partir des tokens existants
# Cette méthode est utile si vous avez déjà effectué l'authentification
import googleapiclient.http

# Obtenir le chemin vers les tokens pour le compte 'bloky'
tokens_path = YouTubeUploader.get_tokens_path("bloky")

# Créer un service YouTube directement à partir des tokens
youtube = YouTubeUploader.create_service_from_tokens(tokens_path)

# Utiliser le service pour uploader une vidéo
if youtube:
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Titre de ma vidéo",
                "description": "Description de ma vidéo",
                "tags": ["python", "api", "youtube"]
            },
            "status": {
                "privacyStatus": "unlisted"
            }
        },
        media_body=googleapiclient.http.MediaFileUpload(
            "ma_video.mp4", 
            resumable=True
        )
    )
    
    # Exécuter l'upload
    response = None
    while response is None:
        status, response = request.next_chunk()
        
    print(f"Vidéo uploadée! ID: {response['id']}")
"""
