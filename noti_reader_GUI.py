from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QSlider, QFormLayout, QLineEdit, QCheckBox, QDialog, QGridLayout, QTableWidgetItem, QTableWidget, QHeaderView, QComboBox, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread
import sys
import json
import logging
logger = logging.getLogger('')
if not logger.hasHandlers():
    logging.basicConfig(filename='/home/u0/Docs/my_coding_projects_2023/Notification_reader_TTS/logs/debug.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logger.addHandler(console)

from noti_reader import NotificationReader

class NotificationThread(QThread):
    newText = pyqtSignal(str)

    def __init__(self):
        super(NotificationThread, self).__init__()
        self.reader = NotificationReader(callback=self.new_text_emitted)

    def run(self):
        logging.debug("NotificationThread: Starting NotificationReader.")
        self.reader.start()

    def stop(self):
        logging.debug("NotificationThread: Stopping NotificationReader.")
        if self.reader:  # Make sure reader exists before calling stop
            self.reader.stop()

    def new_text_emitted(self, text):
        self.newText.emit(text)

class AdvancedRuleDialog(QDialog):
    advancedRuleSet = pyqtSignal(int, str)  # New signal
    def __init__(self, parent=None):
        super(AdvancedRuleDialog, self).__init__(parent)
        self.entry_index = None
        self.source = None
        layout = QVBoxLayout()
        self.advanced_rules = {}

        self.setWindowTitle("Advanced Rule Settings")

        # "If" section layout
        self.if_layout = QVBoxLayout()
        self.if_combo_box = QComboBox()
        self.if_combo_box.addItems(["Entry 1", "Entry 2", "Entry 3", "Entry 4"])
        self.if_condition_combo_box = QComboBox()
        self.if_condition_combo_box.addItems(["contains word", "contains symbol", "is in language", "has this amount of words"])
        self.if_value_edit = QLineEdit()

        if_condition_layout = QHBoxLayout()
        if_condition_layout.addWidget(self.if_combo_box)
        if_condition_layout.addWidget(self.if_condition_combo_box)
        if_condition_layout.addWidget(self.if_value_edit)

        self.if_layout.addLayout(if_condition_layout)
        layout.addLayout(self.if_layout)

        # "Then" section layout
        self.then_layout = QVBoxLayout()
        self.then_combo_box = QComboBox()
        self.then_combo_box.addItems(["Entry 1", "Entry 2", "Entry 3", "Entry 4"])
        self.then_action_combo_box = QComboBox()
        self.then_action_combo_box.addItems(["read", "do not read", "read certain words"])
        self.then_value_edit = QLineEdit()

        then_condition_layout = QHBoxLayout()
        then_condition_layout.addWidget(self.then_combo_box)
        then_condition_layout.addWidget(self.then_action_combo_box)
        then_condition_layout.addWidget(self.then_value_edit)

        self.then_layout.addLayout(then_condition_layout)
        layout.addLayout(self.then_layout)

        # Cancel and Apply buttons
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_and_close)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def apply_and_close(self):
        print("DEBUG: apply_and_close() has been triggered.")
        try:
            # Debug lines
            print(f"DEBUG: self.parent(): {self.parent()}")
            print(f"DEBUG: self.parent().thread: {self.parent().thread}")

            if not isinstance(self.parent(), FilterSettingsDialog):
                print("DEBUG: Parent is not of type FilterSettingsDialog.")
                return

            if not isinstance(self.parent().thread, NotificationThread):
                print("DEBUG: Parent's thread is not of type NotificationThread.")
                return
            
            if_rule = {
                "entry": self.if_combo_box.currentText(),
                "condition": self.if_condition_combo_box.currentText(),
                "value": self.if_value_edit.text()
            }

            then_rule = {
                "entry": self.then_combo_box.currentText(),
                "action": self.then_action_combo_box.currentText(),
                "value": self.then_value_edit.text()
            }

            advanced_rule = {"if": if_rule, "then": then_rule}
            advanced_rule_json = json.dumps(advanced_rule)
            
            # Debug line
            print(f"DEBUG: Applying advanced rule: {advanced_rule}")  
            
            # Save the advanced rule to the parent dialog
            self.parent().advanced_rules[self.entry_index] = advanced_rule  
            
            source = self.source
            self.parent().thread.reader.advanced_rules[source] = advanced_rule
            self.parent().thread.reader.save_advanced_rules()
            
            self.advancedRuleSet.emit(self.entry_index, advanced_rule_json)
            self.accept()  
            
            # Debug lines
            print(f"DEBUG: self.parent() type: {type(self.parent())}")  
            print(f"DEBUG: self.parent().thread type: {type(self.parent().thread)}")  
            
        except AttributeError:
            print(f"DEBUG: Caught AttributeError. self.parent(): {self.parent()}, type: {type(self.parent())}")
            print(f"DEBUG: self.parent().thread: {self.parent().thread}, type: {type(self.parent().thread)}")
            raise

class FilterSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(FilterSettingsDialog, self).__init__(parent)
        layout = QGridLayout()
        layout.addWidget(QLabel("Reading Filter Settings"), 0, 0)
        self.advanced_rules = {}
        self.setMinimumWidth(700)
        self.setMinimumHeight(600) 

        self.rule_table = QTableWidget(0, 3)
        self.rule_table.setHorizontalHeaderLabels(["Rule", "Entries", "Action"])
        layout.addWidget(self.rule_table, 7, 0, 1, 2)  # Spanning 1 row and 2 columns
        self.rule_table.itemClicked.connect(self.on_rule_clicked)
        #self.rule_table.horizontalHeader().setStretchLastSection(True)
        #self.rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        #self.rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
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

         # Add labels to indicate advanced rule
        self.first_advanced_rule_label = QLabel("Advanced Rule applied")
        self.second_advanced_rule_label = QLabel("Advanced Rule applied")
        self.third_advanced_rule_label = QLabel("Advanced Rule applied")
        self.fourth_advanced_rule_label = QLabel("Advanced Rule applied")

        layout.addWidget(self.first_advanced_rule_label, 2, 2)
        layout.addWidget(self.second_advanced_rule_label, 3, 2)
        layout.addWidget(self.third_advanced_rule_label, 4, 2)
        layout.addWidget(self.fourth_advanced_rule_label, 5, 2)

        for label in [self.first_advanced_rule_label, self.second_advanced_rule_label, self.third_advanced_rule_label, self.fourth_advanced_rule_label]:
            label.hide()  # Initially hidden

        # Add buttons to open AdvancedRuleDialog
        self.first_advanced_rule_button = QPushButton("Advanced")
        self.second_advanced_rule_button = QPushButton("Advanced")
        self.third_advanced_rule_button = QPushButton("Advanced")
        self.fourth_advanced_rule_button = QPushButton("Advanced")

        self.first_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog(0))
        self.second_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog(1))
        self.third_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog(2))
        self.fourth_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog(3))

        layout.addWidget(self.first_advanced_rule_button, 2, 3)
        layout.addWidget(self.second_advanced_rule_button, 3, 3)
        layout.addWidget(self.third_advanced_rule_button, 4, 3)
        layout.addWidget(self.fourth_advanced_rule_button, 5, 3)

        self.adv_rule_table = QTableWidget(0, 2)
        self.adv_rule_table.setHorizontalHeaderLabels(["If Condition", "Then Action"])
        layout.addWidget(self.adv_rule_table, 7, 2, 1, 2)  # Spanning 1 row and 2 columns
        self.adv_rule_table.horizontalHeader().setStretchLastSection(True)
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.adv_rule_table.setColumnWidth(0, 120)
        self.adv_rule_table.setColumnWidth(1, 120)
        self.adv_rule_table.setMinimumWidth(400)
        #self.adv_rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        #self.adv_rule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)

        self.apply_button = QPushButton('Apply')
        self.apply_button.clicked.connect(self.apply_settings)
        print("DEBUG: Apply button connected to apply_and_close method.")
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

        entries = [e - 1 for e in map(int, entries_str.split(','))] if entries_str else []
        self.source_line_edit.setText(source.strip())

        self.first_entry_checkbox.setChecked(0 in entries)
        self.second_entry_checkbox.setChecked(1 in entries)
        self.third_entry_checkbox.setChecked(2 in entries)
        self.fourth_entry_checkbox.setChecked(3 in entries)

        self.update_adv_rule_table(source.strip())
        self.update_advanced_rule_labels()

    def update_adv_rule_table(self, source=None):
        logging.debug(f"FilterSettingsDialog: Updating advanced rule table for source: {source}")  # Debug line
        self.adv_rule_table.setRowCount(0)

        if source and source in self.parent().thread.reader.advanced_rules:
            logging.debug(f"FilterSettingsDialog: Advanced rules found for source {source}.")  # Debug line
            advanced_rules_for_source = self.parent().thread.reader.advanced_rules[source]
            for idx, rule in enumerate(advanced_rules_for_source):
                self.adv_rule_table.insertRow(idx)
                self.adv_rule_table.setItem(idx, 0, QTableWidgetItem(rule['if']['condition']))
                self.adv_rule_table.setItem(idx, 1, QTableWidgetItem(rule['then']['action']))
        else:
            logging.debug(f"FilterSettingsDialog: No advanced rules found for source {source}.")  # Debug line
            self.adv_rule_table.insertRow(0)
            self.adv_rule_table.setItem(0, 0, QTableWidgetItem("No advanced rules"))



    # Call update_rule_list when the dialog is shown
    def show_and_exec(self):
        self.update_rule_list()
        self.update_adv_rule_table()
        self.update_advanced_rule_labels()
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
        logging.debug("FilterSettingsDialog: Applying settings.")
        new_rules = self.get_settings()
        self.parent().thread.reader.update_rules(new_rules)

        source = self.source_line_edit.text().strip()
        # Use source as the key for advanced rules
        if source:
            self.parent().thread.reader.advanced_rules[source] = self.advanced_rules.get(0, {})

        # Deserialize the JSON string back to dictionary
        deserialized_advanced_rules = {k: json.loads(v) for k, v in self.advanced_rules.items()}
        self.parent().thread.reader.update_advanced_rules(deserialized_advanced_rules)
            
        self.update_rule_list()
        # Update UI
        self.update_advanced_rule_ui()

    def update_advanced_rule_ui(self):
        source = self.source_line_edit.text().strip()
        checkboxes = [self.first_entry_checkbox, self.second_entry_checkbox, self.third_entry_checkbox, self.fourth_entry_checkbox]
        labels = [self.first_advanced_rule_label, self.second_advanced_rule_label, self.third_advanced_rule_label, self.fourth_advanced_rule_label]

        advanced_rules_for_source = self.advanced_rules.get(source, {})
        if isinstance(advanced_rules_for_source, str):  # If it's a JSON string, deserialize it
            advanced_rules_for_source = json.loads(advanced_rules_for_source)

        for i, (checkbox, label) in enumerate(zip(checkboxes, labels)):
            if i in advanced_rules_for_source:
                checkbox.setEnabled(False)  # Disable checkbox
                label.show()
            else:
                checkbox.setEnabled(True)  # Enable checkbox
                label.hide()


    def show_advanced_rule_dialog(self, entry_index):
        source = self.source_line_edit.text().strip()
        dialog = AdvancedRuleDialog(self)
        dialog.entry_index = entry_index  # Pass the entry index to the advanced rule dialog
        dialog.source = source
        dialog.advancedRuleSet.connect(self.set_advanced_rule)  # Connect to the new signal
        dialog.exec_()
        self.update_advanced_rule_ui()  # Refresh the UI to reflect the new advanced rule

    def set_advanced_rule(self, entry_index, advanced_rule):
        self.advanced_rules[entry_index] = advanced_rule
        self.update_adv_rule_table()
        self.update_advanced_rule_labels()
        print(f"DEBUG: Updated advanced_rules: {self.advanced_rules}") 

    def update_advanced_rule_labels(self):
        source = self.source_line_edit.text().strip()
        if source in self.parent().thread.reader.advanced_rules:
            self.first_advanced_rule_label.show()
        else:
            self.first_advanced_rule_label.hide()


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
        self.filter_settings_dialog.show_and_exec()

    def start_tts(self):
        logging.debug("App: Starting TTS.")
        self.status_label.setText('TTS Status: Started')
        self.thread.start()

    def stop_tts(self):
        logging.debug("App: Stopping TTS.")
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
