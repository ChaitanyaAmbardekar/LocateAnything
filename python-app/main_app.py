import sys
import io
import os
import time
import traceback

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QDialog
)
from PySide6.QtGui import QPixmap, QImage, QFont
from PySide6.QtCore import Qt

from PIL import Image, ImageDraw
from locate_engine import run_detection

# File extensions we'll treat as images when scanning a folder.
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

# Example use cases shown on the welcome screen — purely informational,
# doesn't affect app behavior. Edit this list freely.
USE_CASES = [
    "Find lost items — scan room photos for 'keys', 'wallet', 'remote'",
    "Home security — scan camera snapshots for 'person' or 'vehicle'",
    "Retail shelf audit — batch-scan shelf photos for a product name",
    "Safety compliance — scan site photos for 'helmet' to spot missing gear",
    "Event photo sorting — group photos by 'cake', 'banner', etc.",
    "Parking/crowd counting — batch-scan for 'car' or 'person' counts",
    "Accessibility mapping — locate 'staircase', 'ramp', or 'door' in photos",
]

# ---- Dark theme stylesheet (Qt Style Sheets — similar syntax to CSS) ----
DARK_STYLESHEET = """
QWidget {
    background-color: #1e1e2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QPushButton {
    background-color: #313244;
    color: #e0e0e0;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 12px;
}
QPushButton:hover {
    background-color: #45475a;
    border: 1px solid #89b4fa;
}
QPushButton:pressed {
    background-color: #585b70;
}
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
    color: #e0e0e0;
}
QLineEdit:focus {
    border: 1px solid #89b4fa;
}
QLabel#ImageArea {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 8px;
}
"""


def pil_image_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    """Converts a Pillow Image into a Qt QPixmap so it can be displayed in the GUI."""
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    qimage = QImage.fromData(buffer.getvalue())
    return QPixmap.fromImage(qimage)


def draw_detections_on_image(image_path: str, detections: list) -> Image.Image:
    """
    Opens the image at image_path and draws a red box + label for each
    detection. Returns a new Pillow Image (the original file on disk is
    never modified). Shared by both single-image and batch/folder modes,
    so the drawing style only needs to be defined in one place.
    """
    pil_image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(pil_image)
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        draw.rectangle([x1, y1, x2, y2], outline="red", width=6)
        draw.text((x1, max(0, y1 - 12)), det["label"], fill="red")
    return pil_image


