#!/usr/bin/env -S uv run --script
#
# /// script
# dependencies = ['pillow', 'sixel', 'piexif', 'anthropic', 'openai']
# ///

import sys
import os
import argparse
from base64 import b64encode, standard_b64encode
from PIL import Image, ExifTags
import io
import glob
import piexif
from datetime import datetime
import termios
import tty
import tempfile
import sixel
import signal
import select
from concurrent.futures import ThreadPoolExecutor, as_completed


# Graphics protocol detection
GRAPHICS_PROTOCOL = None  # Will be set to 'kitty', 'sixel', or None


def detect_graphics_protocol():
    """Detect terminal graphics protocol support. Prefer kitty over sixel."""
    global GRAPHICS_PROTOCOL

    # First try kitty protocol detection
    if detect_kitty_support():
        GRAPHICS_PROTOCOL = "kitty"
        return

    # Then try sixel detection
    if detect_sixel_support():
        GRAPHICS_PROTOCOL = "sixel"
        return

    GRAPHICS_PROTOCOL = None


def detect_kitty_support():
    """Detect kitty graphics protocol support via environment variables."""
    # Check for KITTY_WINDOW_ID environment variable (set by kitty)
    if os.environ.get("KITTY_WINDOW_ID"):
        return True

    # Check TERM_PROGRAM for known kitty-protocol terminals
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program in ("ghostty", "kitty"):
        return True

    return False


def detect_sixel_support():
    """Detect sixel support using DA1 escape sequence or known terminal."""
    # Known sixel-supporting terminals
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program in ("iTerm.app", "WezTerm", "mintty"):
        return True

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Send DA1 (Primary Device Attributes) query
        sys.stdout.write("\x1b[c")
        sys.stdout.flush()

        response = ""
        while True:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                ch = sys.stdin.read(1)
                response += ch
                if ch == "c":
                    break
            else:
                break

        # Sixel support is indicated by "4" in the response parameters
        # Response format: ESC [ ? Ps ; Ps ; ... c
        # 4 indicates sixel graphics support
        return ";4;" in response or ";4c" in response or "?4;" in response
    except Exception:
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def display_image_kitty(image):
    """Display image using kitty graphics protocol."""
    # Convert to PNG in memory
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    data = standard_b64encode(buffered.getvalue()).decode("ascii")

    # Send image in chunks (kitty protocol limit is 4096 bytes per chunk)
    chunk_size = 4096
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        m = 0 if is_last else 1  # m=1 means more chunks coming
        if i == 0:
            # First chunk: include all parameters
            sys.stdout.write(f"\x1b_Gf=100,a=T,m={m};{chunk}\x1b\\")
        else:
            # Subsequent chunks: only m parameter
            sys.stdout.write(f"\x1b_Gm={m};{chunk}\x1b\\")

    sys.stdout.write("\n")
    sys.stdout.flush()


def display_image(image):
    """Display image using the detected graphics protocol."""
    if GRAPHICS_PROTOCOL == "kitty":
        display_image_kitty(image)
    elif GRAPHICS_PROTOCOL == "sixel":
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            image.save(tmp.name, format="PNG")
            sixel.converter.SixelConverter(tmp.name).write(sys.stdout)
        print()  # newline after sixel image
    else:
        print("[Image display not supported in this terminal]")

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ord(ch) == 3:
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_date_taken(image_path):
    try:
        exif_dict = piexif.load(image_path)
        date_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode("utf-8")
        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S").strftime("%Y%m%d")
    except:
        return None


def fix_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == "Orientation":
                break
        exif = dict(image._getexif().items())

        if exif[orientation] == 3:
            image = image.rotate(180, expand=True)
        elif exif[orientation] == 6:
            image = image.rotate(270, expand=True)
        elif exif[orientation] == 8:
            image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        pass
    return image


