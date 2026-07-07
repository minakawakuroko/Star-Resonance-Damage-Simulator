import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget {
            background-color: #f0f0f0;
            color: #222;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: white;
            color: #222;
            border: 1px solid #aaa;
        }
        QPushButton {
            background-color: #e0e0e0;
            color: #222;
            border: 1px solid #aaa;
            border-radius: 4px;
            padding: 4px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        /* 垂直滚动条加宽50% → 18px */
        QScrollBar:vertical {
            width: 18px;
            background: #d0d0d0;
            border-radius: 9px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #a0a0a0;
            min-height: 40px;
            border-radius: 9px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        /* 水平滚动条加高50% → 18px */
        QScrollBar:horizontal {
            height: 18px;
            background: #d0d0d0;
            border-radius: 9px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #a0a0a0;
            min-width: 40px;
            border-radius: 9px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        QLabel {
            background: transparent;
            color: #222;
        }
        QCheckBox {
            color: #222;
        }
        QListWidget {
            background: white;
            color: #222;
        }
        QTabWidget::pane {
            background: white;
        }
        QTabBar::tab {
            background: #e0e0e0;
            color: #222;
        }
        QTabBar::tab:selected {
            background: white;
        }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()