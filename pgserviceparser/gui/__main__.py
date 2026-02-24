"""Entry point for pgserviceparser GUI."""

import sys
from pathlib import Path

try:
    from .compat import QtGui, QtWidgets
except ImportError:
    print(
        "Error: PyQt6 is required for the GUI.\n" "Install it with: pip install pgserviceparser[gui]",
        file=sys.stderr,
    )
    sys.exit(1)

QApplication = QtWidgets.QApplication
QIcon = QtGui.QIcon

from .main_window import _MainWindow


def main():
    """Launch the pgserviceparser GUI application.

    Creates the QApplication, sets the window icon, and opens the main window.
    Can be invoked via the ``pgserviceparser-gui`` console script or with
    ``python -m pgserviceparser.gui``.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("pgserviceparser-gui")

    icon_path = Path(__file__).parent / "images" / "logo.png"
    app.setWindowIcon(QIcon(str(icon_path)))

    window = _MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