def resize_image(image_path, scale_factor=0.2):
    try:
        with Image.open(image_path) as img:
            img = fix_orientation(img)
            width, height = img.size
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)

            buffered = io.BytesIO()
            resized_img.save(buffered, format="JPEG")
            return b64encode(buffered.getvalue()).decode("utf-8"), resized_img
    except Exception as e:
        print(f"Error processing image: {e}")
        return None, None


def classify_image(image_path, use_openai=False):
    base64_image, thumbnail = resize_image(image_path)
    if base64_image is None:
        return image_path, "Unable to process image", None

    try:
        if use_openai:
            if OpenAI is None:
                raise ImportError("OpenAI library not installed")
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                            {
                                "type": "text",
                                "text": "Is this person an adult male, adult female, child with glasses, or child without glasses? Reply with only exactly one of those options or 'unable to classify'. Do not reply with any other text whatsoever.",
                            },
                        ],
                    }
                ],
            )
            classification = response.choices[0].message.content.strip().lower()
        else:
            if Anthropic is None:
                raise ImportError("Anthropic library not installed")
            client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Is this person an adult male, adult female, child with glasses, or child without glasses? Reply with only exactly one of those options or 'unable to classify'. Do not reply with any other text whatsoever.",
                            },
                        ],
                    }
                ],
            )
            classification = response.content[0].text.strip().lower()

        if classification == "adult male":
            return image_path, "dada", thumbnail
        elif classification == "adult female":
            return image_path, "mama", thumbnail
        elif classification == "child with glasses":
            return image_path, "capy", thumbnail
        elif classification == "child without glasses":
            return image_path, "platy", thumbnail
        else:
            return image_path, "Unable to classify", thumbnail
    except Exception as e:
        print(f"Error calling API: {e}")
        return image_path, "Error in classification process", None


def process_images(use_openai=False):
    image_paths = glob.glob("I*.jpeg")
    if not image_paths:
        print("No images matching I* found.")
        return
    results = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_image = {
            executor.submit(classify_image, image_path, use_openai): image_path
            for image_path in image_paths
        }
        try:
            for future in as_completed(future_to_image):
                image_path, classification, thumbnail = future.result()
                results[image_path] = (classification, thumbnail)
        except KeyboardInterrupt:
            print("Caught KeyboardInterrupt, cancelling tasks...")
            executor.shutdown(wait=False, cancel_futures=True)
            raise

    for image_path, (classification, thumbnail) in results.items():
        date_taken = get_date_taken(image_path)
        if not date_taken:
            print(f"Couldn't determine date for {image_path}. Skipping...")
            continue

        manual_label = False

        if classification not in ["dada", "mama", "capy", "platy"]:
            print(f"Error classifying image {image_path}.")
            if thumbnail:
                display_image(thumbnail)

            print("Choose: (c)apy, (m)ama, (d)ada, or (p)laty: ", end="", flush=True)
            user_choice = get_key()
            print(user_choice)

            if user_choice == "c":
                classification = "capy"
                manual_label = True
            elif user_choice == "m":
                classification = "mama"
                manual_label = True
            elif user_choice == "d":
                classification = "dada"
                manual_label = True
            elif user_choice == "p":
                classification = "platy"
                manual_label = True
            else:
                print("Invalid choice. Skipping...")
                continue

        if (
            thumbnail
            and classification in ["dada", "mama", "capy", "platy"]
            and not manual_label
        ):
            display_image(thumbnail)
        new_filename = f"originals/{classification}/{classification}-{date_taken}.jpg"

        if manual_label:
            os.rename(image_path, new_filename)
            print(f"Renamed to {new_filename}")
            continue

        print(f"{classification}? (y/n) ", end="", flush=True)

        user_input = get_key()
        print(user_input)

        if user_input == "y":
            os.rename(image_path, new_filename)
            print(f"Renamed to {new_filename}")
        else:
            print("Skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify and rename images using AI")
    parser.add_argument(
        "--openai",
        action="store_true",
        help="Use OpenAI API instead of Anthropic (default)",
    )
    args = parser.parse_args()

    detect_graphics_protocol()
    process_images(use_openai=args.openai)
