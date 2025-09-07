import subprocess
import time
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, text


def wait_for_postgres(host: str, port: int, user: str, password: str, db: str, timeout_s: int = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            eng = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")
            with eng.connect() as conn:
                conn.execute(text("select 1"))
                return True
        except Exception:
            time.sleep(1)
    return False


@contextmanager
def postgres_container(image: str = "postgres:13"):
    """Spin up an isolated Postgres container on a random high port and tear it down."""
    container_name = f"hsai-migtest-{uuid.uuid4().hex[:8]}"
    user = "testuser"
    password = "testpass"
    dbname = "testdb"
    for port in (55432, 55433, 55434, 55435):
        try:
            proc = subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "-e", f"POSTGRES_USER={user}",
                "-e", f"POSTGRES_PASSWORD={password}",
                "-e", f"POSTGRES_DB={dbname}",
                "-p", f"{port}:5432",
                image
            ], capture_output=True, text=True)
            if proc.returncode == 0:
                host = "localhost"
                if not wait_for_postgres(host, port, user, password, dbname, timeout_s=90):
                    raise RuntimeError("Postgres container did not become ready in time")
                url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
                try:
                    yield url, container_name
                finally:
                    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
                return
        except Exception:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            continue
    raise RuntimeError("Failed to start Postgres test container on any candidate port")

