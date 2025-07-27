from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url):
    """Wyciąga ID video z różnych formatów URL YouTube"""
    patterns = [
        r'(?:youtube\.com/watch\?v=)([^&\n?#]+)',
        r'(?:youtu\.be/)([^&\n?#]+)',
        r'(?:youtube\.com/embed/)([^&\n?#]+)',
        r'(?:youtube\.com/v/)([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Health check endpoint
        if self.path == '/api/transcript':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "OK",
                "message": "YouTube Transcript API is running",
                "endpoints": {
                    "POST /api/transcript": "Send JSON with 'url' field",
                    "GET /api/transcript?url=YOUTUBE_URL": "Direct URL parameter"
                }
            }
            self.wfile.write(json.dumps(response).encode())
            return
        
        # GET request with URL parameter
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'url' not in query_params:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "error": "Brak parametru 'url'",
                "example": "/api/transcript?url=https://youtube.com/watch?v=VIDEO_ID&lang=pl"
            }
            self.wfile.write(json.dumps(error_response).encode())
            return
        
        youtube_url = query_params['url'][0]
        language = query_params.get('lang', ['pl'])[0]
        
        try:
            result = self.get_transcript(youtube_url, language)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "error": f"Błąd: {str(e)}",
                "url": youtube_url
            }
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            
            if 'url' not in data:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_response = {
                    "error": "Brak pola 'url' w JSON",
                    "example": {"url": "https://youtube.com/watch?v=VIDEO_ID", "language": "pl"}
                }
                self.wfile.write(json.dumps(error_response).encode())
                return
            
            youtube_url = data['url']
            language = data.get('language', 'pl')
            
            result = self.get_transcript(youtube_url, language)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {"error": "Nieprawidłowy format JSON"}
            self.wfile.write(json.dumps(error_response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "error": f"Błąd: {str(e)}",
                "url": data.get('url', 'unknown') if 'data' in locals() else 'unknown'
            }
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def get_transcript(self, url, language):
        # Wyciągnij ID video
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("Nieprawidłowy URL YouTube")
        
        # Lista języków do wypróbowania
        languages_to_try = [language]
        if language != 'en':
            languages_to_try.append('en')
        if language != 'auto':
            languages_to_try.append('auto')
        
        # Pobierz transkrypcję
        transcript_list = YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=languages_to_try
        )
        
        # Połącz tekst w jeden string
        full_text = ' '.join([item['text'] for item in transcript_list])
        
        # Oblicz całkowity czas trwania
        total_duration = max([item['start'] + item['duration'] for item in transcript_list]) if transcript_list else 0
        
        return {
            "video_id": video_id,
            "url": url,
            "language": language,
            "transcript": full_text,
            "segments": transcript_list,
            "total_segments": len(transcript_list),
            "duration": round(total_duration, 2),
            "word_count": len(full_text.split())
        }