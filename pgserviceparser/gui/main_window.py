"""Main window for pgserviceparser GUI."""

from pgserviceparser.gui.compat import QtWidgets

QMainWindow = QtWidgets.QMainWindow

from pgserviceparser.gui.service_widget import PGServiceParserWidget


class _MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PG Service Parser")
        self.setMinimumSize(600, 400)

        self._service_widget = PGServiceParserWidget()
        self.setCentralWidget(self._service_widget)
