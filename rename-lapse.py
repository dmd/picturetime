#!/Users/dmd/Library/CloudStorage/Dropbox-Personal/dashare/timelapse/classify/bin/python

import sys
import os
import anthropic
from anthropic import Anthropic
from base64 import b64encode
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
from concurrent.futures import ThreadPoolExecutor, as_completed


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


def classify_image(image_path):
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    base64_image, thumbnail = resize_image(image_path)
    if base64_image is None:
        return image_path, "Unable to process image", None

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
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
        print(f"Error calling Anthropic API: {e}")
        return image_path, "Error in classification process", None


def process_images():
    image_paths = glob.glob("I*.jpeg")
    if not image_paths:
        print("No images matching I* found.")
        return
    results = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_image = {
            executor.submit(classify_image, image_path): image_path
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

        if classification not in ["dada", "mama", "capy", "platy"]:
            print(f"Error classifying image {image_path}. Skipping...")
            continue

        if thumbnail:
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                thumbnail.save(tmp.name, format="PNG")
                sixel.converter.SixelConverter(tmp.name).write(sys.stdout)

        print(f"{classification}? (y/n) ", end="", flush=True)

        user_input = get_key()
        print(user_input)

        if user_input == "y":
            new_filename = (
                f"originals/{classification}/{classification}-{date_taken}.jpg"
            )
            os.rename(image_path, new_filename)
            print(f"Renamed to {new_filename}")
        else:
            print("Skipped.")


if __name__ == "__main__":
    process_images()
