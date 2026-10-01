# Atlas — Google Maps lead finder

Atlas is a local web interface for the MIT-licensed [`gosom/google-maps-scraper`](https://github.com/gosom/google-maps-scraper). It geocodes a place, starts a conservative search job, shows the results, and exports the original CSV.

## Run

```bash
docker compose up --build -d
curl http://127.0.0.1:3000/api/health
```

Open `http://127.0.0.1:3000`. Stop it with `docker compose down`.

`GOOGLE_MAPS_API_KEY` is optional. When present with the **Geocoding API** enabled, it resolves typed locations server-side and is never sent to the browser. Without a key, Atlas tries OpenStreetMap Nominatim. If public geocoding is blocked or offline, users can choose **Use my location** (browser geolocation) or enter latitude/longitude manually; those paths require no geocoding API or key.

Business results use a scraper rather than Google's official Places API and can be rate-limited. Start with depth 3–5, avoid repeated bulk jobs, follow Google's terms and applicable privacy/marketing laws, and verify results before using them.

## Architecture

- `app.py`: dependency-free Python web server, API gateway, input validation, and Nominatim geocoding.
- `web/`: responsive frontend.
- `google-maps-scraper`: server-side scraper container; it is not directly exposed to the host.

The app itself is bound to `127.0.0.1` by default. Add authentication before exposing it publicly.

## Credits

Inspired by the MIT-licensed [Google Maps Scraper Kit](https://github.com/Mahanaicoach/google-maps-scraper-kit). The underlying scraper is by Georgios Komninos and is also MIT-licensed.
