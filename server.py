from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL
import os, uuid
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

DOWNLOADS_DIR = 'downloads'
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# === Firebase Setup ===
cred = credentials.Certificate('firebase_key.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

def save_to_firebase(url, title, platform, thumbnail):
    db.collection('media_history').add({
        'url': url,
        'title': title,
        'platform': platform,
        'thumbnail': thumbnail,
        'timestamp': datetime.utcnow()
    })

@app.route('/')
def home():
    return "Media Downloader API is running!"

@app.route('/api/get-media', methods=['POST'])
def get_media():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        uid = str(uuid.uuid4())
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, f"{uid}.%(ext)s"),
            'quiet': True,
            'noplaylist': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get('ext', 'mp4')
            filename = f"{uid}.{ext}"
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            title = info.get('title', 'media')
            platform = info.get('extractor_key', 'unknown')
            thumb = info.get('thumbnail', '')

        save_to_firebase(url, title, platform, thumb)

        return jsonify({
            'download_url': f'/api/download/{filename}',
            'stream_url': f'/api/stream/{filename}',
            'title': title,
            'platform': platform,
            'thumbnail': thumb
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream/<filename>')
def stream_file(filename):
    path = os.path.join(DOWNLOADS_DIR, filename)
    if os.path.exists(path):
        return send_file(path)  # Stream for preview
    return "File not found", 404

@app.route('/api/download/<filename>')
def download_file(filename):
    path = os.path.join(DOWNLOADS_DIR, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)  # Download
    return "File not found", 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)