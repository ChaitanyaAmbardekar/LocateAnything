from PIL import Image, ImageDraw
from locate_engine import run_detection

# ---- Config for this test ----
IMAGE_PATH = r"C:\Users\DELL\locate-anything.cpp\test.jpg"
PROMPT = "person"
OUTPUT_PATH = r"C:\Users\DELL\locate-anything.cpp\python-app\output_python.png"

# ---- Step 1: Run detection using our engine function ----
print(f"Running detection for prompt='{PROMPT}'...")
data = run_detection(IMAGE_PATH, PROMPT)
print("Detections:", data)

# ---- Step 2: Open the original image ----
image = Image.open(IMAGE_PATH).convert("RGB")
draw = ImageDraw.Draw(image)

# ---- Step 3: Draw a rectangle for each detection ----
# Box format confirmed earlier: [x1, y1, x2, y2] in pixel coordinates
for detection in data["detections"]:
    label = detection["label"]
    x1, y1, x2, y2 = detection["box"]

    # Draw the rectangle outline (red, 3px thick)
    draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

    # Draw the label text just above the top-left corner of the box
    draw.text((x1, max(0, y1 - 12)), label, fill="red")

# ---- Step 4: Save the result ----
image.save(OUTPUT_PATH)
print(f"Saved annotated image to: {OUTPUT_PATH}")
