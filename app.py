import base64
import requests
from PIL import Image, ImageDraw
from io import BytesIO
import os
import time

# === CONFIGURATION ===
PRINTFUL_API_KEY = 'your_api_key_here'
SOURCE_IMAGE_PATH = 'test.png'
OUTPUT_PREVIEW_PATH = 'alignment_preview.png'
PRODUCT_ID = 257
VARIANT_ID = 8852

# === TEMPLATE SIZE ===
TEMPLATE_WIDTH = 4800
TEMPLATE_HEIGHT = 5100

# === CROP AREAS FROM OFFICIAL TEMPLATE ===
FRONT_AREA = (600, 900, 2400, 4200)
BACK_AREA = (2400, 900, 4200, 4200)
LEFT_SLEEVE_AREA = (0, 900, 600, 3300)
RIGHT_SLEEVE_AREA = (4200, 900, 4800, 3300)

BOX_COLORS = {
    "front": "green",
    "back": "blue",
    "left_sleeve": "red",
    "right_sleeve": "orange"
}

# === STEP 1: Visual Overlay ===
def draw_alignment_overlay():
    img = Image.open(SOURCE_IMAGE_PATH).convert("RGBA")
    if img.size != (TEMPLATE_WIDTH, TEMPLATE_HEIGHT):
        raise ValueError(f"❌ Image must be {TEMPLATE_WIDTH}x{TEMPLATE_HEIGHT}px.")

    draw = ImageDraw.Draw(img, "RGBA")

    def draw_box(area, label, color):
        draw.rectangle(area, outline=color, width=6)
        draw.text((area[0] + 10, area[1] + 10), label, fill=color)

    draw_box(FRONT_AREA, "FRONT", BOX_COLORS["front"])
    draw_box(BACK_AREA, "BACK", BOX_COLORS["back"])
    draw_box(LEFT_SLEEVE_AREA, "LEFT SLEEVE", BOX_COLORS["left_sleeve"])
    draw_box(RIGHT_SLEEVE_AREA, "RIGHT SLEEVE", BOX_COLORS["right_sleeve"])

    img.save(OUTPUT_PREVIEW_PATH)
    print(f"📐 Alignment preview saved as '{OUTPUT_PREVIEW_PATH}'")

# === STEP 2: Prepare Cropped & Encoded Images ===
def crop_image(image, box):
    return image.crop(box)

def encode_image_base64(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{encoded}'

def prepare_images(path):
    image = Image.open(path)
    if image.size != (TEMPLATE_WIDTH, TEMPLATE_HEIGHT):
        raise ValueError(f"❌ Source image must be exactly {TEMPLATE_WIDTH}x{TEMPLATE_HEIGHT}px.")

    print(f"✅ Loaded source image: {image.size}")

    front = crop_image(image, FRONT_AREA)
    back = crop_image(image, BACK_AREA)
    left_sleeve = crop_image(image, LEFT_SLEEVE_AREA)
    right_sleeve = crop_image(image, RIGHT_SLEEVE_AREA)

    return {
        "front": encode_image_base64(front),
        "back": encode_image_base64(back),
        "left_sleeve": encode_image_base64(left_sleeve),
        "right_sleeve": encode_image_base64(right_sleeve)
    }

# === STEP 3: Submit to Printful API ===
def create_mockup(images):
    url = 'https://api.printful.com/mockup-generator/create-task'
    headers = {
        'Authorization': f'Bearer {PRINTFUL_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        "product_id": PRODUCT_ID,
        "variant_ids": [VARIANT_ID],
        "format": "jpg",
        "files": [
            {"placement": "front", "image": images["front"]},
            {"placement": "back", "image": images["back"]},
            {"placement": "left_sleeve", "image": images["left_sleeve"]},
            {"placement": "right_sleeve", "image": images["right_sleeve"]}
        ]
    }

    print("🚀 Submitting mockup generation request to Printful...")
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print("❌ API Error:", response.status_code, response.text)
        response.raise_for_status()

    task_key = response.json()["result"]["task_key"]
    return task_key

# === STEP 4: Poll Until Complete ===
def poll_mockup(task_key):
    url = f'https://api.printful.com/mockup-generator/task?task_key={task_key}'
    headers = {'Authorization': f'Bearer {PRINTFUL_API_KEY}'}

    print("⏳ Waiting for Printful to finish mockup...")
    for _ in range(15):
        time.sleep(5)
        response = requests.get(url, headers=headers)
        result = response.json().get("result", {})
        status = result.get("status")

        if status == "completed":
            print("✅ Mockup generation complete.")
            return result["mockups"][0]["mockup_url"]

        elif status == "failed":
            raise RuntimeError("❌ Mockup generation failed.")

    raise TimeoutError("⏰ Timed out waiting for Printful to complete.")

# === MAIN ===
def main():
    draw_alignment_overlay()  # Optional but useful
    images = prepare_images(SOURCE_IMAGE_PATH)
    task_key = create_mockup(images)
    mockup_url = poll_mockup(task_key)
    print("🖼️ Final Mockup URL:", mockup_url)

if __name__ == "__main__":
    main()
