from src.crawlers import YoutubeCrawler
from datetime import datetime, timedelta
from src.downloader import YouTubeDownloader
from src.editor import Editor
from src.uploader import YouTubeUploader
import os
import time
import json
import googleapiclient.errors
import googleapiclient.http
from rich.console import Console

# Configuration
YOUTUBE_ACCOUNT = "bloky"
MEDIA_DIR = "src/media/videos/"
MAX_VIDEOS = 1
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADED_VIDEOS_FILE = "src/media/uploaded_videos.json"

# Requête de recherche
query = "minecraft shorts"
filters = {
    "duration": {"min": 15, "max": 175},
    "views": {"min": 1000000, "max": 1000000000},
    "publishedTime": {
        "min": (datetime.now() - timedelta(days=365)).isoformat(),
        "max": datetime.now().isoformat()
    }
}

# Initialisation
console = Console()
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, "accounts", YOUTUBE_ACCOUNT), exist_ok=True)

# Listes de vidéos
buffer_videos = []
uploaded_videos = []
failed_videos = []

def get_tokens_path(account_name):
    return os.path.join(PROJECT_DIR, "accounts", account_name, "tokens.json")

def truncate_text(text, max_length=50):
    if not text:
        return ""
    return text if len(text) <= max_length else text[:max_length-3] + "..."

def clean_tags(tags_str):
    if not tags_str:
        return []
    if ',' in tags_str:
        return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    return [tag.strip() for tag in tags_str.split() if tag.strip()]

def init_youtube_service():
    tokens_path = get_tokens_path(YOUTUBE_ACCOUNT)
    
    if not os.path.exists(tokens_path):
        console.print(f"[bold red]Fichier de tokens introuvable: {tokens_path}")
        console.print("[yellow]Exécutez d'abord src/uploader.py pour générer les tokens.")
        return None
    
    try:
        service = YouTubeUploader.create_service_from_tokens(tokens_path)
        return service
    except Exception as e:
        console.print(f"[bold red]Erreur: {str(e)}")
        return None

