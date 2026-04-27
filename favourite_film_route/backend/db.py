import subprocess

from config import DB_SOCKET, DB_PORT, DB_USER, DB_NAME


def mysql_query(sql: str) -> list[list[str]]:
    proc = subprocess.run(
        [
            "mysql",
            "-u",
            DB_USER,
            "--socket",
            DB_SOCKET,
            "--port",
            DB_PORT,
            "-D",
            DB_NAME,
            "--batch",
            "--raw",
            "--skip-column-names",
            "-e",
            sql,
        ],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Unknown MySQL error")

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return [line.split("\t") for line in lines]


def sql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "''")