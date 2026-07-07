import os, json, shutil, sys
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QTextEdit, QDialog, QDialogButtonBox, QMessageBox,
    QFileDialog, QFrame, QGridLayout, QCheckBox, QListWidget,
    QListWidgetItem, QSizePolicy, QAbstractItemView,
    QApplication, QSizeGrip, QComboBox, QSplitter, QTableWidget,
    QTableWidgetItem, QHeaderView, QButtonGroup
)
from PySide6.QtCore import Qt, QPoint, QSize, QRect, QEvent, QTimer, Signal
from PySide6.QtGui import (
    QFont, QColor, QCursor, QPainter, QPixmap, QLinearGradient, QBrush, QPalette, QIcon
)
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import matplotlib.pyplot as plt

import os, json, shutil, sys, gc
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False

from gui.skill_editor import SkillEditor
from gui.buff_editor import BuffEditor
from panel_builder import build_panel, load_panel_inputs, save_panel_inputs
from jisuan import calc_damage_from_entity
from models import GameEntity
from data_manager import load_skills, load_buffs, load_panel, save_panel
from buffed import buffed
from evaluator import eval_expr, resolve_target
from copy import deepcopy
from gui.custom_widgets import (
    FramelessDialog, GRADIENT_BUTTON_STYLE, apply_gradient_style,
    _get_app_dir, BackgroundWidget, ConfirmDialog, MessageDialog, get_resource_path
)


# ==================== 辅助函数 ====================
def _add_str_formula(target_str: str, add_str: str) -> str:
    if add_str == "0":
        return target_str
    if target_str == "0":
        return add_str
    return f"({target_str}) + ({add_str})"

def merge_skill_into_panel(panel: GameEntity, skill: GameEntity) -> GameEntity:
    merged = deepcopy(panel)
    for field in GameEntity.__dataclass_fields__:
        if field in ('编号', '名称', '类别', 'buffci', '输入参数', '输出参数'):
            continue
        if field in ('元素增伤', '全能增伤'):
            continue
        skill_val = getattr(skill, field)
        if isinstance(skill_val, str) and skill_val != "0":
            if field == '伤害类型':
                # 伤害类型直接覆盖，不做拼接
                setattr(merged, field, skill_val)
                continue
            original = getattr(merged, field)
            setattr(merged, field, _add_str_formula(original, skill_val))
    return merged

def safe_int_or_formula(val, context=None):
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        val = val.strip()
        if val == '':
            return 1
        try:
            return int(val)
        except:
            if context is not None:
                try:
                    result = eval_expr(val, context)
                    return int(result)
                except:
                    pass
            return 1
    return 1

def entity_to_context(entity: GameEntity) -> dict:
    ctx = {}
    for f in GameEntity.__dataclass_fields__:
        if f in ('编号', '名称', '类别', '伤害类型', 'buffci', '输入参数', '输出参数'):
            continue
        val = getattr(entity, f)
        if isinstance(val, str):
            try:
                ctx[f] = float(val)
            except:
                ctx[f] = 0.0
        else:
            ctx[f] = float(val) if isinstance(val, (int, float)) else 0.0
    return ctx


# ==================== 边缘缩放抓手 ====================
class CustomGrip(QWidget):
    def __init__(self, parent, position):
        super().__init__(parent)
        self.parent = parent
        self.position = position
        self.setCursor(self._cursor_for(position))
        self.setStyleSheet("background: transparent;")
        self.updateGeometry()

    def _cursor_for(self, pos):
        if pos in (Qt.TopEdge, Qt.BottomEdge):
            return QCursor(Qt.SizeVerCursor)
        return QCursor(Qt.SizeHorCursor)

    def updateGeometry(self):
        pw, ph = self.parent.width(), self.parent.height()
        if self.position == Qt.TopEdge:
            self.setGeometry(0, 0, pw, 10)
        elif self.position == Qt.BottomEdge:
            self.setGeometry(0, ph - 10, pw, 10)
        elif self.position == Qt.LeftEdge:
            self.setGeometry(0, 10, 10, ph - 20)
        elif self.position == Qt.RightEdge:
            self.setGeometry(pw - 10, 10, 10, ph - 20)

    def mouseMoveEvent(self, event):
        delta = event.pos()
        if self.position == Qt.TopEdge:
            new_h = max(self.parent.minimumHeight(), self.parent.height() - delta.y())
            geo = self.parent.geometry()
            geo.setTop(geo.bottom() - new_h)
            self.parent.setGeometry(geo)
        elif self.position == Qt.BottomEdge:
            new_h = max(self.parent.minimumHeight(), self.parent.height() + delta.y())
            self.parent.resize(self.parent.width(), new_h)
        elif self.position == Qt.LeftEdge:
            new_w = max(self.parent.minimumWidth(), self.parent.width() - delta.x())
            geo = self.parent.geometry()
            geo.setLeft(geo.right() - new_w)
            self.parent.setGeometry(geo)
        elif self.position == Qt.RightEdge:
            new_w = max(self.parent.minimumWidth(), self.parent.width() + delta.x())
            self.parent.resize(new_w, self.parent.height())

    def resizeEvent(self, event):
        self.updateGeometry()
        super().resizeEvent(event)


