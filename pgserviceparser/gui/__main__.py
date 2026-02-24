"""Entry point for pgserviceparser GUI."""

import sys
from pathlib import Path

try:
    from pgserviceparser.gui.compat import QtGui, QtWidgets
except ImportError:
    print(
        "Error: PyQt6 is required for the GUI.\n" "Install it with: pip install pgserviceparser[gui]",
        file=sys.stderr,
    )
    sys.exit(1)

QApplication = QtWidgets.QApplication
QIcon = QtGui.QIcon

from pgserviceparser.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("pgserviceparser-gui")

    icon_path = Path(__file__).parent / "images" / "logo.png"
    app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
