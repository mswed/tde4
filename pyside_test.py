# 3DE4.script.name: Pyside Test
# 3DE4.script.version:  v1.0
# 3DE4.script.gui:  Main Window::Dev

from PySide import QtGui
from PySide import QtCore

import tde4


def _timer():
    QtCore.QCoreApplication.processEvents()


if not QtCore.QCoreApplication.instance():
    QtGui.QApplication([])
    tde4.setTimerCallbackFunction("_timer", 100)

test_window = QtGui.QWidget()
test_window.show()
