FROM python:3.12-alpine
WORKDIR /app
COPY app.py ./
COPY web ./web
ENV PORT=3000 SCRAPER_BASE_URL=http://google-maps-scraper:8080
EXPOSE 3000
CMD ["python3", "app.py"]