# ==================== 自定义标题栏 ====================
class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(35)
        self.parent = parent
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        self.title_label = QLabel("DPS 计算器")
        self.title_label.setStyleSheet("color: #333; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)
        layout.addStretch()

        self.btn_min = QPushButton("─")
        self.btn_min.setFixedSize(30, 25)
        self.btn_min.setStyleSheet("QPushButton { background: transparent; color: #555; border: none; font-size: 16px; } QPushButton:hover { background: #ddd; }")
        self.btn_min.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.btn_min)

        self.btn_max = QPushButton("□")
        self.btn_max.setFixedSize(30, 25)
        self.btn_max.setStyleSheet("QPushButton { background: transparent; color: #555; border: none; font-size: 16px; } QPushButton:hover { background: #ddd; }")
        self.btn_max.clicked.connect(self.maximize_restore)
        layout.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 25)
        self.btn_close.setStyleSheet("QPushButton { background: transparent; color: #555; border: none; font-size: 16px; } QPushButton:hover { background: #e04343; color: white; }")
        self.btn_close.clicked.connect(self.parent.close)
        layout.addWidget(self.btn_close)

    def maximize_restore(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.btn_max.setText("□")
        else:
            self.parent.showMaximized()
            self.btn_max.setText("❐")


# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(400, 300)

        icon_path = get_resource_path('gui/jpg/封面.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.bg_widget = BackgroundWidget()
        self.setCentralWidget(self.bg_widget)

        main_layout = QVBoxLayout(self.bg_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: rgba(255,255,255,180); border-radius: 8px; }
            QTabBar::tab {
                background: rgba(255,255,255,150); color: #333;
                padding: 8px 16px; border-top-left-radius: 8px; border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: white; }
        """)
        main_layout.addWidget(self.tabs)

        self.calc_tab = CalcWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.calc_tab)
        self.tabs.addTab(scroll, "计算")

        self.skill_tab = SkillEditor()
        self.tabs.addTab(self.skill_tab, "技能管理")

        self.buff_tab = BuffEditor()
        self.tabs.addTab(self.buff_tab, "Buff 管理")

        self.tabs.currentChanged.connect(self.update_background_for_tab)
        self.update_background_for_tab(0)

        self.grips = []
        for pos in (Qt.TopEdge, Qt.BottomEdge, Qt.LeftEdge, Qt.RightEdge):
            grip = CustomGrip(self, pos)
            self.grips.append(grip)

        self._drag_pos = None

    def update_background_for_tab(self, index):
        if index == 0:
            bg_file = get_resource_path('gui/jpg/其他界面.jpg')
        elif index == 1:
            bg_file = get_resource_path('gui/jpg/技能.jpg')
        elif index == 2:
            bg_file = get_resource_path('gui/jpg/buff.jpg')
        else:
            bg_file = ""
        self.bg_widget.setBackgroundImage(bg_file)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            child = self.childAt(pos)
            if child is self.bg_widget or child is self.title_bar or isinstance(child, QLabel):
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

    def resizeEvent(self, event):
        for grip in self.grips:
            grip.updateGeometry()
        super().resizeEvent(event)


# ==================== 计算主界面 ====================
class CalcWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.modules_dir = os.path.join(_get_app_dir(), 'modules')
        os.makedirs(self.modules_dir, exist_ok=True)
        self.current_module = None
        self.cached_panel = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: transparent;")
        self.auto_history = [0.0] * 7
        self.full_result_text = ""
        self.skill_damage_data = {}
        self.segment_names = []
        self.merged_skill_map = {}
        self.init_ui()
        self.load_saved_panel_to_inputs()
        self.refresh_modules()
        apply_gradient_style(self)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ---- 面板属性区 ----
        panel_bg_path = get_resource_path('gui/jpg/面板.jpg').replace('\\', '/')
        panel_frame = QFrame()
        panel_frame.setStyleSheet(f"QFrame {{ background-image: url({panel_bg_path}); border-radius: 10px; padding: 10px; }}")
        panel_grid = QGridLayout(panel_frame)
        panel_grid.setHorizontalSpacing(12)
        panel_grid.setVerticalSpacing(8)

        self.panel_inputs = {}
        fields = [
            "站街主属性", "装备主属性百分比(%)", "天赋来源主属性百分比(%)", "幻想主属性百分比(%)", "其他主属性百分比(%)",
            "转化系数",
            "武器固定攻击力", "模组固定攻击力", "其他固定攻击力",
            "装备攻击力百分比(%)", "天赋攻击力百分比(%)", "其他攻击力百分比(%)",
            "精炼攻击力",
            "本元素攻击力", "全元素攻击力",
            "本元素攻击力百分比(%)", "全元素攻击力百分比(%)",
            "暴击固定值", "急速固定值", "幸运固定值", "精通固定值", "全能固定值",
            "一般增伤(%)",
            "本元素增伤(%)", "全元素增伤(%)",
            "敌人物理防御", "敌人法术防御", "防御系数常数",
            "爆伤(%)",
            "百分比穿防(%)", "固定穿防"
        ]
        defaults = {
            "站街主属性": "5000",
            "装备主属性百分比(%)": "100", "天赋来源主属性百分比(%)": "0", "幻想主属性百分比(%)": "0", "其他主属性百分比(%)": "0",
            "转化系数": "0.5",
            "武器固定攻击力": "1000", "模组固定攻击力": "0", "其他固定攻击力": "0",
            "装备攻击力百分比(%)": "50", "天赋攻击力百分比(%)": "0", "其他攻击力百分比(%)": "0",
            "精炼攻击力": "1000",
            "本元素攻击力": "500", "全元素攻击力": "0",
            "本元素攻击力百分比(%)": "0", "全元素攻击力百分比(%)": "0",
            "暴击固定值": "50000", "急速固定值": "50000", "幸运固定值": "50000", "精通固定值": "50000", "全能固定值": "28000",
            "一般增伤(%)": "10",
            "本元素增伤(%)": "0", "全元素增伤(%)": "0",
            "敌人物理防御": "9945", "敌人法术防御": "2018", "防御系数常数": "23205",
            "爆伤(%)": "60",
            "百分比穿防(%)": "0", "固定穿防": "0"
        }
        cols = 5
        for i, field in enumerate(fields):
            row = i // cols
            col = (i % cols) * 2
            label = QLabel(field)
            label.setStyleSheet("color: #333; font-size: 11px; background: transparent;")
            le = QLineEdit()
            le.setFixedWidth(80)
            le.setStyleSheet("QLineEdit { background: white; color: #222; border: 1px solid #ccc; border-radius: 4px; padding: 2px; }")
            panel_grid.addWidget(label, row, col)
            panel_grid.addWidget(le, row, col + 1)
            self.panel_inputs[field] = le

        save_panel_btn = QPushButton("保存面板")
        save_panel_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        save_panel_btn.clicked.connect(self.save_panel)

        total_rows = (len(fields) + cols - 1) // cols
        panel_grid.addWidget(save_panel_btn, total_rows, 0, 1, -1, Qt.AlignCenter)
        main_layout.addWidget(panel_frame)

        # ---- 模组卡片区域 ----
        mod_bg_path = get_resource_path('gui/jpg/模组.jpg').replace('\\', '/')
        mod_frame = QFrame()
        mod_frame.setStyleSheet(f"QFrame {{ background-image: url({mod_bg_path}); border-radius: 12px; }}")
        mod_layout = QVBoxLayout(mod_frame)
        mod_layout.setContentsMargins(12, 12, 12, 12)

        title_row = QHBoxLayout()
        title = QLabel("输出模组")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; background: transparent;")
        title_row.addWidget(title)
        title_row.addStretch()
        self.new_mod_btn = QPushButton("新建模组")
        self.edit_mod_btn = QPushButton("编辑模组")
        self.import_mod_btn = QPushButton("导入模组")
        self.export_mod_btn = QPushButton("导出模组")
        self.delete_mod_btn = QPushButton("删除模组")
        for btn in [self.new_mod_btn, self.edit_mod_btn, self.import_mod_btn, self.export_mod_btn, self.delete_mod_btn]:
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
            title_row.addWidget(btn)
        mod_layout.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #aaa;")
        mod_layout.addWidget(sep)

        self.card_scroll = QScrollArea()
        self.card_scroll.setWidgetResizable(True)
        self.card_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.card_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.card_scroll.setFixedHeight(150)
        self.card_container = QWidget()
        self.card_layout = QHBoxLayout(self.card_container)
        self.card_layout.setAlignment(Qt.AlignLeft)
        self.card_layout.setSpacing(12)
        self.card_layout.setContentsMargins(8, 8, 8, 8)
        self.card_scroll.setWidget(self.card_container)
        mod_layout.addWidget(self.card_scroll)
        main_layout.addWidget(mod_frame)

        # ---- 计算与结果 ----
        bottom = QHBoxLayout()
        self.calc_btn = QPushButton("计算选中模组")
        self.calc_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        self.calc_btn.setFixedHeight(36)
        self.calc_btn.clicked.connect(self.calculate_selected)
        bottom.addWidget(self.calc_btn)
        self.detail_btn = QPushButton("显示详情")
        self.detail_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        self.detail_btn.clicked.connect(self.show_detail_dialog)
        self.detail_btn.setEnabled(False)
        bottom.addWidget(self.detail_btn)
        bottom.addStretch()
        main_layout.addLayout(bottom)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedHeight(60)
        main_layout.addWidget(self.result_text)

        self.setup_manual_table(main_layout)
        self.setup_auto_table(main_layout)

        # ---- 占比分析区域 ----
        self.dmg_tabs = QButtonGroup(self)
        self.dmg_tabs.setExclusive(True)
        self.tab_container = QWidget()
        self.tab_layout = QHBoxLayout(self.tab_container)
        self.tab_layout.setSpacing(0)
        self.tab_layout.setContentsMargins(0, 0, 0, 0)

        self.total_tab_btn = QPushButton("模组")
        self.total_tab_btn.setCheckable(True)
        self.total_tab_btn.setChecked(True)
        self.total_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #d0d0d0; color: #333; border-top-left-radius: 6px; border-top-right-radius: 6px;
                padding: 6px 16px; font-weight: bold;
            }
            QPushButton:checked {
                background-color: white; border-bottom-left-radius: 0; border-bottom-right-radius: 0;
                border: 1px solid #ccc; border-bottom: none;
            }
        """)
        self.tab_layout.addWidget(self.total_tab_btn)
        self.dmg_tabs.addButton(self.total_tab_btn, 0)
        self.total_tab_btn.clicked.connect(lambda: self.update_damage_table_and_chart("total"))

        self.seg_tab_buttons = []

        self.tab_layout.addStretch()
        main_layout.addWidget(self.tab_container)

        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.dmg_table = QTableWidget()
        self.dmg_table.setColumnCount(8)  # 增加到8列
        self.dmg_table.setHorizontalHeaderLabels(
            ["技能名", "合并前技能名", "合并前总伤", "总伤", "占比", "总hit数", "均伤", "合并"])
        self.dmg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dmg_table.verticalHeader().setVisible(False)
        self.dmg_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dmg_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dmg_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.dmg_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dmg_table.horizontalHeader().setVisible(True)
        self.dmg_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                color: #333;
                background: #f0f0f0;
                font-weight: bold;
                padding: 12px 6px;
                border: 1px solid #ddd;
            }
        """)
        self.dmg_table.horizontalHeader().setFixedHeight(52)
        self.dmg_table.setShowGrid(True)
        self.dmg_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                border: 1px solid #ccc;
                font-size: 13px;
            }
            QTableWidget::item {
                border: 1px solid #ddd;
                padding: 6px;
            }
        """)
        self.dmg_table.cellDoubleClicked.connect(self.on_skill_name_double_click)
        content_layout.addWidget(self.dmg_table, stretch=2)

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: white;")
        self.canvas.setFixedSize(500, 400)
        content_layout.addWidget(self.canvas, stretch=0)

        main_layout.addWidget(content_widget)

        btn_layout = QHBoxLayout()
        self.merge_btn = QPushButton("合并选中技能")
        self.merge_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        self.merge_btn.clicked.connect(self.merge_selected_skills)
        btn_layout.addStretch()
        btn_layout.addWidget(self.merge_btn)
        main_layout.addLayout(btn_layout)

        self.dmg_table.setMinimumHeight(300)

        self.new_mod_btn.clicked.connect(self.on_new_module)
        self.edit_mod_btn.clicked.connect(self.on_edit_module)
        self.import_mod_btn.clicked.connect(self.on_import_module)
        self.export_mod_btn.clicked.connect(self.on_export_module)
        self.delete_mod_btn.clicked.connect(self.on_delete_module)
        # 内存清理定时器（每30秒执行一次）
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_memory)
        self.cleanup_timer.start(30000)

    # ========== 手动对比表格设置 ==========
    def setup_manual_table(self, parent_layout):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: rgba(255,255,255,180); border-radius: 8px; padding: 8px; }")
        layout = QVBoxLayout(frame)
        mode_layout = QHBoxLayout()
        self.dps_check = QCheckBox("DPS形式")
        self.total_check = QCheckBox("总伤形式")
        self.dps_check.toggled.connect(lambda: self.total_check.setChecked(False) if self.dps_check.isChecked() else None)
        self.total_check.toggled.connect(lambda: self.dps_check.setChecked(False) if self.total_check.isChecked() else None)
        self.dps_check.setChecked(True)
        mode_layout.addWidget(self.dps_check)
        mode_layout.addWidget(self.total_check)
        layout.addLayout(mode_layout)

        headers = ["当前伤害", "伤害1", "伤害2", "伤害3", "伤害4", "伤害5", "伤害6"]
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        self.manual_headers = []
        for j, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet("font-weight: bold; color: #333;")
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, j + 1)
            self.manual_headers.append(lbl)
        self.manual_inputs = []
        for j in range(7):
            le = QLineEdit()
            le.setAlignment(Qt.AlignCenter)
            le.setStyleSheet("QLineEdit { border: 1px solid #aaa; border-radius: 4px; padding: 2px; background: white; }")
            if j == 0:
                le.setReadOnly(True)
            grid.addWidget(le, 1, j + 1)
            self.manual_inputs.append(le)
        self.manual_num1 = []
        for j in range(7):
            lbl = QLabel("--")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #555; background: transparent; font-size: 12px;")
            grid.addWidget(lbl, 2, j + 1)
            self.manual_num1.append(lbl)
        self.manual_num2 = []
        for j in range(7):
            lbl = QLabel("--")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #555; background: transparent; font-size: 12px;")
            grid.addWidget(lbl, 3, j + 1)
            self.manual_num2.append(lbl)
        layout.addLayout(grid)
        parent_layout.addWidget(frame)

    # ========== 自动计算表格设置 ==========
    def setup_auto_table(self, parent_layout):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: rgba(255,255,255,180); border-radius: 8px; padding: 8px; }")
        layout = QVBoxLayout(frame)
        title_lbl = QLabel("自动计算")
        title_lbl.setStyleSheet("font-weight: bold; color: #333; font-size: 14px;")
        layout.addWidget(title_lbl)
        headers = ["当前伤害", "伤害1", "伤害2", "伤害3", "伤害4", "伤害5", "伤害6"]
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        for j, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet("font-weight: bold; color: #333;")
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, j + 1)
        self.auto_inputs = []
        for j in range(7):
            le = QLineEdit()
            le.setAlignment(Qt.AlignCenter)
            le.setReadOnly(True)
            le.setStyleSheet("QLineEdit { border: 1px solid #aaa; border-radius: 4px; padding: 2px; background: #f0f0f0; }")
            grid.addWidget(le, 1, j + 1)
            self.auto_inputs.append(le)
        self.auto_num1 = []
        for j in range(7):
            lbl = QLabel("--")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #555; background: transparent; font-size: 12px;")
            grid.addWidget(lbl, 2, j + 1)
            self.auto_num1.append(lbl)
        self.auto_num2 = []
        for j in range(7):
            lbl = QLabel("--")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #555; background: transparent; font-size: 12px;")
            grid.addWidget(lbl, 3, j + 1)
            self.auto_num2.append(lbl)
        layout.addLayout(grid)
        parent_layout.addWidget(frame)

    def get_current_mode(self):
        return "dps" if self.dps_check.isChecked() else "total"

    def update_manual_table(self, current_value):
        self.manual_inputs[0].setText(f"{current_value:.2f}")
        manual_values = []
        for i in range(1, 7):
            try:
                val = float(self.manual_inputs[i].text())
            except:
                val = 0.0
            manual_values.append(val)
        for i in range(6):
            if current_value != 0:
                pct = (manual_values[i] / current_value) * 100
                self.manual_num1[i+1].setText(f"{pct:.2f}%")
            else:
                self.manual_num1[i+1].setText("--")
        self.manual_num1[0].setText("100.00%")
        if current_value != 0:
            self.manual_num2[0].setText("100.00%")
            for i in range(6):
                prev = current_value if i == 0 else manual_values[i-1]
                if prev != 0:
                    ratio = (manual_values[i] / prev) * 100
                    self.manual_num2[i+1].setText(f"{ratio:.2f}%")
                else:
                    self.manual_num2[i+1].setText("--")
        else:
            for lbl in self.manual_num2:
                lbl.setText("--")

    def update_auto_table(self, current_value):
        self.auto_history = [current_value] + self.auto_history[:6]
        for i in range(7):
            self.auto_inputs[i].setText(f"{self.auto_history[i]:.2f}")
        base = self.auto_history[0] if self.auto_history[0] != 0 else 1
        for i in range(7):
            if base != 0:
                pct = (self.auto_history[i] / base) * 100
                self.auto_num1[i].setText(f"{pct:.2f}%")
            else:
                self.auto_num1[i].setText("--")
        for i in range(7):
            if i == 0:
                self.auto_num2[i].setText("100.00%")
            else:
                prev = self.auto_history[i-1]
                curr = self.auto_history[i]
                if prev != 0:
                    ratio = (curr / prev) * 100
                    self.auto_num2[i].setText(f"{ratio:.2f}%")
                else:
                    self.auto_num2[i].setText("--")

    def load_saved_panel_to_inputs(self):
        from panel_builder import load_panel_inputs
        saved = load_panel_inputs()
        if saved:
            for field, le in self.panel_inputs.items():
                if field in saved:
                    le.setText(saved[field])

    def save_panel(self):
        try:
            vals = {f: le.text() for f, le in self.panel_inputs.items()}
            from panel_builder import save_panel_inputs
            save_panel_inputs(vals)
            panel = build_panel(
                站街主属性=vals["站街主属性"],
                装备主属性百分比=vals["装备主属性百分比(%)"],
                天赋来源主属性百分比=vals["天赋来源主属性百分比(%)"],
                幻想主属性百分比=vals["幻想主属性百分比(%)"],
                其他主属性百分比=vals["其他主属性百分比(%)"],
                转化系数=vals["转化系数"],
                武器固定攻击力=vals["武器固定攻击力"],
                模组固定攻击力=vals["模组固定攻击力"],
                其他固定攻击力=vals["其他固定攻击力"],
                装备攻击力百分比=vals["装备攻击力百分比(%)"],
                天赋攻击力百分比=vals["天赋攻击力百分比(%)"],
                其他攻击力百分比=vals["其他攻击力百分比(%)"],
                精炼攻击力=vals["精炼攻击力"],
                本元素攻击力=vals["本元素攻击力"],
                全元素攻击力=vals["全元素攻击力"],
                本元素攻击力百分比=vals["本元素攻击力百分比(%)"],
                全元素攻击力百分比=vals["全元素攻击力百分比(%)"],
                暴击固定值=vals["暴击固定值"],
                急速固定值=vals["急速固定值"],
                幸运固定值=vals["幸运固定值"],
                精通固定值=vals["精通固定值"],
                全能固定值=vals["全能固定值"],
                一般增伤=vals["一般增伤(%)"],
                本元素增伤=vals["本元素增伤(%)"],
                全元素增伤=vals["全元素增伤(%)"],
                敌人物理防御=vals["敌人物理防御"],
                敌人法术防御=vals["敌人法术防御"],
                防御系数常数=vals["防御系数常数"],
                爆伤=vals["爆伤(%)"],
                百分比穿防=vals["百分比穿防(%)"],
                固定穿防=vals["固定穿防"]
            )
            from data_manager import save_panel
            save_panel(panel)
            self.cached_panel = panel
            MessageDialog(self, "成功", "面板已保存并应用").exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"面板保存失败: {e}")

    def get_panel_def(self) -> GameEntity:
        if self.cached_panel:
            return self.cached_panel
        from data_manager import load_panel
        panel = load_panel()
        if panel:
            self.cached_panel = panel
            return panel
        vals = {f: le.text() for f, le in self.panel_inputs.items()}
        panel = build_panel(
            站街主属性=vals["站街主属性"],
            装备主属性百分比=vals["装备主属性百分比(%)"],
            天赋来源主属性百分比=vals["天赋来源主属性百分比(%)"],
            幻想主属性百分比=vals["幻想主属性百分比(%)"],
            其他主属性百分比=vals["其他主属性百分比(%)"],
            转化系数=vals["转化系数"],
            武器固定攻击力=vals["武器固定攻击力"],
            模组固定攻击力=vals["模组固定攻击力"],
            其他固定攻击力=vals["其他固定攻击力"],
            装备攻击力百分比=vals["装备攻击力百分比(%)"],
            天赋攻击力百分比=vals["天赋攻击力百分比(%)"],
            其他攻击力百分比=vals["其他攻击力百分比(%)"],
            精炼攻击力=vals["精炼攻击力"],
            本元素攻击力=vals["本元素攻击力"],
            全元素攻击力=vals["全元素攻击力"],
            本元素攻击力百分比=vals["本元素攻击力百分比(%)"],
            全元素攻击力百分比=vals["全元素攻击力百分比(%)"],
            暴击固定值=vals["暴击固定值"],
            急速固定值=vals["急速固定值"],
            幸运固定值=vals["幸运固定值"],
            精通固定值=vals["精通固定值"],
            全能固定值=vals["全能固定值"],
            一般增伤=vals["一般增伤(%)"],
            本元素增伤=vals["本元素增伤(%)"],
            全元素增伤=vals["全元素增伤(%)"],
            敌人物理防御=vals["敌人物理防御"],
            敌人法术防御=vals["敌人法术防御"],
            防御系数常数=vals["防御系数常数"],
            爆伤=vals["爆伤(%)"],
            百分比穿防=vals["百分比穿防(%)"],
            固定穿防=vals["固定穿防"]
        )
        from data_manager import save_panel
        save_panel(panel)
        self.cached_panel = panel
        return panel

    def refresh_modules(self):
        for i in reversed(range(self.card_layout.count())):
            w = self.card_layout.itemAt(i).widget()
            if w: w.deleteLater()
        files = [f for f in os.listdir(self.modules_dir) if f.endswith('.json')]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(self.modules_dir, f)), reverse=True)
        for fname in files:
            self.card_layout.addWidget(self.create_module_card(fname[:-5]))

    def create_module_card(self, mod_name):
        total_duration = 0.0
        note_text = ""
        path = os.path.join(self.modules_dir, f"{mod_name}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                mod_data = json.load(f)
            note_text = mod_data.get('note', '')
            segs = mod_data.get('segments', [])
            plan = mod_data.get('execution_plan', {})
            for seg in segs:
                seg_name = seg.get('name', '')
                repeat = plan.get(seg_name, 1)
                total_duration += seg.get('duration', 0) * repeat

        card = QFrame()
        card.setObjectName("modCard")
        card.setFixedSize(170, 120)
        default_style = "#modCard { background-color: white; border: 1px solid #b3d9ff; border-radius: 10px; }"
        card.setStyleSheet(default_style)
        card.setProperty("default_style", default_style)
        card.setProperty("multi_selected", False)   # 多选状态
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        name_lbl = QLabel(mod_name)
        name_lbl.setFont(QFont("", 13, QFont.Bold))
        name_lbl.setStyleSheet("color: #333; background: transparent;")
        name_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_lbl)
        note_edit = QLineEdit()
        note_edit.setPlaceholderText("备注...")
        note_edit.setText(note_text)
        note_edit.setReadOnly(True)
        note_edit.setStyleSheet("QLineEdit { background: white; border: 1px solid #ccc; border-radius: 6px; padding: 4px; color: #333; }")
        layout.addWidget(note_edit)
        time_lbl = QLabel(f"总时长: {total_duration:.0f}s")
        time_lbl.setStyleSheet("color: #666; background: transparent;")
        time_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(time_lbl)

        def select(e, n=mod_name):
            ctrl_held = QApplication.keyboardModifiers() == Qt.ControlModifier
            if ctrl_held:
                # 切换当前卡片的多选状态
                is_selected = card.property("multi_selected")
                if is_selected:
                    card.setStyleSheet(card.property("default_style"))
                    card.setProperty("multi_selected", False)
                else:
                    card.setStyleSheet("#modCard { background-color: white; border: 3px solid #ffcc00; border-radius: 10px; }")
                    card.setProperty("multi_selected", True)
            else:
                # 清除所有卡片的多选，恢复默认样式
                for i in range(self.card_layout.count()):
                    c = self.card_layout.itemAt(i).widget()
                    if c:
                        c.setStyleSheet(c.property("default_style"))
                        c.setProperty("multi_selected", False)
                # 单选当前卡片
                self.current_module = n
                card.setStyleSheet("#modCard { background-color: white; border: 2px solid #88f; border-radius: 10px; }")
        card.mousePressEvent = select
        return card

    def on_new_module(self):
        dialog = ModuleSegmentEditor(self, panel_getter=self.get_panel_def)
        if dialog.exec() == QDialog.Accepted:
            self._save_module_final(dialog.segments, dialog.exec_plan)

    def on_edit_module(self):
        if not self.current_module:
            MessageDialog(self, "提示", "请先选中一个模组").exec()
            return
        path = os.path.join(self.modules_dir, f"{self.current_module}.json")
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        dialog = ModuleSegmentEditor(self, data.get('segments', []), data.get('execution_plan', {}), panel_getter=self.get_panel_def)
        if dialog.exec() == QDialog.Accepted:
            self._save_module_final(dialog.segments, dialog.exec_plan, self.current_module)

    def _save_module_final(self, segments, exec_plan, old_name=None):
        dlg = ModuleNameDialog(self, old_name)
        if dlg.exec() == QDialog.Accepted:
            name = dlg.name_edit.text().strip()
            note = dlg.note_edit.toPlainText().strip()
            module = {"name": name, "segments": segments, "execution_plan": exec_plan, "note": note}
            if old_name and old_name != name:
                os.remove(os.path.join(self.modules_dir, f"{old_name}.json"))
            with open(os.path.join(self.modules_dir, f"{name}.json"), 'w', encoding='utf-8') as f:
                json.dump(module, f, ensure_ascii=False, indent=2)
            self.refresh_modules()

    def on_import_module(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "导入模组", "", "JSON Files (*.json)")
        if file_paths:
            for file_path in file_paths:
                base_name = os.path.basename(file_path)
                dest = os.path.join(self.modules_dir, base_name)
                # 如果重名，自动加序号
                if os.path.exists(dest):
                    name, ext = os.path.splitext(base_name)
                    counter = 1
                    while True:
                        new_name = f"{name} ({counter}){ext}"
                        new_dest = os.path.join(self.modules_dir, new_name)
                        if not os.path.exists(new_dest):
                            dest = new_dest
                            break
                        counter += 1
                shutil.copy2(file_path, dest)
            self.refresh_modules()

    def on_export_module(self):
        # 收集多选的卡片
        selected_cards = []
        for i in range(self.card_layout.count()):
            card = self.card_layout.itemAt(i).widget()
            if card and card.property("multi_selected") == True:
                selected_cards.append(card)
        if len(selected_cards) >= 2:
            # 批量导出
            folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
            if folder:
                for card in selected_cards:
                    name_lbl = card.findChild(QLabel)
                    if name_lbl:
                        mod_name = name_lbl.text()
                        src = os.path.join(self.modules_dir, f"{mod_name}.json")
                        if os.path.exists(src):
                            shutil.copy2(src, os.path.join(folder, f"{mod_name}.json"))
            return
        if not self.current_module:
            # 检查是否有选中的卡片（可能是单选）
            single_card = None
            for i in range(self.card_layout.count()):
                card = self.card_layout.itemAt(i).widget()
                if card and card.property("default_style") is not None and "border: 2px solid #88f" in card.styleSheet():
                    single_card = card
                    break
            if single_card:
                name_lbl = single_card.findChild(QLabel)
                if name_lbl:
                    self.current_module = name_lbl.text()
            else:
                dlg = MessageDialog(self, "提示", "按住ctrl选定导出")
                dlg.exec()
                return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出模组", f"{self.current_module}.json", "JSON Files (*.json)")
        if file_path:
            src = os.path.join(self.modules_dir, f"{self.current_module}.json")
            if os.path.exists(src):
                shutil.copy2(src, file_path)

    def on_delete_module(self):
        if not self.current_module:
            MessageDialog(self, "提示", "请先选中一个模组").exec()
            return
        dlg = ConfirmDialog(self, "确认删除", f"确定删除模组 {self.current_module} 吗？")
        if dlg.exec() == QDialog.Accepted:
            path = os.path.join(self.modules_dir, f"{self.current_module}.json")
            if os.path.exists(path): os.remove(path)
            self.current_module = None
            self.refresh_modules()

    # ========== 占比分析 ==========
    def refresh_damage_analysis(self, skill_damage_data, seg_names):
        self.skill_damage_data = skill_damage_data
        self.segment_names = seg_names
        self.merged_skill_map.clear()

        for btn in self.seg_tab_buttons:
            self.dmg_tabs.removeButton(btn)
            btn.deleteLater()
        self.seg_tab_buttons.clear()

        for name in seg_names:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #d0d0d0; color: #333; border-top-left-radius: 6px; border-top-right-radius: 6px;
                    padding: 6px 16px; font-weight: bold;
                }
                QPushButton:checked {
                    background-color: white; border-bottom-left-radius: 0; border-bottom-right-radius: 0;
                    border: 1px solid #ccc; border-bottom: none;
                }
            """)
            self.seg_tab_buttons.append(btn)
            self.tab_layout.insertWidget(self.tab_layout.count() - 1, btn)
            self.dmg_tabs.addButton(btn, len(self.seg_tab_buttons))
            btn.clicked.connect(lambda checked, n=name: self.update_damage_table_and_chart(n))

        if self.current_module:
            self.total_tab_btn.setText(self.current_module)
        else:
            self.total_tab_btn.setText("模组")

        self.total_tab_btn.setChecked(True)
        self.update_damage_table_and_chart("total")

    def update_damage_table_and_chart(self, mode):
        data = self.skill_damage_data.get(mode, [])
        if not data:
            self.dmg_table.setRowCount(0)
            return

        self.dmg_table.clearContents()
        self.dmg_table.setRowCount(0)
        self.merged_skill_map.clear()

        data.sort(key=lambda x: x['total'], reverse=True)

        self.dmg_table.setRowCount(len(data))
        total_all = sum(item['total'] for item in data)

        for i, item in enumerate(data):
            self.dmg_table.setItem(i, 0, QTableWidgetItem(item['name']))
            self.dmg_table.setItem(i, 1, QTableWidgetItem(""))
            self.dmg_table.setItem(i, 2, QTableWidgetItem(""))
            self.dmg_table.setItem(i, 3, QTableWidgetItem(f"{item['total']:.2f}"))
            pct = (item['total'] / total_all * 100) if total_all > 0 else 0
            self.dmg_table.setItem(i, 4, QTableWidgetItem(f"{pct:.2f}%"))
            self.dmg_table.setItem(i, 5, QTableWidgetItem(f"{item.get('hits', 0):.2f}"))
            self.dmg_table.setItem(i, 6, QTableWidgetItem(f"{item.get('avg', 0):.2f}"))
            chk = QCheckBox()
            chk.setFixedSize(24, 24)
            chk.setStyleSheet("""
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    background: white;
                    border: 2px solid #999;
                    border-radius: 3px;
                }
                QCheckBox::indicator:checked {
                    background: #66b2ff;
                    border: 2px solid #3380cc;
                }
            """)
            self.dmg_table.setCellWidget(i, 7, chk)   # 合并列索引改为7

        self.update_chart_from_table_data(data)

    def update_chart_from_table_data(self, data):
        labels = [item['name'] for item in data]
        values = [item['total'] for item in data]
        total_all = sum(values)
        if total_all == 0:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        other_val = 0
        new_labels = []
        new_values = []
        for i, v in enumerate(values):
            pct = (v / total_all * 100)
            if pct < 10:
                other_val += v
                if "其他" not in new_labels:
                    new_labels.append("其他")
                    new_values.append(other_val)
                else:
                    idx = new_labels.index("其他")
                    new_values[idx] += v
            else:
                new_labels.append(labels[i])
                new_values.append(v)

        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6', '#c2f0c2']
        wedges, texts, autotexts = ax.pie(
            new_values, labels=None, autopct='%1.1f%%',
            startangle=90, colors=colors[:len(new_labels)],
            pctdistance=0.85, radius=1.2
        )
        bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
        kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")
        for i, wedge in enumerate(wedges):
            ang = (wedge.theta2 - wedge.theta1)/2. + wedge.theta1
            y = np.sin(np.deg2rad(ang))
            x = np.cos(np.deg2rad(ang))
            horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
            connectionstyle = f"angle,angleA=0,angleB={ang}"
            kw["arrowprops"].update({"connectionstyle": connectionstyle})
            ax.annotate(
                f"{new_labels[i]}\n({new_values[i]/total_all*100:.1f}%)",
                xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                horizontalalignment=horizontalalignment, **kw
            )
        ax.axis('equal')
        self.canvas.draw()

    def merge_selected_skills(self):
        selected_rows = []
        for row in range(self.dmg_table.rowCount()):
            widget = self.dmg_table.cellWidget(row, 7)   # 合并列索引改为7
            if widget and isinstance(widget, QCheckBox) and widget.isChecked():
                selected_rows.append(row)
        if len(selected_rows) < 2:
            MessageDialog(self, "提示", "请至少勾选两个技能进行合并").exec()
            return

        # 先清除已存在的合并
        for merged_row, merged_rows in list(self.merged_skill_map.items()):
            self.unmerge_skills(merged_row, merged_rows)

        selected_rows.sort()
        first = selected_rows[0]
        others = selected_rows[1:]

        # 获取原始数据
        orig_names = []
        orig_totals = []
        orig_hits = []
        for r in range(self.dmg_table.rowCount()):
            name_item = self.dmg_table.item(r, 0)
            total_item = self.dmg_table.item(r, 3)
            hits_item = self.dmg_table.item(r, 5)
            orig_names.append(name_item.text() if name_item else "")
            orig_totals.append(float(total_item.text().replace(',', '')) if total_item else 0.0)
            orig_hits.append(float(hits_item.text().replace(',', '')) if hits_item else 0.0)

        # 计算合并后的数据
        merged_name = f"{orig_names[first]}+{'+'.join(orig_names[o] for o in others)}"
        merged_total = orig_totals[first] + sum(orig_totals[o] for o in others)
        merged_hits = orig_hits[first] + sum(orig_hits[o] for o in others)
        merged_avg = merged_total / merged_hits if merged_hits > 0 else 0

        # 重新排列行顺序（合并组放在一起）
        new_order = []
        added = set()
        for r in range(self.dmg_table.rowCount()):
            if r == first:
                new_order.append(r)
                added.add(r)
                for o in others:
                    new_order.append(o)
                    added.add(o)
            elif r not in added:
                new_order.append(r)

        # 保存行数据（8列）
        row_data = []
        for r in new_order:
            row_items = []
            for c in range(8):
                item = self.dmg_table.item(r, c)
                row_items.append(item.text() if item else "")
            row_data.append(row_items)

        # 重新构建表格
        self.dmg_table.clearContents()
        self.dmg_table.setRowCount(len(new_order))
        for i, r in enumerate(new_order):
            for c in range(8):
                self.dmg_table.setItem(i, c, QTableWidgetItem(row_data[i][c]))
            # 设置复选框
            if i == 0:   # 仅在第一行放置复选框？后续会重新设置
                pass
        # 更新复选框位置：合并后的主行放解除按钮，被合并行不放复选框
        for i in range(self.dmg_table.rowCount()):
            chk = QCheckBox()
            chk.setFixedSize(24, 24)
            chk.setStyleSheet("""
                QCheckBox::indicator {
                    width: 18px; height: 18px;
                    background: white; border: 2px solid #999; border-radius: 3px;
                }
                QCheckBox::indicator:checked {
                    background: #66b2ff; border: 2px solid #3380cc;
                }
            """)
            self.dmg_table.setCellWidget(i, 7, chk)

        main_pos = new_order.index(first)
        other_positions = [new_order.index(o) for o in others]

        # 更新合并主行数据
        self.dmg_table.item(main_pos, 0).setText(merged_name)
        self.dmg_table.item(main_pos, 1).setText(orig_names[first])
        self.dmg_table.item(main_pos, 2).setText(f"{orig_totals[first]:.2f}")
        self.dmg_table.item(main_pos, 3).setText(f"{merged_total:.2f}")
        self.dmg_table.item(main_pos, 5).setText(f"{merged_hits:.2f}")
        self.dmg_table.item(main_pos, 6).setText(f"{merged_avg:.2f}")

        # 被合并的行清空显示
        for o, pos in zip(others, other_positions):
            self.dmg_table.item(pos, 0).setText("")
            self.dmg_table.item(pos, 1).setText(orig_names[o])
            self.dmg_table.item(pos, 2).setText(f"{orig_totals[o]:.2f}")
            self.dmg_table.item(pos, 3).setText("")
            self.dmg_table.item(pos, 4).setText("")
            self.dmg_table.item(pos, 5).setText("")
            self.dmg_table.item(pos, 6).setText("")

        # 重新计算占比
        total_all = 0.0
        for r in range(self.dmg_table.rowCount()):
            total_str = self.dmg_table.item(r, 3).text()
            if total_str:
                try:
                    total_all += float(total_str.replace(',', ''))
                except:
                    pass
        for r in range(self.dmg_table.rowCount()):
            total_str = self.dmg_table.item(r, 3).text()
            if total_str:
                try:
                    val = float(total_str.replace(',', ''))
                    pct = (val / total_all * 100) if total_all > 0 else 0
                    self.dmg_table.item(r, 4).setText(f"{pct:.2f}%")
                except:
                    self.dmg_table.item(r, 4).setText("")
            else:
                self.dmg_table.item(r, 4).setText("")

        # 替换合并主行的复选框为“解除”按钮
        old_widget = self.dmg_table.cellWidget(main_pos, 7)
        if old_widget:
            self.dmg_table.removeCellWidget(main_pos, 7)
        unmerge_btn = QPushButton("解除")
        unmerge_btn.setStyleSheet("""
            QPushButton {
                background: white; color: #333; border: 1px solid #aaa; border-radius: 4px;
                padding: 2px; font-size: 12px;
            }
        """)
        unmerge_btn.clicked.connect(lambda: self.unmerge_skills(main_pos, [first] + others))
        self.dmg_table.setCellWidget(main_pos, 7, unmerge_btn)

        self.merged_skill_map[main_pos] = [first] + others
        self.update_chart_from_visible_rows()

    def unmerge_skills(self, merged_row, original_rows):
        current_mode = None
        for btn in self.dmg_tabs.buttons():
            if btn.isChecked():
                if btn == self.total_tab_btn:
                    current_mode = "total"
                else:
                    current_mode = btn.text()
                break
        if current_mode:
            self.merged_skill_map.pop(merged_row, None)
            self.update_damage_table_and_chart(current_mode)

    def update_chart_from_visible_rows(self):
        labels = []
        values = []
        for row in range(self.dmg_table.rowCount()):
            name_item = self.dmg_table.item(row, 0)
            total_item = self.dmg_table.item(row, 3)
            if name_item and total_item:
                try:
                    val = float(total_item.text().replace(',', ''))
                    if val > 0:
                        labels.append(name_item.text().split('\n')[0])
                        values.append(val)
                except:
                    pass
        total_all = sum(values)
        if total_all == 0:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        other_val = 0
        new_labels = []
        new_values = []
        for i, v in enumerate(values):
            pct = (v / total_all * 100)
            if pct < 10:
                other_val += v
                if "其他" not in new_labels:
                    new_labels.append("其他")
                    new_values.append(other_val)
                else:
                    idx = new_labels.index("其他")
                    new_values[idx] += v
            else:
                new_labels.append(labels[i])
                new_values.append(v)

        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6', '#c2f0c2']
        wedges, texts, autotexts = ax.pie(
            new_values, labels=None, autopct='%1.1f%%',
            startangle=90, colors=colors[:len(new_labels)],
            pctdistance=0.85
        )
        bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
        kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")
        for i, wedge in enumerate(wedges):
            ang = (wedge.theta2 - wedge.theta1)/2. + wedge.theta1
            y = np.sin(np.deg2rad(ang))
            x = np.cos(np.deg2rad(ang))
            horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
            connectionstyle = f"angle,angleA=0,angleB={ang}"
            kw["arrowprops"].update({"connectionstyle": connectionstyle})
            ax.annotate(
                f"{new_labels[i]}\n({new_values[i]/total_all*100:.1f}%)",
                xy=(x, y), xytext=(1.35*np.sign(x), 1.4*y),
                horizontalalignment=horizontalalignment, **kw
            )
        ax.axis('equal')
        self.canvas.draw()

    def on_skill_name_double_click(self, row, col):
        if col == 0:
            item = self.dmg_table.item(row, 0)
            if item:
                self.dmg_table.editItem(item)

    # ---------- 核心计算 ----------
    def calculate_selected(self):
        if not self.current_module:
            MessageDialog(self, "警告", "请先选中一个模组").exec()
            return
        try:
            base_panel = self.get_panel_def()
        except:
            MessageDialog(self, "警告", "面板数据不完整").exec()
            return
        path = os.path.join(self.modules_dir, f"{self.current_module}.json")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                mod_data = json.load(f)
        except:
            QMessageBox.critical(None, "错误", "模组文件损坏")
            return

        segs = mod_data.get('segments', [])
        plan = mod_data.get('execution_plan', {})

        lines = []
        total_time = 0.0
        total_dmg = 0.0
        total_lucky_hits = 0
        total_all_hits = 0
        total_lucky_triggers = 0.0

        lines.append("===== 模组计算详情 =====")
        lines.append(f"模组名称: {self.current_module}")
        lines.append(f"段落数量: {len(segs)}")
        lines.append("")

        buffs_list = load_buffs()
        global_params = {}
        skill_damage_data = {}
        segment_names = []
        total_skill_damage_map = {}

        lines.append("========== 预计算阶段 ==========")
        pre_params = {}
        for seg_idx, seg in enumerate(segs):
            seg_name = seg.get('name', f'段{seg_idx+1}')
            segment_names.append(seg_name)
            seg_panel = deepcopy(base_panel)
            for bid in seg.get('global_buffs', []):
                b = next((x for x in buffs_list if x.编号 == bid), None)
                if b:
                    buffed(b, seg_panel)

            resolved_seg = resolve_target(seg_panel, {})
            seg_ctx = entity_to_context(resolved_seg)
            seg_ctx.update(pre_params)

            for skill_entry in seg.get('skills', []):
                skill_id = skill_entry.get('skill_id')
                base_skill = next((s for s in load_skills() if s.编号 == skill_id), None)
                if not base_skill:
                    continue

                final_skill = merge_skill_into_panel(seg_panel, base_skill)
                for bid in skill_entry.get('buffs_on', []):
                    b = next((x for x in buffs_list if x.编号 == bid), None)
                    if b:
                        buffed(b, final_skill)

                resolved_final = resolve_target(final_skill, seg_ctx)

                skill_ctx = {}
                skill_ctx.update(seg_ctx)
                skill_ctx.update(entity_to_context(resolved_final))
                skill_ctx.update(pre_params)

                raw_count = skill_entry.get('count', 1)
                try:
                    count = int(raw_count)
                except:
                    try:
                        count = int(eval_expr(str(raw_count), skill_ctx))
                    except:
                        count = 1
                hit_num = safe_int_or_formula(resolved_final.hit数)
                skill_total_hits = hit_num * count

                skill_ctx["hit数"] = hit_num
                skill_ctx["hit_num"] = hit_num
                skill_ctx["触发次数"] = count
                skill_ctx["count"] = count
                skill_ctx["总hit"] = skill_total_hits
                skill_ctx["skill_total_hits"] = skill_total_hits

                if base_skill.是否幸运 == "1":
                    lucky_rate = min(resolved_final.幸运, 100.0) / 100.0
                    skill_lucky_trigger = skill_total_hits * lucky_rate
                else:
                    skill_lucky_trigger = 0.0
                skill_ctx["触发幸运数"] = skill_lucky_trigger
                skill_ctx["skill_lucky_trigger"] = skill_lucky_trigger

                if base_skill.输出参数:
                    try:
                        output_params = json.loads(base_skill.输出参数)
                    except:
                        output_params = []
                    for out in output_params:
                        name = out.get("name", "")
                        formula = out.get("formula", "")
                        if name and formula:
                            try:
                                val = eval_expr(formula, skill_ctx)
                                pre_params[name] = val
                                skill_ctx[name] = val
                            except:
                                pass

        global_params = dict(pre_params)
        if global_params:
            lines.append("预计算参数列表:")
            for k, v in global_params.items():
                lines.append(f"  {k} = {v}")
        lines.append("==============================\n")

        lines.append("========== 真实计算阶段 ==========")
        for seg_idx, seg in enumerate(segs):
            seg_name = seg.get('name', f'段{seg_idx + 1}')
            repeat = plan.get(seg_name, 1)
            seg_duration = seg.get('duration', 0) * repeat
            total_time += seg_duration

            lines.append(f"--- 段落 {seg_idx + 1}: {seg_name} ×{repeat} (总时长: {seg_duration:.0f}s) ---")

            lines.append("【基础面板（来自主界面）】")
            lines.extend(self._format_entity_lines(base_panel))

            seg_panel = deepcopy(base_panel)
            for bid in seg.get('global_buffs', []):
                b = next((x for x in buffs_list if x.编号 == bid), None)
                if b:
                    lines.append(f"【全局 Buff: {b.名称}】")
                    lines.extend(self._format_entity_lines(b))
                    buffed(b, seg_panel)
            lines.append("【应用全局 Buff 后的段落面板】")
            lines.extend(self._format_entity_lines(seg_panel))

            resolved_seg = resolve_target(seg_panel, global_params)
            seg_ctx = entity_to_context(resolved_seg)
            seg_ctx.update(global_params)

            seg_total = 0.0
            seg_lucky_hits = 0
            seg_all_hits = 0
            seg_lucky_triggers = 0.0
            seg_skill_damages = []

            for sk_idx, skill_entry in enumerate(seg.get('skills', [])):
                skill_id = skill_entry.get('skill_id')
                base_skill = next((s for s in load_skills() if s.编号 == skill_id), None)
                if not base_skill:
                    continue

                lines.append(f"\n技能{sk_idx + 1}: {base_skill.名称}")
                lines.append("【技能原始面板】")
                lines.extend(self._format_entity_lines(base_skill))

                merged_before_buffs = merge_skill_into_panel(seg_panel, base_skill)
                lines.append("【继承段落面板后（未加技能 Buff）】")
                lines.extend(self._format_entity_lines(merged_before_buffs))

                final_skill = deepcopy(merged_before_buffs)
                for bid in skill_entry.get('buffs_on', []):
                    b = next((x for x in buffs_list if x.编号 == bid), None)
                    if b:
                        lines.append(f"【技能专属 Buff: {b.名称}】")
                        lines.extend(self._format_entity_lines(b))
                        buffed(b, final_skill)

                resolved_final = resolve_target(final_skill, seg_ctx)
                lines.append("【最终技能面板（含所有 Buff）】")
                lines.extend(self._format_entity_lines(resolved_final))

                skill_ctx = {}
                skill_ctx.update(seg_ctx)
                skill_ctx.update(entity_to_context(resolved_final))
                skill_ctx.update(global_params)

                is_lucky_attack = int(base_skill.是否是幸运一击) if base_skill.是否是幸运一击 else 0
                is_lucky_flag = int(base_skill.是否幸运) if base_skill.是否幸运 else 1
                hit_num = safe_int_or_formula(resolved_final.hit数)

                raw_count = skill_entry.get('count', 1)
                if is_lucky_attack == 1:
                    count = max(1.0, seg_lucky_triggers)
                else:
                    try:
                        count = int(raw_count)
                    except:
                        try:
                            count = int(eval_expr(str(raw_count), skill_ctx))
                        except:
                            count = 1

                skill_total_hits = hit_num * count
                seg_all_hits += skill_total_hits
                total_all_hits += skill_total_hits

                if is_lucky_flag == 1:
                    seg_lucky_hits += skill_total_hits
                    total_lucky_hits += skill_total_hits
                    lucky_rate = min(resolved_final.幸运, 100.0) / 100.0
                    skill_lucky_trigger = skill_total_hits * lucky_rate
                    seg_lucky_triggers += skill_lucky_trigger
                    total_lucky_triggers += skill_lucky_trigger

                skill_ctx["hit数"] = hit_num
                skill_ctx["hit_num"] = hit_num
                skill_ctx["触发次数"] = count
                skill_ctx["count"] = count
                skill_ctx["总hit"] = skill_total_hits
                skill_ctx["skill_total_hits"] = skill_total_hits
                skill_ctx["触发幸运数"] = skill_lucky_trigger if is_lucky_flag == 1 else 0.0
                skill_ctx["skill_lucky_trigger"] = skill_lucky_trigger if is_lucky_flag == 1 else 0.0

                if base_skill.输出参数:
                    try:
                        output_params = json.loads(base_skill.输出参数)
                    except:
                        output_params = []
                    for out in output_params:
                        name = out.get("name", "")
                        formula = out.get("formula", "")
                        if name and formula:
                            try:
                                val = eval_expr(formula, skill_ctx)
                                global_params[name] = val
                                skill_ctx[name] = val
                            except:
                                pass

                if is_lucky_attack == 1:
                    count = max(1.0, seg_lucky_triggers)
                    skill_ctx["触发次数"] = count
                    skill_ctx["count"] = count
                    skill_total_hits = hit_num * count
                    skill_total_hits = round(skill_total_hits, 2)
                    skill_ctx["总hit"] = skill_total_hits
                    skill_ctx["skill_total_hits"] = skill_total_hits

                if is_lucky_flag == 1:
                    lines.append(
                        f"  技能{sk_idx + 1}: {base_skill.名称} ×{count:.2f} (hit数: {hit_num:.2f}, 总hit: {skill_total_hits:.2f})")
                    lines.append(
                        f"    技能暴击率: {resolved_final.暴击:.2f}%, 技能幸运率: {resolved_final.幸运:.2f}%, 触发幸运数: {skill_lucky_trigger:.2f}")
                else:
                    lines.append(
                        f"  技能{sk_idx + 1}: {base_skill.名称} ×{count} (hit数: {hit_num}, 总hit: {skill_total_hits})")
                    lines.append(f"    技能暴击率: {resolved_final.暴击:.2f}%")

                if is_lucky_attack == 1:
                    lines.append(f"    【幸运一击】触发次数={count:.2f}")

                dmg, formula_details = calc_damage_from_entity(final_skill, extra_context=skill_ctx)
                total_skill_dmg = dmg * count
                total_skill_dmg_repeated = total_skill_dmg * repeat
                seg_total += total_skill_dmg_repeated
                lines.append(
                    f"    单次伤害={dmg:.2f} 总伤={total_skill_dmg:.2f} (含段落次数{repeat}后={total_skill_dmg_repeated:.2f})")

                skill_name = base_skill.名称
                # 计算该技能的总hit数和均伤（考虑段落重复次数）
                skill_hits_total = skill_total_hits * repeat
                avg_damage = total_skill_dmg_repeated / skill_hits_total if skill_hits_total > 0 else 0

                seg_skill_damages.append({
                    'name': skill_name,
                    'total': total_skill_dmg_repeated,
                    'segment': seg_name,
                    'hits': skill_hits_total,
                    'avg': avg_damage
                })
                if skill_name not in total_skill_damage_map:
                    total_skill_damage_map[skill_name] = {'total': 0, 'hits': 0}
                total_skill_damage_map[skill_name]['total'] += total_skill_dmg_repeated
                total_skill_damage_map[skill_name]['hits'] += skill_hits_total

                if base_skill.输入参数:
                    try:
                        input_params = json.loads(base_skill.输入参数)
                    except:
                        input_params = []
                    if input_params:
                        lines.append(f"    输入参数:")
                        for inp in input_params:
                            name = inp.get("name", "")
                            val = global_params.get(name, "N/A")
                            lines.append(f"      {name} = {val}")
                if base_skill.输出参数:
                    try:
                        output_params = json.loads(base_skill.输出参数)
                    except:
                        output_params = []
                    if output_params:
                        lines.append(f"    输出参数:")
                        for out in output_params:
                            name = out.get("name", "")
                            val = global_params.get(name, "N/A")
                            lines.append(f"      {name} = {val}")

                if formula_details:
                    lines.extend(formula_details)

            lines.append(f"  段落总伤: {seg_total:.2f}")
            if seg_duration > 0:
                lines.append(f"  段落DPS: {seg_total / seg_duration:.2f}")
            lines.append(
                f"  段落总hit数: {seg_all_hits:.2f}, 可幸运hit数: {seg_lucky_hits:.2f}, 幸运触发次数: {seg_lucky_triggers:.2f}")
            total_dmg += seg_total
            lines.append("")

            skill_damage_data[seg_name] = seg_skill_damages

        total_data = []
        for k, v in total_skill_damage_map.items():
            total_hits = v['hits']
            total_avg = v['total'] / total_hits if total_hits > 0 else 0
            total_data.append({
                'name': k,
                'total': v['total'],
                'hits': total_hits,
                'avg': total_avg
            })
        skill_damage_data["total"] = total_data

        summary = f"总伤: {total_dmg:.2f}  |  DPS: {total_dmg / total_time:.2f}" if total_time > 0 else f"总伤: {total_dmg:.2f}"
        lines.insert(0, summary)
        lines.insert(0,
                     f"模组总hit数: {total_all_hits:.2f}, 总可幸运hit数: {total_lucky_hits:.2f}, 总幸运触发次数: {total_lucky_triggers:.2f}")
        lines.insert(0, "=======================")

        self.full_result_text = '\n'.join(lines)
        simple_lines = lines[:3] if len(lines) >= 3 else lines
        self.result_text.setText('\n'.join(simple_lines))
        self.detail_btn.setEnabled(True)

        mode = self.get_current_mode()
        current_val = (total_dmg / total_time if total_time > 0 else 0) if mode == "dps" else total_dmg
        self.update_manual_table(current_val)
        self.update_auto_table(current_val)

        self.refresh_damage_analysis(skill_damage_data, segment_names)

    def show_detail_dialog(self):
        if not self.full_result_text: return
        dialog = FramelessDialog(self)
        dialog.setTitle("计算详情")
        dialog.resize(700, 500)
        layout = dialog.getContentLayout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(self.full_result_text)
        layout.addWidget(text_edit)
        dialog.exec()

    def _format_entity_lines(self, entity: GameEntity) -> list:
        from evaluator import resolve_target
        try:
            res = resolve_target(entity, {})
        except:
            res = entity
        fields_to_show = [
            "固定主属性", "百分比主属性", "转化系数", "额外固定攻击力", "额外百分比攻击力",
            "精炼攻击力", "本元素攻击力", "全元素攻击力", "暴击固定值", "急速固定值",
            "幸运固定值", "精通固定值", "全能固定值", "敌人物理防御", "敌人法术防御",
            "防御系数常数", "百分比穿防", "固定穿防", "暴击", "急速", "幸运", "精通", "全能",
            "爆伤", "一般增伤", "本元素增伤", "全元素增伤", "元素增伤", "赛季增伤", "最终增伤",
            "技能倍率", "技能固定值", "hit数", "是否幸运", "是否是幸运一击", "伤害类型",
            "绿值主属性", "绿值攻击力", "雷印"
        ]
        lines_list = []
        for i in range(0, len(fields_to_show), 4):
            group = fields_to_show[i:i+4]
            line_parts = []
            for f in group:
                val = getattr(res, f, "N/A")
                if isinstance(val, float):
                    val = f"{val:.2f}"
                line_parts.append(f"{f}={val}")
            lines_list.append("    " + " | ".join(line_parts))
        return lines_list

    def _cleanup_memory(self):
        """定期清理内存"""
        gc.collect()


# ==================== 模组段落编辑器 ====================
class ModuleSegmentEditor(FramelessDialog):
    def __init__(self, parent, segments=None, exec_plan=None, panel_getter=None):
        super().__init__(parent)
        self.setTitle("编辑模组段落")
        self.resize(700, 500)
        self.segments = segments.copy() if segments else []
        self.exec_plan = exec_plan.copy() if exec_plan else {}
        self.panel_getter = panel_getter
        self._reopen_idx = None
        self.init_ui()

    def init_ui(self):
        layout = self.getContentLayout()
        btn_row = QHBoxLayout()
        add_btn = QPushButton("添加段落")
        edit_btn = QPushButton("修改段落")
        del_btn = QPushButton("删除段落")
        import_seg_btn = QPushButton("导入段落")
        export_seg_btn = QPushButton("导出段落")
        for btn in [add_btn, edit_btn, del_btn, import_seg_btn, export_seg_btn]:
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #aaa;")
        layout.addWidget(sep)
        self.seg_list = QListWidget()
        self.seg_list.setStyleSheet("""
            QListWidget { background: white; border: 1px solid #ccc; border-radius: 10px; font-size: 15px; padding: 6px; }
            QListWidget::item { border: 1px solid #ddd; border-radius: 8px; padding: 8px; margin: 4px; }
            QListWidget::item:selected { background: #cce5ff; color: #222; }
        """)
        self.seg_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.seg_list.setDragDropMode(QAbstractItemView.InternalMove)   # 拖拽排序
        self.seg_list.setDefaultDropAction(Qt.MoveAction)
        self.seg_list.model().rowsMoved.connect(self._on_seg_order_changed)
        layout.addWidget(self.seg_list)
        self._refresh_seg_list()
        save_btn = QPushButton("保存并命名模组")
        save_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)
        add_btn.clicked.connect(self._add_segment)
        edit_btn.clicked.connect(self._edit_segment)
        del_btn.clicked.connect(self._delete_segment)
        import_seg_btn.clicked.connect(self._import_segment)
        export_seg_btn.clicked.connect(self._export_segment)

        if self._reopen_idx is not None:
            QTimer.singleShot(0, self._reopen_segment)

    def _refresh_seg_list(self):
        self.seg_list.clear()
        for seg in self.segments:
            seg_name = seg.get('name', '?')
            repeat = self.exec_plan.get(seg_name, 1)
            item = QListWidgetItem(f"{seg_name}      | 触发次数: {repeat}")
            item.setData(Qt.UserRole, seg)   # 存储段落对象
            self.seg_list.addItem(item)

    def _on_seg_order_changed(self):
        new_segs = []
        for i in range(self.seg_list.count()):
            item = self.seg_list.item(i)
            new_segs.append(item.data(Qt.UserRole))
        self.segments = new_segs

    def _add_segment(self):
        dlg = SegmentEditor(self, panel_getter=self.panel_getter)
        if dlg.exec() == QDialog.Accepted:
            self.segments.append(dlg.segment)
            self.exec_plan[dlg.segment['name']] = dlg.repeat_count
            self._refresh_seg_list()

    def _edit_segment(self):
        item = self.seg_list.currentItem()
        if not item:
            MessageDialog(self, "警告", "请先选择一个段落").exec()
            return
        seg = item.data(Qt.UserRole)
        idx = self.segments.index(seg)   # 需要找到索引（用于后续替换）
        dlg = SegmentEditor(self, seg, panel_getter=self.panel_getter)
        if dlg.exec() == QDialog.Accepted:
            self.segments[idx] = dlg.segment
            self.exec_plan[dlg.segment['name']] = dlg.repeat_count
            self._refresh_seg_list()
            if getattr(dlg, '_needs_reopen', False):
                self._reopen_idx = idx
                self.accept()

    def _delete_segment(self):
        selected_items = self.seg_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            seg = item.data(Qt.UserRole)
            self.segments.remove(seg)
        self._refresh_seg_list()

    def _import_segment(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "导入段落", "", "JSON Files (*.json)")
        if not file_paths:
            return
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                imported_segs = data if isinstance(data, list) else [data]
                for seg in imported_segs:
                    if isinstance(seg, dict) and 'name' in seg and 'skills' in seg:
                        self.segments.append(seg)
                        self.exec_plan[seg.get('name', '?')] = seg.get('repeat', 1)
            except:
                QMessageBox.warning(self, "错误", f"无法读取文件: {file_path}")
        self._refresh_seg_list()

    def _export_segment(self):
        selected_items = self.seg_list.selectedItems()
        if not selected_items:
            item = self.seg_list.currentItem()
            if not item:
                MessageDialog(self, "提示", "按住ctrl选定导出").exec()
                return
            selected_items = [item]

        segments_to_export = []
        for item in selected_items:
            seg = item.data(Qt.UserRole)
            seg_copy = seg.copy()
            seg_copy['repeat'] = self.exec_plan.get(seg_copy.get('name', ''), 1)
            segments_to_export.append(seg_copy)

        if len(segments_to_export) == 1:
            file_path, _ = QFileDialog.getSaveFileName(self, "导出段落", f"{segments_to_export[0].get('name', 'segment')}.json", "JSON Files (*.json)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(segments_to_export[0], f, ensure_ascii=False, indent=2)
        else:
            folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
            if folder:
                for seg in segments_to_export:
                    file_path = os.path.join(folder, f"{seg.get('name', 'segment')}.json")
                    if os.path.exists(file_path):
                        base_name = seg.get('name', 'segment')
                        counter = 1
                        while True:
                            new_name = f"{base_name} ({counter}).json"
                            file_path = os.path.join(folder, new_name)
                            if not os.path.exists(file_path):
                                break
                            counter += 1
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(seg, f, ensure_ascii=False, indent=2)

    def _on_save(self):
        if not self.segments:
            MessageDialog(self, "警告", "至少需要一个段落").exec()
            return
        self.accept()


# ==================== 段落编辑器 ====================
# ==================== 段落编辑器 ====================
class SegmentEditor(FramelessDialog):
    def __init__(self, parent, segment=None, panel_getter=None):
        super().__init__(parent)
        self.setTitle("编辑段落")
        self.resize(650, 550)
        self.segment = segment.copy() if segment else {
            "name": "", "duration": 0, "skills": [], "global_buffs": []
        }
        self.repeat_count = 1
        if segment and parent and hasattr(parent, 'exec_plan'):
            self.repeat_count = parent.exec_plan.get(segment.get('name', ''), 1)
        self.panel_getter = panel_getter
        self.parent_module_editor = parent
        self.init_ui()
        self.update_hit_labels()
        self.update_all_skill_damages()

    def init_ui(self):
        layout = self.getContentLayout()
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("段落名称:"))
        self.name_edit = QLineEdit(self.segment.get("name", ""))
        self.name_edit.setStyleSheet("QLineEdit { border: 1px solid #aaa; border-radius: 6px; padding: 4px; background: white; }")
        row1.addWidget(self.name_edit)
        row1.addWidget(QLabel("触发次数:"))
        self.repeat_edit = QLineEdit(str(self.repeat_count))
        self.repeat_edit.setMaximumWidth(60)
        self.repeat_edit.setStyleSheet("QLineEdit { border: 1px solid #aaa; border-radius: 6px; padding: 4px; background: white; }")
        row1.addWidget(self.repeat_edit)
        layout.addLayout(row1)

        row_time = QHBoxLayout()
        row_time.addWidget(QLabel("持续时间(秒):"))
        self.duration_edit = QLineEdit(str(self.segment.get("duration", 0)))
        self.duration_edit.setStyleSheet("QLineEdit { border: 1px solid #aaa; border-radius: 6px; padding: 4px; background: white; }")
        row_time.addWidget(self.duration_edit)
        layout.addLayout(row_time)

        self.global_buff_label = QLabel("当前全局 Buff: 无")
        self.global_buff_label.setStyleSheet("color: #333; font-size: 13px;")
        self.global_buff_label.setWordWrap(True)
        layout.addWidget(self.global_buff_label)
        self._update_global_label()

        btn_row = QHBoxLayout()
        add_gb_btn = QPushButton("添加全局 Buff")
        rem_gb_btn = QPushButton("移除全局 Buff")
        refresh_btn = QPushButton("刷新")
        for btn in [add_gb_btn, rem_gb_btn, refresh_btn]:
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        btn_row.addWidget(add_gb_btn)
        btn_row.addWidget(rem_gb_btn)
        btn_row.addWidget(refresh_btn)
        self.lucky_hit_label = QLabel("可幸运hit数: 0")
        self.lucky_hit_label.setStyleSheet("color: #333; border: 1px solid #ccc; border-radius: 4px; padding: 4px; background: white;")
        self.lucky_trigger_label = QLabel("幸运触发次数: 0")
        self.lucky_trigger_label.setStyleSheet("color: #333; border: 1px solid #ccc; border-radius: 4px; padding: 4px; background: white;")
        self.total_hit_label = QLabel("总hit数: 0")
        self.total_hit_label.setStyleSheet("color: #333; border: 1px solid #ccc; border-radius: 4px; padding: 4px; background: white;")
        btn_row.addWidget(self.lucky_hit_label)
        btn_row.addWidget(self.lucky_trigger_label)
        btn_row.addWidget(self.total_hit_label)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        add_gb_btn.clicked.connect(self._choose_global_buffs)
        rem_gb_btn.clicked.connect(self._remove_global_buffs)
        refresh_btn.clicked.connect(self._on_refresh)

        self.skill_frame = QFrame()
        self.skill_frame.setStyleSheet("QFrame { background: white; border: 1px solid #ccc; border-radius: 10px; }")
        self.skill_frame.setFixedHeight(250)

        # 使用 QListWidget 实现拖拽排序
        self.skill_list = QListWidget()
        self.skill_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.skill_list.setDefaultDropAction(Qt.MoveAction)
        self.skill_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.skill_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.skill_list.setStyleSheet("""
            QListWidget { background: white; border: none; }
            QListWidget::item { border: 1px solid #ddd; border-radius: 6px; padding: 2px; margin: 2px; }
            QListWidget::item:selected { background: #cce5ff; }
        """)
        self.skill_list.model().rowsMoved.connect(self._on_skill_order_changed)

        frame_layout = QVBoxLayout(self.skill_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.addWidget(self.skill_list)
        layout.addWidget(self.skill_frame)
        self._refresh_skills()

        add_sk_btn = QPushButton("添加技能")
        add_sk_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        add_sk_btn.clicked.connect(self._add_skill)
        layout.addWidget(add_sk_btn)

        save_btn = QPushButton("保存段落")
        save_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _update_global_label(self):
        buffs = load_buffs()
        ids = self.segment.get("global_buffs", [])
        names = [b.名称 for b in buffs if b.编号 in ids]
        self.global_buff_label.setText("当前全局 Buff: " + (", ".join(names) if names else "无"))

    def _choose_global_buffs(self):
        dlg = BuffSelectionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.segment.setdefault("global_buffs", [])
            self.segment["global_buffs"].extend(dlg.selected_ids)
            self._update_global_label()
            self._reapply_global_buffs_to_skills()

    def _remove_global_buffs(self):
        current_ids = self.segment.get("global_buffs", [])
        dlg = RemoveItemDialog(self, "全局 Buff", current_ids, load_buffs, lambda b: b.编号, lambda b: b.名称)
        if dlg.exec() == QDialog.Accepted:
            self.segment["global_buffs"] = dlg.remaining_ids
            self._update_global_label()
            self._reapply_global_buffs_to_skills()

    def _reapply_global_buffs_to_skills(self):
        self.update_all_skill_damages()

    def _add_skill_to_list(self, entry):
        skill_widget = SkillEntry(entry, self, panel_getter=self.panel_getter)
        item = QListWidgetItem()
        item.setSizeHint(skill_widget.sizeHint())
        self.skill_list.addItem(item)
        self.skill_list.setItemWidget(item, skill_widget)
        item.setData(Qt.UserRole, entry)

    def _refresh_skills(self):
        self.skill_list.clear()
        skills = self.segment.get("skills", [])
        normal, lucky = [], []
        for entry in skills:
            skill_id = entry.get('skill_id')
            sk = next((s for s in load_skills() if s.编号 == skill_id), None)
            if sk and sk.是否是幸运一击 == "1":
                lucky.append(entry)
            else:
                normal.append(entry)
        ordered_skills = normal + lucky
        self.segment["skills"] = ordered_skills
        for entry in ordered_skills:
            self._add_skill_to_list(entry)
        self.update_hit_labels()

    def _on_skill_order_changed(self):
        new_skills = []
        for i in range(self.skill_list.count()):
            item = self.skill_list.item(i)
            entry = item.data(Qt.UserRole)
            new_skills.append(entry)
        self.segment["skills"] = new_skills

    def update_hit_labels(self):
        total_hits = 0
        lucky_hits = 0
        for i in range(self.skill_list.count()):
            item = self.skill_list.item(i)
            entry = item.data(Qt.UserRole)
            sk = next((s for s in load_skills() if s.编号 == entry.get('skill_id')), None)
            if not sk:
                continue
            hit_num = safe_int_or_formula(sk.hit数)
            count = safe_int_or_formula(entry.get('count', 1))
            total_hits += hit_num * count
            if sk.是否幸运 == "1":
                lucky_hits += hit_num * count
        self.lucky_hit_label.setText(f"可幸运hit数: {lucky_hits}")
        self.lucky_trigger_label.setText(f"幸运触发次数: 0.00")
        self.total_hit_label.setText(f"总hit数: {total_hits}")

    def update_all_skill_damages(self):
        for i in range(self.skill_list.count()):
            item = self.skill_list.item(i)
            widget = self.skill_list.itemWidget(item)
            if isinstance(widget, SkillEntry):
                widget.update_damage()
        total_triggers = 0.0
        for i in range(self.skill_list.count()):
            widget = self.skill_list.itemWidget(self.skill_list.item(i))
            if isinstance(widget, SkillEntry):
                total_triggers += widget.skill_lucky_trigger
        self.lucky_trigger_label.setText(f"幸运触发次数: {total_triggers:.2f}")

        for i in range(self.skill_list.count()):
            widget = self.skill_list.itemWidget(self.skill_list.item(i))
            if isinstance(widget, SkillEntry) and widget.is_lucky_attack:
                widget.cnt_edit.setText(str(int(total_triggers)))

    def _add_skill(self):
        dlg = SkillSelectionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            for sid in dlg.selected_ids:
                self.segment.setdefault("skills", []).append({"skill_id": sid, "buffs_on": [], "count": 1})
            self._refresh_skills()
            self.update_all_skill_damages()

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            MessageDialog(self, "警告", "段落名称不能为空").exec()
            return
        try:
            self.repeat_count = int(self.repeat_edit.text())
        except:
            self.repeat_count = 1
        try:
            self.segment["duration"] = float(self.duration_edit.text())
        except:
            self.segment["duration"] = 0.0
        skills = []
        for i in range(self.skill_list.count()):
            item = self.skill_list.item(i)
            widget = self.skill_list.itemWidget(item)
            if isinstance(widget, SkillEntry):
                entry, count = widget.get_data()
                entry["count"] = count
                skills.append(entry)
        self.segment["skills"] = skills
        self.segment["name"] = name
        self.accept()

    def _on_refresh(self):
        if not self.parent_module_editor:
            return
        name = self.name_edit.text().strip()
        if not name:
            MessageDialog(self, "警告", "段落名称不能为空，刷新失败").exec()
            return
        try:
            self.repeat_count = int(self.repeat_edit.text())
        except:
            self.repeat_count = 1
        try:
            self.segment["duration"] = float(self.duration_edit.text())
        except:
            self.segment["duration"] = 0.0
        skills = []
        for i in range(self.skill_list.count()):
            item = self.skill_list.item(i)
            widget = self.skill_list.itemWidget(item)
            if isinstance(widget, SkillEntry):
                entry, count = widget.get_data()
                entry["count"] = count
                skills.append(entry)
        self.segment["skills"] = skills
        self.segment["name"] = name

        parent = self.parent_module_editor
        seg_idx = None
        for i, seg in enumerate(parent.segments):
            if seg.get('name') == name:
                seg_idx = i
                break
        if seg_idx is not None:
            parent.segments[seg_idx] = self.segment
            parent.exec_plan[name] = self.repeat_count
        else:
            parent.segments.append(self.segment)
            parent.exec_plan[name] = self.repeat_count

        self.accept()
        parent.seg_list.setCurrentRow(seg_idx if seg_idx is not None else len(parent.segments)-1)
        parent._edit_segment()


# ==================== 技能条目组件 ====================
class SkillEntry(QWidget):
    def __init__(self, entry, editor, panel_getter=None):
        super().__init__()
        self.entry = entry
        self.editor = editor
        self.panel_getter = panel_getter
        self.sk = next((s for s in load_skills() if s.编号 == entry.get("skill_id")), None)
        self.is_lucky_attack = (self.sk.是否是幸运一击 == "1") if self.sk else False
        self.skill_lucky_trigger = 0.0

        self.setFixedHeight(40)  # 高度稍增，容纳控件
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)  # 上下边距略大，让长条更高
        layout.setSpacing(6)                    # 控件间距适中

        # 技能名称（字体缩小）
        name = self.sk.名称 if self.sk else str(entry.get("skill_id"))
        name_lbl = QLabel(name)
        name_lbl.setFixedWidth(90)
        name_lbl.setFixedHeight(35)
        name_lbl.setStyleSheet("color: #333; font-size: 12px; background: transparent;")
        name_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(name_lbl)

        # 分隔线
        sep1 = QFrame(); sep1.setFrameShape(QFrame.VLine); sep1.setStyleSheet("border: 1px dashed #aaa;"); layout.addWidget(sep1)

        # Buff 标签（更紧凑，省略号）
        self.buff_lbl = QLabel("Buff: 无")
        self.buff_lbl.setFixedWidth(140)
        self.buff_lbl.setFixedHeight(35)
        self.buff_lbl.setStyleSheet("color: #555; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; padding: 2px;")
        self.buff_lbl.setWordWrap(False)
        self.buff_lbl.setToolTip("")   # 悬停显示完整
        layout.addWidget(self.buff_lbl)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.VLine); sep2.setStyleSheet("border: 1px dashed #aaa;"); layout.addWidget(sep2)

        # 触发次数（缩小输入框）
        self.cnt_edit = QLineEdit(str(entry.get("count", 1)))
        self.cnt_edit.setFixedWidth(45)
        self.cnt_edit.setFixedHeight(35)
        if self.is_lucky_attack:
            self.cnt_edit.setReadOnly(True)
            self.cnt_edit.setStyleSheet("QLineEdit { background: #f0f0f0; border: 1px solid #aaa; border-radius: 4px; padding: 2px; font-size: 11px; }")
        else:
            self.cnt_edit.setStyleSheet("QLineEdit { background: white; border: 1px solid #aaa; border-radius: 4px; padding: 2px; font-size: 11px; }")
        self.cnt_edit.textChanged.connect(self.on_count_changed)
        layout.addWidget(self.cnt_edit)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.VLine); sep3.setStyleSheet("border: 1px dashed #aaa;"); layout.addWidget(sep3)

        # 伤害显示（字体缩小）
        self.dmg_lbl = QLabel("伤害: -")
        self.dmg_lbl.setMinimumWidth(75)
        self.dmg_lbl.setMinimumWidth(40)
        self.dmg_lbl.setStyleSheet("color: #555; font-size: 11px; background: transparent;")
        layout.addWidget(self.dmg_lbl)

        # 操作按钮（缩小）
        add_btn = QPushButton("+Buff")
        rem_btn = QPushButton("-Buff")
        del_btn = QPushButton("删除")
        for btn in [add_btn, rem_btn, del_btn]:
            btn.setFixedHeight(40)
            btn.setFixedWidth(48)
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 white, stop:0.4 #b3d9ff, stop:0.6 #b3d9ff, stop:1 white);
                    color: #222; border: 1px solid #99c2ff; border-radius: 4px; font-size: 11px; padding: 1px;
                }
                QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 white, stop:0.4 #99c2ff, stop:0.6 #99c2ff, stop:1 white); }
            """)
            layout.addWidget(btn)
        add_btn.clicked.connect(self._add_buff)
        rem_btn.clicked.connect(self._remove_buff)
        del_btn.clicked.connect(self._delete_self)

        self._update_buff_display()
        self.update_damage()

    def _update_buff_display(self):
        buffs = load_buffs()
        ids = self.entry.get("buffs_on", [])
        names = [b.名称 for b in buffs if b.编号 in ids]
        text = "Buff: " + (", ".join(names) if names else "无")
        self.buff_lbl.setText(text)
        self.buff_lbl.setToolTip(text)

    def _add_buff(self):
        dlg = BuffSelectionDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.entry.setdefault("buffs_on", [])
            self.entry["buffs_on"].extend(dlg.selected_ids)
            self._update_buff_display()
            self.update_damage()

    def _remove_buff(self):
        current_ids = self.entry.get("buffs_on", [])
        dlg = RemoveItemDialog(self, "技能 Buff", current_ids, load_buffs, lambda b: b.编号, lambda b: b.名称)
        if dlg.exec() == QDialog.Accepted:
            self.entry["buffs_on"] = dlg.remaining_ids
            self._update_buff_display()
            self.update_damage()

    def _delete_self(self):
        self.setParent(None)
        self.deleteLater()
        self.editor.update_hit_labels()
        self.editor.update_all_skill_damages()

    def on_count_changed(self):
        self.editor.update_hit_labels()
        self.update_damage()

    def get_final_skill_panel(self):
        if not self.panel_getter or not self.sk:
            return None
        try:
            base_panel = self.panel_getter()
        except:
            return None
        seg = self.editor.segment
        global_buff_ids = seg.get('global_buffs', [])
        buffs_list = load_buffs()
        seg_panel = deepcopy(base_panel)
        for bid in global_buff_ids:
            b = next((x for x in buffs_list if x.编号 == bid), None)
            if b:
                buffed(b, seg_panel)
        final = merge_skill_into_panel(seg_panel, self.sk)
        for bid in self.entry.get('buffs_on', []):
            b = next((x for x in buffs_list if x.编号 == bid), None)
            if b:
                buffed(b, final)
        return final

    def update_damage(self):
        final_panel = self.get_final_skill_panel()
        if final_panel is None:
            self.dmg_lbl.setText("伤害: -")
            return
        dmg, _ = calc_damage_from_entity(final_panel)
        from evaluator import resolve_target
        resolved = resolve_target(final_panel, {})
        if self.sk and self.sk.是否幸运 == "1":
            hit_num = safe_int_or_formula(resolved.hit数)
            count = safe_int_or_formula(self.entry.get('count', 1))
            lucky_rate = min(resolved.幸运, 100.0) / 100.0
            self.skill_lucky_trigger = hit_num * count * lucky_rate
        else:
            self.skill_lucky_trigger = 0.0
        self.dmg_lbl.setText(f"单次: {dmg:.1f} 触发幸运: {self.skill_lucky_trigger:.2f}")

    def get_data(self):
        return self.entry, self.cnt_edit.text()


# ==================== Buff / 技能选择弹窗 ====================
class BuffSelectionDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("选择 Buff")
        self.resize(650, 450)
        self.selected_ids = []
        self.current_category = "法"
        self.buffs = load_buffs()
        self.card_widgets = []
        self.selected_cards = set()
        self.filter_text = ""
        layout = self.getContentLayout()
        search_row = QHBoxLayout()
        search_lbl = QLabel("搜索:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入Buff名称...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_row.addWidget(search_lbl)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        cat_row = QHBoxLayout()
        self.cat_buttons = {}
        categories = ["法", "枪", "刀", "斧", "弓", "巨刃", "剑盾", "手铐", "吉他", "幻想", "其他"]
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
            btn.clicked.connect(lambda _, c=cat: self.switch_cat(c))
            if cat == self.current_category:
                btn.setChecked(True)
            cat_row.addWidget(btn)
            self.cat_buttons[cat] = btn
        layout.addLayout(cat_row)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.card_widget = QWidget()
        self.card_grid = QGridLayout(self.card_widget)
        self.card_grid.setSpacing(12)
        self.card_grid.setContentsMargins(10, 10, 10, 10)
        self.card_grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.scroll.setWidget(self.card_widget)
        layout.addWidget(self.scroll)
        self.refresh_cards()
        btn_ok = QPushButton("确认添加")
        btn_ok.setStyleSheet(GRADIENT_BUTTON_STYLE)
        btn_ok.clicked.connect(self._accept)
        layout.addWidget(btn_ok)

    def switch_cat(self, cat):
        self.current_category = cat
        for c, btn in self.cat_buttons.items():
            btn.setChecked(c == cat)
        self.refresh_cards()

    def on_search_changed(self, text):
        self.filter_text = text.strip().lower()
        self.refresh_cards()

    def refresh_cards(self):
        for i in reversed(range(self.card_grid.count())):
            item = self.card_grid.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()
        self.card_widgets.clear()
        self.selected_cards.clear()
        filtered = [b for b in self.buffs if b.类别 == self.current_category]
        if self.filter_text:
            filtered = [b for b in filtered if self.filter_text in b.名称.lower()]
        cols = 4
        for i, b in enumerate(filtered):
            card = QFrame()
            card.setFixedSize(140, 80)
            card.setStyleSheet("QFrame { background: white; border: 1px solid #b3d9ff; border-radius: 8px; }")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(6, 6, 6, 6)
            name_lbl = QLabel(b.名称)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setFont(QFont("", 11, QFont.Bold))
            name_lbl.setStyleSheet("color: #333; background: transparent;")
            layout.addWidget(name_lbl)
            def toggle_card(event, fr=card, bid=b.编号):
                if fr in self.selected_cards:
                    self.selected_cards.discard(fr)
                    fr.setStyleSheet("QFrame { background: white; border: 1px solid #b3d9ff; border-radius: 8px; }")
                else:
                    self.selected_cards.add(fr)
                    fr.setStyleSheet("QFrame { background: #cce5ff; border: 2px solid #66b2ff; border-radius: 8px; }")
            card.mousePressEvent = toggle_card
            self.card_grid.addWidget(card, i // cols, i % cols)
            self.card_widgets.append(card)

    def _accept(self):
        selected = []
        for card in self.selected_cards:
            lbl = card.findChild(QLabel)
            if lbl:
                name = lbl.text()
                for b in self.buffs:
                    if b.名称 == name:
                        selected.append(b.编号)
                        break
        self.selected_ids = selected
        self.accept()


class SkillSelectionDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("选择技能")
        self.resize(650, 450)
        self.selected_ids = []
        self.current_category = "法"
        self.skills = load_skills()
        self.card_widgets = []
        self.selected_cards = set()
        self.filter_text = ""
        layout = self.getContentLayout()
        search_row = QHBoxLayout()
        search_lbl = QLabel("搜索:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入技能名称...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_row.addWidget(search_lbl)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        cat_row = QHBoxLayout()
        self.cat_buttons = {}
        categories = ["法", "枪", "刀", "斧", "弓", "巨刃", "剑盾", "手铐", "吉他", "其他"]
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
            btn.clicked.connect(lambda _, c=cat: self.switch_cat(c))
            if cat == self.current_category:
                btn.setChecked(True)
            cat_row.addWidget(btn)
            self.cat_buttons[cat] = btn
        layout.addLayout(cat_row)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.card_widget = QWidget()
        self.card_grid = QGridLayout(self.card_widget)
        self.card_grid.setSpacing(12)
        self.card_grid.setContentsMargins(10, 10, 10, 10)
        self.card_grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.scroll.setWidget(self.card_widget)
        layout.addWidget(self.scroll)
        self.refresh_cards()
        btn_ok = QPushButton("确认添加")
        btn_ok.setStyleSheet(GRADIENT_BUTTON_STYLE)
        btn_ok.clicked.connect(self._accept)
        layout.addWidget(btn_ok)

    def switch_cat(self, cat):
        self.current_category = cat
        for c, btn in self.cat_buttons.items():
            btn.setChecked(c == cat)
        self.refresh_cards()

    def on_search_changed(self, text):
        self.filter_text = text.strip().lower()
        self.refresh_cards()

    def refresh_cards(self):
        for i in reversed(range(self.card_grid.count())):
            item = self.card_grid.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()
        self.card_widgets.clear()
        self.selected_cards.clear()
        filtered = [s for s in self.skills if s.类别 == self.current_category]
        if self.filter_text:
            filtered = [s for s in filtered if self.filter_text in s.名称.lower()]
        cols = 4
        for i, s in enumerate(filtered):
            card = QFrame()
            card.setFixedSize(140, 80)
            card.setStyleSheet("QFrame { background: white; border: 1px solid #b3d9ff; border-radius: 8px; }")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(6, 6, 6, 6)
            name_lbl = QLabel(s.名称)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setFont(QFont("", 11, QFont.Bold))
            name_lbl.setStyleSheet("color: #333; background: transparent;")
            layout.addWidget(name_lbl)
            def toggle_card(event, fr=card, sid=s.编号):
                if fr in self.selected_cards:
                    self.selected_cards.discard(fr)
                    fr.setStyleSheet("QFrame { background: white; border: 1px solid #b3d9ff; border-radius: 8px; }")
                else:
                    self.selected_cards.add(fr)
                    fr.setStyleSheet("QFrame { background: #cce5ff; border: 2px solid #66b2ff; border-radius: 8px; }")
            card.mousePressEvent = toggle_card
            self.card_grid.addWidget(card, i // cols, i % cols)
            self.card_widgets.append(card)

    def _accept(self):
        selected = []
        for card in self.selected_cards:
            lbl = card.findChild(QLabel)
            if lbl:
                name = lbl.text()
                for s in self.skills:
                    if s.名称 == name:
                        selected.append(s.编号)
                        break
        self.selected_ids = selected
        self.accept()


# ==================== 移除条目对话框 ====================
class RemoveItemDialog(FramelessDialog):
    def __init__(self, parent, title, id_list, item_loader, id_getter, name_getter):
        super().__init__(parent)
        self.setTitle(f"移除 {title}")
        self.resize(400, 300)
        self.remaining_ids = id_list.copy()
        layout = self.getContentLayout()
        scroll = QScrollArea()
        w = QWidget()
        grid = QGridLayout(w)
        self.checks = []
        cols = 4
        for i, rid in enumerate(id_list):
            name = str(rid)
            for item in item_loader():
                if id_getter(item) == rid:
                    name = name_getter(item)
                    break
            card = QFrame()
            card.setStyleSheet("QFrame { background: white; border: 1px solid #ccc; border-radius: 8px; padding: 6px; }")
            card_layout = QVBoxLayout(card)
            cb = QCheckBox(name)
            cb.setProperty("item_id", rid)
            card_layout.addWidget(cb)
            grid.addWidget(card, i // cols, i % cols)
            self.checks.append(cb)
        scroll.setWidget(w)
        layout.addWidget(scroll)
        btn = QPushButton("移除选中项")
        btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        btn.clicked.connect(self._remove)
        layout.addWidget(btn)

    def _remove(self):
        selected = [cb.property("item_id") for cb in self.checks if cb.isChecked()]
        temp = self.remaining_ids.copy()
        for sel in selected:
            if sel in temp:
                temp.remove(sel)
        self.remaining_ids = temp
        self.accept()


class ModuleNameDialog(FramelessDialog):
    def __init__(self, parent, old_name=None):
        super().__init__(parent)
        self.setTitle("保存模组")
        self.resize(400, 250)
        layout = self.getContentLayout()
        layout.addWidget(QLabel("模组名称:"))
        self.name_edit = QLineEdit(old_name if old_name else "")
        self.name_edit.setStyleSheet("QLineEdit { border: 1px solid #aaa; border-radius: 8px; padding: 8px; font-size: 16px; background: white; }")
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("备注:"))
        self.note_edit = QTextEdit()
        self.note_edit.setStyleSheet("QTextEdit { border: 1px solid #aaa; border-radius: 8px; padding: 6px; background: white; }")
        layout.addWidget(self.note_edit)
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)