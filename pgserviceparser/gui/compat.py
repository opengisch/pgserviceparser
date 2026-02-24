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


def icon_add() -> QtGui.QIcon:
    """Return a platform-appropriate 'add' icon."""
    if _QGIS:
        from qgis.core import QgsApplication

        return QgsApplication.getThemeIcon("/symbologyAdd.svg")
    return QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListAdd)


def icon_remove() -> QtGui.QIcon:
    """Return a platform-appropriate 'remove' icon."""
    if _QGIS:
        from qgis.core import QgsApplication

        return QgsApplication.getThemeIcon("/symbologyRemove.svg")
    return QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListRemove)
