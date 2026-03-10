import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
import os
import csv
from project_utilities.json_utility import JsonUtility

from app.utils.theme_manager import ThemeManager
from app.utils.ui_scaling import UIScaling


class PieChartWidget(QWidget):
    """Custom widget that draws a pie chart using QPainter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  # list of (value, color, label)
        self.setMinimumSize(UIScaling.scale(200), UIScaling.scale(200))

    def set_data(self, data):
        """data: list of (value, QColor or str, label)"""
        self.data = data
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Calculate chart area (square, centered)
        w = self.width()
        h = self.height()
        side = min(w, h) - UIScaling.scale(20)
        if side < 50:
            painter.end()
            return

        x = (w - side) / 2
        y = (h - side) / 2
        rect = QRectF(x, y, side, side)

        total = sum(d[0] for d in self.data if d[0] > 0)
        if total <= 0:
            # Draw empty circle
            painter.setPen(QPen(QColor("#D1D5DB"), 3))
            painter.setBrush(QColor("#F3F4F6"))
            painter.drawEllipse(rect)
            painter.end()
            return

        # Draw pie segments
        start_angle = 90 * 16  # Start from top (12 o'clock)
        for value, color, label in self.data:
            if value <= 0:
                continue
            span = int(round(value / total * 360 * 16))
            if isinstance(color, str):
                color = QColor(color)
            painter.setPen(QPen(QColor("#1F2937"), 2))
            painter.setBrush(color)
            painter.drawPie(rect, start_angle, -span)
            start_angle -= span

        painter.end()


class ReportDetailPage(QWidget):
    """Full-screen report detail page with pie chart and WO info."""

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.theme = ThemeManager.get_colors()
        self.current_record = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #ECEEF2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ═══════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════
        header = QFrame()
        header.setFixedHeight(UIScaling.scale(70))
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #D8D8D8;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(UIScaling.scale(20), 0, UIScaling.scale(20), 0)
        h_layout.setSpacing(UIScaling.scale(14))

        btn_back = QPushButton("❮")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFixedSize(UIScaling.scale(48), UIScaling.scale(48))
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color: #F0F0F5;
                border: none;
                border-radius: {UIScaling.scale(24)}px;
                font-size: {UIScaling.scale_font(20)}px;
                font-weight: 700;
                color: #333;
            }}
            QPushButton:hover {{ background-color: #E0E0E5; }}
            QPushButton:pressed {{ background-color: #D0D0D5; }}
        """)
        btn_back.clicked.connect(self.go_back)
        h_layout.addWidget(btn_back)

        lbl_title = QLabel("Detail Report")
        lbl_title.setStyleSheet(f"font-size: {UIScaling.scale_font(24)}px; font-weight: 800; color: #1C1C1E;")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        btn_export = QPushButton("Export CSV")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setFixedHeight(UIScaling.scale(40))
        btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: #2563EB;
                color: white;
                border-radius: {UIScaling.scale(8)}px;
                padding: 0 {UIScaling.scale(16)}px;
                font-size: {UIScaling.scale_font(14)}px;
                font-weight: 700;
                border: none;
            }}
            QPushButton:hover {{ background-color: #1D4ED8; }}
            QPushButton:pressed {{ background-color: #1E40AF; }}
        """)
        btn_export.clicked.connect(self.export_csv)
        h_layout.addWidget(btn_export)

        layout.addWidget(header)

        # ═══════════════════════════════════════
        # MAIN CONTENT (Split: Left chart + Right info)
        # ═══════════════════════════════════════
        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)

        c_layout = QHBoxLayout()
        c_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(20), UIScaling.scale(24), UIScaling.scale(24))
        c_layout.setSpacing(UIScaling.scale(24))

        # --- LEFT: Chart & Summary ---
        left_frame = QFrame()
        left_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(16)}px;
            }}
        """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(UIScaling.scale(28), UIScaling.scale(24), UIScaling.scale(28), UIScaling.scale(24))
        left_layout.setSpacing(UIScaling.scale(16))

        # Pie Chart
        self.pie_chart = PieChartWidget()
        self.pie_chart.setMinimumHeight(UIScaling.scale(250))
        left_layout.addWidget(self.pie_chart, 1)

        # Total label
        self.lbl_total = QLabel("total : 0 sandals")
        self.lbl_total.setAlignment(Qt.AlignCenter)
        self.lbl_total.setStyleSheet(f"""
            font-size: {UIScaling.scale_font(15)}px;
            font-weight: 600;
            color: #6B7280;
            border: none;
        """)
        left_layout.addWidget(self.lbl_total)

        # Summary boxes row
        summary_row = QHBoxLayout()
        summary_row.setSpacing(UIScaling.scale(12))

        self.box_good = self._create_summary_box("0", "Good", "#10B981")
        self.box_oven = self._create_summary_box("0", "Oven", "#F59E0B")
        self.box_bs = self._create_summary_box("0", "BS", "#EF4444")

        summary_row.addWidget(self.box_good)
        summary_row.addWidget(self.box_oven)
        summary_row.addWidget(self.box_bs)
        summary_row.addStretch()

        left_layout.addLayout(summary_row)

        c_layout.addWidget(left_frame, 3)

        # --- RIGHT: WO Info ---
        right_frame = QFrame()
        right_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(16)}px;
            }}
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(UIScaling.scale(28), UIScaling.scale(24), UIScaling.scale(28), UIScaling.scale(24))
        right_layout.setSpacing(UIScaling.scale(14))

        # WO header
        lbl_wo_label = QLabel("Presets dari WO :")
        lbl_wo_label.setStyleSheet(f"font-size: {UIScaling.scale_font(12)}px; color: #9CA3AF; font-weight: 600; border: none; letter-spacing: 0.5px;")
        right_layout.addWidget(lbl_wo_label)

        self.lbl_wo_title = QLabel("")
        self.lbl_wo_title.setStyleSheet(f"font-size: {UIScaling.scale_font(22)}px; font-weight: 800; color: #111827; border: none;")
        self.lbl_wo_title.setWordWrap(True)
        right_layout.addWidget(self.lbl_wo_title)

        # Separator
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #E5E7EB; border: none;")
        right_layout.addWidget(line)

        # Info rows
        info_grid = QVBoxLayout()
        info_grid.setSpacing(UIScaling.scale(12))

        self.info_plant = self._make_info_row("Plant", info_grid)
        self.info_shift = self._make_info_row("Shift", info_grid)
        self.info_prod_date = self._make_info_row("Tanggal produksi", info_grid)
        self.info_finish_date = self._make_info_row("Tanggal selesai", info_grid)
        self.info_mps = self._make_info_row("MPS", info_grid)

        right_layout.addLayout(info_grid)
        right_layout.addStretch()

        c_layout.addWidget(right_frame, 2)

        # ═══════════════════════════════════════
        # BOTTOM CONTENT (Table for Per-SKU breakdown)
        # ═══════════════════════════════════════
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1.5px solid #E5E7EB;
                border-radius: {UIScaling.scale(16)}px;
            }}
        """)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(UIScaling.scale(24), UIScaling.scale(20), UIScaling.scale(24), UIScaling.scale(20))
        bottom_layout.setSpacing(UIScaling.scale(12))

        lbl_table_title = QLabel("Detail Per SKU & Size")
        lbl_table_title.setStyleSheet(f"font-size: {UIScaling.scale_font(18)}px; font-weight: 700; color: #111827; border: none;")
        bottom_layout.addWidget(lbl_table_title)

        self.sku_table = QTableWidget()
        self.sku_table.setColumnCount(5)
        self.sku_table.setHorizontalHeaderLabels(["SKU", "Size", "Good", "Oven", "BS"])
        self.sku_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sku_table.verticalHeader().setVisible(False)
        self.sku_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sku_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sku_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid #E5E7EB;
                border-radius: {UIScaling.scale(8)}px;
                background-color: white;
                gridline-color: #E5E7EB;
                font-size: {UIScaling.scale_font(14)}px;
            }}
            QHeaderView::section {{
                background-color: #F9FAFB;
                padding: 8px;
                border: 1px solid #E5E7EB;
                font-weight: 600;
                color: #374151;
            }}
        """)
        bottom_layout.addWidget(self.sku_table)

        scroll_layout.addLayout(c_layout)
        
        # Wrap bottom_frame in a layout with margins to match c_layout
        bottom_wrapper = QHBoxLayout()
        bottom_wrapper.setContentsMargins(UIScaling.scale(24), 0, UIScaling.scale(24), UIScaling.scale(24))
        bottom_wrapper.addWidget(bottom_frame)
        scroll_layout.addLayout(bottom_wrapper)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

    def _create_summary_box(self, value, label, color):
        box = QFrame()
        box.setFixedSize(UIScaling.scale(100), UIScaling.scale(80))
        box.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: {UIScaling.scale(12)}px;
                border: none;
            }}
        """)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(0, UIScaling.scale(8), 0, UIScaling.scale(8))
        box_layout.setSpacing(UIScaling.scale(2))
        box_layout.setAlignment(Qt.AlignCenter)

        lbl_val = QLabel(value)
        lbl_val.setAlignment(Qt.AlignCenter)
        lbl_val.setStyleSheet(f"""
            font-size: {UIScaling.scale_font(24)}px;
            font-weight: 800;
            color: white;
            border: none;
        """)
        lbl_val.setObjectName("val")
        box_layout.addWidget(lbl_val)

        lbl_name = QLabel(label)
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setStyleSheet(f"""
            font-size: {UIScaling.scale_font(13)}px;
            font-weight: 700;
            color: rgba(255,255,255,0.9);
            border: none;
        """)
        box_layout.addWidget(lbl_name)

        return box

    def _make_info_row(self, label_text, parent_layout):
        row = QHBoxLayout()
        row.setSpacing(UIScaling.scale(16))

        lbl = QLabel(label_text)
        lbl.setFixedWidth(UIScaling.scale(150))
        lbl.setStyleSheet(f"font-size: {UIScaling.scale_font(14)}px; font-weight: 600; color: #6B7280; border: none;")
        row.addWidget(lbl)

        val = QLabel("")
        val.setStyleSheet(f"font-size: {UIScaling.scale_font(15)}px; font-weight: 700; color: #111827; border: none;")
        row.addWidget(val, 1)

        parent_layout.addLayout(row)
        return val

    # ─── LOAD DATA ────────────────────────────────────────

    def load_record(self, record):
        self.current_record = record

        # WO Info
        wo = record.get("wo_number", "Unknown")
        machine = record.get("machine", "")
        self.lbl_wo_title.setText(f"{wo} - {machine}" if machine else wo)

        self.info_plant.setText(record.get("plant", "-"))
        self.info_shift.setText(record.get("shift", "-"))
        self.info_prod_date.setText(record.get("production_date", "-"))
        self.info_finish_date.setText(record.get("finished_at", "-") or "-")
        self.info_mps.setText(record.get("mps", "-"))

        # Counts
        counts = record.get("counts", {})
        good = counts.get("TOTAL GOOD", 0)
        oven = counts.get("OVEN 1", 0) + counts.get("OVEN 2", 0)
        bs = counts.get("TOTAL BS", 0)
        total = good + oven + bs

        self.lbl_total.setText(f"total : {total} sandals")

        # Update summary boxes
        self._update_box_value(self.box_good, good)
        self._update_box_value(self.box_oven, oven)
        self._update_box_value(self.box_bs, bs)

        # Pie chart
        pie_data = []
        if good > 0:
            pie_data.append((good, "#10B981", "Good"))
        if oven > 0:
            pie_data.append((oven, "#F59E0B", "Oven"))
        if bs > 0:
            pie_data.append((bs, "#EF4444", "BS"))
        self.pie_chart.set_data(pie_data)

        # ─── Load Per-SKU Counts into Table ───
        per_sku_counts = record.get("per_sku_counts", {})
        preset_id = record.get("preset_id")
        
        # Load profiles map to find the presets array
        profiles_file = os.path.join("output", "settings", "profiles.json")
        profiles = JsonUtility.load_from_json(profiles_file) or []
        target_profile = None
        for p in profiles:
            if p.get("id") == preset_id:
                target_profile = p
                break

        presets_arr = target_profile.get("presets", []) if target_profile else []
        self._populate_table(presets_arr, per_sku_counts)

    def _populate_table(self, presets_arr, per_sku_counts):
        self.sku_table.setRowCount(0)
        
        # Build merged rows (combine multiple indices into valid entries)
        # Even if profile was deleted or modified, we try to match indices
        row_idx = 0
        for idx_str, counts in per_sku_counts.items():
            try:
                idx = int(idx_str)
                if idx < len(presets_arr):
                    sku = presets_arr[idx].get("sku", "Unknown")
                    size = presets_arr[idx].get("size", "Unknown")
                else:
                    sku = f"Slot {idx}"
                    size = "-"
            except ValueError:
                sku = idx_str
                size = "-"

            c_good = counts.get("TOTAL GOOD", 0)
            c_oven = counts.get("OVEN 1", 0) + counts.get("OVEN 2", 0)
            c_bs = counts.get("TOTAL BS", 0)

            # Skip rows with all zero values
            if c_good == 0 and c_oven == 0 and c_bs == 0:
                continue
                
            self.sku_table.insertRow(row_idx)
            
            # SKU
            it_sku = QTableWidgetItem(str(sku))
            it_sku.setTextAlignment(Qt.AlignCenter)
            self.sku_table.setItem(row_idx, 0, it_sku)
            
            # Size
            it_size = QTableWidgetItem(str(size))
            it_size.setTextAlignment(Qt.AlignCenter)
            self.sku_table.setItem(row_idx, 1, it_size)
            
            # Good
            it_good = QTableWidgetItem(str(c_good))
            it_good.setTextAlignment(Qt.AlignCenter)
            self.sku_table.setItem(row_idx, 2, it_good)
            
            # Oven
            it_oven = QTableWidgetItem(str(c_oven))
            it_oven.setTextAlignment(Qt.AlignCenter)
            self.sku_table.setItem(row_idx, 3, it_oven)
            
            # BS
            it_bs = QTableWidgetItem(str(c_bs))
            it_bs.setTextAlignment(Qt.AlignCenter)
            self.sku_table.setItem(row_idx, 4, it_bs)
            
            row_idx += 1

    def _update_box_value(self, box, value):
        for child in box.findChildren(QLabel):
            if child.objectName() == "val":
                child.setText(str(value))
                break

    def go_back(self):
        if self.controller:
            self.controller.go_to_reports()

    def export_csv(self):
        if not self.current_record:
            QMessageBox.warning(self, "Export", "No record loaded.")
            return
            
        default_name = f"Report_{self.current_record.get('wo_number', 'unknown')}_{self.current_record.get('production_date', 'date').replace('/', '-')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Detail Report", default_name, "CSV Files (*.csv)")
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header Details
                writer.writerow(["REPORT DETAIL"])
                writer.writerow(["WO Number:", self.current_record.get('wo_number', '-')])
                writer.writerow(["Machine:", self.current_record.get('machine', '-')])
                writer.writerow(["Plant:", self.current_record.get('plant', '-')])
                writer.writerow(["Shift:", self.current_record.get('shift', '-')])
                writer.writerow(["Production Date:", self.current_record.get('production_date', '-')])
                writer.writerow(["Finished At:", self.current_record.get('finished_at', '-')])
                writer.writerow(["MPS:", self.current_record.get('mps', '-')])
                writer.writerow([])
                
                # Summary
                counts = self.current_record.get("counts", {})
                good = counts.get("TOTAL GOOD", 0)
                oven = counts.get("OVEN 1", 0) + counts.get("OVEN 2", 0)
                bs = counts.get("TOTAL BS", 0)
                total = good + oven + bs
                
                writer.writerow(["SUMMARY"])
                writer.writerow(["Total Sandals", "Good", "Oven", "BS"])
                writer.writerow([total, good, oven, bs])
                writer.writerow([])
                
                # Per SKU Breakdown
                writer.writerow(["PER SKU & SIZE BREAKDOWN"])
                writer.writerow(["SKU", "Size", "Good", "Oven", "BS"])
                
                rows = self.sku_table.rowCount()
                for r in range(rows):
                    sku = self.sku_table.item(r, 0).text()
                    size = self.sku_table.item(r, 1).text()
                    c_good = self.sku_table.item(r, 2).text()
                    c_oven = self.sku_table.item(r, 3).text()
                    c_bs = self.sku_table.item(r, 4).text()
                    
                    writer.writerow([sku, size, c_good, c_oven, c_bs])
                    
            QMessageBox.information(self, "Export Successful", f"Report saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{e}")
