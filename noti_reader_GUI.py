from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QSlider, QFormLayout, QLineEdit, QCheckBox, QDialog, QGridLayout, QTableWidgetItem, QTableWidget, QHeaderView, QComboBox, QHBoxLayout, QSplitter, QListWidget, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QThread
from functools import partial
import sys
import os
import json
import logging
logger = logging.getLogger('')
if not logger.hasHandlers():
    # Determine the directory where this script resides
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    
    # Create a 'logs' directory if it doesn't exist
    logs_dir_path = os.path.join(current_script_path, 'logs')
    os.makedirs(logs_dir_path, exist_ok=True)
    
    # Create a log file within that directory
    log_file_path = os.path.join(logs_dir_path, 'debug.log')
    
    # Configure logging
    logging.basicConfig(filename=log_file_path, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
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
        self.if_condition_combo_box.addItems(["contains words/symbols", "does not contain words/symbols", "is in language", "has this amount of words"])
        self.if_value_edit = QLineEdit()

        if_condition_layout = QHBoxLayout()
        if_condition_layout.addWidget(self.if_combo_box)
        if_condition_layout.addWidget(self.if_condition_combo_box)
        if_condition_layout.addWidget(self.if_value_edit)
        self.regex_checkbox = QCheckBox("Use Regex")
        if_condition_layout.addWidget(self.regex_checkbox)
        self.if_label = QLabel("Condition:")
        self.if_layout.addWidget(self.if_label)

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
        self.then_label = QLabel("Action:")
        self.then_layout.addWidget(self.then_label)

        self.then_layout.addLayout(then_condition_layout)
        layout.addLayout(self.then_layout)

        # Cancel and Apply buttons
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_and_close_advanced_rule)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)


    def apply_and_close_advanced_rule(self):
        print("DEBUG: apply_and_close_advanced_rule() has been triggered.")
        try:
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

            advanced_rule = {
                "if": if_rule,
                "then": then_rule,
                "use_regex": self.regex_checkbox.isChecked()
            }
            advanced_rule_json = json.dumps(advanced_rule)
            
            # Debug line
            print(f"DEBUG: Applying advanced rule: {advanced_rule}")  
            
            # Save the advanced rule to the parent dialog
            self.parent().advanced_rules[self.entry_index] = advanced_rule  
            
            source = self.source
            print(f"DEBUG: Source for the advanced rule is {source}")
            
            # Initialize if the source does not exist
            if source not in self.parent().thread.reader.advanced_rules:
                self.parent().thread.reader.advanced_rules[source] = []
            
            # Remove existing rule for the same entry_index if any
            self.parent().thread.reader.advanced_rules[source] = [rule for rule in self.parent().thread.reader.advanced_rules[source] if rule["entry_index"] != self.entry_index]
            
            # Append the new rule
            self.parent().thread.reader.advanced_rules[source].append({"entry_index": self.entry_index, "rule": advanced_rule})
            
            self.parent().thread.reader.save_advanced_rules()
            updated_entry_index = int(self.if_combo_box.currentText().split(" ")[-1]) - 1
            self.advancedRuleSet.emit(self.entry_index, advanced_rule_json)
            self.accept()  
            
            # Debug lines
            print(f"DEBUG: self.parent() type: {type(self.parent())}")  
            
        except AttributeError:
            print(f"DEBUG: Caught AttributeError. self.parent(): {self.parent()}, type: {type(self.parent())}")
            print(f"DEBUG: self.parent().thread: {self.parent().thread}, type: {type(self.parent().thread)}")
            raise


    def populate_fields(self, rule, entry_index):
        self.entry_index = entry_index
        self.if_combo_box.setCurrentText(rule.get('if', {}).get('entry', 'Entry 1'))
        self.if_condition_combo_box.setCurrentText(rule.get('if', {}).get('condition', ''))
        self.if_value_edit.setText(rule.get('if', {}).get('value', ''))
        self.regex_checkbox.setChecked(rule.get('use_regex', False))
        self.then_combo_box.setCurrentText(rule.get('then', {}).get('entry', 'Entry 1'))
        self.then_action_combo_box.setCurrentText(rule.get('then', {}).get('action', ''))
        self.then_value_edit.setText(rule.get('then', {}).get('value', ''))





class FilterSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(FilterSettingsDialog, self).__init__(parent)
        self.thread = NotificationThread()
        self.source_list = QListWidget(self)
        layout = QGridLayout()
        layout.addWidget(QLabel("Reading Filter Settings"), 0, 0)
        self.advanced_rules = {}
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)

        self.rule_table = QTableWidget(0, 3)
        self.rule_table.setHorizontalHeaderLabels(["Rule", "Entries", "Action"])
        self.rule_table.itemClicked.connect(self.on_rule_clicked)
        #self.rule_table.horizontalHeader().setStretchLastSection(True)
        self.rule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # "Rule" column
        self.rule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)    # "Entries" column
        self.rule_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)    # "Action" column
        self.rule_table.setColumnWidth(1, 90)
        self.rule_table.setColumnWidth(1, 60)
        self.rule_table.setColumnWidth(2, 52)
        layout.addWidget(self.rule_table, 7, 0, 1, 2)

        # Fields for source and entries
        layout.addWidget(QLabel("Source of notification:"), 1, 0)
        self.source_line_edit = QLineEdit()
        self.source_line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.source_line_edit.setMaximumWidth(600)  # set a sensible maximum width
        self.source_line_edit.setMinimumWidth(230) 
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

        # Advanced Rule Labels and Buttons
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

        self.first_advanced_rule_button = QPushButton("Advanced")
        self.second_advanced_rule_button = QPushButton("Advanced")
        self.third_advanced_rule_button = QPushButton("Advanced")
        self.fourth_advanced_rule_button = QPushButton("Advanced")

        # Connect the buttons to the function that shows the AdvancedRuleDialog
        self.first_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog_for_filter(0))
        self.second_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog_for_filter(1))
        self.third_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog_for_filter(2))
        self.fourth_advanced_rule_button.clicked.connect(lambda: self.show_advanced_rule_dialog_for_filter(3))

        layout.addWidget(self.first_advanced_rule_button, 2, 3)
        layout.addWidget(self.second_advanced_rule_button, 3, 3)
        layout.addWidget(self.third_advanced_rule_button, 4, 3)
        layout.addWidget(self.fourth_advanced_rule_button, 5, 3)

        self.adv_rule_table = QTableWidget(0, 8)
        self.adv_rule_table.setHorizontalHeaderLabels(["If Entry", "If Condition", "If Value", "Then Action", "Then Entry", "Action value", "Edit", "Delete"])
        self.adv_rule_table.horizontalHeader().setStretchLastSection(True)
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # "If Entry" column
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # "If Condition" column
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # "If Value" column
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)  # "Then Action" column
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)  # "Then Entry" column
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # "Action value" column
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)  # "Edit" column
        self.adv_rule_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)  # "Delete" column

        self.adv_rule_table.setColumnWidth(0, 60) 
        self.adv_rule_table.setColumnWidth(3, 82) 
        self.adv_rule_table.setColumnWidth(4, 75)
        self.adv_rule_table.setColumnWidth(5, 78)
        self.adv_rule_table.setColumnWidth(6, 52) 
        self.adv_rule_table.setColumnWidth(7, 52)
        layout.addWidget(self.adv_rule_table, 7, 2, 1, 2)

        self.apply_button = QPushButton('Apply')
        self.apply_button.clicked.connect(self.apply_filter_settings)
        layout.addWidget(self.apply_button, 6, 1)
        self.adv_rule_table.itemChanged.connect(self.on_adv_rule_item_changed)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 9)
        layout.setColumnStretch(3, 9)

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
        if source != DEFAULT_SOURCE:  # Prevent deletion of the default entry
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

    def update_adv_rule_table(self, source):
        logging.debug("Entering update_adv_rule_table")

        self.adv_rule_table.clearContents()  # Clear the contents
        self.adv_rule_table.setRowCount(0)  # Set row count to 0

        if source and source in self.parent().thread.reader.advanced_rules:
            advanced_rules = self.parent().thread.reader.advanced_rules[source]
            for rule_dict in advanced_rules:
                
                logging.debug(f"DEBUG: Processing rule_dict: {rule_dict}")  # Debug log
                
                entry_index = rule_dict['entry_index']
                rule = rule_dict['rule']
                
                row_position = self.adv_rule_table.rowCount()
                self.adv_rule_table.insertRow(row_position)

                # Set the "If Entry" based on the 'if' rule
                if_entry = rule.get('if', {}).get('entry', '')
                self.adv_rule_table.setItem(row_position, 0, QTableWidgetItem(if_entry))  # Changed this line

                self.adv_rule_table.setItem(row_position, 1, QTableWidgetItem(rule.get('if', {}).get('condition', '')))
                self.adv_rule_table.setItem(row_position, 2, QTableWidgetItem(rule.get('if', {}).get('value', '')))
                self.adv_rule_table.setItem(row_position, 3, QTableWidgetItem(rule.get('then', {}).get('action', '')))
                self.adv_rule_table.setItem(row_position, 4, QTableWidgetItem(rule.get('then', {}).get('entry', '')))
                self.adv_rule_table.setItem(row_position, 5, QTableWidgetItem(rule.get('then', {}).get('value', '')))

                edit_btn = QPushButton('Edit')
                edit_btn.clicked.connect(lambda checked, s=source, index=entry_index: self.edit_adv_rule(s, index))
                self.adv_rule_table.setCellWidget(row_position, 6, edit_btn) 

                delete_btn = QPushButton('Delete')
                delete_btn.clicked.connect(partial(self.delete_adv_rule, source, entry_index))
                self.adv_rule_table.setCellWidget(row_position, 7, delete_btn)

                self.adv_rule_table.resizeColumnToContents(1) 
                self.adv_rule_table.resizeColumnToContents(3)


        logging.debug("Exiting update_adv_rule_table")  # Debug log at the end



    def log_and_delete_advanced_rule(self, entry_index):
        logging.debug(f"Delete button clicked for entry_index {entry_index}")
        self.delete_advanced_rule(entry_index)  # Assuming you have a method named `delete_advanced_rule`

    def delete_adv_rule(self, source, entry_index):
        if source in self.parent().thread.reader.advanced_rules:
            rule_list = self.parent().thread.reader.advanced_rules[source]
            rule_to_remove = None
            for r in rule_list:
                if r["entry_index"] == entry_index:
                    rule_to_remove = r
                    break

            if rule_to_remove is not None:
                rule_list.remove(rule_to_remove)
                # If the list becomes empty, remove the source entry
                if not rule_list:
                    del self.parent().thread.reader.advanced_rules[source]
                    
                self.parent().thread.reader.save_advanced_rules()  # Save the updated rules
                self.update_adv_rule_table(source)  # Refresh the table
            else:
                print("DEBUG: No rule found for deletion.")

    # Call update_rule_list when the dialog is shown
    def show_and_execute_filter_settings(self):
        self.update_rule_list()

        source = self.source_line_edit.text().strip()  # Getting source from QLineEdit
        if not source:  # If no source is set, you might set it to None or some default value.
            source = None  # Or any default source

        self.update_adv_rule_table(source)  # Now providing source as an argument
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

    def apply_filter_settings(self):
        logging.debug("FilterSettingsDialog: Applying settings.")
        new_rules = self.get_settings()
        self.parent().thread.reader.update_rules(new_rules)

        source = self.source_line_edit.text().strip()
        # Updating only the source_rules, not touching advanced_rules here
        if source:
            advanced_rules_for_source = self.parent().thread.reader.advanced_rules.get(source, {})
            if advanced_rules_for_source:
                self.parent().thread.reader.advanced_rules[source] = advanced_rules_for_source
            else:
                # If there are no advanced rules for this source, ensure it doesn't exist in the dictionary
                if source in self.parent().thread.reader.advanced_rules:
                    del self.parent().thread.reader.advanced_rules[source]
        
        # Save advanced rules only if they exist
        if self.parent().thread.reader.advanced_rules:
            self.parent().thread.reader.save_advanced_rules()
                
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

    def show_advanced_rule_dialog_for_filter(self, entry_index):
        source = self.source_line_edit.text().strip()
        print(f"DEBUG: Source obtained in FilterSettingsDialog: {source}")  # Debug log 1
        dialog = AdvancedRuleDialog(self)
        dialog.entry_index = entry_index
        dialog.source = source
        print(f"DEBUG: dialog.source set to: {dialog.source}")  # Debug log 2
        initial_entry_text = f"Entry {entry_index + 1}"
        dialog.if_combo_box.setCurrentText(initial_entry_text)
        dialog.then_combo_box.setCurrentText(initial_entry_text)

        dialog.advancedRuleSet.connect(self.set_advanced_rule_for_filter)
        dialog.exec_()
        self.update_advanced_rule_ui()


    def set_advanced_rule_for_filter(self, entry_index, advanced_rule_json):
        source = self.source_line_edit.text().strip()
        print(f"DEBUG: Source set in FilterSettingsDialog: {source}")

        if source not in self.parent().thread.reader.advanced_rules:
            self.parent().thread.reader.advanced_rules[source] = []
        elif not isinstance(self.parent().thread.reader.advanced_rules[source], list):
            existing_rules = self.parent().thread.reader.advanced_rules[source]
            self.parent().thread.reader.advanced_rules[source] = [{"entry_index": k, "rule": v} for k, v in existing_rules.items()]

        # Update the advanced rule using the received entry_index
        for rule in self.parent().thread.reader.advanced_rules[source]:
            if rule["entry_index"] == entry_index:
                rule["rule"] = json.loads(advanced_rule_json)
                break
        else:
            self.parent().thread.reader.advanced_rules[source].append({
                "entry_index": entry_index,
                "rule": json.loads(advanced_rule_json)
            })

        self.parent().thread.reader.save_advanced_rules()

        # Update the advanced_rules dictionary using the received entry_index
        self.advanced_rules[entry_index] = advanced_rule_json
        
        self.update_adv_rule_table(source)
        self.update_advanced_rule_labels()
        print(f"DEBUG: Updated advanced_rules: {self.advanced_rules}")


    def update_advanced_rule_labels(self):
        if not self.advanced_rules:
            logging.debug("No advanced rules to save. Skipping.")
            return
        source = self.source_line_edit.text().strip()
        if source in self.parent().thread.reader.advanced_rules:
            self.first_advanced_rule_label.show()
        else:
            self.first_advanced_rule_label.hide()

    @pyqtSlot(QTableWidgetItem)
    def on_adv_rule_item_changed(self, item):
        row = item.row()
        column = item.column()
        new_value = item.text()
        source = self.source_line_edit.text().strip()
        
        # Assuming entry_index is stored in the first column
        entry_index = self.adv_rule_table.item(row, 0).text()
        
        if source in self.parent().thread.reader.advanced_rules:
            if str(entry_index) in self.parent().thread.reader.advanced_rules[source]:
                rule = self.parent().thread.reader.advanced_rules[source][entry_index]
                
                # Update the rule based on the column that was changed
                if column == 1:  # 'If Condition'
                    rule['if']['condition'] = new_value
                elif column == 2:  # 'If Value'
                    rule['if']['value'] = new_value
                elif column == 3:  # 'Then Action'
                    rule['then']['action'] = new_value
                    
                # Save the updated rules
                self.parent().thread.reader.save_advanced_rules()

    def edit_adv_rule(self, source, entry_index):
        # Fetch the existing rule data for the specified source and entry_index
        rule_list = self.parent().thread.reader.advanced_rules.get(source, [])
        rule = None
        for r in rule_list:
            if r["entry_index"] == entry_index:
                rule = r["rule"]
                break

        if rule is None:
            print("DEBUG: No existing rule found for the given source and entry_index.")
            return

        dialog = AdvancedRuleDialog(self)
        
        # Pre-fill the dialog with the existing rule's data
        dialog.entry_index = entry_index
        dialog.source = source
        dialog.populate_fields(rule, entry_index)  # You'll need to implement this method in AdvancedRuleDialog if not already done
        
        dialog.advancedRuleSet.connect(self.set_advanced_rule_for_filter)
        dialog.exec_()
        self.update_adv_rule_table(source)


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
        self.filter_settings_dialog.show_and_execute_filter_settings()

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
