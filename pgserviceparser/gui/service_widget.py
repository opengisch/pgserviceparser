"""Reusable widget for managing PostgreSQL connection services."""

from pathlib import Path

from .compat import QtCore, QtGui, QtWidgets, icon_add, icon_remove

QPixmap = QtGui.QPixmap
QIcon = QtGui.QIcon
QItemSelection = QtCore.QItemSelection
QModelIndex = QtCore.QModelIndex
Qt = QtCore.Qt
pyqtSlot = QtCore.pyqtSlot
QAbstractItemView = QtWidgets.QAbstractItemView
QApplication = QtWidgets.QApplication
QDialogButtonBox = QtWidgets.QDialogButtonBox
QHBoxLayout = QtWidgets.QHBoxLayout
QHeaderView = QtWidgets.QHeaderView
QInputDialog = QtWidgets.QInputDialog
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QListWidget = QtWidgets.QListWidget
QListWidgetItem = QtWidgets.QListWidgetItem
QMenu = QtWidgets.QMenu
QMessageBox = QtWidgets.QMessageBox
QPushButton = QtWidgets.QPushButton
QSizePolicy = QtWidgets.QSizePolicy
QTableView = QtWidgets.QTableView
QToolButton = QtWidgets.QToolButton
QVBoxLayout = QtWidgets.QVBoxLayout
QWidget = QtWidgets.QWidget

import pgserviceparser
from pgserviceparser.exceptions import ServiceFileNotFound, ServiceNotFound
from pgserviceparser.service_settings import SERVICE_SETTINGS, SETTINGS_TEMPLATE

from .item_delegates import _ServiceConfigDelegate
from .setting_model import _ServiceConfigModel

_IMAGES_DIR = Path(__file__).parent / "images"


