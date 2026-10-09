"""Local PostgreSQL for development without Docker.

Docker isn't installed on this machine (see TODO.md — same limitation documented for M1), so
this uses the `pgserver` package's bundled real PostgreSQL binaries to run a genuine, persistent
instance on 127.0.0.1:5432 — the same host/port `docker-compose.yml` would expose, matching the
default `DATABASE_URL` in `core/config/settings.py`. This is a dev-only bootstrap, not a
production deployment path.

Usage: `python -m scripts.dev_postgres {start|stop|status}`
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pgserver

REPO_ROOT = Path(__file__).resolve().parent.parent
PGDATA = REPO_ROOT / ".devdb" / "pgdata"
PGLOG = REPO_ROOT / ".devdb" / "pg.log"
BIN_DIR = Path(pgserver.__file__).resolve().parent / "pginstall" / "bin"
HOST = "127.0.0.1"
PORT = 5432
SUPERUSER = "postgres"
SUPERUSER_PASSWORD = "postgres"  # noqa: S105 — local-only dev database, never exposed
DBNAME = "ai_business_os"


def _bin(name: str) -> str:
    return str(BIN_DIR / f"{name}.exe")


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a short-lived helper binary (initdb/psql/createdb/pg_isready) and capture output.

    Never use this for `pg_ctl start`: on Windows the long-running `postgres.exe` it spawns
    inherits the captured pipes, so `communicate()` blocks forever waiting for EOF that never
    comes. See `_start_server` for that case.
    """
    return subprocess.run(  # noqa: S603 — fixed argv against our own bundled binaries, no shell
        [_bin(args[0]), *args[1:]], capture_output=True, text=True, check=check
    )


def is_running() -> bool:
    result = _run("pg_isready", "-h", HOST, "-p", str(PORT), check=False)
    return result.returncode == 0


def _start_server() -> None:
    with open(os.devnull, "wb") as devnull:
        subprocess.run(  # noqa: S603 — fixed argv against our own bundled binaries, no shell
            [
                _bin("pg_ctl"),
                "-D",
                str(PGDATA),
                "-l",
                str(PGLOG),
                "-o",
                f"-p {PORT} -h {HOST}",
                "start",
            ],
            stdout=devnull,
            stderr=devnull,
            check=True,
        )


def start() -> None:
    if is_running():
        print(f"postgres already running on {HOST}:{PORT}")
        return

    if not (PGDATA / "PG_VERSION").exists():
        PGDATA.parent.mkdir(parents=True, exist_ok=True)
        pwfile = PGDATA.parent / "pwfile"
        pwfile.write_text(SUPERUSER_PASSWORD)
        _run(
            "initdb",
            "-D",
            str(PGDATA),
            "-U",
            SUPERUSER,
            f"--pwfile={pwfile}",
            "-A",
            "md5",
            "-E",
            "UTF8",
        )
        pwfile.unlink()

    _start_server()
    for _ in range(30):
        if is_running():
            break
        time.sleep(0.5)
    else:
        raise RuntimeError(f"postgres did not become ready — check {PGLOG}")

    print(f"postgres ready on {HOST}:{PORT}")
    _ensure_database()


def _ensure_database() -> None:
    env = {**os.environ, "PGPASSWORD": SUPERUSER_PASSWORD}
    check = subprocess.run(  # noqa: S603 — fixed argv against our own bundled binaries, no shell
        [_bin("psql"), "-h", HOST, "-p", str(PORT), "-U", SUPERUSER, "-lqt"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    if DBNAME in check.stdout:
        return
    subprocess.run(  # noqa: S603 — fixed argv against our own bundled binaries, no shell
        [_bin("createdb"), "-h", HOST, "-p", str(PORT), "-U", SUPERUSER, DBNAME],
        env=env,
        check=True,
    )
    print(f"created database {DBNAME!r}")


def stop() -> None:
    if not is_running():
        print("postgres is not running")
        return
    _run("pg_ctl", "-D", str(PGDATA), "stop", "-m", "fast")
    print("postgres stopped")


def status() -> None:
    print(f"running: {is_running()}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"start": start, "stop": stop, "status": status}[command]()
