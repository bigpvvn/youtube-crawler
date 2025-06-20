"""Module de téléchargement YouTube avec yt-dlp"""

import os
import uuid
from yt_dlp import YoutubeDL

class Downloader:
    def __init__(self, download_dir="src/media/download"):
        self.download_dir = download_dir
        self.download_id = str(uuid.uuid4())
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

class YouTubeDownloader(Downloader):
    def __init__(self, download_dir="src/media/download"):
        self.download_dir = download_dir
        self.download_id = str(uuid.uuid4())
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    def download(self, url, quality='best'):
        try:
            if isinstance(url, dict):
                video_url = url.get('url') or f"https://www.youtube.com/watch?v={url.get('videoId')}"
                if not video_url:
                    return {'success': False, 'error': 'Aucune URL trouvée', 'download_id': self.download_id}
            else:
                video_url = url
            
            format_selector = 'best[ext=mp4]/best' if quality == 'best' else \
                            f'best[height<={quality}][ext=mp4]/best[height<={quality}]/best' if quality.isdigit() else \
                            'best'
            
            ydl_opts = {
                'format': format_selector,
                'outtmpl': os.path.join(self.download_dir, f'{self.download_id}.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [self._progress_hook],
                'prefer_free_formats': True,
                'noplaylist': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                return {
                    'success': True,
                    'download_id': self.download_id
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e), 'download_id': self.download_id}
    
    def _progress_hook(self, d):
        pass

if __name__ == "__main__":
    input_url = input("Enter the URL: ")
    downloader = YouTubeDownloader()
    downloader.download(input_url)