#!/usr/bin/env python3
"""Small dependency-free web gateway for the local Google Maps scraper."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent / "web"
SCRAPER_URL = os.environ.get("SCRAPER_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
PORT = int(os.environ.get("PORT", "3000"))
USER_AGENT = "maps-lead-finder/1.0 (local development app)"
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print(f"{self.client_address[0]} - {fmt % args}")

    def json_response(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def proxy(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{SCRAPER_URL}{path}", data=data, method=method,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=65) as response:
                payload = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as error:
            self.json_response(error.code, {"error": error.read().decode(errors="replace")[:500]})
        except (urllib.error.URLError, TimeoutError) as error:
            self.json_response(502, {"error": "Scraper service is unavailable", "detail": str(error.reason if hasattr(error, "reason") else error)})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            return self.proxy("GET", "/api/v1/jobs")
        if parsed.path == "/api/geocode":
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
            if not query:
                return self.json_response(400, {"error": "Location is required"})
            try:
                if GOOGLE_MAPS_API_KEY:
                    url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode({
                        "address": query, "key": GOOGLE_MAPS_API_KEY,
                    })
                else:
                    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
                        "q": query, "format": "jsonv2", "limit": 1,
                    })
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read())
                if GOOGLE_MAPS_API_KEY:
                    if payload.get("status") != "OK" or not payload.get("results"):
                        detail = payload.get("error_message") or payload.get("status", "No result")
                        return self.json_response(502, {"error": "Google geocoding failed", "detail": detail})
                    result = payload["results"][0]
                    point = result["geometry"]["location"]
                    return self.json_response(200, {
                        "lat": str(point["lat"]), "lon": str(point["lng"]),
                        "label": result["formatted_address"], "provider": "google",
                    })
                if not payload:
                    return self.json_response(404, {"error": "Location not found"})
                hit = payload[0]
                return self.json_response(200, {
                    "lat": hit["lat"], "lon": hit["lon"], "label": hit["display_name"],
                    "provider": "nominatim",
                })
            except Exception as error:
                return self.json_response(502, {"error": "Geocoding failed", "detail": str(error)})
        if parsed.path.startswith("/api/jobs/"):
            suffix = parsed.path.removeprefix("/api/jobs/")
            if not suffix.replace("/", "").replace("-", "").isalnum():
                return self.json_response(400, {"error": "Invalid job id"})
            return self.proxy("GET", f"/api/v1/jobs/{suffix}")
        if parsed.path == "/api/jobs":
            return self.proxy("GET", "/api/v1/jobs")
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/jobs":
            return self.json_response(404, {"error": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            incoming = json.loads(self.rfile.read(length) or b"{}")
            keyword = str(incoming.get("keyword", "")).strip()
            lat = str(incoming.get("lat", "")).strip()
            lon = str(incoming.get("lon", "")).strip()
            depth = max(1, min(int(incoming.get("depth", 5)), 20))
            if not keyword or not lat or not lon:
                raise ValueError("keyword, lat and lon are required")
            latitude = float(lat); longitude = float(lon)
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError("coordinates are outside the valid range")
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return self.json_response(400, {"error": str(error)})
        payload = {
            "name": "maps-lead-finder", "keywords": [keyword], "lang": "en",
            "zoom": 15, "lat": lat, "lon": lon, "radius": 10000,
            "depth": depth, "email": bool(incoming.get("email", False)),
            "fast_mode": False, "max_time": 600,
        }
        return self.proxy("POST", "/api/v1/jobs", payload)


if __name__ == "__main__":
    print(f"Maps Lead Finder: http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
