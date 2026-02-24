"""Item delegates for service configuration editing."""

from pgserviceparser.gui.compat import QtCore, QtWidgets

Qt = QtCore.Qt
QComboBox = QtWidgets.QComboBox
QFileDialog = QtWidgets.QFileDialog
QLineEdit = QtWidgets.QLineEdit
QStyledItemDelegate = QtWidgets.QStyledItemDelegate
QWidget = QtWidgets.QWidget

from pgserviceparser.gui.setting_model import ServiceConfigModel
from pgserviceparser.service_settings import WidgetType


class ServiceConfigDelegate(QStyledItemDelegate):
    """Delegate that provides appropriate editors for service settings."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

    def createEditor(self, parent: QWidget, option, index):
        if ServiceConfigModel.is_custom_widget_cell(index):
            meta = index.data(Qt.ItemDataRole.UserRole)
            widget_type = meta["widget_type"]
            config = meta.get("config") or {}

            if widget_type == WidgetType.COMBOBOX:
                widget = QComboBox(parent)
                for value in config.get("values", []):
                    widget.addItem(value, value)
                widget.currentIndexChanged.connect(self._commit_and_close)
                return widget

            elif widget_type == WidgetType.PASSWORD:
                widget = QLineEdit(parent)
                widget.setEchoMode(QLineEdit.EchoMode.Password)
                widget.editingFinished.connect(self._commit_and_close)
                return widget

            elif widget_type == WidgetType.FILE:
                # For file settings, open a dialog immediately
                file_filter = config.get("filter", "")
                title = config.get("title", "Select file")
                path, _ = QFileDialog.getOpenFileName(parent, title, "", file_filter)
                if path:
                    # Set directly and close
                    model = index.model()
                    model.setData(index, path, Qt.ItemDataRole.EditRole)
                return None  # No persistent editor needed

        return super().createEditor(parent, option, index)

    def _commit_and_close(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def setEditorData(self, editor: QWidget, index):
        if ServiceConfigModel.is_custom_widget_cell(index):
            meta = index.data(Qt.ItemDataRole.UserRole)
            widget_type = meta["widget_type"]
            value = index.data(Qt.ItemDataRole.EditRole)

            if widget_type == WidgetType.COMBOBOX and isinstance(editor, QComboBox):
                editor.setCurrentText(value or "")
                return
            elif widget_type == WidgetType.PASSWORD and isinstance(editor, QLineEdit):
                editor.setText(value or "")
                return

        super().setEditorData(editor, index)

    def setModelData(self, editor: QWidget, model, index):
        if ServiceConfigModel.is_custom_widget_cell(index):
            meta = index.data(Qt.ItemDataRole.UserRole)
            widget_type = meta["widget_type"]

            if widget_type == WidgetType.COMBOBOX and isinstance(editor, QComboBox):
                model.setData(index, editor.currentData(), Qt.ItemDataRole.EditRole)
                return
            elif widget_type == WidgetType.PASSWORD and isinstance(editor, QLineEdit):
                model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)
                return

        super().setModelData(editor, model, index)
