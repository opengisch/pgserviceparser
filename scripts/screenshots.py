#!/usr/bin/env python3
"""Generate screenshots of the pgserviceparser GUI for documentation.

Usage::

    QT_QPA_PLATFORM=offscreen python scripts/screenshots.py

Screenshots are saved to ``docs/docs/assets/images/screenshots/``.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap – ensure the package is importable from the repo root
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pgserviceparser.gui.compat import QtCore, QtGui, QtWidgets  # noqa: E402

QApplication = QtWidgets.QApplication
QIcon = QtGui.QIcon
QPixmap = QtGui.QPixmap
QPainter = QtGui.QPainter
QColor = QtGui.QColor
QPen = QtGui.QPen
QPoint = QtCore.QPoint
Qt = QtCore.Qt

from pgserviceparser.gui.main_window import MainWindow  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = REPO_ROOT / "docs" / "docs" / "assets" / "images" / "screenshots"

# Realistic sample services written to a temp file
SAMPLE_CONF = """\
[production-db]
host=db.example.com
dbname=app_prod
port=5432
user=app_admin
password=s3cur3P@ss
sslmode=verify-full

[staging-api]
host=staging.internal
dbname=api_staging
port=5432
user=api_user
password=staging_pwd

[dev-local]
host=localhost
dbname=myapp_dev
port=5432
user=developer
"""

# Window geometry
WIN_WIDTH = 820
WIN_HEIGHT = 520

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
_app: QApplication | None = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _grab(widget: QtWidgets.QWidget, filename: str, click_targets: list[QPoint] | None = None):
    """Grab a screenshot of *widget* and save it as *filename*.

    Optionally draw red-circle click markers at each *click_targets* position
    (coordinates relative to *widget*).
    """
    pixmap = widget.grab()

    if click_targets:
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(220, 50, 50, 200), 3)
        painter.setPen(pen)
        painter.setBrush(QColor(220, 50, 50, 60))
        for pt in click_targets:
            painter.drawEllipse(pt, 14, 14)
        painter.end()

    dest = OUTPUT_DIR / filename
    pixmap.save(str(dest))
    print(f"    saved {dest.relative_to(REPO_ROOT)}")


def _widget_center_in(child: QtWidgets.QWidget, ancestor: QtWidgets.QWidget) -> QPoint:
    """Return the centre of *child* mapped into *ancestor* coordinates."""
    centre = QPoint(child.width() // 2, child.height() // 2)
    return child.mapTo(ancestor, centre)


def _process_events(ms: int = 100):
    """Process events for *ms* milliseconds."""
    _app.processEvents()
    if ms > 0:
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(ms, loop.quit)
        loop.exec()
        _app.processEvents()


# ---------------------------------------------------------------------------
# Screenshot steps
# ---------------------------------------------------------------------------


def step_01_overview(window: MainWindow):
    """Step 01 – Full window overview with a service selected."""
    sw = window.centralWidget()
    # Select the first service ("dev-local" is alphabetically first)
    sw.lstServices.setCurrentRow(0)
    _process_events()
    _grab(window, "01_overview.png")


def step_02_service_selected(window: MainWindow):
    """Step 02 – Service selected, settings visible, highlight the list."""
    sw = window.centralWidget()
    # Select "production-db"
    items = sw.lstServices.findItems("production-db", Qt.MatchFlag.MatchExactly)
    if items:
        sw.lstServices.setCurrentItem(items[0])
    _process_events()

    click_pos = _widget_center_in(sw.lstServices, window)
    _grab(window, "02_service_selected.png", click_targets=[click_pos])


def step_03_settings_editor(window: MainWindow):
    """Step 03 – Close-up of the settings table for a service."""
    sw = window.centralWidget()
    items = sw.lstServices.findItems("production-db", Qt.MatchFlag.MatchExactly)
    if items:
        sw.lstServices.setCurrentItem(items[0])
    _process_events()

    # Grab only the right panel (settings editor)
    _grab(sw.editRightPanel, "03_settings_editor.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    global _app

    _app = QApplication(sys.argv)
    _app.setApplicationName("pgserviceparser-gui-screenshots")
    icon_path = REPO_ROOT / "pgserviceparser" / "gui" / "images" / "logo.png"
    if icon_path.exists():
        _app.setWindowIcon(QIcon(str(icon_path)))

    _ensure_output_dir()

    # Write sample config to a temp file
    tmp_dir = tempfile.mkdtemp(prefix="pgserviceparser_screenshots_")
    conf_path = Path(tmp_dir) / "pg_service.conf"
    conf_path.write_text(SAMPLE_CONF)
    print(f"  temp config: {conf_path}")

    try:
        from pgserviceparser.gui.service_widget import ServiceWidget

        window = MainWindow()
        # Replace the central widget with one pointing to our temp config
        widget = ServiceWidget(conf_file_path=conf_path)
        # Show a plausible path instead of the temp directory
        widget.txtConfFile.setText(str(Path.home() / ".pg_service.conf"))
        window.setCentralWidget(widget)
        window.resize(WIN_WIDTH, WIN_HEIGHT)
        window.show()
        _process_events(200)

        print("  01 Overview...")
        step_01_overview(window)

        print("  02 Service selected...")
        step_02_service_selected(window)

        print("  03 Settings editor...")
        step_03_settings_editor(window)

        window.close()
        print(f"\nDone — screenshots in {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
