import subprocess
import json

# ---- Paths (hardcoded for this first test step) ----
EXE_PATH = r"C:\Users\DELL\locate-anything.cpp\build\examples\cli\Release\locate-anything-cli.exe"
MODEL_PATH = r"C:\Users\DELL\locate-anything.cpp\models\locate-anything-q4_k.gguf"
IMAGE_PATH = r"C:\Users\DELL\locate-anything.cpp\test.jpg"
PROMPT = "person"

# ---- Build the command as a list of arguments ----
# This is equivalent to typing the command in PowerShell, but Python
# needs it as a list of separate pieces instead of one string.
command = [
    EXE_PATH,
    "detect",
    "--model", MODEL_PATH,
    "--input", IMAGE_PATH,
    "--prompt", PROMPT,
    "--threads", "4",
]

print("Running command:")
print(" ".join(command))
print("-" * 50)

# ---- Run it and capture the output ----
result = subprocess.run(
    command,
    capture_output=True,  # capture stdout and stderr instead of printing directly
    text=True,             # decode output as text (not raw bytes)
)

print("Exit code:", result.returncode)
print("---- STDOUT ----")
print(result.stdout)
print("---- STDERR ----")
print(result.stderr)

# ---- Try to parse the JSON from stdout ----
if result.returncode == 0:
    try:
        data = json.loads(result.stdout.strip().splitlines()[0])
        print("---- Parsed JSON ----")
        print(data)
    except (json.JSONDecodeError, IndexError) as e:
        print("Could not parse JSON:", e)
