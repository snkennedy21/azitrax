"""Database migration runner using Flyway CLI.

This module provides a function to run Flyway migrations during application startup.
Flyway is executed as a subprocess, allowing the FastAPI app to control when migrations
run and handle errors appropriately.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_migrations() -> None:
    """Run Flyway database migrations.

    Executes Flyway migrate command using environment variables for database connection.
    This function should be called during FastAPI startup, before the application begins
    accepting requests.

    Raises:
        RuntimeError: If Flyway execution fails or returns non-zero exit code.
    """
    # Validate required environment variables
    required_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise RuntimeError(
            f"Missing required environment variables for migrations: {', '.join(missing_vars)}"
        )

    # Flyway command: migrate runs all pending migrations
    flyway_cmd = ["flyway", "-configFiles=/app/flyway.conf", "migrate"]

    # Log migration attempt
    print("=" * 80, file=sys.stderr)
    print("Starting database migrations with Flyway...", file=sys.stderr)
    print(
        f"Database: {os.getenv('POSTGRES_DB')} at {os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}",
        file=sys.stderr,
    )
    print("=" * 80, file=sys.stderr)

    try:
        # Run Flyway as subprocess
        result = subprocess.run(
            flyway_cmd,
            check=True,
            env=os.environ.copy(),
            cwd="/app",
            capture_output=True,
            text=True,
        )

        # Print Flyway output for debugging
        print(result.stdout, file=sys.stderr)

        print("=" * 80, file=sys.stderr)
        print("Database migrations completed successfully!", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

    except subprocess.CalledProcessError as exc:
        # Flyway failed - log error and re-raise
        print("=" * 80, file=sys.stderr)
        print("MIGRATION FAILED!", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(exc.stdout, file=sys.stderr)
        print(exc.stderr, file=sys.stderr)

        raise RuntimeError(
            f"Flyway migration failed with exit code {exc.returncode}. "
            "Check logs above for details."
        ) from exc
    except FileNotFoundError:
        raise RuntimeError(
            "Flyway command not found. Ensure Flyway is installed in the Docker image."
        )


def validate_migrations() -> None:
    """Validate that migration files exist and are readable.

    This is a pre-flight check before running Flyway. It ensures the migrations
    directory exists and contains SQL files.

    Raises:
        RuntimeError: If migrations directory is missing or empty.
    """
    migrations_dir = Path("/app/migrations")

    if not migrations_dir.exists():
        raise RuntimeError(
            f"Migrations directory not found: {migrations_dir}. "
            "Ensure migrations are copied into the Docker image."
        )

    sql_files = list(migrations_dir.glob("*.sql"))
    if not sql_files:
        raise RuntimeError(
            f"No migration files found in {migrations_dir}. "
            "Ensure migration SQL files are present."
        )

    print(f"Found {len(sql_files)} migration file(s):", file=sys.stderr)
    for sql_file in sorted(sql_files):
        print(f"  - {sql_file.name}", file=sys.stderr)
