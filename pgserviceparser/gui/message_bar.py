"""A stackable message bar widget for displaying success/warning/error messages."""

import traceback
from enum import IntEnum

from .compat import QtCore, QtWidgets

QDialog = QtWidgets.QDialog
QDialogButtonBox = QtWidgets.QDialogButtonBox
QFrame = QtWidgets.QFrame
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QProgressBar = QtWidgets.QProgressBar
QPropertyAnimation = QtCore.QPropertyAnimation
QScrollArea = QtWidgets.QScrollArea
QSizePolicy = QtWidgets.QSizePolicy
Qt = QtCore.Qt
QTextEdit = QtWidgets.QTextEdit
QTimer = QtCore.QTimer
QToolButton = QtWidgets.QToolButton
QVBoxLayout = QtWidgets.QVBoxLayout
QWidget = QtWidgets.QWidget

try:
    from qgis.core import Qgis
    from qgis.gui import QgsMessageBar

    HAS_QGS_MESSAGE_BAR = True
except ImportError:
    HAS_QGS_MESSAGE_BAR = False


class MessageLevel(IntEnum):
    SUCCESS = 0
    WARNING = 1
    ERROR = 2


# Duration in ms for auto-dismiss of success messages
_SUCCESS_TIMEOUT_MS = 5000
# Timer resolution for the countdown progress bar
_TIMER_INTERVAL_MS = 50

_STYLE_TEMPLATES = {
    MessageLevel.SUCCESS: (
        "QFrame#messageItem {"
        "  background-color: #a5d6a7;"
        "  border: 2px solid #2e7d32;"
        "  border-radius: 4px;"
        "}"
        "QLabel { color: #1b5e20; font-weight: bold; }"
        "QToolButton { color: #1b5e20; border: none; font-weight: bold; }"
        "QToolButton:hover { background-color: rgba(0,0,0,25); border-radius: 2px; }"
        "QProgressBar {"
        "  background-color: #66bb6a;"
        "  border: none;"
        "  border-radius: 2px;"
        "  max-height: 3px;"
        "}"
        "QProgressBar::chunk {"
        "  background-color: #2e7d32;"
        "  border-radius: 2px;"
        "}"
    ),
    MessageLevel.WARNING: (
        "QFrame#messageItem {"
        "  background-color: #ffe082;"
        "  border: 2px solid #f57f17;"
        "  border-radius: 4px;"
        "}"
        "QLabel { color: #e65100; font-weight: bold; }"
        "QToolButton { color: #e65100; border: none; font-weight: bold; }"
        "QToolButton:hover { background-color: rgba(0,0,0,25); border-radius: 2px; }"
    ),
    MessageLevel.ERROR: (
        "QFrame#messageItem {"
        "  background-color: #ef9a9a;"
        "  border: 2px solid #c62828;"
        "  border-radius: 4px;"
        "}"
        "QLabel { color: #b71c1c; font-weight: bold; }"
        "QToolButton { color: #b71c1c; border: none; font-weight: bold; }"
        "QToolButton:hover { background-color: rgba(0,0,0,25); border-radius: 2px; }"
    ),
}

_LEVEL_ICONS = {
    MessageLevel.SUCCESS: "\u2705 ",  # ✅
    MessageLevel.WARNING: "\u26a0\ufe0f ",  # ⚠️
    MessageLevel.ERROR: "\u274c ",  # ❌
}


