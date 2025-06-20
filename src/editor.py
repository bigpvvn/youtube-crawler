import os
import random
import uuid
from moviepy import VideoFileClip, CompositeVideoClip
import glob
import logging
import sys
from contextlib import contextmanager

# Configurer le logging pour réduire la verbosité
logging.basicConfig(level=logging.ERROR)

# Créer un context manager pour rediriger stdout/stderr
@contextmanager
def suppress_stdout_stderr():
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    null = open(os.devnull, "w")
    sys.stdout = null
    sys.stderr = null
    try:
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        null.close()

class Editor:
    @staticmethod
    def add_entertainment_video(download_id, duration=None):
        download_dir = "src/media/download"
        entertainment_dir = "src/media/entertainment_videos"
        output_dir = "src/media/videos"
        
        # Créer les répertoires nécessaires
        os.makedirs(entertainment_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Find main video
        main_videos = glob.glob(os.path.join(download_dir, f"*{download_id}*.mp4"))
        if not main_videos:
            return None
        
        main_video_path = main_videos[0]
        
        # Utiliser le context manager pour supprimer les sorties lors du chargement
        with suppress_stdout_stderr():
            main_clip = VideoFileClip(main_video_path)
        
        if duration is None:
            duration = main_clip.duration
        
        # Extract audio from main video
        main_audio = main_clip.audio
        
        # Get random entertainment video
        entertainment_videos = glob.glob(os.path.join(entertainment_dir, "*.mp4"))
        if not entertainment_videos:
            main_clip.close()
            return None
        
        entertainment_path = random.choice(entertainment_videos)
        
        # Utiliser le context manager pour supprimer les sorties lors du chargement
        with suppress_stdout_stderr():
            entertainment_clip = VideoFileClip(entertainment_path)
        
        # Extract random part
        if entertainment_clip.duration > duration:
            start = random.uniform(0, entertainment_clip.duration - duration)
            entertainment_clip = entertainment_clip.subclipped(start, start + duration)
        else:
            # Dans MoviePy v2.x, loop() a été remplacé
            entertainment_clip = entertainment_clip.with_loop(duration=duration)
        
        # Calculer les dimensions pour que l'entertainment video couvre 1/3 de la hauteur
        w = main_clip.w
        h = main_clip.h
        entertainment_height = h // 3  # 1/3 de la hauteur originale
        
        # Redimensionner l'entertainment video pour qu'elle couvre 1/3 de la hauteur
        entertainment_clip = entertainment_clip.resized(width=w, height=entertainment_height)
        
        # Positionner l'entertainment video en superposition en bas de la vidéo originale
        # La position y est la hauteur de la vidéo originale moins la hauteur de l'entertainment video
        entertainment_clip = entertainment_clip.with_position((0, h - entertainment_height))
        
        # Créer la vidéo composite avec l'entertainment video par-dessus la vidéo originale
        final = CompositeVideoClip([main_clip, entertainment_clip])
        
        # Remplacer l'audio par l'audio original
        if main_audio is not None:
            final = final.with_audio(main_audio)
        
        # Save with new ID
        new_id = str(uuid.uuid4())[:8]
        output_path = os.path.join(output_dir, f"{new_id}.mp4")
        
        # Écrire le fichier vidéo en supprimant la sortie standard
        with suppress_stdout_stderr():
            try:
                # Utiliser ffmpeg_params pour désactiver les barres de progression
                final.write_videofile(output_path, codec='libx264', audio_codec='aac', 
                                     ffmpeg_params=["-loglevel", "quiet", "-hide_banner"])
            except Exception as e:
                print(f"Erreur lors de l'écriture de la vidéo: {e}")
        
        # Fermer les clips pour libérer les ressources
        main_clip.close()
        entertainment_clip.close()
        final.close()
        
        # Supprimer la vidéo originale après avoir terminé le montage
        try:
            if os.path.exists(main_video_path):
                os.remove(main_video_path)
        except Exception:
            pass  # Ignorer silencieusement les erreurs
        
        return new_id
