import time
import requests
import json
import io
import base64
from PIL import Image

# Configuration
PRINTFUL_API_KEY = 'YOUR_PRINTFUL_API_KEY'
PRODUCT_ID = 257  # All-Over Print Men's Crew Neck T-Shirt
VARIANT_ID = 8852  # Size L, for example

# Example cropping parameters (update according to your actual template)
FRONT_AREA = (1500, 1000, 4500, 4000)  # (left, top, right, bottom)
SLEEVE_WIDTH = 1500  # Width of sleeves (adjust based on template)

def crop_and_prepare_images(source_path):
    image = Image.open(source_path)
    width, height = image.size

    print(f"Image size: {width}x{height}")

    # Front crop
    front = image.crop(FRONT_AREA)

    # Back: mirrored front
    back = front.transpose(Image.FLIP_LEFT_RIGHT)

    # Left Sleeve: far left slice
    left_sleeve = image.crop((0, 0, SLEEVE_WIDTH, height))

    # Right Sleeve: far right slice
    right_sleeve = image.crop((width - SLEEVE_WIDTH, 0, width, height))

    return {
        'front': front,
        'back': back,
        'left_sleeve': left_sleeve,
        'right_sleeve': right_sleeve
    }

def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def upload_to_printful(images):
    url = 'https://api.printful.com/mockup-generator/create-task'
    headers = {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}",
        "Content-Type": "application/json"
    }

    files_payload = []
    for placement, img in images.items():
        files_payload.append({
            "placement": placement,
            "image": f"data:image/png;base64,{encode_image(img)}"
        })

    payload = {
        "variant_ids": [VARIANT_ID],
        "format": "jpg",
        "product_id": PRODUCT_ID,
        "files": files_payload
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()

    task_key = response.json()['result']['task_key']
    print(f"✅ Upload successful. Task key: {task_key}")
    return task_key

def poll_mockup_status(task_key, timeout=120):
    url = f'https://api.printful.com/mockup-generator/task?task_key={task_key}'
    headers = {
        "Authorization": f"Bearer {PRINTFUL_API_KEY}"
    }

    print("⏳ Polling for mockup completion...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        status = data['result']['status']
        if status == 'completed':
            mockups = data['result']['mockups']
            print("✅ Mockup generation completed.")
            return [m['mockup_url'] for m in mockups]
        elif status == 'failed':
            raise Exception("❌ Mockup generation failed.")
        else:
            print(f"⌛ Status: {status}. Retrying in 5s...")
            time.sleep(5)

    raise TimeoutError("❌ Mockup generation timed out.")

def generate_mockup(source_image_path):
    print("🚀 Starting mockup generation...")
    images = crop_and_prepare_images(source_image_path)
    task_key = upload_to_printful(images)
    mockup_urls = poll_mockup_status(task_key)
    return mockup_urls

# Example usage
if __name__ == "__main__":
    source_image = "test_1.png"  # Change this to test_2.png or test_3.png accordingly
    try:
        urls = generate_mockup(source_image)
        print("\n🎉 Final Mockup URLs:")
        for url in urls:
            print(url)
    except Exception as e:
        print(str(e))
