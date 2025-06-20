import requests
import json
import bs4
import re
from abc import abstractmethod
from datetime import datetime, timedelta
import os

class Crawler:
    def __init__(self, key):

        self.routes = self.get_routes(key)
        self.uploaded_videos = self.load_uploaded_videos()

    def get_routes(self, key):
        with open("src/routes.json", "r") as f:
            return json.load(f)[key]
    
    def reload_uploaded_videos(self):
        """Recharge la liste des vidéos déjà téléchargées"""
        self.uploaded_videos = self.load_uploaded_videos()
        return len(self.uploaded_videos)
    
    def load_uploaded_videos(self):
        """Charge la liste des vidéos déjà téléchargées"""
        try:
            with open("src/media/uploaded_videos.json", "r") as f:
                data = json.load(f)
                # Création d'un ensemble contenant à la fois les IDs originaux et les IDs uploadés
                uploaded_ids = set()
                for video in data.get("videos", []):
                    if video.get("videoId"):
                        uploaded_ids.add(video.get("videoId"))
                    if video.get("uploadedId"):
                        uploaded_ids.add(video.get("uploadedId"))
                return uploaded_ids
        except (FileNotFoundError, json.JSONDecodeError):
            return set()

    def headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }
    
    def get_video_soup(self, video_url):
        return bs4.BeautifulSoup(requests.get(video_url, headers=self.headers()).text, "html.parser")
    
    def _matches_filters(self, video, filters):
        """Vérifie si une vidéo correspond aux filtres spécifiés"""
        # Vérifier si la vidéo est déjà téléchargée
        if video.get('videoId') in self.uploaded_videos:
            return False
            
        if not filters:
            return True
        
        # Filtre par durée
        if 'duration' in filters and video.get('duration') is not None:
            duration = video['duration']
            if 'min' in filters['duration'] and duration < filters['duration']['min']:
                return False
            if 'max' in filters['duration'] and duration > filters['duration']['max']:
                return False
        
        # Filtre par nombre de vues
        if 'views' in filters and video.get('views') is not None:
            views = video['views']
            if 'min' in filters['views'] and views < filters['views']['min']:
                return False
            if 'max' in filters['views'] and views > filters['views']['max']:
                return False
        
        # Filtre par date de publication
        if 'publishedTime' in filters and video.get('publishedTime'):
            try:
                # Convertir la date de la vidéo en datetime pour la comparaison
                video_date = video['publishedTime']
                if isinstance(video_date, str) and 'T' in video_date:
                    video_datetime = datetime.fromisoformat(video_date.replace('Z', '+00:00'))
                    
                    if 'min' in filters['publishedTime']:
                        min_date = datetime.fromisoformat(filters['publishedTime']['min'].replace('Z', '+00:00'))
                        if video_datetime < min_date:
                            return False
                    
                    if 'max' in filters['publishedTime']:
                        max_date = datetime.fromisoformat(filters['publishedTime']['max'].replace('Z', '+00:00'))
                        if video_datetime > max_date:
                            return False
            except:
                # Si on ne peut pas parser la date, on ignore ce filtre
                pass
        
        return True
    
    def crawl(self, query, size, filters=None):
        crawled_videos = []
        matched_videos = []
        seen_videosID = set()  # Pour éviter les doublons

        # Recherche initiale
        init_search = self.search(query)
        init_videos = self.extract_videos(init_search)

        # Ajout des vidéos initiales
        for video in init_videos:
            if video["videoId"] not in seen_videosID and video["videoId"] not in self.uploaded_videos:
                crawled_videos.append(video)
                seen_videosID.add(video["videoId"])
                if self._matches_filters(video, filters):
                    matched_videos.append(video)

        # Boucle principale de recherche
        iteration = 0
        explored_videos = set()  # Pour tracker les vidéos déjà explorées
        
        while len(matched_videos) < size:
            iteration += 1
            
            # Vérifier s'il y a encore des vidéos non explorées
            videos_to_explore = [v for v in crawled_videos if v['videoId'] not in explored_videos]
            
            if not videos_to_explore:
                break
                
            current_batch = videos_to_explore  # Explorer seulement les vidéos non explorées
            
            for video in current_batch:
                if len(matched_videos) >= size:
                    break
                
                explored_videos.add(video['videoId'])  # Marquer comme explorée
                video_url = video["url"]
                video_soup = self.get_video_soup(video_url)

                if video_soup:
                    related_videos = self.extract_videos(video_soup)
                    # Ajout des nouvelles vidéos uniques
                    for new_video in related_videos:
                        if new_video["videoId"] not in seen_videosID and new_video["videoId"] not in self.uploaded_videos:
                            crawled_videos.append(new_video)
                            seen_videosID.add(new_video["videoId"])
                            if self._matches_filters(new_video, filters):
                                matched_videos.append(new_video)
                            
                            if len(matched_videos) >= size:
                                break

        return matched_videos[:size]  # Retourne exactement le nombre demandé de vidéos

    def stream_crawl(self, query, filters=None):
        """
        Générateur qui retourne les vidéos une par une au fur et à mesure du crawl
        Sans limite de taille - continue indéfiniment jusqu'à épuisement
        
        Args:
            query (str): Terme de recherche initial
            filters (dict): Filtres optionnels à appliquer
            
        Yields:
            dict: Vidéo qui correspond aux filtres (une à la fois)
        """
        seen_videosID = set()  # Pour éviter les doublons
        videos_to_explore = []  # Liste des vidéos à explorer
        explored_videos = set()  # Vidéos déjà explorées
        
        # Recherche initiale
        init_search = self.search(query)
        if init_search:
            init_videos = self.extract_videos(init_search)
            
            # Ajouter les vidéos initiales
            for video in init_videos:
                if video["videoId"] not in seen_videosID and video["videoId"] not in self.uploaded_videos:
                    seen_videosID.add(video["videoId"])
                    videos_to_explore.append(video)
                    
                    # Yield si elle correspond aux filtres
                    if self._matches_filters(video, filters):
                        yield video
        
        # Exploration continue
        while videos_to_explore:
            # Prendre la prochaine vidéo non explorée
            current_video = None
            for video in videos_to_explore:
                if video['videoId'] not in explored_videos:
                    current_video = video
                    break
            
            if not current_video:
                # Toutes les vidéos ont été explorées
                break
            
            explored_videos.add(current_video['videoId'])
            video_url = current_video["url"]
            
            # Obtenir les vidéos connexes
            video_soup = self.get_video_soup(video_url)
            if video_soup:
                related_videos = self.extract_videos(video_soup)
                
                for new_video in related_videos:
                    if new_video["videoId"] not in seen_videosID and new_video["videoId"] not in self.uploaded_videos:
                        seen_videosID.add(new_video["videoId"])
                        videos_to_explore.append(new_video)
                        
                        # Yield immédiatement si elle correspond aux filtres
                        if self._matches_filters(new_video, filters):
                            yield new_video

    @abstractmethod
    def search(self, query):
        pass

