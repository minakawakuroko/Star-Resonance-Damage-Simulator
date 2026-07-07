import os, sys, json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QGridLayout, QLineEdit, QDialog,
    QDialogButtonBox, QMessageBox, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

from data_manager import (
    load_skills, save_skills, add_skill, update_skill, delete_skill,
    SKILL_CATEGORY_INDEX, SKILL_CATEGORY_NAMES, import_preset
)
from models import GameEntity
from gui.custom_widgets import (
    FramelessDialog, GRADIENT_BUTTON_STYLE, apply_gradient_style,
    _get_app_dir, ConfirmDialog, MessageDialog, get_resource_path
)

CATEGORIES = SKILL_CATEGORY_NAMES
MAGIC_CATEGORIES = {"法", "手铐", "吉他"}


def _get_next_skill_short_id(category: str) -> int:
    """返回指定类别下一个可用的最小流水号（插空）"""
    skills = [s for s in load_skills() if s.类别 == category]
    used = set()
    cat_idx = SKILL_CATEGORY_INDEX.get(category, 10)
    for s in skills:
        sid = s.编号
        if 1000 + cat_idx*10 <= sid:
            short = sid - (1000 + cat_idx*10)
            used.add(short)
    short = 1
    while short in used:
        short += 1
    return short


class SkillEditDialog(FramelessDialog):
    def __init__(self, parent, skill: GameEntity = None, category="其他"):
        super().__init__(parent)
        self.setTitle("编辑技能" if skill else "添加技能")
        self.resize(650, 700)
        self.skill = skill
        self.category = category if skill is None else skill.类别
        self.default_damage_type = "法术" if self.category in MAGIC_CATEGORIES else "物理"
        if self.skill:
            cat_idx = SKILL_CATEGORY_INDEX.get(self.skill.类别, 10)
            self.short_id = (self.skill.编号 - 1000 - cat_idx*10)
        else:
            self.short_id = _get_next_skill_short_id(self.category)

        self.output_param_rows = []   # (name_edit, formula_edit, row_widget)
        self.input_param_rows = []    # (name_edit, row_widget)
        self.init_ui()
        apply_gradient_style(self)

    @staticmethod
    def _clean_bl_display(bl: str) -> str:
        s = bl.strip()
        if s.endswith("/100"):
            s = s[:-4].strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
        return s if s else "0"

    def init_ui(self):
        layout = self.getContentLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        form = QGridLayout(w)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(8)

        self.id_edit = QLineEdit(str(self.short_id))
        self.name_edit = QLineEdit(self.skill.名称 if self.skill else "")
        self.cat_edit = QLineEdit(self.category)
        self.cat_edit.setReadOnly(True)
        stored_type = self.skill.伤害类型 if self.skill else ("0" if self.default_damage_type == "物理" else "1")
        display_type = "物理" if stored_type == "0" else "法术"
        self.type_edit = QLineEdit(display_type)

        bl_stored = self.skill.技能倍率 if self.skill else "0"
        bl_display = self._clean_bl_display(bl_stored)
        self.bl_edit = QLineEdit(bl_display)

        self.fix_edit = QLineEdit(self.skill.技能固定值 if self.skill else "0")
        self.hit_edit = QLineEdit(self.skill.hit数 if self.skill else "1")
        self.pen_per_edit = QLineEdit(self.skill.百分比穿防 if self.skill else "0")
        self.pen_fix_edit = QLineEdit(self.skill.固定穿防 if self.skill else "0")
        self.crit_edit = QLineEdit(self.skill.暴击 if self.skill else "0")
        self.luck_edit = QLineEdit(self.skill.幸运 if self.skill else "0")
        self.critdmg_edit = QLineEdit(self.skill.爆伤 if self.skill else "0")
        self.dmg_common_edit = QLineEdit(self.skill.一般增伤 if self.skill else "0")

        self.elem_atk_edit = QLineEdit(self.skill.本元素攻击力 if self.skill else "0")
        self.elem_all_atk_edit = QLineEdit(self.skill.全元素攻击力 if self.skill else "0")
        self.elem_atk_per_edit = QLineEdit(self.skill.本元素攻击力百分比 if self.skill else "0")
        self.elem_all_atk_per_edit = QLineEdit(self.skill.全元素攻击力百分比 if self.skill else "0")
        self.elem_dmg_edit = QLineEdit(self.skill.本元素增伤 if self.skill else "0")
        self.elem_all_dmg_edit = QLineEdit(self.skill.全元素增伤 if self.skill else "0")

        self.f_crit_fixed = QLineEdit(self.skill.暴击固定值 if self.skill else "0")
        self.f_haste_fixed = QLineEdit(self.skill.急速固定值 if self.skill else "0")
        self.f_luck_fixed = QLineEdit(self.skill.幸运固定值 if self.skill else "0")
        self.f_mastery_fixed = QLineEdit(self.skill.精通固定值 if self.skill else "0")
        self.f_omni_fixed = QLineEdit(self.skill.全能固定值 if self.skill else "0")
        self.f_crit_pct = QLineEdit(self.skill.暴击 if self.skill else "0")
        self.f_haste_pct = QLineEdit(self.skill.急速 if self.skill else "0")
        self.f_luck_pct = QLineEdit(self.skill.幸运 if self.skill else "0")
        self.f_mastery_pct = QLineEdit(self.skill.精通 if self.skill else "0")
        self.f_omni_pct = QLineEdit(self.skill.全能 if self.skill else "0")
        self.dmg_season_edit = QLineEdit(self.skill.赛季增伤 if self.skill else "0")
        self.dmg_final_edit = QLineEdit(self.skill.最终增伤 if self.skill else "0")
        self.lucky_flag_edit = QLineEdit(self.skill.是否幸运 if self.skill else "1")
        self.lucky_attack_flag_edit = QLineEdit(self.skill.是否是幸运一击 if self.skill else "0")

        field_defs = [
            ("流水号", self.id_edit, ""),
            ("名称", self.name_edit, ""),
            ("类别", self.cat_edit, ""),
            ("伤害类型", self.type_edit, "物理/法术"),
            ("技能倍率", self.bl_edit, "% (支持公式)"),
            ("技能固定值", self.fix_edit, ""),
            ("hit数", self.hit_edit, ""),
            ("穿防百分比", self.pen_per_edit, "%"),
            ("固定穿防", self.pen_fix_edit, ""),
            ("暴击固定值", self.f_crit_fixed, ""),
            ("急速固定值", self.f_haste_fixed, ""),
            ("幸运固定值", self.f_luck_fixed, ""),
            ("精通固定值", self.f_mastery_fixed, ""),
            ("全能固定值", self.f_omni_fixed, ""),
            ("暴击(%)", self.f_crit_pct, "%"),
            ("急速(%)", self.f_haste_pct, "%"),
            ("幸运(%)", self.f_luck_pct, "%"),
            ("精通(%)", self.f_mastery_pct, "%"),
            ("全能(%)", self.f_omni_pct, "%"),
            ("爆伤", self.critdmg_edit, "%"),
            ("一般增伤", self.dmg_common_edit, "%"),
            ("本元素攻击力", self.elem_atk_edit, ""),
            ("全元素攻击力", self.elem_all_atk_edit, ""),
            ("本元素攻击力%", self.elem_atk_per_edit, "%"),
            ("全元素攻击力%", self.elem_all_atk_per_edit, "%"),
            ("本元素增伤", self.elem_dmg_edit, "%"),
            ("全元素增伤", self.elem_all_dmg_edit, "%"),
            ("赛季增伤", self.dmg_season_edit, "%"),
            ("最终增伤", self.dmg_final_edit, "%"),
            ("是否幸运", self.lucky_flag_edit, ""),
            ("是否是幸运一击", self.lucky_attack_flag_edit, ""),
        ]

        cols = 2
        for i, (label, widget, suffix) in enumerate(field_defs):
            row = i // cols
            col = i % cols
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 12px; color: #333; background: transparent;")
            lbl.setFixedWidth(80)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cell_layout.addWidget(lbl)
            widget.setFixedWidth(70)
            widget.setStyleSheet("border: 1px solid #aaa; border-radius: 4px; padding: 2px; background: white; color: #333;")
            cell_layout.addWidget(widget, alignment=Qt.AlignLeft)
            if suffix:
                suf_lbl = QLabel(suffix)
                suf_lbl.setStyleSheet("color: #666; font-size: 11px; background: transparent;")
                cell_layout.addWidget(suf_lbl)
            cell_layout.addStretch()
            form.addWidget(cell, row, col)

        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)
        scroll.setWidget(w)
        layout.addWidget(scroll)

        # 参数管理区域
        param_group = QFrame()
        param_group.setStyleSheet("QFrame { background: #f0f0f0; border: 1px solid #ccc; border-radius: 6px; padding: 6px; }")
        param_layout = QVBoxLayout(param_group)

        btn_row = QHBoxLayout()
        add_out_btn = QPushButton("添加输出参数")
        add_in_btn = QPushButton("添加输入参数")
        add_out_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        add_in_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        btn_row.addWidget(add_out_btn)
        btn_row.addWidget(add_in_btn)
        btn_row.addStretch()
        param_layout.addLayout(btn_row)

        out_label = QLabel("输出参数:")
        out_label.setStyleSheet("font-weight: bold;")
        param_layout.addWidget(out_label)
        self.output_container = QWidget()
        self.output_layout = QVBoxLayout(self.output_container)
        self.output_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.addWidget(self.output_container)

        in_label = QLabel("输入参数:")
        in_label.setStyleSheet("font-weight: bold;")
        param_layout.addWidget(in_label)
        self.input_container = QWidget()
        self.input_layout = QVBoxLayout(self.input_container)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.addWidget(self.input_container)

        layout.addWidget(param_group)

        self._load_params()
        add_out_btn.clicked.connect(self._add_output_param)
        add_in_btn.clicked.connect(self._add_input_param)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    # ---------- 输出参数 ----------
    def _add_output_param(self):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("参数名")
        formula_edit = QLineEdit()
        formula_edit.setPlaceholderText("公式 (如 hit数*2)")
        del_btn = QPushButton("×")
        del_btn.setFixedSize(30, 24)
        del_btn.setStyleSheet("QPushButton { background: #ddd; color: #333; border: 1px solid #aaa; border-radius: 4px; } QPushButton:hover { background: #f99; }")
        del_btn.clicked.connect(lambda: self._delete_output_row(row))
        h.addWidget(QLabel("名称:"))
        h.addWidget(name_edit)
        h.addWidget(QLabel("公式:"))
        h.addWidget(formula_edit)
        h.addWidget(del_btn)
        self.output_layout.addWidget(row)
        self.output_param_rows.append((name_edit, formula_edit, row))

    def _delete_output_row(self, row):
        self.output_layout.removeWidget(row)
        row.deleteLater()
        for i, (name_edit, formula_edit, r) in enumerate(self.output_param_rows):
            if r == row:
                self.output_param_rows.pop(i)
                break

    def _collect_output_params(self) -> list:
        params = []
        for name_edit, formula_edit, _ in self.output_param_rows:
            name = name_edit.text().strip()
            formula = formula_edit.text().strip()
            if name or formula:
                params.append({"name": name, "formula": formula})
        return params

    # ---------- 输入参数 ----------
    def _add_input_param(self):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("参数名")
        del_btn = QPushButton("×")
        del_btn.setFixedSize(30, 24)
        del_btn.setStyleSheet("QPushButton { background: #ddd; color: #333; border: 1px solid #aaa; border-radius: 4px; } QPushButton:hover { background: #f99; }")
        del_btn.clicked.connect(lambda: self._delete_input_row(row))
        h.addWidget(QLabel("名称:"))
        h.addWidget(name_edit)
        h.addWidget(del_btn)
        self.input_layout.addWidget(row)
        self.input_param_rows.append((name_edit, row))

    def _delete_input_row(self, row):
        self.input_layout.removeWidget(row)
        row.deleteLater()
        for i, (name_edit, r) in enumerate(self.input_param_rows):
            if r == row:
                self.input_param_rows.pop(i)
                break

    def _collect_input_params(self) -> list:
        params = []
        for name_edit, _ in self.input_param_rows:
            name = name_edit.text().strip()
            if name:
                params.append({"name": name})
        return params

    # ---------- 加载已有参数 ----------
    def _load_params(self):
        # 加载输出参数
        if self.skill and self.skill.输出参数:
            try:
                out_params = json.loads(self.skill.输出参数)
                for p in out_params:
                    self._add_output_param()
                    self.output_param_rows[-1][0].setText(p.get("name", ""))
                    self.output_param_rows[-1][1].setText(p.get("formula", ""))
            except:
                pass
        # 加载输入参数
        if self.skill and self.skill.输入参数:
            try:
                in_params = json.loads(self.skill.输入参数)
                for p in in_params:
                    self._add_input_param()
                    self.input_param_rows[-1][0].setText(p.get("name", ""))
            except:
                pass

    def get_skill(self) -> GameEntity:
        user_short = int(self.id_edit.text()) if self.id_edit.text() else _get_next_skill_short_id(self.category)
        cat_idx = SKILL_CATEGORY_INDEX.get(self.category, 10)
        full_id = 1000 + cat_idx*10 + user_short

        dmg_type_str = self.type_edit.text().strip()
        dmg_type = "1" if dmg_type_str == "法术" else "0"

        raw_bl = self.bl_edit.text().strip()
        if raw_bl:
            clean = raw_bl
            if clean.endswith("/100"):
                clean = clean[:-4].strip()
            if clean.startswith("(") and clean.endswith(")"):
                clean = clean[1:-1].strip()
            bl_stored = f"({clean})/100"
        else:
            bl_stored = "0"

        entity = GameEntity()
        entity.编号 = full_id
        entity.名称 = self.name_edit.text().strip()
        entity.类别 = self.category
        entity.伤害类型 = dmg_type
        entity.技能倍率 = bl_stored
        entity.技能固定值 = self.fix_edit.text().strip()
        entity.hit数 = self.hit_edit.text().strip()
        entity.百分比穿防 = self.pen_per_edit.text().strip()
        entity.固定穿防 = self.pen_fix_edit.text().strip()
        entity.暴击固定值 = self.f_crit_fixed.text().strip()
        entity.急速固定值 = self.f_haste_fixed.text().strip()
        entity.幸运固定值 = self.f_luck_fixed.text().strip()
        entity.精通固定值 = self.f_mastery_fixed.text().strip()
        entity.全能固定值 = self.f_omni_fixed.text().strip()
        entity.暴击 = self.f_crit_pct.text().strip()
        entity.急速 = self.f_haste_pct.text().strip()
        entity.幸运 = self.f_luck_pct.text().strip()
        entity.精通 = self.f_mastery_pct.text().strip()
        entity.全能 = self.f_omni_pct.text().strip()
        entity.爆伤 = self.critdmg_edit.text().strip()
        entity.一般增伤 = self.dmg_common_edit.text().strip()
        entity.本元素攻击力 = self.elem_atk_edit.text().strip()
        entity.全元素攻击力 = self.elem_all_atk_edit.text().strip()
        entity.本元素攻击力百分比 = self.elem_atk_per_edit.text().strip()
        entity.全元素攻击力百分比 = self.elem_all_atk_per_edit.text().strip()
        entity.本元素增伤 = self.elem_dmg_edit.text().strip()
        entity.全元素增伤 = self.elem_all_dmg_edit.text().strip()
        entity.赛季增伤 = self.dmg_season_edit.text().strip()
        entity.最终增伤 = self.dmg_final_edit.text().strip()
        entity.是否幸运 = self.lucky_flag_edit.text().strip()
        entity.是否是幸运一击 = self.lucky_attack_flag_edit.text().strip()
        entity.输出参数 = json.dumps(self._collect_output_params(), ensure_ascii=False)
        entity.输入参数 = json.dumps(self._collect_input_params(), ensure_ascii=False)
        return entity


class SkillEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self.current_category = "法"
        self.selected_skill_card = None
        self.selected_skill = None
        self.multi_selected = set()
        self.card_widgets = []
        self.filter_text = ""
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.bg = QLabel()
        img_path = get_resource_path('gui/jpg/技能.jpg')
        if os.path.exists(img_path):
            pix = QPixmap(img_path)
            self.bg.setPixmap(pix.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self.bg.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.bg, 0, 0)

        content = QWidget()
        content.setStyleSheet("background: rgba(255,255,255,180); border-radius: 10px;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)

        io_row = QHBoxLayout()
        import_btn = QPushButton("导入预设")
        export_btn = QPushButton("导出选中")
        for btn in [import_btn, export_btn]:
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
            io_row.addWidget(btn)
        io_row.addStretch()
        import_btn.clicked.connect(self.on_import)
        export_btn.clicked.connect(self.on_export)
        content_layout.addLayout(io_row)

        search_row = QHBoxLayout()
        search_lbl = QLabel("搜索:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入技能名称...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_row.addWidget(search_lbl)
        search_row.addWidget(self.search_edit)
        content_layout.addLayout(search_row)

        cat_row = QHBoxLayout()
        self.cat_buttons = {}
        for cat in CATEGORIES:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
            btn.clicked.connect(lambda _, c=cat: self.switch_category(c))
            if cat == self.current_category:
                btn.setChecked(True)
            cat_row.addWidget(btn)
            self.cat_buttons[cat] = btn
        content_layout.addLayout(cat_row)

        op_row = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.edit_btn = QPushButton("编辑")
        self.del_btn = QPushButton("删除")
        self.batch_del_btn = QPushButton("批量删除")
        for btn in [self.add_btn, self.edit_btn, self.del_btn, self.batch_del_btn]:
            btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
            op_row.addWidget(btn)
        op_row.addStretch()
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        self.del_btn.clicked.connect(self.on_delete_clicked)
        self.batch_del_btn.clicked.connect(self.on_batch_delete)
        content_layout.addLayout(op_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.card_container = QWidget()
        self.card_layout = QGridLayout(self.card_container)
        self.card_layout.setSpacing(12)
        self.card_layout.setContentsMargins(10, 10, 10, 10)
        self.card_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.scroll.setWidget(self.card_container)
        content_layout.addWidget(self.scroll)

        main_layout.addWidget(content, 0, 0)

    def _clear_all_selection(self):
        for card in self.card_widgets:
            card.setStyleSheet(card.property("default_style"))
        self.multi_selected.clear()
        self.selected_skill = None
        self.selected_skill_card = None

    def switch_category(self, cat):
        self.current_category = cat
        for c, btn in self.cat_buttons.items():
            btn.setChecked(c == cat)
        self.refresh_list()

    def _calculate_cols(self):
        if not self.card_container:
            return 4
        container_width = self.scroll.viewport().width() - 20
        card_width = 140 + 12
        cols = max(1, container_width // card_width)
        return cols

    def refresh_list(self):
        for i in reversed(range(self.card_layout.count())):
            item = self.card_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.card_widgets.clear()
        self.multi_selected.clear()
        self.selected_skill = None
        self.selected_skill_card = None
        skills = [s for s in load_skills() if s.类别 == self.current_category]
        if self.filter_text:
            skills = [s for s in skills if self.filter_text in s.名称.lower()]
        cols = self._calculate_cols()
        for i, sk in enumerate(skills):
            card = self.create_skill_card(sk)
            self.card_layout.addWidget(card, i // cols, i % cols)
            self.card_widgets.append(card)

    def create_skill_card(self, skill: GameEntity):
        frame = QFrame()
        frame.setFixedSize(140, 80)

        if skill.是否是幸运一击 == "1":
            border_color = "#66cc66"
            border_width = "2px"
        elif skill.是否幸运 == "1":
            border_color = "#66b2ff"
            border_width = "2px"
        else:
            border_color = "#ffcc66"
            border_width = "2px"

        default_style = f"""
            QFrame {{
                background-color: white;
                border: {border_width} solid {border_color};
                border-radius: 8px;
            }}
        """
        frame.setStyleSheet(default_style)
        frame.setProperty("default_style", default_style)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        name_lbl = QLabel(skill.名称)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setFont(QFont("", 12))
        name_lbl.setStyleSheet("color: #333; background: transparent;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        def select_card(event):
            ctrl_held = event.modifiers() & Qt.ControlModifier
            if ctrl_held:
                if frame in self.multi_selected:
                    self.multi_selected.discard(frame)
                    frame.setStyleSheet(frame.property("default_style"))
                else:
                    self.multi_selected.add(frame)
                    frame.setStyleSheet("""
                        QFrame {
                            background-color: #cce5ff;
                            border: 2px solid #66b2ff;
                            border-radius: 8px;
                        }
                    """)
                if self.multi_selected:
                    self.selected_skill_card = frame
                    self.selected_skill = skill
                else:
                    self.selected_skill = None
                    self.selected_skill_card = None
            else:
                self._clear_all_selection()
                self.selected_skill_card = frame
                self.selected_skill = skill
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #cce5ff;
                        border: 2px solid #66b2ff;
                        border-radius: 8px;
                    }
                """)
            event.accept()

        frame.mousePressEvent = select_card
        frame.mouseDoubleClickEvent = lambda e, s=skill: self.edit_skill(s)
        return frame

    def on_search_changed(self, text):
        self.filter_text = text.strip().lower()
        self.refresh_list()

    def on_edit_clicked(self):
        if self.selected_skill is None:
            dlg = MessageDialog(self, "提示", "你在点什么？")
            dlg.exec()
            return
        self.edit_skill(self.selected_skill)

    def on_delete_clicked(self):
        if self.selected_skill is None:
            dlg = MessageDialog(self, "提示", "你在点什么？")
            dlg.exec()
            return
        dlg = ConfirmDialog(self, "确认", f"确定删除技能 {self.selected_skill.名称}？")
        if dlg.exec() == QDialog.Accepted:
            delete_skill(self.selected_skill.编号)
            self.selected_skill = None
            self.selected_skill_card = None
            self.refresh_list()

    def on_batch_delete(self):
        if not self.multi_selected:
            dlg = MessageDialog(self, "提示", "请按住Ctrl多选要删除的技能")
            dlg.exec()
            return
        count = len(self.multi_selected)
        dlg = ConfirmDialog(self, "确认", f"确定删除选中的 {count} 个技能吗？")
        if dlg.exec() == QDialog.Accepted:
            for card in self.multi_selected:
                name_lbl = card.findChild(QLabel)
                if name_lbl:
                    skill_name = name_lbl.text()
                    for s in load_skills():
                        if s.名称 == skill_name and s.类别 == self.current_category:
                            delete_skill(s.编号)
                            break
            self.refresh_list()

    def on_add(self):
        dialog = SkillEditDialog(self, category=self.current_category)
        if dialog.exec() == QDialog.Accepted:
            skill = dialog.get_skill()
            try:
                add_skill(skill, auto_id=False)
                self.refresh_list()
            except ValueError as e:
                QMessageBox.critical(None, "错误", str(e))

    def edit_skill(self, skill: GameEntity):
        dialog = SkillEditDialog(self, skill)
        if dialog.exec() == QDialog.Accepted:
            updated = dialog.get_skill()
            try:
                update_skill(updated)
                self.refresh_list()
            except ValueError as e:
                QMessageBox.critical(None, "错误", str(e))

    def on_import(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入技能预设", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                preset = json.load(f)
            skills_data = preset.get('skills', [])
            if not skills_data:
                QMessageBox.information(None, "提示", "没有可导入的技能")
                return

            current_skills = load_skills()
            cat_idx = SKILL_CATEGORY_INDEX.get(self.current_category, 10)
            used_shorts = set()
            for s in current_skills:
                if s.类别 == self.current_category:
                    sid = s.编号
                    if 1000 + cat_idx*10 <= sid:
                        short = sid - (1000 + cat_idx*10)
                        used_shorts.add(short)

            imported_count = 0
            for skill_dict in skills_data:
                from dataclasses import fields
                valid_fields = {f.name for f in fields(GameEntity)}
                filtered = {k: v for k, v in skill_dict.items() if k in valid_fields}
                for fn in valid_fields:
                    if fn not in filtered:
                        filtered[fn] = "0"
                skill = GameEntity(**filtered)
                skill.类别 = self.current_category

                new_short = 1
                while new_short in used_shorts:
                    new_short += 1
                skill.编号 = 1000 + cat_idx*10 + new_short
                used_shorts.add(new_short)
                current_skills.append(skill)
                imported_count += 1

            save_skills(current_skills)
            self.refresh_list()
            QMessageBox.information(None, "导入成功", f"已导入 {imported_count} 个技能到当前分类。")

    def on_export(self):
        selected = []
        cards_to_export = self.multi_selected if self.multi_selected else {self.selected_skill_card}
        for card in cards_to_export:
            if card is None:
                continue
            name_lbl = card.findChild(QLabel)
            if name_lbl:
                skill_name = name_lbl.text()
                for s in load_skills():
                    if s.名称 == skill_name and s.类别 == self.current_category:
                        selected.append(s)
                        break
        if not selected:
            QMessageBox.warning(None, "提示", "请选中要导出的技能")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出技能预设", "skills_preset.json", "JSON Files (*.json)")
        if file_path:
            from data_manager import export_preset
            export_preset(selected, [], file_path)
            QMessageBox.information(None, "导出成功", f"已导出 {len(selected)} 个技能。")

    def resizeEvent(self, event):
        if self.bg.pixmap() and not self.bg.pixmap().isNull():
            self.bg.setPixmap(QPixmap(self.bg.pixmap()).scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self.refresh_list()
        super().resizeEvent(event)


class SkillSelectionDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("选择技能")
        self.resize(650, 500)
        self.selected_ids = []
        self.current_category = "法"
        self.skills = load_skills()
        self.card_widgets = []
        self.selected_cards = set()
        self.filter_text = ""
        self.init_ui()

    def init_ui(self):
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