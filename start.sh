docker build -t duckly-app .
docker rm -f duckly-container
docker run -d \
  --name duckly-container \
  -p 1800:1800 \
  -v /home/amir/Duckly/instance:/app/instance \
  duckly-app