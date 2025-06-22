from flask import Flask, request, Response
import requests
from urllib.parse import urlparse, urljoin, quote, unquote
import re

app = Flask(__name__)

def detect_m3u_type(content):
    if "#EXTM3U" in content and "#EXTINF" in content:
        return "m3u8"
    return "m3u"

def replace_key_uri(line, headers_query):
    match = re.search(r'URI="([^"]+)"', line)
    if match:
        key_url = match.group(1)
        proxied_key_url = f"/proxy/key?url={quote(key_url)}&{headers_query}"
        return line.replace(key_url, proxied_key_url)
    return line

def extract_headers_from_request():
    # Gelen query'den h_ ile başlayanları header formatına çevir
    return {
        unquote(k[2:]).replace("_", "-"): unquote(v).strip()
        for k, v in request.args.items()
        if k.lower().startswith("h_")
    }

@app.route('/proxy/m3u')
def proxy_m3u():
    m3u_url = request.args.get('url', '').strip()
    if not m3u_url:
        return "Hata: 'url' parametresi eksik", 400

    default_headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bosstv4.com/"
    }
    headers = {**default_headers, **extract_headers_from_request()}

    try:
        resp = requests.get(m3u_url, headers=headers, timeout=(10, 20))
        resp.raise_for_status()
        m3u_content = resp.text
        file_type = detect_m3u_type(m3u_content)

        allowed_extensions = [".ts", ".avif", ".mp4", ".aac", ".m4s", ".jpg", ".png"]
        segment_lines = [l for l in m3u_content.splitlines() if l.strip() and not l.startswith("#")]

        if file_type == "m3u8" and all(any(ext in l for ext in allowed_extensions) for l in segment_lines):
            # Eğer direkt streamlenebilir uzantılar varsa orijinal content-type ile dön
            return Response(m3u_content, content_type="application/vnd.apple.mpegurl")

        parsed_url = urlparse(resp.url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path.rsplit('/', 1)[0]}/"
        headers_query = "&".join([f"h_{quote(k)}={quote(v)}" for k, v in headers.items()])

        modified_lines = []
        for line in m3u_content.splitlines():
            line = line.strip()
            if line.startswith("#EXT-X-KEY") and 'URI="' in line:
                line = replace_key_uri(line, headers_query)
            elif line and not line.startswith("#"):
                full_url = urljoin(base_url, line)
                # Segmentleri proxy/ts endpointine yönlendiriyoruz, headerları da parametre olarak iletiyoruz
                line = f"/proxy/ts?url={quote(full_url)}&{headers_query}"
            modified_lines.append(line)

        return Response("\n".join(modified_lines), content_type="application/vnd.apple.mpegurl")

    except requests.RequestException as e:
        return f"İndirme hatası: {str(e)}", 500

@app.route('/proxy/ts')
def proxy_ts():
    ts_url = request.args.get('url', '').strip()
    if not ts_url:
        return "Hata: 'url' parametresi eksik", 400

    headers = extract_headers_from_request()
    # Eğer Accept-Encoding varsa 'gzip, deflate, br' gibi ayar yapabiliriz (requests default handle eder)

    try:
        # Stream modunda segmenti çekip aynı şekilde akıtıyoruz
        resp = requests.get(ts_url, headers=headers, stream=True, timeout=(10, 30))
        resp.raise_for_status()

        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        # İçeriği video/mp2t olarak dön, segment tipine göre Content-Type değişebilir ama genelde bu yeterli
        return Response(generate(), content_type=resp.headers.get('Content-Type', 'application/octet-stream'))

    except requests.RequestException as e:
        return f"Segment hatası: {str(e)}", 500

@app.route('/proxy/key')
def proxy_key():
    key_url = request.args.get('url', '').strip()
    if not key_url:
        return "Hata: 'url' parametresi eksik", 400

    headers = extract_headers_from_request()

    try:
        resp = requests.get(key_url, headers=headers, timeout=(5, 15))
        resp.raise_for_status()
        return Response(resp.content, content_type="application/octet-stream")
    except requests.RequestException as e:
        return f"Key hatası: {str(e)}", 500

@app.route('/')
def index():
    return "Proxy aktif!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7860)
