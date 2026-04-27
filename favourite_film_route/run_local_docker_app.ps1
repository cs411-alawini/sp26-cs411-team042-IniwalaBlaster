$ErrorActionPreference = "Stop"

$env:DOCKER_API_VERSION = "1.49"
$env:SCENETRIP_DB_SOCKET = "/var/run/mysqld/mysqld.sock"
$env:SCENETRIP_DB_PORT = "3306"
$env:SCENETRIP_DB_USER = "root"
$env:SCENETRIP_DB_NAME = "scenetrip"
$env:SCENETRIP_MYSQL_COMMAND = "docker exec -i scenetrip-mysql mysql"
$env:PATH = "$PSScriptRoot;$env:PATH"

python "$PSScriptRoot\app.py"