class _MessageItem(QFrame):
    """A single message bar entry."""

    def __init__(self, text: str, level: MessageLevel, exception: Exception | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("messageItem")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet(_STYLE_TEMPLATES[level])
        self._exception = exception

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # --- Top row: text + buttons ---
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)

        self._label = QLabel(_LEVEL_ICONS.get(level, "") + text)
        self._label.setWordWrap(True)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_row.addWidget(self._label)

        # Details button (only shown when an exception is attached)
        if exception is not None:
            self._details_btn = QToolButton()
            self._details_btn.setText("Details")
            self._details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._details_btn.clicked.connect(self._show_details)
            top_row.addWidget(self._details_btn)

        self._close_btn = QToolButton()
        self._close_btn.setText("\u2715")  # ✕
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._dismiss)
        top_row.addWidget(self._close_btn)

        layout.addLayout(top_row)

        # --- Countdown progress bar (success messages only) ---
        self._progress_bar = None
        self._countdown_timer = None
        self._elapsed = 0

        if level == MessageLevel.SUCCESS:
            self._progress_bar = QProgressBar()
            self._progress_bar.setTextVisible(False)
            self._progress_bar.setRange(0, _SUCCESS_TIMEOUT_MS)
            self._progress_bar.setValue(_SUCCESS_TIMEOUT_MS)
            self._progress_bar.setFixedHeight(3)
            layout.addWidget(self._progress_bar)

            self._countdown_timer = QTimer(self)
            self._countdown_timer.setInterval(_TIMER_INTERVAL_MS)
            self._countdown_timer.timeout.connect(self._tick)
            self._countdown_timer.start()

    def _tick(self):
        self._elapsed += _TIMER_INTERVAL_MS
        remaining = max(0, _SUCCESS_TIMEOUT_MS - self._elapsed)
        if self._progress_bar:
            self._progress_bar.setValue(remaining)
        if remaining <= 0:
            if self._countdown_timer:
                self._countdown_timer.stop()
            self._dismiss()

    def _dismiss(self):
        if self._countdown_timer and self._countdown_timer.isActive():
            self._countdown_timer.stop()

        # Animate fade-out by shrinking height
        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(200)
        self._anim.setStartValue(self.sizeHint().height())
        self._anim.setEndValue(0)
        self._anim.finished.connect(self._remove)
        self._anim.start()

    def _remove(self):
        message_bar = self._message_bar()
        self.setParent(None)
        self.deleteLater()
        # Let the message bar know so it can hide itself when empty
        if message_bar is not None:
            message_bar._on_item_removed()

    def _show_details(self):
        """Show a dialog with the full exception traceback."""
        if self._exception is None:
            return

        dlg = QDialog(self.window())
        dlg.setWindowTitle("Error Details")
        dlg.resize(700, 400)

        layout = QVBoxLayout(dlg)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFontFamily("monospace")
        details = "".join(
            traceback.format_exception(type(self._exception), self._exception, self._exception.__traceback__)
        )
        text_edit.setPlainText(details)
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dlg.close)
        layout.addWidget(button_box)

        dlg.exec()

    def _message_bar(self):
        """Walk up the parent chain to find the owning MessageBar."""
        widget = self.parent()
        while widget is not None:
            if isinstance(widget, MessageBar):
                return widget
            widget = widget.parent()
        return None


# Maximum height the message bar can occupy before it becomes scrollable
_MAX_BAR_HEIGHT = 50

# Mapping from custom MessageLevel to Qgis.MessageLevel
_QGIS_LEVEL_MAP = {}
if HAS_QGS_MESSAGE_BAR:
    _QGIS_LEVEL_MAP = {
        MessageLevel.SUCCESS: Qgis.MessageLevel.Success,  # type: ignore[possibly-undefined]
        MessageLevel.WARNING: Qgis.MessageLevel.Warning,  # type: ignore[possibly-undefined]
        MessageLevel.ERROR: Qgis.MessageLevel.Critical,  # type: ignore[possibly-undefined]
    }

# Duration in seconds for QgsMessageBar auto-dismiss (0 = manual dismiss)
_QGIS_SUCCESS_DURATION_S = 5