class PGServiceParserWidget(QWidget):
    """Widget for listing, creating, editing, and removing PostgreSQL services.

    Can be embedded in any PyQt6 application or used inside QGIS via
    the plugin adapter.
    """

    def __init__(
        self,
        conf_file_path: Path | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._conf_file_path = conf_file_path or pgserviceparser.conf_path()
        self._edit_model: _ServiceConfigModel | None = None
        self._new_empty_file = False

        self._build_ui()
        self._connect_signals()
        self._initialize()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        outer = QVBoxLayout(self)

        # ---- Status bar: config file path ----
        status_row = QHBoxLayout()
        self.lblWarning = QLabel()
        self.lblWarning.setMaximumSize(24, 24)
        _images_dir = Path(__file__).resolve().parent / "images"
        self.lblWarning.setPixmap(QPixmap(str(_images_dir / "warning.svg")))
        self.lblWarning.setScaledContents(True)
        status_row.addWidget(self.lblWarning)

        self.lblConfFile = QLabel()
        status_row.addWidget(self.lblConfFile)

        self.txtConfFile = QLineEdit()
        self.txtConfFile.setReadOnly(True)
        status_row.addWidget(self.txtConfFile)

        self.btnCreateServiceFile = QPushButton("Create file at default location")
        status_row.addWidget(self.btnCreateServiceFile)

        outer.addLayout(status_row)

        # ---- Message bar (dismissible) ----
        self._message_bar = QWidget()
        self._message_bar.setVisible(False)
        msg_layout = QHBoxLayout(self._message_bar)
        msg_layout.setContentsMargins(4, 2, 4, 2)
        self._lblMessage = QLabel()
        self._lblMessage.setWordWrap(True)
        msg_layout.addWidget(self._lblMessage, 1)
        self._btnDismiss = QToolButton()
        self._btnDismiss.setText("\u2715")
        self._btnDismiss.setAutoRaise(True)
        self._btnDismiss.setToolTip("Dismiss")
        self._btnDismiss.clicked.connect(self._dismiss_message)
        msg_layout.addWidget(self._btnDismiss)
        outer.addWidget(self._message_bar)

        # ---- Main content ----
        self._content_widget = QWidget()
        root = QHBoxLayout(self._content_widget)
        root.setContentsMargins(0, 0, 0, 0)

        # ---- Left: service list + buttons ----
        left = QVBoxLayout()

        btn_row = QHBoxLayout()
        self.btnAddService = QToolButton()
        self.btnAddService.setIcon(icon_add())
        self.btnAddService.setToolTip("Add a new service")
        self.btnRemoveService = QToolButton()
        self.btnRemoveService.setIcon(icon_remove())
        self.btnRemoveService.setToolTip("Remove selected service(s)")
        self.btnRemoveService.setEnabled(False)
        btn_row.addWidget(self.btnAddService)
        btn_row.addWidget(self.btnRemoveService)
        btn_row.addStretch()
        left.addLayout(btn_row)

        self.lstServices = QListWidget()
        self.lstServices.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lstServices.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lstServices.setAlternatingRowColors(True)
        self.lstServices.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self.lstServices.setMinimumWidth(120)
        self.lstServices.setMaximumWidth(200)
        left.addWidget(self.lstServices)

        root.addLayout(left, 0)

        # ---- Right: settings editor ----
        self.editRightPanel = QWidget()
        right = QVBoxLayout(self.editRightPanel)
        right.setContentsMargins(0, 0, 0, 0)

        table_row = QHBoxLayout()
        self.tblServiceConfig = QTableView()
        self.tblServiceConfig.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.tblServiceConfig.setAlternatingRowColors(True)
        self.tblServiceConfig.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tblServiceConfig.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tblServiceConfig.horizontalHeader().setVisible(False)
        self.tblServiceConfig.horizontalHeader().setStretchLastSection(True)
        self.tblServiceConfig.verticalHeader().setVisible(False)
        table_row.addWidget(self.tblServiceConfig)

        setting_btns = QVBoxLayout()
        self.btnAddSettings = QPushButton()
        self.btnAddSettings.setIcon(icon_add())
        self.btnAddSettings.setToolTip("Add settings to current service")
        self.btnAddSettings.setFixedSize(28, 28)
        self.btnRemoveSetting = QPushButton()
        self.btnRemoveSetting.setIcon(icon_remove())
        self.btnRemoveSetting.setToolTip("Remove setting from current service")
        self.btnRemoveSetting.setFixedSize(28, 28)
        self.btnRemoveSetting.setEnabled(False)
        setting_btns.addWidget(self.btnAddSettings)
        setting_btns.addWidget(self.btnRemoveSetting)
        setting_btns.addStretch()
        table_row.addLayout(setting_btns)

        right.addLayout(table_row)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.btnCopySettings = QPushButton()
        self.btnCopySettings.setText("\U0001f4cb")  # clipboard emoji
        self.btnCopySettings.setToolTip("Copy settings to clipboard")
        self.btnCopySettings.setMaximumSize(25, 25)
        self.btnUpdateService = QPushButton("Update service")
        self.btnUpdateService.setEnabled(False)
        bottom_row.addWidget(self.btnCopySettings)
        bottom_row.addWidget(self.btnUpdateService)
        right.addLayout(bottom_row)

        root.addWidget(self.editRightPanel, 1)

        outer.addWidget(self._content_widget)
        self._set_edit_panel_enabled(False)

    # ------------------------------------------------------------- Signals --

    def _connect_signals(self):
        self.btnAddService.clicked.connect(self._add_service_clicked)
        self.btnRemoveService.clicked.connect(self._remove_service_clicked)
        self.lstServices.itemSelectionChanged.connect(self._service_list_selection_changed)
        self.lstServices.customContextMenuRequested.connect(self._service_list_context_menu)
        self.lstServices.itemDoubleClicked.connect(self._service_list_double_clicked)
        self.btnAddSettings.clicked.connect(self._add_settings_clicked)
        self.btnRemoveSetting.clicked.connect(self._remove_setting_clicked)
        self.btnCopySettings.clicked.connect(self._copy_settings_clicked)
        self.btnUpdateService.clicked.connect(self._update_service_clicked)
        self.btnCreateServiceFile.clicked.connect(self._create_file_clicked)

    # ---------------------------------------------------------- Initialize --

    def _initialize(self):
        if not self._conf_file_path.exists():
            self.lblConfFile.setText("Config file not found!")
            not_found_tooltip = (
                "Create a config file at a default location or\n"
                "set your PGSERVICEFILE environment variable and reopen the dialog."
            )
            self.lblConfFile.setToolTip(not_found_tooltip)
            self.lblWarning.setToolTip(not_found_tooltip)
            self.txtConfFile.setVisible(False)
            self._content_widget.setEnabled(False)
            return

        self.lblWarning.setVisible(False)
        self.lblConfFile.setText("Config file path found at ")
        self.txtConfFile.setText(str(self._conf_file_path))
        self.btnCreateServiceFile.setVisible(False)

        self._refresh_service_list()
        self._update_add_settings_button()

    def _refresh_service_list(self):
        self._edit_model = None
        self.lstServices.blockSignals(True)
        selected_text = self.lstServices.currentItem().text() if self.lstServices.currentItem() else ""
        self.lstServices.clear()
        try:
            names = pgserviceparser.service_names(self._conf_file_path, sorted_alphabetically=True)
        except ServiceFileNotFound:
            self._service_file_warning()
            self.lstServices.blockSignals(False)
            return
        self.lstServices.addItems(names)
        self.lstServices.blockSignals(False)

        if selected_text:
            items = self.lstServices.findItems(selected_text, Qt.MatchFlag.MatchExactly)
            if items:
                self.lstServices.setCurrentItem(items[0])

    def _set_edit_panel_enabled(self, enabled: bool):
        self.editRightPanel.setEnabled(enabled)

    def _update_add_settings_button(self):
        enable = bool(self._edit_model and self._edit_model.rowCount() < len(SERVICE_SETTINGS))
        self.btnAddSettings.setEnabled(enable)

    @pyqtSlot()
    def _create_file_clicked(self):
        name, ok = QInputDialog.getText(self, "New service", "Enter a service name:")
        name = name.strip().replace(" ", "-") if name else ""
        if ok and name:
            self._conf_file_path = pgserviceparser.conf_path(create_if_missing=True)
            try:
                pgserviceparser.create_service(name, {}, self._conf_file_path)
            except PermissionError:
                self._permission_warning()
            else:
                self._new_empty_file = True
                self._initialize()

    # ---------------------------------------------------- Service list ops --

    @pyqtSlot()
    def _service_list_selection_changed(self):
        selected_items = self.lstServices.selectedItems()
        count = len(selected_items)
        self.btnRemoveService.setEnabled(count > 0)

        if count == 1:
            self._edit_service_selected(selected_items[0].text())
            self._set_edit_panel_enabled(True)
        else:
            self._edit_model = None
            self.tblServiceConfig.setModel(None)
            self._set_edit_panel_enabled(False)
            self.btnUpdateService.setDisabled(True)
            self._update_add_settings_button()

    def _edit_service_selected(self, service_name: str):
        if self._edit_model and self._edit_model.is_dirty():
            if (
                QMessageBox.question(
                    self,
                    "Pending edits",
                    f"There are pending edits for service '{self._edit_model.service_name()}'. "
                    "Are you sure you want to discard them?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                self.lstServices.blockSignals(True)
                items = self.lstServices.findItems(self._edit_model.service_name(), Qt.MatchFlag.MatchExactly)
                if items:
                    self.lstServices.setCurrentItem(items[0])
                self.lstServices.blockSignals(False)
                return

        try:
            config = pgserviceparser.service_config(service_name, self._conf_file_path)
        except ServiceNotFound:
            self._service_not_found_warning(service_name)
            self._refresh_service_list()
            return
        except ServiceFileNotFound:
            self._service_file_warning()
            return

        self._edit_model = _ServiceConfigModel(service_name, config)
        self.tblServiceConfig.setModel(self._edit_model)
        self.tblServiceConfig.setItemDelegate(_ServiceConfigDelegate(self))
        self.tblServiceConfig.selectionModel().selectionChanged.connect(self._update_settings_buttons)
        self._edit_model.is_dirty_changed.connect(self.btnUpdateService.setEnabled)
        self.btnUpdateService.setDisabled(True)

        if self._new_empty_file:
            self._edit_model.add_settings(SETTINGS_TEMPLATE)
            self._new_empty_file = False

        self._update_add_settings_button()
        self._update_settings_buttons(QItemSelection(), QItemSelection())

    # --------------------------------------------------- Add / Remove / etc --

    @pyqtSlot()
    def _add_service_clicked(self):
        name, ok = QInputDialog.getText(self, "New service", "Enter a service name:")
        name = name.strip().replace(" ", "-") if name else ""
        if ok and name:
            try:
                pgserviceparser.create_service(name, {}, self._conf_file_path)
            except (PermissionError, ServiceFileNotFound) as e:
                self._permission_warning() if isinstance(e, PermissionError) else self._service_file_warning()
            else:
                self._refresh_service_list()
                items = self.lstServices.findItems(name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.lstServices.setCurrentItem(items[0])

    @pyqtSlot()
    def _remove_service_clicked(self):
        selected_items = self.lstServices.selectedItems()
        if not selected_items:
            return

        names = [item.text() for item in selected_items]
        if len(names) == 1:
            message = f"Are you sure you want to remove the service '{names[0]}'?"
        else:
            message = f"Are you sure you want to remove {len(names)} services?\n\n" + "\n".join(names)

        if (
            QMessageBox.question(
                self,
                "Remove service(s)",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            for name in names:
                try:
                    pgserviceparser.remove_service(name, self._conf_file_path)
                except PermissionError:
                    self._permission_warning()
                    return
                except ServiceFileNotFound:
                    self._service_file_warning()
                    return
                except ServiceNotFound:
                    pass  # already gone — continue

            self._edit_model = None
            self.tblServiceConfig.setModel(None)
            self._set_edit_panel_enabled(False)
            self._refresh_service_list()

    @pyqtSlot("QPoint")
    def _service_list_context_menu(self, pos):
        item = self.lstServices.itemAt(pos)
        if not item:
            return

        selected_items = self.lstServices.selectedItems()
        if len(selected_items) != 1:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("Rename service\u2026")
        rename_action.triggered.connect(lambda: self._rename_service(item.text()))
        duplicate_action = menu.addAction("Duplicate service\u2026")
        duplicate_action.triggered.connect(lambda: self._duplicate_and_edit_service(item.text()))
        menu.exec(self.lstServices.viewport().mapToGlobal(pos))

    def _service_list_double_clicked(self, item: QListWidgetItem):
        if item:
            self._rename_service(item.text())

    def _rename_service(self, old_name: str):
        new_name, ok = QInputDialog.getText(
            self,
            "Rename service",
            f"Enter the new name for '{old_name}':",
            text=old_name,
        )
        new_name = new_name.strip().replace(" ", "-") if new_name else ""
        if ok and new_name and new_name != old_name:
            try:
                pgserviceparser.rename_service(old_name, new_name, self._conf_file_path)
            except PermissionError:
                self._permission_warning()
            except ServiceNotFound:
                self._service_not_found_warning(old_name)
                self._refresh_service_list()
            except ServiceFileNotFound:
                self._service_file_warning()
            else:
                self._refresh_service_list()
                items = self.lstServices.findItems(new_name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.lstServices.setCurrentItem(items[0])

    def _duplicate_and_edit_service(self, source_service_name: str):
        target_name, ok = QInputDialog.getText(self, "Duplicate service", "Enter a name for the copy:")
        target_name = target_name.strip().replace(" ", "-") if target_name else ""
        if ok and target_name:
            try:
                pgserviceparser.copy_service_settings(source_service_name, target_name, self._conf_file_path)
            except PermissionError:
                self._permission_warning()
            except ServiceNotFound:
                self._service_not_found_warning(source_service_name)
                self._refresh_service_list()
            except ServiceFileNotFound:
                self._service_file_warning()
            else:
                self._refresh_service_list()
                items = self.lstServices.findItems(target_name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.lstServices.setCurrentItem(items[0])

    # ------------------------------------------------------- Settings ops --

    @pyqtSlot(QItemSelection, QItemSelection)
    def _update_settings_buttons(self, selected, deselected):
        self.btnRemoveSetting.setEnabled(bool(selected.indexes()))

    @pyqtSlot()
    def _add_settings_clicked(self):
        if not self._edit_model:
            return

        used = self._edit_model.current_setting_keys()
        available = [k for k in SERVICE_SETTINGS if k not in used]
        if not available:
            return

        chosen, ok = QInputDialog.getItem(self, "Add setting", "Select a setting to add:", available, editable=False)
        if ok and chosen:
            default = SERVICE_SETTINGS[chosen].get("default", "")
            self._edit_model.add_settings({chosen: default})
            self._update_add_settings_button()

    @pyqtSlot()
    def _remove_setting_clicked(self):
        selected_indexes = self.tblServiceConfig.selectedIndexes()
        if not selected_indexes:
            return

        setting_key = self._edit_model.index_to_setting_key(selected_indexes[0])
        if (
            QMessageBox.question(
                self,
                "Remove service setting",
                f"Are you sure you want to remove the '{setting_key}' setting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self._edit_model.remove_setting(selected_indexes[0])
            self._update_add_settings_button()

    @pyqtSlot()
    def _copy_settings_clicked(self):
        selected_items = self.lstServices.selectedItems()
        if not selected_items or len(selected_items) != 1:
            return

        service_name = selected_items[0].text()
        settings_text = pgserviceparser.write_service_to_text(service_name, self._edit_model.service_config())
        QApplication.clipboard().setText(settings_text)

    @pyqtSlot()
    def _update_service_clicked(self):
        if self._edit_model and self._edit_model.is_dirty():
            invalid = self._edit_model.invalid_settings()
            if invalid:
                self._show_message(
                    f"Settings '{', '.join(invalid)}' have invalid values. Adjust them and try again.",
                    error=True,
                )
                return

            selected_items = self.lstServices.selectedItems()
            if not selected_items or len(selected_items) != 1:
                return

            target_service = selected_items[0].text()
            try:
                pgserviceparser.write_service(
                    target_service,
                    self._edit_model.service_config(),
                    self._conf_file_path,
                )
            except PermissionError:
                self._permission_warning()
            except ServiceFileNotFound:
                self._service_file_warning()
            except ServiceNotFound:
                self._service_not_found_warning(target_service)
                self._refresh_service_list()
            else:
                self._edit_model.set_not_dirty()

    # ---------------------------------------------------------------- Misc --

    def _permission_warning(self):
        self._show_message(
            "The service file is read-only and permissions could not be changed.",
            error=True,
        )

    def _service_file_warning(self):
        self._show_message(
            f"The service file '{self._conf_file_path}' could not be found. " "It may have been moved or deleted.",
            error=True,
        )

    def _service_not_found_warning(self, service_name: str):
        self._show_message(
            f"The service '{service_name}' no longer exists in the configuration file. "
            "The service list has been refreshed.",
            error=True,
        )

    def _show_message(self, text: str, error: bool = False):
        color = "#f8d7da" if error else "#d4edda"
        border = "#f5c6cb" if error else "#c3e6cb"
        self._message_bar.setStyleSheet(f"background-color: {color}; border: 1px solid {border}; border-radius: 4px;")
        self._lblMessage.setText(text)
        self._message_bar.setVisible(True)

    def _dismiss_message(self):
        self._message_bar.setVisible(False)
