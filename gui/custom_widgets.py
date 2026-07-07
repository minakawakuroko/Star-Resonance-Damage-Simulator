import os, sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog, QGridLayout
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QPixmap, QLinearGradient, QBrush, QColor

def _get_app_dir():
    """返回应用程序根目录（开发时为项目根，打包后为 exe 所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_path(relative_path):
    """获取资源文件绝对路径，兼容开发与打包环境"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

GRADIENT_BUTTON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 white, stop:0.4 #b3d9ff, stop:0.6 #b3d9ff, stop:1 white);
        color: #222;
        border: 1px solid #99c2ff;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 13px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 white, stop:0.4 #99c2ff, stop:0.6 #99c2ff, stop:1 white);
    }
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #e6e6e6, stop:0.5 #80b3ff, stop:1 #e6e6e6);
    }
"""

def apply_gradient_style(widget):
    for btn in widget.findChildren(QPushButton):
        if "background: transparent" in (btn.styleSheet() or ""):
            continue
        btn.setStyleSheet(GRADIENT_BUTTON_STYLE)


class BackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None

    def setBackgroundImage(self, path: str):
        if path and os.path.exists(path):
            self._pixmap = QPixmap(path)
        else:
            self._pixmap = QPixmap()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        if self._pixmap and not self._pixmap.isNull():
            pix = self._pixmap.scaledToHeight(self.height(), Qt.SmoothTransformation)
            draw_width = min(pix.width(), self.width())
            painter.drawPixmap(0, 0, pix, 0, 0, draw_width, self.height())
            gradient = QLinearGradient(0, 0, draw_width, 0)
            gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
            gradient.setColorAt(1.0, QColor(255, 255, 255, 255))
            painter.fillRect(0, 0, draw_width, self.height(), QBrush(gradient))
        painter.end()


class FramelessDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = None

        # 最外层容器，用于提供圆角和阴影（白色背景）
        self.container = QWidget(self)
        self.container.setObjectName("dialogContainer")
        self.container.setStyleSheet("""
            #dialogContainer {
                background-color: white;
                border-radius: 12px;
            }
        """)
        self.container.setAttribute(Qt.WA_StyledBackground, True)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.container)

        # 容器内主布局
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 自定义标题栏
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 0, 0)
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("color: #333; font-weight: bold; font-size: 14px;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 25)
        close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #555; border: none; font-size: 16px; }
            QPushButton:hover { background: #e04343; color: white; }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        self.main_layout.addWidget(title_bar)

        # 内容区域（使用 QGridLayout 实现背景层叠）
        self.content_area = QWidget()
        self.content_area.setStyleSheet("background: transparent;")
        self.main_layout.addWidget(self.content_area, stretch=1)

        # 使用网格布局，将背景和内容放在同一单元格实现层叠
        grid = QGridLayout(self.content_area)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        # 背景图片层
        self.bg_widget = BackgroundWidget()
        self.bg_widget.setBackgroundImage(get_resource_path('gui/jpg/其他界面.jpg'))
        grid.addWidget(self.bg_widget, 0, 0)

        # 内容层（透明）
        self.inner_content = QWidget()
        self.inner_content.setStyleSheet("background: transparent;")
        grid.addWidget(self.inner_content, 0, 0)

        # 默认内容布局
        self.inner_layout = QVBoxLayout(self.inner_content)
        self.inner_layout.setContentsMargins(10, 10, 10, 10)

    def setTitle(self, title):
        self.title_label.setText(title)

    def getContentLayout(self):
        return self.inner_layout

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            if self.container.geometry().contains(pos):
                self._drag_pos = event.globalPosition().toPoint()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self._drag_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


class ConfirmDialog(FramelessDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.setTitle(title)
        self.resize(320, 120)
        layout = self.getContentLayout()
        lbl = QLabel(message)
        lbl.setStyleSheet("color: #333; font-size: 14px;")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        btn_layout = QHBoxLayout()
        yes_btn = QPushButton("是")
        no_btn = QPushButton("否")
        yes_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        no_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        btn_layout.addStretch()
        btn_layout.addWidget(yes_btn)
        btn_layout.addWidget(no_btn)
        layout.addLayout(btn_layout)
        yes_btn.clicked.connect(self.accept)
        no_btn.clicked.connect(self.reject)


class MessageDialog(FramelessDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.setTitle(title)
        self.resize(400, 200)
        # 更换背景为 报错.jpg
        self.bg_widget.setBackgroundImage(get_resource_path('gui/jpg/报错.jpg'))
        
        layout = self.getContentLayout()
        lbl = QLabel(message)
        lbl.setStyleSheet("color: #222; font-size: 16px; font-weight: bold; background: transparent;")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)