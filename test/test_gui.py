#!/usr/bin/env python3

"""GUI unit tests.

Usage from the repo root folder:

    export PGSERVICEPARSER_SRC_DIR=$pwd
    python -m unittest test.test_gui

These tests use a temporary pg_service.conf copy so the real file is never
modified.  A QApplication is created once for the whole test session.
"""

import os
import shutil
import unittest
from pathlib import Path

from pgserviceparser.gui.compat import QtCore, QtWidgets

QApplication = QtWidgets.QApplication

# A single QApplication instance is required for the whole process.
_app = QApplication.instance() or QApplication([])

PGSERVICEPARSER_SRC_PATH = Path(os.environ["PGSERVICEPARSER_SRC_DIR"])


class _TempServiceFileMixin:
    """Mixin that copies the base service file to a temp location for each test."""

    def setUp(self):
        super().setUp()
        self._base = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "service_base.txt"
        self._conf = PGSERVICEPARSER_SRC_PATH / "test" / "data" / "pgservice_gui_test.conf"
        shutil.copy(self._base, self._conf)

    def tearDown(self):
        if self._conf.exists():
            self._conf.unlink()
        super().tearDown()


# ---------------------------------------------------------------------------
# ServiceConfigModel tests
# ---------------------------------------------------------------------------
class TestServiceConfigModel(unittest.TestCase):
    """Unit tests for the ServiceConfigModel (no service file needed)."""

    def _make_model(self, name="svc", config=None):
        from pgserviceparser.gui.setting_model import ServiceConfigModel

        if config is None:
            config = {"host": "localhost", "port": "5432", "dbname": "mydb"}
        return ServiceConfigModel(name, config)

    # -- basic properties --

    def test_row_and_column_count(self):
        m = self._make_model()
        self.assertEqual(m.rowCount(), 3)
        self.assertEqual(m.columnCount(), 2)

    def test_service_name(self):
        m = self._make_model(name="demo")
        self.assertEqual(m.service_name(), "demo")

    def test_service_config_returns_copy(self):
        cfg = {"host": "h"}
        m = self._make_model(config=cfg)
        out = m.service_config()
        self.assertEqual(out, cfg)
        out["host"] = "changed"
        self.assertEqual(m.service_config()["host"], "h")

    # -- dirty tracking --

    def test_not_dirty_initially(self):
        m = self._make_model()
        self.assertFalse(m.is_dirty())

    def test_setData_marks_dirty(self):
        m = self._make_model()
        idx = m.index(0, 1)  # value column of first row
        m.setData(idx, "new_value")
        self.assertTrue(m.is_dirty())

    def test_setData_same_value_not_dirty(self):
        m = self._make_model(config={"host": "localhost"})
        idx = m.index(0, 1)
        result = m.setData(idx, "localhost")
        self.assertFalse(result)
        self.assertFalse(m.is_dirty())

    def test_revert_clears_dirty(self):
        m = self._make_model(config={"host": "localhost"})
        idx = m.index(0, 1)
        m.setData(idx, "changed")
        self.assertTrue(m.is_dirty())
        m.setData(idx, "localhost")
        self.assertFalse(m.is_dirty())

    def test_set_not_dirty(self):
        m = self._make_model()
        idx = m.index(0, 1)
        m.setData(idx, "changed")
        self.assertTrue(m.is_dirty())
        m.set_not_dirty()
        self.assertFalse(m.is_dirty())

    # -- add / remove settings --

    def test_add_settings(self):
        m = self._make_model(config={"host": "h"})
        m.add_settings({"port": "5432"})
        self.assertEqual(m.rowCount(), 2)
        self.assertTrue(m.is_dirty())
        self.assertIn("port", m.current_setting_keys())

    def test_remove_setting(self):
        m = self._make_model(config={"host": "h", "port": "5432"})
        idx = m.index(0, 0)
        m.remove_setting(idx)
        self.assertEqual(m.rowCount(), 1)
        self.assertTrue(m.is_dirty())

    def test_remove_invalid_index(self):
        from pgserviceparser.gui.compat import QtCore

        m = self._make_model()
        m.remove_setting(QtCore.QModelIndex())  # should not raise
        self.assertEqual(m.rowCount(), 3)

    # -- data roles --

    def test_display_role_key(self):
        m = self._make_model(config={"host": "localhost"})
        idx = m.index(0, 0)
        self.assertEqual(m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole), "host")

    def test_display_role_value(self):
        m = self._make_model(config={"host": "localhost"})
        idx = m.index(0, 1)
        self.assertEqual(m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole), "localhost")

    def test_password_masked_in_display(self):
        m = self._make_model(config={"password": "secret"})
        idx = m.index(0, 1)
        display = m.data(idx, QtCore.Qt.ItemDataRole.DisplayRole)
        self.assertNotEqual(display, "secret")
        self.assertEqual(display, "************")

    def test_password_visible_in_edit_role(self):
        m = self._make_model(config={"password": "secret"})
        idx = m.index(0, 1)
        self.assertEqual(m.data(idx, QtCore.Qt.ItemDataRole.EditRole), "secret")

    def test_tooltip_on_known_key(self):
        m = self._make_model(config={"host": "localhost"})
        idx = m.index(0, 0)
        tooltip = m.data(idx, QtCore.Qt.ItemDataRole.ToolTipRole)
        self.assertIsNotNone(tooltip)

    def test_tooltip_on_unknown_key(self):
        m = self._make_model(config={"custom_key": "val"})
        idx = m.index(0, 0)
        tooltip = m.data(idx, QtCore.Qt.ItemDataRole.ToolTipRole)
        self.assertIsNone(tooltip)

    # -- flags --

    def test_key_column_not_editable(self):
        m = self._make_model()
        idx = m.index(0, 0)
        self.assertFalse(m.flags(idx) & QtCore.Qt.ItemFlag.ItemIsEditable)

    def test_value_column_editable(self):
        m = self._make_model()
        idx = m.index(0, 1)
        self.assertTrue(m.flags(idx) & QtCore.Qt.ItemFlag.ItemIsEditable)

    # -- invalid settings --

    def test_invalid_settings_empty_value(self):
        m = self._make_model(config={"host": "", "port": "5432"})
        self.assertEqual(m.invalid_settings(), ["host"])

    def test_invalid_settings_whitespace_only(self):
        m = self._make_model(config={"host": "   "})
        self.assertEqual(m.invalid_settings(), ["host"])

    def test_no_invalid_settings(self):
        m = self._make_model(config={"host": "localhost"})
        self.assertEqual(m.invalid_settings(), [])

    # -- index_to_setting_key --

    def test_index_to_setting_key(self):
        m = self._make_model(config={"host": "h", "port": "p"})
        self.assertEqual(m.index_to_setting_key(m.index(0, 0)), "host")
        self.assertEqual(m.index_to_setting_key(m.index(1, 0)), "port")

    # -- current_setting_keys --

    def test_current_setting_keys(self):
        m = self._make_model(config={"host": "h", "dbname": "d"})
        self.assertEqual(m.current_setting_keys(), ["host", "dbname"])

    # -- is_dirty_changed signal --

    def test_is_dirty_changed_signal(self):
        m = self._make_model(config={"host": "h"})
        received = []
        m.is_dirty_changed.connect(lambda v: received.append(v))
        m.setData(m.index(0, 1), "new")
        self.assertEqual(received, [True])


