docker build -t duckly-app .
docker rm -f duckly-container
docker run -d \
  --name duckly-container \
  -p 1800:1800 \
  # Mount the local ./instance directory to /app/instance in the container
  # $(pwd) resolves to the current working directory (Linux/macOS)
  -v $(pwd)/instance:/app/instance \
  # IMPORTANT: Change this SECRET_KEY for production environments!
  -e SECRET_KEY='your-development-secret-key-here' \
  duckly-app