import subprocess
import json
import tempfile
import os

from PIL import Image

# ---- Fixed paths (these don't change between runs) ----
EXE_PATH = r"C:\Users\DELL\locate-anything.cpp\build\examples\cli\Release\locate-anything-cli.exe"
MODEL_PATH = r"C:\Users\DELL\locate-anything.cpp\models\locate-anything-q4_k.gguf"

# Maximum width/height (in pixels) we'll feed into the model.
# Chosen based on our own testing: 1024px worked reliably; a very-high-res
# phone photo did not (returned 0 detections, and crashed entirely in
# --mode slow due to a ~41GB memory request).
MAX_DIMENSION = 1024


def _prepare_image(image_path: str):
    """
    Opens the image and, if it's larger than MAX_DIMENSION on its longest side,
    creates a resized temporary copy for the model to use.

    Returns:
        (path_to_use, scale_x, scale_y)
        - path_to_use: the path to actually feed into the CLI (original or resized temp copy)
        - scale_x, scale_y: multipliers to convert box coordinates from the
          (possibly resized) image back to the ORIGINAL image's pixel space.
          These are 1.0 if no resizing happened.
    """
    with Image.open(image_path) as img:
        orig_width, orig_height = img.size

        if max(orig_width, orig_height) <= MAX_DIMENSION:
            # No resizing needed — use the original file directly.
            return image_path, 1.0, 1.0

        # Resize a COPY, preserving aspect ratio
        resized = img.copy()
        resized.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        resized_width, resized_height = resized.size

        # Save to a temporary file. delete=False because the CLI (a separate
        # process) needs to open it after we close it here; we clean it up manually later.
        temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        temp_path = temp_file.name
        temp_file.close()
        resized.convert("RGB").save(temp_path, format="JPEG", quality=90)

        # Scale factors to convert resized-image coordinates back to original size.
        scale_x = orig_width / resized_width
        scale_y = orig_height / resized_height

        return temp_path, scale_x, scale_y


def run_detection(image_path: str, prompt: str, threads: int = 4):
    """
    Runs the LocateAnything CLI on a given image with a given prompt.
    Automatically downscales large images before inference (for reliability
    and memory safety), then scales the returned box coordinates back up to
    match the ORIGINAL image's pixel dimensions — so callers can always draw
    boxes directly on the original, full-resolution image.

    Parameters:
        image_path: full path to the input image
        prompt: what to search for, e.g. "person", "red car", "dog"
        threads: CPU threads to use (default 4)

    Returns:
        A dict like {"detections": [{"label": "...", "box": [x1, y1, x2, y2]}, ...]}
        with box coordinates in the ORIGINAL image's pixel space.
        Raises RuntimeError if the CLI failed.
    """
    prepared_path, scale_x, scale_y = _prepare_image(image_path)
    used_temp_file = (prepared_path != image_path)

    try:
        command = [
            EXE_PATH,
            "detect",
            "--model", MODEL_PATH,
            "--input", prepared_path,
            "--prompt", prompt,
            "--threads", str(threads),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"CLI failed (exit code {result.returncode}).\n"
                f"STDERR: {result.stderr}\n"
                f"STDOUT: {result.stdout}"
            )

        stdout_clean = result.stdout.strip()
        if not stdout_clean:
            raise RuntimeError("CLI returned no output on stdout.")

        try:
            data = json.loads(stdout_clean)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Could not parse CLI output as JSON: {e}\nRaw output: {stdout_clean}")

        # Rescale every box back to the ORIGINAL image's coordinate space.
        if scale_x != 1.0 or scale_y != 1.0:
            for detection in data.get("detections", []):
                x1, y1, x2, y2 = detection["box"]
                detection["box"] = [
                    x1 * scale_x,
                    y1 * scale_y,
                    x2 * scale_x,
                    y2 * scale_y,
                ]

        return data

    finally:
        # Clean up the temp resized file, if we made one — whether things
        # succeeded or failed above.
        if used_temp_file and os.path.exists(prepared_path):
            os.remove(prepared_path)


# ---- Quick manual test when running this file directly ----
if __name__ == "__main__":
    test_image = r"C:\Users\DELL\locate-anything.cpp\test.jpg"
    test_prompt = "person"

    print(f"Testing run_detection() with prompt='{test_prompt}'...")
    data = run_detection(test_image, test_prompt)
    print("Result:", data)
