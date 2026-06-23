# Timelapse project automation

# Show available commands
default:
    @just --list

# Classify and rename new photos using AI
classify *args:
    ./rename-lapse.py {{args}}

# Start alignment service
start-align:
    #!/usr/bin/env bash
    if ! command -v docker >/dev/null 2>&1; then
        echo "Error: Docker CLI not found. Please install Docker and try again." >&2
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker daemon is not running. Start Docker and retry." >&2
        exit 1
    fi

    if ! docker ps --filter "name=^alignfacehttp$" --filter "status=running" --quiet | grep -q .; then
        if ! docker image inspect alignfacehttp >/dev/null 2>&1; then
            # Prefer the frozen, fully-local image; only build as a last resort.
            if [ -f alignfacehttp/alignfacehttp-image.tar.gz ]; then
                echo "Loading frozen alignment image (offline)..."
                gunzip -c alignfacehttp/alignfacehttp-image.tar.gz | docker load
            else
                echo "Frozen image not found; building from scratch (needs network)..."
                cd alignfacehttp && docker build -t alignfacehttp --force-rm .
            fi
        fi
        echo "Starting alignment service..."
        docker run -p 15000:5000 -d --name alignfacehttp --rm alignfacehttp
        sleep 2
    fi

# Stop alignment service
stop-align:
    -docker stop alignfacehttp

# Re-freeze the alignment image to its local tarball (run after rebuilding it)
freeze-align:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! docker image inspect alignfacehttp >/dev/null 2>&1; then
        echo "Error: no 'alignfacehttp' image to freeze. Build it first (just align)." >&2
        exit 1
    fi
    echo "Freezing alignfacehttp image to tarball..."
    docker save alignfacehttp:latest | gzip > alignfacehttp/alignfacehttp-image.tar.gz
    ls -lh alignfacehttp/alignfacehttp-image.tar.gz

# Align faces in photos (auto-manages Docker container)
align: start-align
    alignfacehttp/make-aligned
    just stop-align

# Generate web gallery
web:
    ./make-web4up

# Generate timelapse videos
videos:
    ./make-vid4up

# Generate yearly average portraits
averages:
    ./generate-averages

# Build everything (align, averages, videos, web)
build: align averages videos web
