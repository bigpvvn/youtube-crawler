# Importer la classe YouTubeUploader
from uploader import YouTubeUploader

# Méthode 1: Utiliser directement l'uploader (nécessite une authentification préalable)
uploader = YouTubeUploader("bloky")
uploader.upload_video(
    "media/videos/3034011d.mp4",
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
            "media/videos/3034011d.mp4", 
            resumable=True
        )
    )
    
    # Exécuter l'upload
    response = None
    while response is None:
        status, response = request.next_chunk()
        
    print(f"Vidéo uploadée! ID: {response['id']}")
