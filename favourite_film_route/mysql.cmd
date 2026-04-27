@echo off
set DOCKER_API_VERSION=1.49
docker exec -i scenetrip-mysql mysql %*
