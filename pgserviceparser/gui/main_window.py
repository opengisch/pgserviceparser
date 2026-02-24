"""Main window for pgserviceparser GUI."""

from pgserviceparser.gui.compat import QtWidgets

QMainWindow = QtWidgets.QMainWindow

from pgserviceparser.gui.service_widget import ServiceWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PG Service Parser")
        self.setMinimumSize(600, 400)

        self._service_widget = ServiceWidget()
        self.setCentralWidget(self._service_widget)