def upload_to_youtube(youtube_service, video_path, title, description, tags, privacy="private"):
    if not os.path.exists(video_path) or not youtube_service:
        return {"success": False, "error": f"Fichier introuvable ou service non initialisé"}
    
    try:
        request = youtube_service.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "22"
                },
                "status": {
                    "privacyStatus": privacy
                }
            },
            media_body=googleapiclient.http.MediaFileUpload(video_path, resumable=True)
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
        
        if response and "id" in response:
            return {
                "success": True,
                "video_id": response["id"],
                "url": f"https://www.youtube.com/watch?v={response['id']}",
                "video_path": video_path
            }
        else:
            return {"success": False, "error": "Upload échoué"}
            
    except googleapiclient.errors.HttpError as e:
        error_reason = "Erreur inconnue"
        try:
            error_content = json.loads(e.content.decode('utf-8'))
            if 'error' in error_content and 'message' in error_content['error']:
                error_reason = error_content['error']['message']
        except:
            pass
        
        return {"success": False, "error": f"Erreur HTTP: {error_reason}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def process_video(youtube_service, video):
    current_video = video.copy()
    
    console.print("\n[bold cyan]Traitement:[/bold cyan] " + current_video['title'])
    console.print("[bold]Téléchargement...[/bold]")
    
    video_download = YouTubeDownloader().download(current_video['url'])
    
    if not video_download['success']:
        console.print("[bold red]✗ Échec du téléchargement[/bold red]")
        current_video["error"] = "Échec du téléchargement"
        failed_videos.append(current_video)
        return False
    
    download_id = video_download['download_id']
    console.print("[bold green]✓ Téléchargement terminé[/bold green]")
    
    console.print("[bold]Édition...[/bold]")
    try:
        edited_video_id = Editor.add_entertainment_video(download_id)
        console.print(f"[bold green]✓ Édition terminée[/bold green] [bold cyan]ID: {edited_video_id}[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]✗ Échec de l'édition[/bold red]")
        current_video["error"] = f"Échec de l'édition: {str(e)}"
        failed_videos.append(current_video)
        return False
    
    upload_data = {
        "title": current_video['title'],
        "description": "Follow and like for more videos like this one ! ❤",
        "tags": clean_tags(query),
        "privacy": "private",
        "video_path": f"{edited_video_id}.mp4"
    }
    
    full_video_path = os.path.join(MEDIA_DIR, upload_data["video_path"])
    
    if not os.path.exists(full_video_path):
        alt_video_path = os.path.join("videos", upload_data["video_path"])
        if os.path.exists(alt_video_path):
            full_video_path = alt_video_path
        else:
            console.print("[bold red]✗ Fichier vidéo introuvable[/bold red]")
            current_video["error"] = "Fichier vidéo introuvable"
            failed_videos.append(current_video)
            return False
    
    console.print("[bold]Upload YouTube...[/bold]")
    upload_result = upload_to_youtube(
        youtube_service,
        full_video_path,
        upload_data["title"],
        upload_data["description"],
        upload_data["tags"],
        privacy=upload_data["privacy"]
    )
    
    if upload_result["success"]:
        console.print(f"[bold green]✓ Upload terminé - ID: {upload_result['video_id']}[/bold green]")
        
        current_video["video_id"] = upload_result["video_id"]
        current_video["youtube_url"] = upload_result["url"]
        uploaded_videos.append(current_video)
        
        # Ajouter l'ID YouTube au fichier de vidéos uploadées
        try:
            # Charger le fichier existant
            uploaded_data = {"videos": []}
            if os.path.exists(UPLOADED_VIDEOS_FILE):
                with open(UPLOADED_VIDEOS_FILE, "r") as f:
                    uploaded_data = json.load(f)
            
            # Ajouter la nouvelle vidéo
            uploaded_data["videos"].append({
                "videoId": current_video.get("youtube_id", ""),
                "uploadedId": upload_result["video_id"]
            })
            
            # Sauvegarder le fichier
            with open(UPLOADED_VIDEOS_FILE, "w") as f:
                json.dump(uploaded_data, f, indent=4)
            
            console.print("[bold green]✓ ID YouTube ajouté à uploaded_videos.json[/bold green]")
        except Exception as e:
            console.print(f"[bold yellow]⚠ Erreur lors de l'ajout à uploaded_videos.json: {str(e)}[/bold yellow]")
        
        # Supprimer le fichier vidéo
        try:
            if os.path.exists(full_video_path):
                os.remove(full_video_path)
                console.print("[bold green]✓ Fichier vidéo supprimé[/bold green]")
        except Exception as e:
            console.print(f"[bold yellow]⚠ Erreur lors de la suppression du fichier vidéo: {str(e)}[/bold yellow]")
        
        return True
    else:
        console.print(f"[bold red]✗ Échec de l'upload: {upload_result.get('error')}[/bold red]")
        current_video["error"] = upload_result.get("error", "Erreur inconnue")
        failed_videos.append(current_video)
        return False

def display_summary():
    console.print("\n[bold blue]RÉSUMÉ[/bold blue]")
    
    if buffer_videos:
        console.print(f"[cyan]Buffer:[/cyan] {len(buffer_videos)} vidéos")
    
    if uploaded_videos:
        console.print(f"[green]Uploadées:[/green] {len(uploaded_videos)} vidéos")
        for i, video in enumerate(uploaded_videos, 1):
            console.print(f"  {i}. {truncate_text(video['title'], 60)} [ID: {video.get('video_id', 'N/A')}]")
    
    if failed_videos:
        console.print(f"[red]Échecs:[/red] {len(failed_videos)} vidéos")
        for i, video in enumerate(failed_videos, 1):
            console.print(f"  {i}. {truncate_text(video['title'], 60)} [Erreur: {truncate_text(video.get('error', 'Erreur'), 40)}]")

def main():
    youtube_service = init_youtube_service()
    if not youtube_service:
        return
    
    try:
        console.print("[bold cyan]RECHERCHE DE VIDÉOS[/bold cyan]")
        
        youtube_crawler = YoutubeCrawler()
        
        for video in youtube_crawler.stream_crawl(query, filters):
            video_info = {
                "title": video['title'],
                "url": video['url'],
                "thumbnail": video['thumbnail'],
                "youtube_id": video['videoId']
            }
            buffer_videos.append(video_info)
            
            console.print(f"Trouvé: {truncate_text(video['title'], 60)}")
            
            if len(buffer_videos) >= MAX_VIDEOS:
                console.print(f"[yellow]Limite de {MAX_VIDEOS} vidéos atteinte.[/yellow]")
                break
        
        display_summary()
        
        console.print("\n[bold cyan]TRAITEMENT DES VIDÉOS[/bold cyan]")
        
        while buffer_videos:
            video = buffer_videos.pop(0)
            process_success = process_video(youtube_service, video)
            
            # Recharger la liste des vidéos déjà téléchargées pour éviter les doublons
            if process_success:
                console.print("[cyan]Mise à jour de la liste des vidéos téléchargées...[/cyan]")
                youtube_crawler.reload_uploaded_videos()
                
            display_summary()
        
        console.print("\n[bold green]TRAITEMENT TERMINÉ ![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interruption manuelle détectée.[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Erreur: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()

