"""
BookVault - Project Gutenberg Library Explorer
CS200 Data Structures & Algorithms - Project 1

Run:  python main.py
"""
import os
import sys

from PyQt5.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox, QSplitter, QTableView,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

import scraper
import searching
import sorting_algos as sa
from schema import FIELDS, HEADERS, NUMERIC_FIELDS, get_key

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.csv")
BENCHMARK_SAMPLE = 3000        # slow O(n^2) algorithms are benchmarked on this many rows
SLOW_WARNING_ROWS = 5000

STYLE = """
QWidget { background: #f1f5f9; color: #1e293b; font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; }
QFrame#banner { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:0.55 #7c3aed, stop:1 #06b6d4);
                border-radius: 14px; }
QLabel#bannerTitle { background: transparent; color: white; font-size: 21pt; font-weight: 700; }
QLabel#bannerSub { background: transparent; color: #e0e7ff; font-size: 10pt; }
QLabel#bannerCount { background: rgba(255,255,255,0.18); color: white; border-radius: 10px;
                     padding: 8px 16px; font-size: 11pt; font-weight: 600; }
QGroupBox { background: white; border: 1px solid #e2e8f0; border-radius: 12px; margin-top: 16px;
            padding: 14px 8px 8px 8px; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 2px 10px; color: white;
                   background: #4f46e5; border-radius: 8px; }
QGroupBox#scrapeBox::title { background: #16a34a; }
QGroupBox#searchBox::title { background: #0891b2; }
QGroupBox#filterBox::title { background: #db2777; }
QGroupBox#sortBox::title { background: #7c3aed; }
QGroupBox QLabel { background: transparent; font-weight: 500; }
QGroupBox QCheckBox { background: transparent; }
QLineEdit, QComboBox, QSpinBox { background: white; border: 1px solid #cbd5e1; border-radius: 7px;
                                 padding: 5px 8px; min-height: 22px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 2px solid #6366f1; }
QComboBox QAbstractItemView { background: white; selection-background-color: #6366f1; selection-color: white; }
QPushButton { border: none; border-radius: 8px; padding: 8px 16px; color: white; font-weight: 700;
              background: #64748b; }
QPushButton:hover { background: #475569; }
QPushButton:disabled { background: #cbd5e1; color: #94a3b8; }
QPushButton[role="success"] { background: #16a34a; }
QPushButton[role="success"]:hover { background: #15803d; }
QPushButton[role="primary"] { background: #4f46e5; }
QPushButton[role="primary"]:hover { background: #4338ca; }
QPushButton[role="warning"] { background: #f59e0b; }
QPushButton[role="warning"]:hover { background: #d97706; }
QPushButton[role="danger"] { background: #dc2626; }
QPushButton[role="danger"]:hover { background: #b91c1c; }
QPushButton[role="info"] { background: #0891b2; }
QPushButton[role="info"]:hover { background: #0e7490; }
QPushButton[role="purple"] { background: #7c3aed; }
QPushButton[role="purple"]:hover { background: #6d28d9; }
QPushButton[role="orange"] { background: #ea580c; }
QPushButton[role="orange"]:hover { background: #c2410c; }
QPushButton[role="pink"] { background: #db2777; }
QPushButton[role="pink"]:hover { background: #be185d; }
QPushButton:disabled[role] { background: #cbd5e1; color: #94a3b8; }
QTableView { background: white; alternate-background-color: #eef2ff; gridline-color: #e2e8f0;
             border: 1px solid #e2e8f0; border-radius: 10px; selection-background-color: #6366f1;
             selection-color: white; }
QHeaderView::section { background: #1e1b4b; color: white; padding: 8px; border: none;
                       border-right: 1px solid #3730a3; font-weight: 700; }
QTextEdit { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px; }
QProgressBar { border: 1px solid #cbd5e1; border-radius: 9px; text-align: center; background: white;
               min-height: 20px; font-weight: 600; }
QProgressBar::chunk { border-radius: 8px;
                      background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #06b6d4); }
QLabel[role="pill"] { background: #ede9fe; color: #5b21b6; border-radius: 8px; padding: 7px 12px; font-weight: 600; }
QLabel[role="status"] { background: #e0f2fe; color: #075985; border-radius: 8px; padding: 7px 12px; font-weight: 600; }
QLabel[role="scrape"] { background: #dcfce7; color: #166534; border-radius: 8px; padding: 6px 12px; font-weight: 600; }
QScrollBar:vertical { background: #f1f5f9; width: 12px; }
QScrollBar::handle:vertical { background: #a5b4fc; border-radius: 6px; min-height: 24px; }
QSplitter::handle { background: #cbd5e1; }
"""


