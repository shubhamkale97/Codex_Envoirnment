# SYNCAXIS LEADGEN TOOL

Syncaxis Leadgen Tool is a local web interface for the MIT-licensed [`gosom/google-maps-scraper`](https://github.com/gosom/google-maps-scraper). It geocodes a place, starts a conservative search job, shows the results, and exports the original CSV. Developed by [SNIPER](https://www.linkedin.com/in/sniper97/).

## Branding and copyright year

The responsive layout uses a locally bundled Bootstrap 5.3.8. The Syncaxis logo is
served locally. `network_year.py` obtains the copyright year from TimeAPI over HTTPS,
with Cloudflare internet time as a fallback, using the Asia/Kolkata time zone.
`/api/time` refreshes that year hourly; `web/branding.js` updates open pages hourly
and when a page becomes visible. Neither the browser nor host wall clock supplies
the copyright year. If internet time is unavailable, the last verified year is
retained in the `leadgen_meta` Docker volume; a first-time offline start shows 2026.

## Run

```bash
docker compose up --build -d
curl http://127.0.0.1:3000/api/health
```

Open `http://127.0.0.1:3000`. Stop it with `docker compose down`.

### LAN access

The safe default listens only on localhost. To serve the UI from a specific LAN address, create a `.env` file next to `docker-compose.yml`:

```dotenv
HOST_BIND=192.168.3.9
```

Then recreate the web container:

```bash
docker compose up --build -d --force-recreate
```

Other devices on the same network can open `http://192.168.3.9:3000`. Allow inbound TCP port 3000 in the host firewall for the private network profile. The scraper API remains internal to Docker and is not published.

`GOOGLE_MAPS_API_KEY` is optional. When present with the **Geocoding API** enabled, it resolves typed locations server-side and is never sent to the browser. Without a key, Atlas tries OpenStreetMap Nominatim. If public geocoding is blocked or offline, users can choose **Use my location** (browser geolocation) or enter latitude/longitude manually; those paths require no geocoding API or key.

Business results use a scraper rather than Google's official Places API and can be rate-limited. Start with depth 3–5, avoid repeated bulk jobs, follow Google's terms and applicable privacy/marketing laws, and verify results before using them.

## Architecture

- `app.py`: dependency-free Python web server, API gateway, input validation, and Nominatim geocoding.
- `web/`: responsive frontend.
- `google-maps-scraper`: server-side scraper container; it is not directly exposed to the host.

The app itself is bound to `127.0.0.1` by default. `HOST_BIND` can expose it to a trusted LAN. Add authentication and TLS before exposing it to the public Internet.

## Credits

Inspired by the MIT-licensed [Google Maps Scraper Kit](https://github.com/Mahanaicoach/google-maps-scraper-kit). The underlying scraper is by Georgios Komninos and is also MIT-licensed.
