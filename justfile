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
    if ! docker ps | grep -q "alignfacehttp"; then
        if ! docker images | grep -q "alignfacehttp"; then
            echo "Building alignment service..."
            cd alignfacehttp && docker build -t alignfacehttp --force-rm .
        fi
        echo "Starting alignment service..."
        docker run -p 15000:5000 -d --name alignfacehttp --rm alignfacehttp
        sleep 2
    fi

# Stop alignment service  
stop-align:
    -docker stop alignfacehttp

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

