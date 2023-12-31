import os
import re
import subprocess
import tempfile
import torch
import torchaudio
import json
import sys
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

from omegaconf import OmegaConf
from langdetect import detect
from scipy.io.wavfile import write
DEFAULT_SOURCE = 'Default - all notifications'


class NotificationReader:
    def __init__(self, callback=None):
        # Load Silero model for Russian TTS
        self.language = 'ru'
        self.model_id = 'v4_ru'
        self.sample_rate = 48000
        self.speaker = 'aidar'
        self.device = torch.device('cpu')
        self.model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                       model='silero_tts',
                                       language=self.language,
                                       speaker=self.model_id)
        self.model.to(self.device)
        logging.debug(f'TTS initialized with language: {self.language} and model ID: {self.model_id}')
        # Database for notification sources and their corresponding rules
        current_script_path = os.path.dirname(os.path.abspath(__file__))
        self.current_source = ''
        self.advanced_rules_file_path = os.path.join(current_script_path, 'advanced_rules.json')
        self.json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source_rules.json')  # Absolute path
        print(f"DEBUG: JSON Path: {self.json_path}")  # Debug line
        self.advanced_rules = {}
        self.load_rules()
        self.load_advanced_rules()
        logging.debug("Application is loaded and ready")

        # List to hold last N notifications for deduplication
        self.recent_notifications = []
        self.max_recent_notifications = 10
        self.running = False
        self.callback = callback
        
    def load_rules(self):
        try:
            with open(self.json_path, 'r') as f:
                self.source_rules = json.load(f)
                if DEFAULT_SOURCE not in self.source_rules:
                    self.source_rules[DEFAULT_SOURCE] = [0, 1]  # Defaults to reading the first two entries
                    self.update_rules({})
        except FileNotFoundError:
            self.source_rules = {DEFAULT_SOURCE: [0, 1]}  # Defaults to reading the first two entries
            logging.debug("source_rules.json not found, initializing with default rules.")

    def update_rules(self, new_rules):
        # Prevent deletion of the default entry
        if DEFAULT_SOURCE in self.source_rules and DEFAULT_SOURCE not in new_rules:
            new_rules[DEFAULT_SOURCE] = self.source_rules[DEFAULT_SOURCE]
        
        self.source_rules.update(new_rules)
        with open(self.json_path, 'w') as f:
            json.dump(self.source_rules, f)
        logging.debug(f"Updated rules saved to {self.json_path}")

    def update_advanced_rules(self, advanced_rules):
        self.advanced_rules = advanced_rules     
        self.save_advanced_rules()  

    def update_single_advanced_rule(self, source, advanced_rule):
        self.advanced_rules[source] = advanced_rule
        self.save_advanced_rules()

    def apply_advanced_rule(self, sequential_strings, source, actions):
        logging.debug("Entering apply_advanced_rule.")

        if source not in self.advanced_rules:
            logging.debug(f"No advanced rules for source {source}.")
            return  # No rules matched

        logging.debug(f"Advanced rules exist for source {source}. Rules: {self.advanced_rules[source]}")

        for advanced_rule_entry in self.advanced_rules[source]:
            entry_index = advanced_rule_entry["entry_index"]
            advanced_rule = advanced_rule_entry["rule"]

            logging.debug(f"Processing advanced_rule_entry {advanced_rule_entry}")

            if entry_index < len(sequential_strings):
                logging.debug(f"entry_index: {entry_index}, len(sequential_strings): {len(sequential_strings)}")
                text_to_check = sequential_strings[entry_index]
                logging.debug(f"Checking text {text_to_check} for advanced rules.")

                if_rule = advanced_rule.get('if', {})
                condition = if_rule.get('condition', '')
                logging.debug(f"Condition from advanced rule: {condition}")

                value = if_rule.get('value', '')
                match = False

                if condition == 'contains words/symbols':
                    if advanced_rule.get('use_regex', False):
                        match = re.search(value, text_to_check) is not None
                    else:
                        quoted_terms = re.findall(r'"[^"]+"', value)
                        unquoted_terms = re.findall(r'\b\w+\b', re.sub(r'"[^"]+"', '', value))
                        terms = quoted_terms + unquoted_terms
                        operators = re.findall(r'AND|OR', value)

                        if not operators:
                            operators = ['AND'] * (len(terms) - 1)

                        grouped_results = []
                        for i, term in enumerate(terms):
                            if term.startswith('"') and term.endswith('"'):
                                term = term.strip('"')
                                grouped_results.append(term in text_to_check)
                            else:
                                grouped_results.append(term in text_to_check.split())

                        match = any(grouped_results) if 'OR' in operators else all(grouped_results)

                elif condition == 'does not contain words/symbols':
                    if advanced_rule.get('use_regex', False):
                        match = re.search(value, text_to_check) is None
                    else:
                        quoted_terms = re.findall(r'"[^"]+"', value)
                        unquoted_terms = re.findall(r'\b\w+\b', re.sub(r'"[^"]+"', '', value))
                        terms = quoted_terms + unquoted_terms
                        operators = re.findall(r'AND|OR', value)

                        if not operators:
                            operators = ['AND'] * (len(terms) - 1)

                        grouped_results = []
                        for i, term in enumerate(terms):
                            if term.startswith('"') and term.endswith('"'):
                                term = term.strip('"')
                                grouped_results.append(term not in text_to_check)
                            else:
                                grouped_results.append(term not in text_to_check.split())

                        match = any(grouped_results) if 'OR' in operators else all(grouped_results)

                elif condition == 'is in language':
                    detected_lang = detect(text_to_check)
                    match = detected_lang == value

                elif condition == 'has this amount of words':
                    match = len(text_to_check.split()) == int(value)

                if match:
                    logging.debug(f"Condition matched. Processing actions.")
                    then_rule = advanced_rule.get('then', {})
                    action = then_rule.get('action', '')
                    target_entry_str = then_rule.get('entry', str(entry_index))
                    target_entry_index = int(re.search(r'\d+', target_entry_str).group()) - 1 if re.search(r'\d+', target_entry_str) else entry_index

                    if action in ['read', 'do not read']:
                        if target_entry_index < len(actions):
                            actions[target_entry_index] = action
                    elif action == 'read certain words':
                        replacement_words = then_rule.get('value', '')
                        if target_entry_index < len(sequential_strings):
                            sequential_strings[target_entry_index] = replacement_words
                            actions[target_entry_index] = 'read'
                else:
                    logging.debug(f"Condition not matched. Skipping actions.")

        return actions

    def start(self):
        self.running = True
        self.run()

    def stop(self):
        self.running = False

    def read_text(self, text, lang):
        if self.callback:
            self.callback(text)
        logging.debug(f'Trying to read text: "{text}" in language: "{lang}"')
        if self.callback:
            self.callback(text)
        if lang == 'en':
            with tempfile.NamedTemporaryFile('w', delete=False) as f:
                f.write(text)
                f.flush()
                command = f'cat {f.name} | tts --text "{text}" --model_name "tts_models/en/vctk/vits" --speaker_idx p230 --out_path /tmp/tts_output.wav  --use_cuda USE_CUDA'
                logging.debug(f'Executing TTS command: {command}')
                subprocess.run(command, shell=True)
                play_command = 'aplay /tmp/tts_output.wav'
                logging.debug(f'Executing play command: {play_command}')
                subprocess.run(play_command, shell=True)
        elif lang == 'ru':
            audio = self.model.apply_tts(text=text,
                                         speaker=self.speaker,
                                         sample_rate=self.sample_rate)
            audio = audio.squeeze().numpy()
            write('/tmp/tts_output.wav', self.sample_rate, audio)
            play_command = 'aplay /tmp/tts_output.wav'
            subprocess.run(play_command, shell=True)

    def run(self):
        # Intercept a notification
        command = "dbus-monitor \"interface='org.freedesktop.Notifications'\""
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        except Exception as e:
            logging.debug(f"Failed to start subprocess: {e}")

        sequential_strings = []
        current_time = None
        is_new_notification = False

        while self.running:
            line = process.stdout.readline().decode('utf-8').strip()
            logging.debug(f'Intercepted line: {line}')

            time_match = re.search(r'signal time=(\d+\.\d+)', line)
            if time_match:
                current_time = time_match.group(1)

            if "member=Notify" in line:
                logging.debug('Starting to process a new notification.')
                sequential_strings = []
                is_new_notification = True

            string_match = re.search(r'string "([^"]+)"', line)
            if string_match:
                captured_string = string_match.group(1)
                sequential_strings.append(captured_string)
                logging.debug(f'Captured sequential string: {captured_string}')

            if "signal time=" in line and "member=NotificationClosed" in line:
                if not is_new_notification:
                    logging.debug('Ignoring closed notification.')
                    continue

                logging.debug('Finished processing the notification.')
                logging.debug(f'Sequential strings: {sequential_strings}')

                source = sequential_strings[0] if sequential_strings else ''
                self.current_source = source
                rules = self.source_rules.get(source, [0, 1])

                # Initialize actions with 'do not read' first
                actions = ['do not read'] * len(sequential_strings)

                # Apply simple rules to populate actions
                if rules:
                    for i in rules:
                        if i < len(actions):
                            actions[i] = 'read'

                # Apply advanced rules to update actions
                self.apply_advanced_rule(sequential_strings, source, actions)

                # Group text by language
                grouped_text = {'en': [], 'ru': []}

                # Use the final actions array to decide what to read
                for i, action in enumerate(actions):
                    if i < len(sequential_strings):
                        text_to_read = sequential_strings[i]
                        if not text_to_read.strip():
                            logging.debug("Skipping language detection due to empty text.")
                        else:
                            detected_lang = detect(text_to_read)
                        lang = 'ru' if detected_lang == 'ru' else 'en'

                        if action == 'read':
                            grouped_text[lang].append(text_to_read)

                # Process each language group
                for lang, texts in grouped_text.items():
                    if texts:
                        combined_text = ', '.join(texts)
                        logging.debug(f'Notification source: {source}')
                        logging.debug(f'Final text to read: {combined_text}')
                        logging.debug(f'Proceeding to TTS for language: {lang}.')
                        self.read_text(combined_text, lang)
                else:
                    logging.debug(f'No rules found for source: {source}. Skipping.')

                is_new_notification = False  # Reset the flag

    def load_advanced_rules(self):
        advanced_rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'advanced_rules.json')
        try:
            if os.path.exists(self.advanced_rules_file_path):
                with open(self.advanced_rules_file_path, 'r') as f:
                    self.advanced_rules = json.load(f)
            logging.debug(f"Successfully loaded advanced rules: {self.advanced_rules}")
        except FileNotFoundError:
            self.advanced_rules = {}
            logging.debug("advanced_rules.json not found, initializing empty rules.")
        except Exception as e:
            logging.debug(f"Failed to load advanced rules. Error: {e}")


    def save_advanced_rules(self):
        advanced_rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'advanced_rules.json')
        try:
            with open(self.advanced_rules_file_path, 'w') as f:
                json.dump(self.advanced_rules, f)
            logging.debug("Successfully saved advanced rules.")
        except Exception as e:
            logging.debug(f"Failed to save advanced rules. Error: {e}")



if __name__ == "__main__":
    notification_reader = NotificationReader()
    notification_reader.start()
