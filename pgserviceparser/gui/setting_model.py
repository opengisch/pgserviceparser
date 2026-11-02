"""Service configuration table model for the service settings editor."""

from .compat import QtCore, QtGui

QAbstractTableModel = QtCore.QAbstractTableModel
QModelIndex = QtCore.QModelIndex
Qt = QtCore.Qt
pyqtSignal = QtCore.pyqtSignal
QColor = QtGui.QColor
QFont = QtGui.QFont

from ..service_settings import SERVICE_SETTINGS, WidgetType


class _ServiceConfigModel(QAbstractTableModel):
    """Table model that holds settings (key/value pairs) for a single service."""

    KEY_COL = 0
    VALUE_COL = 1

    is_dirty_changed = pyqtSignal(bool)

    def __init__(self, service_name: str, service_config: dict):
        super().__init__()
        self._service_name = service_name
        self._model_data = service_config
        self._original_data = service_config.copy()
        self._settings_data = SERVICE_SETTINGS
        self._dirty = False

    def rowCount(self, parent=QModelIndex()):
        return len(self._model_data)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def index_to_setting_key(self, index: QModelIndex) -> str:
        return list(self._model_data.keys())[index.row()]

    def add_settings(self, settings: dict[str, str]):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount() + len(settings) - 1)
        self._model_data.update(settings)
        self._set_dirty_status(True)
        self.endInsertRows()

        if self._model_data == self._original_data:
            self._set_dirty_status(False)

    def remove_setting(self, index: QModelIndex):
        if not index.isValid():
            return

        self.beginRemoveRows(QModelIndex(), index.row(), index.row())
        del self._model_data[list(self._model_data.keys())[index.row()]]
        self._set_dirty_status(True)
        self.endRemoveRows()

        if self._model_data == self._original_data:
            self._set_dirty_status(False)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        key = list(self._model_data.keys())[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == self.KEY_COL:
                return key
            elif index.column() == self.VALUE_COL:
                setting = self._settings_data.get(key, {})
                if setting.get("widget_type") == WidgetType.PASSWORD:
                    return "************"
                return self._model_data[key]

        elif role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == self.KEY_COL:
                return self._settings_data.get(key, {}).get("description")

        elif role == Qt.ItemDataRole.EditRole and index.column() == self.VALUE_COL:
            return self._model_data[key]

        elif role == Qt.ItemDataRole.FontRole:
            if index.column() == self.KEY_COL:
                font = QFont()
                font.setBold(True)
                return font
            elif index.column() == self.VALUE_COL and (
                key not in self._original_data or self._model_data[key] != self._original_data[key]
            ):
                font = QFont()
                font.setItalic(True)
                return font

        elif role == Qt.ItemDataRole.ForegroundRole and index.column() == self.VALUE_COL:
            if key not in self._original_data or self._model_data[key] != self._original_data[key]:
                return QColor(Qt.GlobalColor.darkGreen)

        elif role == Qt.ItemDataRole.UserRole:
            setting = self._settings_data.get(key, {})
            wtype = setting.get("widget_type")
            if index.column() == self.VALUE_COL and isinstance(wtype, WidgetType):
                return {
                    "widget_type": wtype,
                    "config": setting.get("config"),
                }
            return {}

        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False

        key = list(self._model_data.keys())[index.row()]
        if value != self._model_data[key]:
            self._model_data[key] = value

            if key not in self._original_data or value != self._original_data[key]:
                self._set_dirty_status(True)
            else:
                if self._model_data == self._original_data:
                    self._set_dirty_status(False)

            return True

        return False

    def flags(self, idx: QModelIndex):
        if not idx.isValid():
            return ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled

        _flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if idx.column() == self.VALUE_COL:
            _flags |= Qt.ItemFlag.ItemIsEditable
        return _flags

    def is_dirty(self) -> bool:
        return self._dirty

    def _set_dirty_status(self, status: bool):
        self._dirty = status
        self.is_dirty_changed.emit(status)

    def current_setting_keys(self) -> list[str]:
        return list(self._model_data.keys())

    def service_config(self) -> dict:
        return self._model_data.copy()

    def service_name(self) -> str:
        return self._service_name

    def set_not_dirty(self):
        self._original_data = self._model_data.copy()
        self._set_dirty_status(False)

    def invalid_settings(self) -> list[str]:
        return [k for k, v in self._model_data.items() if v.strip() == ""]

    @staticmethod
    def is_custom_widget_cell(index: QModelIndex) -> bool:
        data = index.data(Qt.ItemDataRole.UserRole)
        return (
            index.column() == _ServiceConfigModel.VALUE_COL
            and isinstance(data, dict)
            and "widget_type" in data
            and data["widget_type"] is not None
        )
