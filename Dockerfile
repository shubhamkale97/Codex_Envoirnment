FROM python:3.12-alpine
WORKDIR /app
COPY app.py network_year.py ./
COPY web ./web
ENV YEAR_CACHE_FILE=/var/lib/leadgen/year.json
ENV PORT=3000 SCRAPER_BASE_URL=http://google-maps-scraper:8080
EXPOSE 3000
CMD ["python3", "app.py"]