class YoutubeCrawler(Crawler):
    def __init__(self):
        super().__init__("youtube")

        self.base_search_url = self.routes["base_search_url"]
        self.base_video_url = self.routes["base_video_url"]
        self.base_channel_url = self.routes["base_channel_url"]
        self.base_playlist_url = self.routes["base_playlist_url"]
        self.base_short_url = self.routes["base_short_url"]

    def search(self, query):
        try:

            url = self.base_search_url + query

            response = requests.get(url, headers=self.headers())
            return bs4.BeautifulSoup(response.text, "html.parser")
        except Exception:
            return None

    def extract_videos(self, soup):
        try:
            script = soup.find('script', string=re.compile('var ytInitialData'))
            if not script:
                return []
            
            script_content = script.string
            json_match = re.search(r'var ytInitialData = ({.*?});', script_content)
            if not json_match:
                return []
            
            data = json.loads(json_match.group(1))
            videos = []
            
            # Cas 1: Page de recherche
            search_contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
            
            if search_contents:
                for section in search_contents:
                    for item in section.get('itemSectionRenderer', {}).get('contents', []):
                        v = item.get('videoRenderer') or item.get('compactVideoRenderer')
                        if v:
                            videos.append(self._extract_video_info(v))
            
            # Cas 2: Page de vidéo - vidéos recommandées dans la colonne secondaire
            secondary_results = data.get('contents', {}).get('twoColumnWatchNextResults', {}).get('secondaryResults', {}).get('secondaryResults', {}).get('results', [])
            
            if secondary_results:
                for item in secondary_results:
                    # Vidéos dans compactVideoRenderer
                    v = item.get('compactVideoRenderer')
                    if v:
                        videos.append(self._extract_video_info(v))
                    
                    # Vidéos dans reel shelf (shorts)
                    reel_shelf = item.get('reelShelfRenderer')
                    if reel_shelf:
                        for reel_item in reel_shelf.get('items', []):
                            v = reel_item.get('reelItemRenderer')
                            if v:
                                videos.append(self._extract_video_info(v, is_short=True))
                    
                    # Vidéos dans shelf renderer
                    shelf = item.get('shelfRenderer')
                    if shelf:
                        shelf_content = shelf.get('content', {}).get('verticalListRenderer', {}).get('items', [])
                        for shelf_item in shelf_content:
                            v = shelf_item.get('compactVideoRenderer')
                            if v:
                                videos.append(self._extract_video_info(v))
            
            # Cas 3: EndScreen videos (vidéos suggérées à la fin)
            endscreen = data.get('playerOverlays', {}).get('playerOverlayRenderer', {}).get('endScreen', {}).get('watchNextEndScreenRenderer', {}).get('results', [])
            
            for item in endscreen:
                v = item.get('endScreenVideoRenderer')
                if v:
                    videos.append(self._extract_video_info(v))
            
            return videos
            
        except (json.JSONDecodeError, Exception) as e:
            return []
    
    def _extract_video_info(self, v, is_short=False):
        """Extrait les informations d'une vidéo depuis le renderer"""
        video_id = v.get('videoId', '')
        
        # Pour les shorts/reels
        if not video_id and 'navigationEndpoint' in v:
            watch_endpoint = v.get('navigationEndpoint', {}).get('watchEndpoint', {})
            video_id = watch_endpoint.get('videoId', '')
            
            # Alternativement, extraire de l'URL
            if not video_id:
                reel_endpoint = v.get('navigationEndpoint', {}).get('reelWatchEndpoint', {})
                video_id = reel_endpoint.get('videoId', '')
        
        # Titre
        title = ''
        if 'title' in v:
            if isinstance(v['title'], dict):
                title = v['title'].get('simpleText', '') or v['title'].get('runs', [{}])[0].get('text', '')
            else:
                title = str(v['title'])
        
        # Propriétaire/Chaîne
        channel = ''
        channel_id = ''
        if 'ownerText' in v:
            channel = v['ownerText'].get('runs', [{}])[0].get('text', '')
            channel_id = v['ownerText'].get('runs', [{}])[0].get('navigationEndpoint', {}).get('browseEndpoint', {}).get('browseId', '')
        elif 'shortBylineText' in v:
            channel = v['shortBylineText'].get('runs', [{}])[0].get('text', '')
            channel_id = v['shortBylineText'].get('runs', [{}])[0].get('navigationEndpoint', {}).get('browseEndpoint', {}).get('browseId', '')
        
        # Vues
        views = 0
        if 'viewCountText' in v:
            if isinstance(v['viewCountText'], dict):
                views_text = v['viewCountText'].get('simpleText', '') or v['viewCountText'].get('runs', [{}])[0].get('text', '')
                views = self._parse_views(views_text)
        elif 'shortViewCountText' in v:
            if isinstance(v['shortViewCountText'], dict):
                views_text = v['shortViewCountText'].get('simpleText', '') or v['shortViewCountText'].get('runs', [{}])[0].get('text', '')
                views = self._parse_views(views_text)
        
        # Durée
        duration = 0
        if 'lengthText' in v:
            duration_text = v['lengthText'].get('simpleText', '')
            duration = self._parse_duration(duration_text)
        
        # Date de publication
        published_time = None
        if 'publishedTimeText' in v:
            published_time_text = v['publishedTimeText'].get('simpleText', '')
            published_time = self._parse_published_time(published_time_text)
        
        # Miniature
        thumbnail = ''
        if 'thumbnail' in v and 'thumbnails' in v['thumbnail']:
            thumbnails = v['thumbnail']['thumbnails']
            if thumbnails:
                thumbnail = thumbnails[-1].get('url', '')
        
        # URL de la vidéo
        url = f"{self.base_video_url}{video_id}" if video_id else ''
        if is_short and video_id:
            url = f"https://www.youtube.com/shorts/{video_id}"
        
        return {
            'videoId': video_id,
            'title': title,
            'channel': channel,
            'channelId': channel_id,
            'views': views,  # Nombre entier de vues
            'publishedTime': published_time,  # Date ISO string ou texte original
            'duration': duration,  # Durée en secondes (entier)
            'thumbnail': thumbnail,
            'url': url
        }

    def _parse_views(self, views_text):
        """Convertit le texte des vues en nombre entier"""
        if not views_text:
            return 0
        try:
            # Supprime 'views', 'vues', les espaces et les virgules
            views_text = views_text.lower()
            views_text = views_text.replace('views', '').replace('vues', '').replace('de vues', '')
            views_text = views_text.replace(',', '').replace(' ', '').strip()
            
            # Gère les suffixes K, M, B
            multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
            for suffix, multiplier in multipliers.items():
                if views_text.endswith(suffix):
                    number = views_text[:-1].replace(',', '.')  # Remplace virgule par point pour les décimales
                    return int(float(number) * multiplier)
            
            # Essaie de parser directement comme nombre
            return int(float(views_text))
        except (ValueError, AttributeError):
            return 0

    def _parse_duration(self, duration_text):
        """Convertit la durée en secondes"""
        if not duration_text:
            return 0
        try:
            parts = duration_text.split(':')
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            return 0
        except (ValueError, AttributeError):
            return 0

    def _parse_published_time(self, time_text):
        """Convertit le texte de la date de publication en chaîne ISO datetime"""
        if not time_text:
            return None
        from datetime import datetime, timedelta
        now = datetime.now()
        
        # Parse le texte pour obtenir la date
        published_date = now
        
        if 'hour' in time_text or 'hours' in time_text:
            hours = int(time_text.split()[0])
            published_date = now - timedelta(hours=hours)
        elif 'day' in time_text or 'days' in time_text:
            days = int(time_text.split()[0])
            published_date = now - timedelta(days=days)
        elif 'week' in time_text or 'weeks' in time_text:
            weeks = int(time_text.split()[0])
            published_date = now - timedelta(weeks=weeks)
        elif 'month' in time_text or 'months' in time_text:
            months = int(time_text.split()[0])
            published_date = now - timedelta(days=months*30)
        elif 'year' in time_text or 'years' in time_text:
            years = int(time_text.split()[0])
            published_date = now - timedelta(days=years*365)
        else:
            return time_text  # Retourne le texte original si non reconnu
        
        # Retourne la date au format ISO
        return published_date.isoformat()
