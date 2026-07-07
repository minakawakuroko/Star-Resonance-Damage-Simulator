import os, sys, json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QGridLayout, QLineEdit, QDialog,
    QDialogButtonBox, QMessageBox, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

from data_manager import (
    load_buffs, save_buffs, add_buff, update_buff, delete_buff,
    BUFF_CATEGORY_INDEX, BUFF_CATEGORY_NAMES, import_preset
)
from models import GameEntity
from gui.custom_widgets import (
    FramelessDialog, GRADIENT_BUTTON_STYLE, apply_gradient_style,
    _get_app_dir, ConfirmDialog, MessageDialog, get_resource_path
)

CATEGORIES = BUFF_CATEGORY_NAMES


def _get_next_buff_short_id(category: str) -> int:
    """返回指定类别下一个可用的最小流水号（插空）"""
    buffs = [b for b in load_buffs() if b.类别 == category]
    used = set()
    cat_idx = BUFF_CATEGORY_INDEX.get(category, 11)
    for b in buffs:
        bid = b.编号
        if 2000 + cat_idx*10 <= bid:
            short = bid - (2000 + cat_idx*10)
            used.add(short)
    short = 1
    while short in used:
        short += 1
    return short


class BuffEditDialog(FramelessDialog):
    def __init__(self, parent, buff: GameEntity = None, category="其他"):
        super().__init__(parent)
        self.setTitle("编辑Buff" if buff else "添加Buff")
        self.resize(620, 600)
        self.buff = buff
        self.category = category if buff is None else buff.类别
        if self.buff:
            cat_idx = BUFF_CATEGORY_INDEX.get(self.buff.类别, 11)
            self.short_id = (self.buff.编号 - 2000 - cat_idx*10)
        else:
            self.short_id = _get_next_buff_short_id(self.category)
        self.input_param_rows = []   # (name_edit, row_widget)
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
        self.name_edit = QLineEdit(self.buff.名称 if self.buff else "")
        self.cat_edit = QLineEdit(self.category)
        self.cat_edit.setReadOnly(True)

        self.f1 = QLineEdit(self.buff.主属性固定值 if self.buff else "0")
        self.f2 = QLineEdit(self.buff.主属性百分比 if self.buff else "0")
        self.f3 = QLineEdit(self.buff.攻击力固定值 if self.buff else "0")
        self.f4 = QLineEdit(self.buff.额外百分比攻击力 if self.buff else "0")
        self.f5 = QLineEdit(self.buff.精炼攻击力 if self.buff else "0")
        self.f6 = QLineEdit(self.buff.本元素攻击力 if self.buff else "0")
        self.f7 = QLineEdit(self.buff.全元素攻击力 if self.buff else "0")
        self.f8 = QLineEdit(self.buff.本元素攻击力百分比 if self.buff else "0")
        self.f9 = QLineEdit(self.buff.全元素攻击力百分比 if self.buff else "0")

        bl_stored = self.buff.技能倍率 if self.buff else "0"
        bl_display = self._clean_bl_display(bl_stored)
        self.bl_edit = QLineEdit(bl_display)

        self.f10 = QLineEdit(self.buff.暴击固定值 if self.buff else "0")
        self.f11 = QLineEdit(self.buff.急速固定值 if self.buff else "0")
        self.f12 = QLineEdit(self.buff.幸运固定值 if self.buff else "0")
        self.f13 = QLineEdit(self.buff.精通固定值 if self.buff else "0")
        self.f14 = QLineEdit(self.buff.全能固定值 if self.buff else "0")
        self.f15 = QLineEdit(self.buff.暴击 if self.buff else "0")
        self.f16 = QLineEdit(self.buff.急速 if self.buff else "0")
        self.f17 = QLineEdit(self.buff.幸运 if self.buff else "0")
        self.f18 = QLineEdit(self.buff.精通 if self.buff else "0")
        self.f19 = QLineEdit(self.buff.全能 if self.buff else "0")
        self.f20 = QLineEdit(self.buff.爆伤 if self.buff else "0")
        self.f21 = QLineEdit(self.buff.百分比穿防 if self.buff else "0")
        self.f22 = QLineEdit(self.buff.固定穿防 if self.buff else "0")
        self.f23 = QLineEdit(self.buff.一般增伤 if self.buff else "0")
        self.f24 = QLineEdit(self.buff.本元素增伤 if self.buff else "0")
        self.f25 = QLineEdit(self.buff.全元素增伤 if self.buff else "0")
        self.f26 = QLineEdit(self.buff.赛季增伤 if self.buff else "0")
        self.f27 = QLineEdit(self.buff.最终增伤 if self.buff else "0")

        self.green_main = QLineEdit(self.buff.绿值主属性 if self.buff else "0")
        self.green_atk = QLineEdit(self.buff.绿值攻击力 if self.buff else "0")
        self.thunder = QLineEdit(self.buff.雷印 if self.buff else "0")

        field_defs = [
            ("流水号", self.id_edit, ""),
            ("名称", self.name_edit, ""),
            ("类别", self.cat_edit, ""),
            ("主属性固定值", self.f1, ""),
            ("主属性百分比", self.f2, "%"),
            ("攻击力固定值", self.f3, ""),
            ("额外攻击力%", self.f4, "%"),
            ("精炼攻击力", self.f5, ""),
            ("本元素攻击力", self.f6, ""),
            ("全元素攻击力", self.f7, ""),
            ("本元素攻击力%", self.f8, "%"),
            ("全元素攻击力%", self.f9, "%"),
            ("倍率增加", self.bl_edit, "% (技能倍率)"),
            ("暴击固定值", self.f10, ""),
            ("急速固定值", self.f11, ""),
            ("幸运固定值", self.f12, ""),
            ("精通固定值", self.f13, ""),
            ("全能固定值", self.f14, ""),
            ("暴击(%)", self.f15, "%"),
            ("急速(%)", self.f16, "%"),
            ("幸运(%)", self.f17, "%"),
            ("精通(%)", self.f18, "%"),
            ("全能(%)", self.f19, "%"),
            ("爆伤", self.f20, "%"),
            ("穿防百分比", self.f21, "%"),
            ("固定穿防", self.f22, ""),
            ("一般增伤", self.f23, "%"),
            ("本元素增伤", self.f24, "%"),
            ("全元素增伤", self.f25, "%"),
            ("赛季增伤", self.f26, "%"),
            ("最终增伤", self.f27, "%"),
            ("绿值主属性", self.green_main, ""),
            ("绿值攻击力", self.green_atk, ""),
            ("雷印", self.thunder, "% (支持公式)"),
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
            lbl.setFixedWidth(90)
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

        add_in_btn = QPushButton("添加输入参数")
        add_in_btn.setStyleSheet(GRADIENT_BUTTON_STYLE)
        param_layout.addWidget(add_in_btn)

        in_label = QLabel("输入参数:")
        in_label.setStyleSheet("font-weight: bold;")
        param_layout.addWidget(in_label)
        self.input_container = QWidget()
        self.input_layout = QVBoxLayout(self.input_container)
        self.input_layout.setContentsMargins(0, 0, 0, 0)
        param_layout.addWidget(self.input_container)

        layout.addWidget(param_group)

        self._load_params()
        add_in_btn.clicked.connect(self._add_input_param)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

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

    def _load_params(self):
        if self.buff and self.buff.输入参数:
            try:
                in_params = json.loads(self.buff.输入参数)
                for p in in_params:
                    self._add_input_param()
                    self.input_param_rows[-1][0].setText(p.get("name", ""))
            except:
                pass

    def get_buff(self) -> GameEntity:
        user_short = int(self.id_edit.text()) if self.id_edit.text() else _get_next_buff_short_id(self.category)
        cat_idx = BUFF_CATEGORY_INDEX.get(self.category, 11)
        full_id = 2000 + cat_idx*10 + user_short

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
        entity.主属性固定值 = self.f1.text().strip()
        entity.主属性百分比 = self.f2.text().strip()
        entity.攻击力固定值 = self.f3.text().strip()
        entity.额外百分比攻击力 = self.f4.text().strip()
        entity.精炼攻击力 = self.f5.text().strip()
        entity.本元素攻击力 = self.f6.text().strip()
        entity.全元素攻击力 = self.f7.text().strip()
        entity.本元素攻击力百分比 = self.f8.text().strip()
        entity.全元素攻击力百分比 = self.f9.text().strip()
        entity.技能倍率 = bl_stored
        entity.暴击固定值 = self.f10.text().strip()
        entity.急速固定值 = self.f11.text().strip()
        entity.幸运固定值 = self.f12.text().strip()
        entity.精通固定值 = self.f13.text().strip()
        entity.全能固定值 = self.f14.text().strip()
        entity.暴击 = self.f15.text().strip()
        entity.急速 = self.f16.text().strip()
        entity.幸运 = self.f17.text().strip()
        entity.精通 = self.f18.text().strip()
        entity.全能 = self.f19.text().strip()
        entity.爆伤 = self.f20.text().strip()
        entity.百分比穿防 = self.f21.text().strip()
        entity.固定穿防 = self.f22.text().strip()
        entity.一般增伤 = self.f23.text().strip()
        entity.本元素增伤 = self.f24.text().strip()
        entity.全元素增伤 = self.f25.text().strip()
        entity.赛季增伤 = self.f26.text().strip()
        entity.最终增伤 = self.f27.text().strip()
        entity.绿值主属性 = self.green_main.text().strip()
        entity.绿值攻击力 = self.green_atk.text().strip()
        entity.雷印 = self.thunder.text().strip()
        entity.hit数 = "0"
        entity.是否幸运 = "0"
        entity.是否是幸运一击 = "0"
        entity.输入参数 = json.dumps(self._collect_input_params(), ensure_ascii=False)
        return entity


class BuffEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        self.current_category = "法"
        self.selected_buff_card = None
        self.selected_buff = None
        self.multi_selected = set()
        self.card_widgets = []
        self.filter_text = ""
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.bg = QLabel()
        img_path = get_resource_path('gui/jpg/buff.jpg')
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
        self.search_edit.setPlaceholderText("输入Buff名称...")
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
            card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #b3d9ff;
                    border-radius: 8px;
                }
            """)
        self.multi_selected.clear()
        self.selected_buff = None
        self.selected_buff_card = None

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
        self.selected_buff = None
        self.selected_buff_card = None
        buffs = [b for b in load_buffs() if b.类别 == self.current_category]
        if self.filter_text:
            buffs = [b for b in buffs if self.filter_text in b.名称.lower()]
        cols = self._calculate_cols()
        for i, b in enumerate(buffs):
            card = self.create_buff_card(b)
            self.card_layout.addWidget(card, i // cols, i % cols)
            self.card_widgets.append(card)

    def create_buff_card(self, buff: GameEntity):
        frame = QFrame()
        frame.setFixedSize(140, 80)
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #b3d9ff;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        name_lbl = QLabel(buff.名称)
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
                    frame.setStyleSheet("""
                        QFrame {
                            background-color: white;
                            border: 1px solid #b3d9ff;
                            border-radius: 8px;
                        }
                    """)
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
                    self.selected_buff_card = frame
                    self.selected_buff = buff
                else:
                    self.selected_buff = None
                    self.selected_buff_card = None
            else:
                self._clear_all_selection()
                self.selected_buff_card = frame
                self.selected_buff = buff
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #cce5ff;
                        border: 2px solid #66b2ff;
                        border-radius: 8px;
                    }
                """)
            event.accept()

        frame.mousePressEvent = select_card
        frame.mouseDoubleClickEvent = lambda e, b=buff: self.edit_buff(b)
        return frame

    def on_search_changed(self, text):
        self.filter_text = text.strip().lower()
        self.refresh_list()

    def on_edit_clicked(self):
        if self.selected_buff is None:
            dlg = MessageDialog(self, "提示", "你在点什么？")
            dlg.exec()
            return
        self.edit_buff(self.selected_buff)

    def on_delete_clicked(self):
        if self.selected_buff is None:
            dlg = MessageDialog(self, "提示", "你在点什么？")
            dlg.exec()
            return
        dlg = ConfirmDialog(self, "确认", f"确定删除Buff {self.selected_buff.名称}？")
        if dlg.exec() == QDialog.Accepted:
            delete_buff(self.selected_buff.编号)
            self.selected_buff = None
            self.selected_buff_card = None
            self.refresh_list()

    def on_batch_delete(self):
        if not self.multi_selected:
            dlg = MessageDialog(self, "提示", "请按住Ctrl多选要删除的Buff")
            dlg.exec()
            return
        count = len(self.multi_selected)
        dlg = ConfirmDialog(self, "确认", f"确定删除选中的 {count} 个Buff吗？")
        if dlg.exec() == QDialog.Accepted:
            for card in self.multi_selected:
                name_lbl = card.findChild(QLabel)
                if name_lbl:
                    buff_name = name_lbl.text()
                    for b in load_buffs():
                        if b.名称 == buff_name and b.类别 == self.current_category:
                            delete_buff(b.编号)
                            break
            self.refresh_list()

    def on_add(self):
        dialog = BuffEditDialog(self, category=self.current_category)
        if dialog.exec() == QDialog.Accepted:
            buff = dialog.get_buff()
            try:
                add_buff(buff, auto_id=False)
                self.refresh_list()
            except ValueError as e:
                QMessageBox.critical(None, "错误", str(e))

    def edit_buff(self, buff: GameEntity):
        dialog = BuffEditDialog(self, buff)
        if dialog.exec() == QDialog.Accepted:
            updated = dialog.get_buff()
            try:
                update_buff(updated)
                self.refresh_list()
            except ValueError as e:
                QMessageBox.critical(None, "错误", str(e))

    def on_import(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入Buff预设", "", "JSON Files (*.json)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                preset = json.load(f)
            buffs_data = preset.get('buffs', [])
            if not buffs_data:
                QMessageBox.information(None, "提示", "没有可导入的Buff")
                return

            current_buffs = load_buffs()
            cat_idx = BUFF_CATEGORY_INDEX.get(self.current_category, 11)
            used_shorts = set()
            for b in current_buffs:
                if b.类别 == self.current_category:
                    bid = b.编号
                    if 2000 + cat_idx*10 <= bid:
                        short = bid - (2000 + cat_idx*10)
                        used_shorts.add(short)

            imported_count = 0
            for buff_dict in buffs_data:
                from dataclasses import fields
                valid_fields = {f.name for f in fields(GameEntity)}
                filtered = {k: v for k, v in buff_dict.items() if k in valid_fields}
                for fn in valid_fields:
                    if fn not in filtered:
                        filtered[fn] = "0"
                buff = GameEntity(**filtered)
                buff.类别 = self.current_category

                new_short = 1
                while new_short in used_shorts:
                    new_short += 1
                buff.编号 = 2000 + cat_idx*10 + new_short
                used_shorts.add(new_short)
                current_buffs.append(buff)
                imported_count += 1

            save_buffs(current_buffs)
            self.refresh_list()
            QMessageBox.information(None, "导入成功", f"已导入 {imported_count} 个Buff到当前分类。")

    def on_export(self):
        selected = []
        cards_to_export = self.multi_selected if self.multi_selected else {self.selected_buff_card}
        for card in cards_to_export:
            if card is None:
                continue
            name_lbl = card.findChild(QLabel)
            if name_lbl:
                buff_name = name_lbl.text()
                for b in load_buffs():
                    if b.名称 == buff_name and b.类别 == self.current_category:
                        selected.append(b)
                        break
        if not selected:
            QMessageBox.warning(None, "提示", "请选中要导出的Buff")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出Buff预设", "buffs_preset.json", "JSON Files (*.json)")
        if file_path:
            from data_manager import export_preset
            export_preset([], selected, file_path)
            QMessageBox.information(None, "导出成功", f"已导出 {len(selected)} 个Buff。")

    def resizeEvent(self, event):
        if self.bg.pixmap() and not self.bg.pixmap().isNull():
            self.bg.setPixmap(QPixmap(self.bg.pixmap()).scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self.refresh_list()
        super().resizeEvent(event)


class BuffSelectionDialog(FramelessDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("选择 Buff")
        self.resize(650, 500)
        self.selected_ids = []
        self.current_category = "法"
        self.buffs = load_buffs()
        self.card_widgets = []
        self.selected_cards = set()
        self.filter_text = ""
        self.init_ui()

    def init_ui(self):
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