# ---------------------------------------------------------------------------
# ServiceWidget tests (integration with temp service file)
# ---------------------------------------------------------------------------
class TestServiceWidget(_TempServiceFileMixin, unittest.TestCase):
    """Integration tests for the ServiceWidget using a temp service file."""

    def _make_widget(self):
        from pgserviceparser.gui.service_widget import ServiceWidget

        return ServiceWidget(conf_file_path=self._conf)

    def test_loads_services(self):
        w = self._make_widget()
        count = w.lstServices.count()
        self.assertGreater(count, 0)

    def test_service_names_match(self):
        import pgserviceparser

        w = self._make_widget()
        expected = pgserviceparser.service_names(self._conf, sorted_alphabetically=True)
        actual = [w.lstServices.item(i).text() for i in range(w.lstServices.count())]
        self.assertEqual(actual, expected)

    def test_select_service_populates_table(self):
        w = self._make_widget()
        w.lstServices.setCurrentRow(0)
        _app.processEvents()
        self.assertIsNotNone(w.tblServiceConfig.model())
        self.assertGreater(w.tblServiceConfig.model().rowCount(), 0)

    def test_edit_panel_disabled_initially(self):
        w = self._make_widget()
        self.assertFalse(w.editRightPanel.isEnabled())

    def test_edit_panel_enabled_on_selection(self):
        w = self._make_widget()
        w.lstServices.setCurrentRow(0)
        _app.processEvents()
        self.assertTrue(w.editRightPanel.isEnabled())

    def test_remove_button_disabled_no_selection(self):
        w = self._make_widget()
        self.assertFalse(w.btnRemoveService.isEnabled())

    def test_remove_button_enabled_on_selection(self):
        w = self._make_widget()
        w.lstServices.setCurrentRow(0)
        _app.processEvents()
        self.assertTrue(w.btnRemoveService.isEnabled())

    def test_missing_conf_file(self):
        from pgserviceparser.gui.service_widget import ServiceWidget

        w = ServiceWidget(conf_file_path=Path("/tmp/nonexistent_pgservice.conf"))
        self.assertFalse(w._content_widget.isEnabled())

    def test_message_bar_hidden_initially(self):
        w = self._make_widget()
        self.assertFalse(w._message_bar.isVisible())

    def test_show_and_dismiss_message(self):
        w = self._make_widget()
        w.show()
        w._show_message("Test error", error=True)
        self.assertTrue(w._message_bar.isVisible())
        self.assertIn("Test error", w._lblMessage.text())

        w._dismiss_message()
        self.assertFalse(w._message_bar.isVisible())

    def test_update_button_disabled_initially(self):
        w = self._make_widget()
        self.assertFalse(w.btnUpdateService.isEnabled())

    def test_conf_file_path_displayed(self):
        w = self._make_widget()
        self.assertEqual(w.txtConfFile.text(), str(self._conf))


if __name__ == "__main__":
    unittest.main()