class MessageBar(QWidget):
    """A container widget that stacks message items at the top of a dialog.

    When running inside QGIS, delegates to ``QgsMessageBar`` for native
    look-and-feel.  Falls back to a custom scroll-area implementation
    otherwise (e.g. standalone mode).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_MAX_BAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        if HAS_QGS_MESSAGE_BAR:
            self._qgs_bar = QgsMessageBar(self)  # type: ignore[possibly-undefined]
            outer.addWidget(self._qgs_bar)
            self._use_qgs = True
        else:
            self._qgs_bar = None
            self._use_qgs = False

            self._scroll_area = QScrollArea()
            self._scroll_area.setWidgetResizable(True)
            self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            outer.addWidget(self._scroll_area)

            self._inner = QWidget()
            self._inner_layout = QVBoxLayout(self._inner)
            self._inner_layout.setContentsMargins(0, 0, 0, 0)
            self._inner_layout.setSpacing(4)
            self._inner_layout.addStretch()
            self._scroll_area.setWidget(self._inner)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def pushMessage(
        self,
        text: str,
        level: MessageLevel = MessageLevel.SUCCESS,
        exception: Exception | None = None,
    ):
        """Add a message to the bar.

        Args:
            text: The message text to display.
            level: MessageLevel.SUCCESS (auto-dismiss 5 s),
                   MessageLevel.WARNING or MessageLevel.ERROR (manual dismiss).
            exception: Optional exception. When provided a *Details* button is
                       shown that opens a dialog with the full traceback.
        """
        if self._use_qgs:
            qgis_level = _QGIS_LEVEL_MAP[level]
            duration = _QGIS_SUCCESS_DURATION_S if level == MessageLevel.SUCCESS else 0
            msg = text
            if exception is not None:
                msg += f"\n{exception}"
            self._qgs_bar.pushMessage("", msg, qgis_level, duration)
        else:
            item = _MessageItem(text, level, exception=exception, parent=self._inner)
            # Insert before the stretch at the end
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, item)
            # Scroll to bottom to reveal the newest message
            QTimer.singleShot(0, self._scroll_to_bottom)

    def pushSuccess(self, text: str):
        self.pushMessage(text, MessageLevel.SUCCESS)

    def pushWarning(self, text: str):
        self.pushMessage(text, MessageLevel.WARNING)

    def pushError(self, text: str, exception: Exception | None = None):
        self.pushMessage(text, MessageLevel.ERROR, exception=exception)

    def clearAll(self):
        """Remove all messages immediately."""
        if self._use_qgs:
            self._qgs_bar.clearWidgets()
        else:
            for i in reversed(range(self._inner_layout.count())):
                item = self._inner_layout.itemAt(i)
                widget = item.widget() if item else None
                if widget and isinstance(widget, _MessageItem):
                    self._inner_layout.removeWidget(widget)
                    widget.setParent(None)
                    widget.deleteLater()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_item_removed(self):
        """Called when a message item removes itself."""
        pass  # Nothing to do — fixed height, no layout changes

    def _scroll_to_bottom(self):
        if not self._use_qgs:
            sb = self._scroll_area.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    # ------------------------------------------------------------------
    # Static helper to find a MessageBar from any child widget
    # ------------------------------------------------------------------

    @staticmethod
    def findMessageBar(widget):
        """Walk up the widget tree to find the nearest MessageBar.

        This allows any child widget to push messages without holding a direct reference.
        Returns None if no message bar is found.
        """
        from .service_widget import PGServiceParserWidget

        w = widget
        while w is not None:
            if isinstance(w, MessageBar):
                return w
            # Check if the parent has a messageBar() accessor or _message_bar attribute
            if isinstance(w, PGServiceParserWidget) and hasattr(w, "_message_bar"):
                return w._message_bar
            parent = w.parent()
            if parent is not None and hasattr(parent, "messageBar"):
                bar = parent.messageBar()
                if isinstance(bar, MessageBar):
                    return bar
            w = parent
        return None

    # ------------------------------------------------------------------
    # Static convenience helpers for child widgets
    # ------------------------------------------------------------------

    @staticmethod
    def pushErrorToBar(widget, text: str, exception=None):
        """Push an error message from any child widget to the message bar.

        If *exception* is not None its string representation is appended to
        the visible text and a *Details* button is added to view the full
        traceback.
        """
        bar = MessageBar.findMessageBar(widget)
        if bar:
            msg = text
            if exception is not None:
                msg += f"\n{exception}"
            bar.pushError(msg, exception=exception)

    @staticmethod
    def pushWarningToBar(widget, text: str):
        """Push a warning message from any child widget to the message bar."""
        bar = MessageBar.findMessageBar(widget)
        if bar:
            bar.pushWarning(text)

    @staticmethod
    def pushSuccessToBar(widget, text: str):
        """Push a success message from any child widget to the message bar."""
        bar = MessageBar.findMessageBar(widget)
        if bar:
            bar.pushSuccess(text)
