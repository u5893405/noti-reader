from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QSlider, QFormLayout, QLineEdit, QCheckBox, QDialog, QGridLayout, QTableWidgetItem, QTableWidget, QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread
import sys
from noti_reader import NotificationReader

class NotificationThread(QThread):
    newText = pyqtSignal(str)

    def __init__(self):
        super(NotificationThread, self).__init__()
        self.reader = NotificationReader(callback=self.new_text_emitted)

    def run(self):
        self.reader.start()

    def stop(self):
        if self.reader:  # Make sure reader exists before calling stop
            self.reader.stop()

    def new_text_emitted(self, text):
        self.newText.emit(text)

class FilterSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(FilterSettingsDialog, self).__init__(parent)
        layout = QGridLayout()
        layout.addWidget(QLabel("Reading Filter Settings"), 0, 0)
        self.setMinimumWidth(600)
        self.setMinimumHeight(600) 

        self.rule_table = QTableWidget(0, 3)
        self.rule_table.setHorizontalHeaderLabels(["Rule", "Entries", "Action"])
        layout.addWidget(self.rule_table, 7, 0, 1, 2)  # Spanning 1 row and 2 columns
        self.rule_table.itemClicked.connect(self.on_rule_clicked)
        self.rule_table.horizontalHeader().setStretchLastSection(True)
        self.rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        #self.rule_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        

        # Fields for source and entries
        layout.addWidget(QLabel("Source of notification:"), 1, 0)
        self.source_line_edit = QLineEdit()
        layout.addWidget(self.source_line_edit, 1, 1)

        layout.addWidget(QLabel("First entry (notification source name):"), 2, 0)
        self.first_entry_checkbox = QCheckBox()
        layout.addWidget(self.first_entry_checkbox, 2, 1)

        layout.addWidget(QLabel("Second entry:"), 3, 0)
        self.second_entry_checkbox = QCheckBox()
        layout.addWidget(self.second_entry_checkbox, 3, 1)

        layout.addWidget(QLabel("Third entry:"), 4, 0)
        self.third_entry_checkbox = QCheckBox()
        layout.addWidget(self.third_entry_checkbox, 4, 1)

        layout.addWidget(QLabel("Fourth entry:"), 5, 0)
        self.fourth_entry_checkbox = QCheckBox()
        layout.addWidget(self.fourth_entry_checkbox, 5, 1)

        self.apply_button = QPushButton('Apply')
        self.apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(self.apply_button, 6, 1)

        self.setLayout(layout)

    def update_rule_list(self):
        print(f"DEBUG: Current source_rules: {self.parent().thread.reader.source_rules}")  # Debug line
        self.rule_table.setRowCount(0)
        rules = self.parent().thread.reader.source_rules
        sorted_rules = sorted(rules.items(), key=lambda x: x[0].lower())

        for source, entries in rules.items():
            row_position = self.rule_table.rowCount()
            self.rule_table.insertRow(row_position)

            # Rule
            entries_display = ", ".join([str(e + 1) for e in entries])  # +1 to start counting from 1
            self.rule_table.setItem(row_position, 0, QTableWidgetItem(f"{source}"))
            self.rule_table.setItem(row_position, 1, QTableWidgetItem(entries_display))

            # Delete button
            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda checked, s=source: self.delete_rule(s))
            self.rule_table.setCellWidget(row_position, 2, delete_button)  

    def delete_rule(self, source):
        del self.parent().thread.reader.source_rules[source]
        self.parent().thread.reader.update_rules({})
        self.update_rule_list()

    @pyqtSlot(QTableWidgetItem)
    def on_rule_clicked(self, item):
        row = item.row()
        source_item = self.rule_table.item(row, 0)
        entries_item = self.rule_table.item(row, 1)
        source = source_item.text() if source_item else ""
        entries_str = entries_item.text().replace("[", "").replace("]", "").replace(" ", "") if entries_item else ""

        entries = list(map(int, entries_str.split(','))) if entries_str else []
        self.source_line_edit.setText(source.strip())

        self.first_entry_checkbox.setChecked(0 in entries)
        self.second_entry_checkbox.setChecked(1 in entries)
        self.third_entry_checkbox.setChecked(2 in entries)
        self.fourth_entry_checkbox.setChecked(3 in entries)

    # Call update_rule_list when the dialog is shown
    def exec_(self):
        self.update_rule_list()
        super().exec_()

    def get_settings(self):
        source = self.source_line_edit.text()
        first_entry = self.first_entry_checkbox.isChecked()
        second_entry = self.second_entry_checkbox.isChecked()
        third_entry = self.third_entry_checkbox.isChecked()
        fourth_entry = self.fourth_entry_checkbox.isChecked()
        
        entries_to_read = []
        if first_entry: entries_to_read.append(0)
        if second_entry: entries_to_read.append(1)
        if third_entry: entries_to_read.append(2)
        if fourth_entry: entries_to_read.append(3)
        
        return {source: entries_to_read}       

    def apply_settings(self):
        new_rules = self.get_settings()
        self.parent().thread.reader.update_rules(new_rules)
        self.update_rule_list()

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.status_label = QLabel('TTS Status: Stopped')
        layout.addWidget(self.status_label)

        self.reading_label = QLabel('Reading: None')
        layout.addWidget(self.reading_label)

        self.start_button = QPushButton('Start TTS')
        self.start_button.clicked.connect(self.start_tts)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton('Stop TTS')
        self.stop_button.clicked.connect(self.stop_tts)
        layout.addWidget(self.stop_button)

        self.speed_slider = QSlider(Qt.Horizontal)
        layout.addWidget(self.speed_slider)

        self.reading_filter_button = QPushButton('Reading Filter')
        self.reading_filter_button.clicked.connect(self.show_reading_filter)
        layout.addWidget(self.reading_filter_button)

        self.quit_button = QPushButton('Quit')
        self.quit_button.clicked.connect(self.quit_app)
        layout.addWidget(self.quit_button)

        self.setLayout(layout)
        self.setWindowTitle('TTS Control Panel')

        self.thread = NotificationThread()
        self.thread.newText.connect(self.update_reading_label)

    def show_reading_filter(self):  
        self.filter_settings_dialog = FilterSettingsDialog(parent=self)
        self.filter_settings_dialog.setWindowTitle("Reading Filter Settings")
        self.filter_settings_dialog.exec_()  

    def start_tts(self):
        self.status_label.setText('TTS Status: Started')
        self.thread.start()

    def stop_tts(self):
        self.status_label.setText('TTS Status: Stopped')
        self.thread.stop()

    @pyqtSlot(str)
    def update_reading_label(self, text):
        self.reading_label.setText(f'Reading: {text}')

    def show_filter_settings(self):
        dialog = FilterSettingsDialog()
        result = dialog.exec_()
        if result == QDialog.Accepted:
            new_rules = dialog.get_settings()
            self.thread.reader.update_rules(new_rules)    

    def quit_app(self):
        self.thread.stop()
        self.close()

app = QApplication(sys.argv)
ex = App()
ex.show()
sys.exit(app.exec_())