# ------------------------------------------------------------------ helpers
def make_button(text, role, handler):
    b = QPushButton(text)
    b.setProperty("role", role)
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(handler)
    return b


def make_label(text, role):
    lab = QLabel(text)
    lab.setProperty("role", role)
    lab.setWordWrap(True)
    return lab


class FuncThread(QThread):
    """Runs a function in the background so the window does not freeze."""
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(str(e))


class ScraperBridge(QObject):
    """Scraper threads emit these signals; Qt delivers them safely to the UI thread."""
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str)


class BookModel(QAbstractTableModel):
    """Table model: shows the rows listed in window.view (indexes into window.data)."""

    def __init__(self, window):
        super().__init__()
        self.window = window

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.window.view)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(FIELDS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        col = FIELDS[index.column()]
        if role == Qt.DisplayRole:
            row = self.window.data[self.window.view[index.row()]]
            return str(row.get(col, ""))
        if role == Qt.TextAlignmentRole and col in NUMERIC_FIELDS:
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return HEADERS[FIELDS[section]]
            return str(section + 1)
        return None

    def refresh(self):
        self.beginResetModel()
        self.endResetModel()


class RecordDialog(QDialog):
    """Add / Edit form for one book."""

    def __init__(self, parent, row=None):
        super().__init__(parent)
        self.setWindowTitle("Edit book" if row else "Add book")
        self.edits = {}
        form = QFormLayout()
        for f in FIELDS:
            edit = QLineEdit(str(row.get(f, "")) if row else "")
            self.edits[f] = edit
            form.addRow(HEADERS[f], edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.check_and_accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(560, 200)

    def check_and_accept(self):
        if not self.edits["title"].text().strip():
            QMessageBox.warning(self, "Missing", "Title is required.")
            return
        for f in NUMERIC_FIELDS:
            text = self.edits[f].text().strip()
            if text:
                try:
                    float(text)
                except ValueError:
                    QMessageBox.warning(self, "Invalid", f"{HEADERS[f]} must be a number.")
                    return
        self.accept()

    def values(self):
        return {f: e.text().strip() for f, e in self.edits.items()}


# -------------------------------------------------------------- main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BookVault - Project Gutenberg Library Explorer")
        self.resize(1420, 920)

        self.data = []            # all records (list of dicts)
        self.master = []          # order of ALL rows (indexes into data)
        self.filter_set = None    # None = no filter, else set of matching row indexes
        self.view = []            # rows currently shown, in shown order
        self.levels = []          # multi-level sort levels: (column, desc)
        self.scraper = None
        self.bridge = ScraperBridge()
        self.bridge.progress.connect(self.on_scrape_progress)
        self.bridge.log.connect(lambda t: self.scrape_status.setText(t))
        self.bridge.finished.connect(self.on_scrape_finished)
        self.worker = None
        self.live_timer = QTimer(self)          # refreshes the table while scraping
        self.live_timer.setInterval(2500)
        self.live_timer.timeout.connect(self.live_refresh)

        self.model = BookModel(self)
        self.build_ui()
        self.load_data()

    # ------------------------------------------------------------- UI build
    def build_ui(self):
        central = QWidget()
        scroll = QScrollArea()                 # small screens can scroll instead of squeezing
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(6)
        root.addWidget(self.build_banner())
        root.addWidget(self.build_scraper_box())

        controls = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self.build_search_box())
        left.addWidget(self.build_composite_box())
        left.addStretch()
        controls.addLayout(left, 1)
        controls.addWidget(self.build_sort_box(), 1)
        root.addLayout(controls)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setMinimumSectionSize(120)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.selectionModel().selectionChanged.connect(self.show_inspector)
        widths = [110, 300, 200, 120, 220, 300, 120, 120, 130, 130, 130, 170, 160, 130]
        for i, w in enumerate(widths):
            self.table.setColumnWidth(i, w)

        self.inspector = QTextEdit()
        self.inspector.setReadOnly(True)
        self.inspector.setPlaceholderText("Book Inspector: select a book to see all its details here.")
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.inspector)
        splitter.setSizes([1050, 340])
        splitter.setMinimumHeight(320)
        root.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        bottom.addWidget(make_button("+ Add", "success", self.add_record))
        bottom.addWidget(make_button("Edit", "primary", self.edit_record))
        bottom.addWidget(make_button("Delete", "danger", self.delete_record))
        bottom.addWidget(make_button("Reload CSV", "neutral", self.load_data))
        bottom.addStretch()
        self.count_label = make_label("", "pill")
        bottom.addWidget(self.count_label)
        root.addLayout(bottom)
        self.status = make_label("Ready", "status")
        root.addWidget(self.status)

    def build_banner(self):
        banner = QFrame()
        banner.setObjectName("banner")
        lay = QHBoxLayout(banner)
        lay.setContentsMargins(22, 14, 22, 14)
        titles = QVBoxLayout()
        title = QLabel("BookVault")
        title.setObjectName("bannerTitle")
        sub = QLabel("Project Gutenberg Library Explorer  -  scrape, search, filter and sort thousands of books")
        sub.setObjectName("bannerSub")
        titles.addWidget(title)
        titles.addWidget(sub)
        lay.addLayout(titles)
        lay.addStretch()
        self.banner_count = QLabel("0 books")
        self.banner_count.setObjectName("bannerCount")
        lay.addWidget(self.banner_count)
        return banner

    def build_scraper_box(self):
        box = QGroupBox("1. Data collection (Project Gutenberg book pages)")
        box.setObjectName("scrapeBox")
        lay = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Target records:"))
        self.target_spin = QSpinBox()
        self.target_spin.setRange(100, 80000)
        self.target_spin.setValue(15500)
        row.addWidget(self.target_spin)
        self.btn_start = make_button("▶ Start", "success", self.start_scraping)
        self.btn_pause = make_button("⏸ Pause", "warning", self.pause_scraping)
        self.btn_resume = make_button("⏯ Resume", "info", self.resume_scraping)
        self.btn_stop = make_button("⏹ Stop", "danger", self.stop_scraping)
        for b in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_stop):
            row.addWidget(b)
        self.progress = QProgressBar()
        self.progress.setFormat("%v / %m books")
        row.addWidget(self.progress, 1)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Bonus - scrape one URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.gutenberg.org/ebooks/84")
        row2.addWidget(self.url_edit, 1)
        row2.addWidget(make_button("Scrape URL", "purple", self.scrape_url))
        lay.addLayout(row2)
        self.scrape_status = make_label("Scraper idle.", "scrape")
        lay.addWidget(self.scrape_status)
        self.set_scraper_buttons(running=False)
        return box

    def column_combo(self):
        combo = QComboBox()
        for f in FIELDS:
            combo.addItem(HEADERS[f], f)
        return combo

    def build_search_box(self):
        box = QGroupBox("2. Search (one column)")
        box.setObjectName("searchBox")
        lay = QHBoxLayout(box)
        self.s_col = self.column_combo()
        self.s_op = QComboBox()
        self.s_op.setMinimumWidth(115)
        self.s_value = QLineEdit()
        self.s_value.setPlaceholderText("value")
        self.s_algo = QComboBox()
        self.s_algo.addItems(searching.SEARCH_ALGORITHMS.keys())
        self.s_algo.setToolTip("\n".join(f"{k}: {v}" for k, v in searching.SEARCH_ALGORITHMS.items()))
        self.s_col.currentIndexChanged.connect(self.update_search_ops)
        self.update_search_ops()
        for w in (self.s_col, self.s_op, self.s_value, self.s_algo,
                  make_button("Search", "info", self.run_search),
                  make_button("Clear", "neutral", self.clear_filter)):
            lay.addWidget(w)
        return box

    def build_composite_box(self):
        box = QGroupBox("3. Composite filter (AND / OR / NOT)")
        box.setObjectName("filterBox")
        lay = QVBoxLayout(box)
        self.c_rows = []
        for n in range(3):
            row = QHBoxLayout()
            if n > 0:
                conn = QComboBox()
                conn.addItems(["AND", "OR"])
                row.addWidget(conn)
            else:
                conn = None
                lbl = QLabel("  IF  ")
                lbl.setMinimumWidth(conn.sizeHint().width() if conn else 56)
                row.addWidget(lbl)
            neg = QCheckBox("NOT")
            col = self.column_combo()
            op = QComboBox()
            op.setMinimumWidth(115)
            value = QLineEdit()
            value.setPlaceholderText("value (empty = skip this row)")
            col.currentIndexChanged.connect(lambda _, c=col, o=op: self.fill_ops(c, o))
            self.fill_ops(col, op)
            for w in (neg, col, op, value):
                row.addWidget(w)
            lay.addLayout(row)
            self.c_rows.append((conn, neg, col, op, value))
        btn_row = QHBoxLayout()
        btn_row.addWidget(make_button("Apply composite filter", "pink", self.run_composite))
        btn_row.addWidget(make_button("Clear", "neutral", self.clear_filter))
        lay.addLayout(btn_row)
        return box

    def build_sort_box(self):
        box = QGroupBox("4. Sorting")
        box.setObjectName("sortBox")
        lay = QVBoxLayout(box)
        row = QHBoxLayout()
        self.o_col = self.column_combo()
        self.o_algo = QComboBox()
        self.o_order = QComboBox()
        self.o_order.addItems(["Ascending", "Descending"])
        self.o_scope = QComboBox()
        self.o_scope.addItems(["Full dataset", "Filtered results only"])
        self.o_col.currentIndexChanged.connect(self.update_sort_algorithms)
        self.update_sort_algorithms()
        for label, w in (("Column", self.o_col), ("Order", self.o_order), ("Scope", self.o_scope)):
            row.addWidget(QLabel(label))
            row.addWidget(w)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel("Algorithm"))
        row.addWidget(self.o_algo, 1)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(make_button("Sort", "purple", self.run_sort))
        row.addWidget(make_button("Benchmark all algorithms", "orange", self.run_benchmark))
        lay.addLayout(row)
        self.sort_result = make_label("No sort yet.", "pill")
        lay.addWidget(self.sort_result)

        lay.addWidget(QLabel("Multi-level sort (first level = most important):"))
        row = QHBoxLayout()
        self.m_col = self.column_combo()
        self.m_order = QComboBox()
        self.m_order.addItems(["Ascending", "Descending"])
        for w in (self.m_col, self.m_order,
                  make_button("Add level", "info", self.add_level),
                  make_button("Clear", "neutral", self.clear_levels)):
            row.addWidget(w)
        lay.addLayout(row)
        lay.addWidget(make_button("Apply multi-level sort", "primary", self.run_multi_sort))
        self.levels_label = make_label("Levels: (none)", "pill")
        lay.addWidget(self.levels_label)
        lay.addStretch()
        return box

    # ------------------------------------------------------- combo helpers
    def fill_ops(self, col_combo, op_combo):
        op_combo.clear()
        op_combo.addItems(searching.ops_for(col_combo.currentData()))

    def update_search_ops(self):
        self.fill_ops(self.s_col, self.s_op)

    def update_sort_algorithms(self):
        """Counting / Radix / Bucket only work on number columns."""
        numeric = self.o_col.currentData() in NUMERIC_FIELDS
        self.o_algo.clear()
        for name, info in sa.ALGORITHMS.items():
            if info["numeric_only"] and not numeric:
                continue
            self.o_algo.addItem(sa.algorithm_label(name), name)

    # --------------------------------------------------------------- data
    def load_data(self):
        self.data = scraper.read_csv(CSV_PATH)
        self.master = list(range(len(self.data)))
        self.filter_set = None
        self.refresh_view()
        self.status.setText(f"Loaded {len(self.data)} books from books.csv")
        self.progress.setMaximum(max(self.target_spin.value(), 1))
        self.progress.setValue(min(len(self.data), self.progress.maximum()))

    def refresh_view(self):
        if self.filter_set is None:
            self.view = list(self.master)
        else:
            self.view = [i for i in self.master if i in self.filter_set]
        self.model.refresh()
        self.update_counts()

    def update_counts(self):
        text = f"{len(self.view)} shown / {len(self.data)} total"
        if self.filter_set is not None:
            text += "  (filter active)"
        self.count_label.setText(text)
        self.banner_count.setText(f"{len(self.data):,} books")

    def live_refresh(self):
        """While scraping: add the newly saved books to the table without resetting it."""
        rows = scraper.read_csv(CSV_PATH)
        have = {str(r.get("ebook_no")) for r in self.data}
        new = [r for r in rows
               if r.get("ebook_no") and r.get("title") and str(r["ebook_no"]) not in have]
        if not new:
            return
        start = len(self.data)
        self.data.extend(new)
        self.master.extend(range(start, len(self.data)))
        if self.filter_set is None:                      # keep scroll position and selection
            old = len(self.view)
            self.model.beginInsertRows(QModelIndex(), old, old + len(new) - 1)
            self.view.extend(range(start, len(self.data)))
            self.model.endInsertRows()
        self.update_counts()

    def save_data(self):
        scraper.write_csv(CSV_PATH, self.data)

    def selected_row_index(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        return self.view[sel[0].row()]

    def show_inspector(self):
        i = self.selected_row_index()
        if i is None:
            return
        r = self.data[i]
        subjects = [s.strip() for s in str(r.get("subjects", "")).split(";") if s.strip()]
        chips = "".join(
            f"<span style='background:#e0e7ff;color:#3730a3;padding:2px 8px;'>{s}</span>&nbsp; "
            for s in subjects) or "-"
        html = (
            f"<h2 style='color:#4f46e5;margin-bottom:0'>{r.get('title', '')}</h2>"
            f"<p style='color:#64748b;margin-top:2px'>by {r.get('author', '') or 'Unknown'}</p>"
            f"<table cellpadding='3'>"
            f"<tr><td><b>eBook #</b></td><td>{r.get('ebook_no', '')}</td></tr>"
            f"<tr><td><b>Language</b></td><td>{r.get('language', '')}</td></tr>"
            f"<tr><td><b>LoC class</b></td><td>{r.get('loc_class', '')}</td></tr>"
            f"<tr><td><b>Category</b></td><td>{r.get('category', '')}</td></tr>"
            f"<tr><td><b>Released</b></td><td>{r.get('release_date', '')}</td></tr>"
            f"<tr><td><b>Last update</b></td><td>{r.get('last_update', '')}</td></tr>"
            f"<tr><td><b>Copyright</b></td><td>{r.get('copyright', '')}</td></tr>"
            f"<tr><td><b>Downloads (30d)</b></td><td><b style='color:#16a34a'>{r.get('downloads_30d', '')}</b></td></tr>"
            f"<tr><td><b>Reading ease</b></td><td>{r.get('reading_ease', '')}</td></tr>"
            f"</table>"
            f"<h4 style='color:#7c3aed'>Subjects ({len(subjects)})</h4><p>{chips}</p>"
            f"<p><a href='https://www.gutenberg.org/ebooks/{r.get('ebook_no', '')}'>Open on gutenberg.org</a></p>")
        self.inspector.setHtml(html)

    # -------------------------------------------------------------- CRUD
    def block_if_scraping(self):
        if self.scraper is not None:
            QMessageBox.information(self, "Scraper running",
                                    "Stop the scraper first, then edit the data.")
            return True
        return False

    def add_record(self):
        if self.block_if_scraping():
            return
        dlg = RecordDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            rec = dlg.values()
            if rec["ebook_no"] and any(str(r["ebook_no"]) == rec["ebook_no"] for r in self.data):
                QMessageBox.warning(self, "Duplicate", "A book with this eBook # already exists.")
                return
            self.data.append(rec)
            new_index = len(self.data) - 1
            self.master.append(new_index)
            if self.filter_set is not None:
                self.filter_set.add(new_index)
            self.save_data()
            self.refresh_view()
            self.status.setText(f"Added '{rec['title']}' and saved.")

    def edit_record(self):
        if self.block_if_scraping():
            return
        i = self.selected_row_index()
        if i is None:
            QMessageBox.information(self, "Edit", "Select a row first.")
            return
        dlg = RecordDialog(self, self.data[i])
        if dlg.exec_() == QDialog.Accepted:
            self.data[i] = dlg.values()
            self.save_data()
            self.refresh_view()
            self.status.setText("Record updated and saved.")

    def delete_record(self):
        if self.block_if_scraping():
            return
        i = self.selected_row_index()
        if i is None:
            QMessageBox.information(self, "Delete", "Select a row first.")
            return
        title = self.data[i]["title"]
        if QMessageBox.question(self, "Delete", f"Delete '{title}'?") != QMessageBox.Yes:
            return
        self.data.pop(i)
        shift = lambda x: x - 1 if x > i else x     # indexes after i move one step up
        self.master = [shift(x) for x in self.master if x != i]
        if self.filter_set is not None:
            self.filter_set = {shift(x) for x in self.filter_set if x != i}
        self.save_data()
        self.refresh_view()
        self.status.setText(f"Deleted '{title}' and saved.")

    # ----------------------------------------------------------- scraping
    def set_scraper_buttons(self, running, paused=False):
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running and not paused)
        self.btn_resume.setEnabled(running and paused)
        self.btn_stop.setEnabled(running)
        self.target_spin.setEnabled(not running)

    def start_scraping(self):
        target = self.target_spin.value()
        self.progress.setMaximum(target)
        b = self.bridge
        self.scraper = scraper.ScraperController(
            CSV_PATH, target,
            on_progress=lambda d, t: b.progress.emit(d, t),
            on_log=lambda s: b.log.emit(s),
            on_finished=lambda r: b.finished.emit(r))
        self.scraper.start()
        self.live_timer.start()
        self.set_scraper_buttons(running=True)
        self.scrape_status.setText("Scraping started...")

    def pause_scraping(self):
        if self.scraper:
            self.scraper.pause()
            self.set_scraper_buttons(running=True, paused=True)
            self.scrape_status.setText("Paused.")

    def resume_scraping(self):
        if self.scraper:
            self.scraper.resume()
            self.set_scraper_buttons(running=True, paused=False)
            self.scrape_status.setText("Resumed.")

    def stop_scraping(self):
        if self.scraper:
            self.scraper.stop()
            self.scrape_status.setText("Stopping...")

    def on_scrape_progress(self, done, target):
        self.progress.setMaximum(target)
        self.progress.setValue(min(done, target))
        self.scrape_status.setText(f"Scraped {done} / {target} books")

    def on_scrape_finished(self, reason):
        self.scraper = None
        self.live_timer.stop()
        self.set_scraper_buttons(running=False)
        messages = {
            "finished": "Target reached. Data saved to books.csv.",
            "stopped": "Stopped. Progress is saved; press Start to continue later.",
            "blocked": "The website blocked or challenged the requests, so scraping stopped. "
                       "Books collected so far are saved.",
            "ran out of books": "No more books left to visit.",
            "error": "Stopped because of a network error (check your internet connection). "
                     "Books collected so far are saved.",
        }
        self.scrape_status.setText(messages.get(reason, reason))
        self.load_data()

    def scrape_url(self):
        if self.block_if_scraping():
            return
        url = self.url_edit.text().strip()
        try:
            rec = scraper.scrape_single_url(url, CSV_PATH)
        except scraper.BotChallenge as e:
            QMessageBox.warning(self, "Blocked", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "Scrape URL", str(e))
            return
        self.load_data()
        self.scrape_status.setText(f"Added '{rec['title']}' from URL.")

    # ----------------------------------------------------------- filtering
    def apply_filter(self, hits):
        self.filter_set = set(hits)
        self.refresh_view()

    def clear_filter(self):
        self.filter_set = None
        self.refresh_view()
        self.status.setText("Filter cleared.")

    def run_search(self):
        text = self.s_value.text()
        if not text.strip():
            QMessageBox.information(self, "Search", "Type a value to search.")
            return
        try:
            hits, info = searching.search_column(
                self.master, self.s_col.currentData(), self.s_op.currentText(),
                text, self.s_algo.currentText(), self.data)
        except ValueError:
            QMessageBox.warning(self, "Search", "This column needs a number.")
            return
        self.apply_filter(hits)
        msg = (f"{len(hits)} match(es) using {info['algorithm']}: {info['ms']:.3f} ms, "
               f"{info['comparisons']} comparisons")
        self.status.setText(msg + ("  |  " + info["note"] if info["note"] else ""))

    def run_composite(self):
        conditions, connectors = [], []
        for conn, neg, col, op, value in self.c_rows:
            if not value.text().strip():
                continue
            if conditions and conn is not None:
                connectors.append(conn.currentText())
            conditions.append((neg.isChecked(), col.currentData(), op.currentText(), value.text()))
        if not conditions:
            QMessageBox.information(self, "Filter", "Fill at least one value.")
            return
        try:
            hits = searching.composite_filter(self.master, conditions, connectors, self.data)
        except ValueError:
            QMessageBox.warning(self, "Filter", "A numeric column needs a number as value.")
            return
        self.apply_filter(hits)
        self.status.setText(f"Composite filter: {len(hits)} match(es).")

    # ------------------------------------------------------------- sorting
    def sort_indices(self):
        """Rows to sort depending on the chosen scope."""
        if self.o_scope.currentIndex() == 0:
            return list(self.master), "full"
        return list(self.view), "filtered"

    def apply_order(self, order, scope):
        if scope == "full":
            self.master = order
            self.refresh_view()
        else:
            self.view = order            # only the shown rows are re-ordered
            self.model.refresh()

    def run_in_background(self, fn, on_done):
        self.worker = FuncThread(fn)
        self.worker.done.connect(on_done)
        self.worker.failed.connect(lambda m: QMessageBox.warning(self, "Error", m))
        self.setCursor(Qt.WaitCursor)
        self.worker.finished.connect(lambda: self.setCursor(Qt.ArrowCursor))
        self.worker.start()

    def run_sort(self):
        if not self.data:
            return
        col = self.o_col.currentData()
        name = self.o_algo.currentData()
        desc = self.o_order.currentIndex() == 1
        indices, scope = self.sort_indices()
        if sa.ALGORITHMS[name]["slow"] and len(indices) > SLOW_WARNING_ROWS:
            ans = QMessageBox.question(
                self, "Slow algorithm",
                f"{name} is O(n²) and {len(indices)} rows may take a few minutes. Continue?")
            if ans != QMessageBox.Yes:
                return
        items = [(get_key(self.data[i], col), i) for i in indices]

        def work():
            return sa.run_sort(name, items, desc)

        def done(res):
            self.apply_order(res["order"], scope)
            self.sort_result.setText(
                f"{name} on '{HEADERS[col]}' ({len(items)} rows): {res['ms']:.2f} ms | "
                f"{res['comparisons']} comparisons | {res['swaps']} swaps")
        self.run_in_background(work, done)

    def run_benchmark(self):
        if not self.data:
            return
        col = self.o_col.currentData()
        desc = self.o_order.currentIndex() == 1
        indices, _ = self.sort_indices()
        numeric = col in NUMERIC_FIELDS
        items_all = [(get_key(self.data[i], col), i) for i in indices]

        def work():
            results = []
            for name, info in sa.ALGORITHMS.items():
                if info["numeric_only"] and not numeric:
                    continue
                items, note = items_all, f"all {len(items_all)} rows"
                if info["slow"] and len(items_all) > BENCHMARK_SAMPLE:
                    items = items_all[:BENCHMARK_SAMPLE]
                    note = f"first {BENCHMARK_SAMPLE} rows only (too slow for all)"
                try:
                    r = sa.run_sort(name, items, desc)
                    results.append((name, info, r, note))
                except ValueError as e:
                    results.append((name, info, None, str(e)))
            return results

        def done(results):
            self.show_benchmark(col, results)
        self.run_in_background(work, done)

    def show_benchmark(self, col, results):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Benchmark - {HEADERS[col]}")
        dlg.resize(1000, 470)
        table = QTableWidget(len(results), 7)
        table.setHorizontalHeaderLabels(["Algorithm", "Complexity", "Stable", "Time (ms)",
                                         "Comparisons", "Swaps", "Ran on"])
        fastest = min((r["ms"] for _, _, r, _ in results if r), default=None)
        for row, (name, info, r, note) in enumerate(results):
            cells = [name, info["complexity"], "yes" if info["stable"] else "no",
                     f"{r['ms']:.2f}" if r else "-", str(r["comparisons"]) if r else "-",
                     str(r["swaps"]) if r else "-", note]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if r and r["ms"] == fastest:
                    item.setBackground(QColor("#bbf7d0"))
                table.setItem(row, c, item)
        table.resizeColumnsToContents()
        lay = QVBoxLayout(dlg)
        lay.addWidget(table)
        lay.addWidget(make_label("Green = fastest. Rows that say 'first 3000 rows only' are not "
                                 "directly comparable with full-size runs.", "pill"))
        dlg.exec_()

    # -------------------------------------------------------- multi-level
    def add_level(self):
        col = self.m_col.currentData()
        if any(c == col for c, _ in self.levels):
            QMessageBox.information(self, "Levels", "This column is already a level.")
            return
        self.levels.append((col, self.m_order.currentIndex() == 1))
        self.update_levels_label()

    def clear_levels(self):
        self.levels = []
        self.update_levels_label()

    def update_levels_label(self):
        if not self.levels:
            self.levels_label.setText("Levels: (none)")
            return
        parts = [f"{i + 1}. {HEADERS[c]} {'desc' if d else 'asc'}"
                 for i, (c, d) in enumerate(self.levels)]
        self.levels_label.setText("Levels: " + "  >  ".join(parts))

    def run_multi_sort(self):
        if len(self.levels) < 2:
            QMessageBox.information(self, "Multi-level", "Add at least two levels.")
            return
        indices, scope = self.sort_indices()
        data = self.data
        levels = [((lambda i, c=c: get_key(data[i], c)), d) for c, d in self.levels]

        def work():
            return sa.multi_level_sort(indices, levels)

        def done(res):
            self.apply_order(res["order"], scope)
            self.sort_result.setText(
                f"Multi-level sort ({len(self.levels)} levels, Merge Sort per level): "
                f"{res['ms']:.2f} ms | {res['comparisons']} comparisons | {res['swaps']} swaps")
        self.run_in_background(work, done)

    def closeEvent(self, event):
        if self.scraper:
            self.scraper.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec_())