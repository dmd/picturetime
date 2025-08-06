# Picture Time!

This project creates timelapse videos and a web gallery from the photos
we take every week.

The web gallery result is at [3e.org/timelapse](https://3e.org/timelapse/).

## Overview

The timelapse project processes photos through multiple stages:

1. **Classification**: Uses Claude to auto-classify photos by person
2. **Face Alignment**: Aligns faces in photos using dlib facial landmarks
3. **Animation**: Creates timelapse videos and interactive web galleries
4. **Averaging**: Generates yearly average portraits

## Project Structure

```
.
├── justfile                  # Main automation commands (Just task runner)
├── rename-lapse.py           # AI-powered photo classification script
├── generate-averages         # Script to create yearly average portraits
├── make-web4up               # Script to generate web gallery
├── make-vid4up               # Script to create 4-up timelapse video
├── alignfacehttp/            # Face alignment service
│   ├── httpsrv.py            # HTTP server for face alignment
│   ├── make-aligned          # Script to align all photos
│   ├── Dockerfile            # Docker container for alignment service
│   └── requirements.txt      # Python dependencies for alignment
├── originals/                # Original photos organized by person
│   ├── capy/                 # Child with glasses
│   ├── platy/                # Child without glasses
│   ├── mama/                 # Adult female
│   └── dada/                 # Adult male
├── aligned/                  # Face-aligned photos
├── animated/                 # Generated timelapse videos
├── web4up/                   # Web gallery assets
└── mosaics/                  # (Directory for mosaic outputs)
```

## Dependencies

### System Requirements
- **Python 3.8+** with `uv` package manager
- **Docker** for face alignment service
- **ImageMagick** for image processing (`magick` command)
- **FFmpeg** for video processing
- **Just** task runner

### Python Dependencies (automatically managed by uv)
- `pillow` - Image processing
- `sixel` - Terminal image display
- `piexif` - EXIF data handling
- `anthropic` - Anthropic API client


### Face Alignment Service Dependencies
- `opencv-python` - Computer vision library
- `dlib` - Facial landmark detection
- `flask` - Web server framework
- `waitress` - WSGI server

## Setup

1. **Install system dependencies**:
   ```bash
   # macOS with Homebrew
   brew install imagemagick ffmpeg docker just uv
   
   # Ubuntu/Debian
   sudo apt-get install imagemagick ffmpeg docker.io
   pip install uv
   ```

2. **Set up API keys**:
   ```bash
   export ANTHROPIC_API_KEY="your_anthropic_key"
   ```

3. **Download face alignment model**:
   The project uses dlib's 5-point facial landmark predictor. The model file `shape_predictor_5_face_landmarks.dat.bz2` should be placed in the `alignfacehttp/` directory.

## Usage

### Quick Start with Just

The `justfile` provides convenient commands for the entire workflow:

```bash
# Show all available commands
just

# Classify new photos (place I*.jpeg files in root directory)
just classify

# Align faces in photos
just align

# Generate yearly averages
just averages

# Create timelapse videos
just videos

# Generate web gallery
just web

# Build everything (align, averages, videos, web)
just build

```

All you really need is `just build`.

### Manual Workflow

#### 1. Photo Classification

Place new photos (named `I*.jpeg`) in the root directory, then:

```bash
just classify
```

The script will:
- Display each photo in the terminal (using sixel)
- Use AI to classify the person as "adult male" (dada), "adult female" (mama), "child with glasses" (capy), or "child without glasses" (platy)
  - This will have to be changed when/if platy gets glasses!

- Ask for confirmation before moving photos to the appropriate `originals/` subdirectory
- Extract date from EXIF data for filename formatting

#### 2. Face Alignment

```bash
just align
```

The alignment process:
- Uses dlib to detect facial landmarks
- Applies affine transformation to standardize eye distance and orientation
- Outputs aligned photos to `aligned/` directory
- Creates timelapse videos for each person

#### 3. Generate Yearly Averages

```bash
just averages
```

This creates average portraits for each person by year using ImageMagick's mean evaluation.

#### 4. Create Web Gallery

```bash
just web
```

This script:
- Resizes aligned photos to 300x400 pixels
- Creates `web4up/filenames.txt` index
- Uploads to web server (currently configured for `3e.org`)

#### 5. Generate 4-Up Video

```bash
just videos
```

Creates a synchronized 4-panel video combining all individual timelapses.

## Scripts Reference

These are all run via just as described above - no need to run them manually.

### `rename-lapse.py`
**Purpose**: AI-powered photo classification and organization

**Features**:
- Displays photos in terminal using sixel protocol
- Extracts EXIF date information
- Interactive confirmation for each classification
- Handles image orientation correction
- Parallel processing for faster classification

**Usage**: `just classify`

### `alignfacehttp/httpsrv.py`
**Purpose**: HTTP service for face alignment using dlib

**API Endpoints**:
- `GET /status` - Service health check
- `POST /align` - Align face in uploaded image

**Parameters**:
- `file` - Image file to process
- `distance` - Target eye distance (default: 120)
- `width` - Output width (default: 480)  
- `height` - Output height (default: 640)
- `shift` - Vertical shift factor (default: 0.1)

### `alignfacehttp/make-aligned`
**Purpose**: Batch process all original photos through alignment service

**Process**:
1. Verifies alignment service is running
2. Processes all `.jpg` files in `originals/` subdirectories
3. Skips already processed files
4. Creates individual timelapse videos using FFmpeg

### `generate-averages`
**Purpose**: Create yearly average portraits using ImageMagick

**Process**:
- Groups photos by subject and year
- Uses ImageMagick's `-evaluate-sequence mean` operation
- Resizes outputs to 300x400 pixels
- Saves to `web4up/averages/`

### `make-web4up`
**Purpose**: Generate web gallery with resized images

**Process**:
- Resizes aligned photos to web-friendly dimensions
- Creates index file for JavaScript gallery
- Deploys to web server via rsync

### `make-vid4up`
**Purpose**: Create synchronized 4-panel timelapse video

**Process**:
- Analyzes duration of individual videos

- Adds padding to synchronize timing

- Uses FFmpeg filter_complex for grid layout

- Outputs combined video as `animated/4up.mp4`

  

## File Naming Convention

Photos are named using the format: `{subject}-{YYYYMMDD}.jpg`

Where:
- `subject` is one of: `capy`, `platy`, `mama`, `dada`
- Date is extracted from EXIF data in YYYYMMDD format