class WelcomeDialog(QDialog):
    """
    A one-time popup shown when the app starts, introducing what the tool
    does and listing example use cases. Purely informational — closing it
    (via the 'Get Started' button) just continues on to the main window.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome to LocateAnything")
        self.resize(480, 420)

        title = QLabel("LocateAnything")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel("Tell it what to find in a photo — it finds it.")
        subtitle.setStyleSheet("color: #a6adc8;")

        instructions = QLabel(
            "Type anything you're looking for — a person, an object, "
            "a piece of clothing, almost any word or short phrase — and "
            "this tool will locate it in your image(s) and draw a box "
            "around it. Works on a single photo or a whole folder at once."
        )
        instructions.setWordWrap(True)

        use_case_title = QLabel("Example use cases:")
        use_case_title.setStyleSheet("font-weight: bold; margin-top: 8px;")

        use_case_text = "\n".join(f"•  {case}" for case in USE_CASES)
        use_case_label = QLabel(use_case_text)
        use_case_label.setWordWrap(True)

        start_button = QPushButton("Get Started")
        start_button.clicked.connect(self.accept)  # closes the dialog

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(instructions)
        layout.addSpacing(10)
        layout.addWidget(use_case_title)
        layout.addWidget(use_case_label)
        layout.addStretch()
        layout.addWidget(start_button)

        self.setLayout(layout)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LocateAnything")
        self.resize(900, 600)

        self.image_path = None    # will hold the chosen single image's file path
        self.folder_path = None   # will hold the chosen folder's path (batch mode)

        # ---- Left side: controls ----
        self.choose_button = QPushButton("Choose Image...")
        self.choose_button.clicked.connect(self.on_choose_image)

        self.choose_folder_button = QPushButton("Choose Folder...")
        self.choose_folder_button.clicked.connect(self.on_choose_folder)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("What should I look for? e.g. 'person'")

        self.run_button = QPushButton("Run Detection")
        self.run_button.clicked.connect(self.on_run_detection)

        self.run_batch_button = QPushButton("Run Batch Detection")
        self.run_batch_button.clicked.connect(self.on_run_batch_detection)

        self.status_label = QLabel("No image or folder selected.")
        self.status_label.setWordWrap(True)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.choose_button)
        left_layout.addWidget(self.choose_folder_button)
        left_layout.addWidget(self.prompt_input)
        left_layout.addWidget(self.run_button)
        left_layout.addWidget(self.run_batch_button)
        left_layout.addWidget(self.status_label)
        left_layout.addStretch()  # pushes everything above to the top

        # ---- Right side: image display ----
        self.image_label = QLabel("Image will appear here")
        self.image_label.setObjectName("ImageArea")  # lets the stylesheet target it specifically
        self.image_label.setAlignment(Qt.AlignCenter)

        # ---- Combine into side-by-side layout ----
        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addWidget(self.image_label, stretch=3)

        self.setLayout(main_layout)

    def on_choose_image(self):
        """Opens a file picker dialog for the user to select an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Choose an image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.image_path = file_path
            self.status_label.setText(f"Selected: {file_path}")
            # Show the original image immediately, before running detection
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(
                pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def on_choose_folder(self):
        """Opens a folder picker dialog for batch/multi-image detection."""
        folder_path = QFileDialog.getExistingDirectory(self, "Choose a folder of images")
        if folder_path:
            self.folder_path = folder_path
            # Count how many image files are inside, just to inform the user up front.
            image_files = [
                f for f in os.listdir(folder_path)
                if f.lower().endswith(IMAGE_EXTENSIONS)
            ]
            self.status_label.setText(
                f"Selected folder: {folder_path}\n({len(image_files)} image(s) found)"
            )

    def on_run_batch_detection(self):
        """Runs detection on every image in the chosen folder, one at a time.
        Shows live progress in the window and saves annotated copies to a
        new subfolder called 'detections_output' inside the chosen folder."""
        if not self.folder_path:
            QMessageBox.warning(self, "No folder", "Please choose a folder first.")
            return

        prompt = self.prompt_input.text().strip()
        if not prompt:
            QMessageBox.warning(self, "No prompt", "Please type something to search for.")
            return

        image_files = sorted(
            f for f in os.listdir(self.folder_path)
            if f.lower().endswith(IMAGE_EXTENSIONS)
        )
        if not image_files:
            QMessageBox.warning(self, "No images", "No image files found in that folder.")
            return

        # Create (or reuse) an output subfolder for the annotated results.
        output_folder = os.path.join(self.folder_path, "detections_output")
        os.makedirs(output_folder, exist_ok=True)

        total = len(image_files)
        found_count = 0        # number of IMAGES that had at least one match
        total_detections = 0   # total individual matches across all images

        # Batch mode hammers the CPU with back-to-back heavy computation and
        # no breaks. On some systems this can starve Windows' own background
        # tasks of CPU time (we saw this cause a real crash: bugcheck 0x19C,
        # WIN32K_POWER_WATCHDOG_TIMEOUT). To avoid that, we (1) use fewer
        # threads per detection than single-image mode, leaving the system
        # some headroom, and (2) pause briefly between images.
        BATCH_THREADS = 2
        COOLDOWN_SECONDS = 1.5

        for index, filename in enumerate(image_files, start=1):
            image_path = os.path.join(self.folder_path, filename)

            self.status_label.setText(f"Processing {index}/{total}: {filename}")
            QApplication.processEvents()  # keep the UI responsive and visibly updating

            try:
                data = run_detection(image_path, prompt, threads=BATCH_THREADS)
            except Exception as e:
                traceback.print_exc()
                self.status_label.setText(f"Error on {filename}, skipping. See console.")
                QApplication.processEvents()
                continue

            detections = data.get("detections", [])

            if detections:
                found_count += 1
                total_detections += len(detections)
                pil_image = draw_detections_on_image(image_path, detections)
            else:
                # No match in this image — still save a copy (unmarked) so the
                # output folder contains one result file per input file.
                pil_image = Image.open(image_path).convert("RGB")

            # Live preview on the right, so you can watch progress as it runs
            pixmap = pil_image_to_qpixmap(pil_image)
            self.image_label.setPixmap(
                pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

            save_path = os.path.join(output_folder, filename)
            pil_image.save(save_path)

            # Brief pause before the next image, so the system gets a moment
            # to breathe rather than being hammered continuously.
            self.status_label.setText(f"Processed {index}/{total}. Cooling down...")
            QApplication.processEvents()
            time.sleep(COOLDOWN_SECONDS)

        self.status_label.setText(
            f"Batch complete: {total_detections} total '{prompt}' detection(s) "
            f"across {found_count}/{total} image(s).\n"
            f"Results saved to:\n{output_folder}"
        )

    def on_run_detection(self):
        """Runs detection on the chosen image with the typed prompt, and displays the result."""
        if not self.image_path:
            QMessageBox.warning(self, "No image", "Please choose an image first.")
            return

        prompt = self.prompt_input.text().strip()
        if not prompt:
            QMessageBox.warning(self, "No prompt", "Please type something to search for.")
            return

        self.status_label.setText("Running detection... please wait.")
        QApplication.processEvents()  # forces the UI to update the status text immediately

        try:
            data = run_detection(self.image_path, prompt)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Detection failed", str(e))
            self.status_label.setText("Detection failed. See error message.")
            return

        detections = data.get("detections", [])
        if not detections:
            self.status_label.setText(f"No '{prompt}' found in image.")
            return

        pil_image = draw_detections_on_image(self.image_path, detections)
        pixmap = pil_image_to_qpixmap(pil_image)
        self.image_label.setPixmap(
            pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.status_label.setText(f"Found {len(detections)} '{prompt}' detection(s).")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)  # apply the dark theme to every widget in the app

    # Show the welcome screen first. exec() blocks until the user closes it
    # (clicking "Get Started" calls self.accept(), which ends this call).
    welcome = WelcomeDialog()
    welcome.exec()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
