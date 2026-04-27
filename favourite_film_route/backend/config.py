import os

DB_SOCKET = os.environ.get("SCENETRIP_DB_SOCKET", "/tmp/scenetrip-mysql-run/mysql.sock")
DB_PORT = os.environ.get("SCENETRIP_DB_PORT", "3307")
DB_USER = os.environ.get("SCENETRIP_DB_USER", "root")
DB_NAME = os.environ.get("SCENETRIP_DB_NAME", "scenetrip")

HOST = os.environ.get("SCENETRIP_HOST", "127.0.0.1")
PORT = int(os.environ.get("SCENETRIP_API_PORT", "8000"))