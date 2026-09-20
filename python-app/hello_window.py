import sys
from PySide6.QtWidgets import QApplication, QLabel

# QApplication manages the whole GUI app — every PySide6 app needs exactly one.
app = QApplication(sys.argv)

# A simple window with just a text label inside it.
label = QLabel("Hello from PySide6 — if you see this, the GUI framework works!")
label.setWindowTitle("LocateAnything - Test Window")
label.resize(400, 100)
label.show()

# Starts the event loop — keeps the window open and responsive until you close it.
sys.exit(app.exec())
