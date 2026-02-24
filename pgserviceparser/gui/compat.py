"""Qt compatibility shim.

Uses ``qgis.PyQt`` when running inside QGIS (works with both Qt 5 and Qt 6),
otherwise falls back to ``PyQt6``.
"""

try:
    from qgis.PyQt import QtCore, QtGui, QtWidgets  # noqa: F401

    _QGIS = True
except ImportError:
    _QGIS = False
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: F401
    except ImportError:
        raise ImportError("PyQt6 is required for the GUI. " "Install it with: pip install pgserviceparser[gui]")


def _make_text_icon(text: str, color: str = "#333333") -> QtGui.QIcon:
    """Create a simple icon with *text* drawn in a circle."""
    size = 64
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    pen = QtGui.QPen(QtGui.QColor(color), 3)
    painter.setPen(pen)
    font = painter.font()
    font.setPixelSize(40)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return QtGui.QIcon(pixmap)


def icon_add() -> QtGui.QIcon:
    """Return a platform-appropriate 'add' icon."""
    if _QGIS:
        from qgis.core import QgsApplication

        return QgsApplication.getThemeIcon("/symbologyAdd.svg")
    # Theme icons are unavailable in headless environments (e.g. CI with
    # QT_QPA_PLATFORM=offscreen), so fall back to a manually drawn icon.
    icon = QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListAdd)
    if icon.isNull():
        icon = _make_text_icon("+")
    return icon


def icon_remove() -> QtGui.QIcon:
    """Return a platform-appropriate 'remove' icon."""
    if _QGIS:
        from qgis.core import QgsApplication

        return QgsApplication.getThemeIcon("/symbologyRemove.svg")
    # Theme icons are unavailable in headless environments (e.g. CI with
    # QT_QPA_PLATFORM=offscreen), so fall back to a manually drawn icon.
    icon = QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListRemove)
    if icon.isNull():
        icon = _make_text_icon("\u2212")
    return icon
