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
    logging.basicConfig(filename='/home/u0/Docs/my_coding_projects_2023/Notification_reader_TTS/logs/debug.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    logger.addHandler(console)




from omegaconf import OmegaConf
from langdetect import detect
from scipy.io.wavfile import write


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
            with open(self.json_path, 'r') as f:  # Use absolute path
                self.source_rules = json.load(f)
        except FileNotFoundError:
            self.source_rules = {}
            print("DEBUG: source_rules.json not found, initializing empty rules.")
            logging.exception("source_rules.json not found, initializing empty rules.")    

    def update_rules(self, new_rules):
        self.source_rules.update(new_rules)
        with open(self.json_path, 'w') as f:  # Use absolute path
            json.dump(self.source_rules, f)
        logging.debug(f"Updated rules saved to {self.json_path}")

    def update_advanced_rules(self, advanced_rules):
        self.advanced_rules = advanced_rules     
        self.save_advanced_rules()  

    def update_single_advanced_rule(self, source, advanced_rule):
        self.advanced_rules[source] = advanced_rule
        self.save_advanced_rules()

    def apply_advanced_rule(self, sequential_strings, rules):
        logging.debug("DEBUG: Applying advanced rules.")
        for entry_index, advanced_rule in self.advanced_rules.items():
            entry_index = int(entry_index)  # Convert the entry index to an integer
            logging.debug(f"DEBUG: Advanced rule type: {type(advanced_rule)}")
            logging.debug(f"DEBUG: Advanced rule content: {advanced_rule}")
            if int(entry_index) < len(sequential_strings):
                text_to_check = sequential_strings[entry_index]
                logging.debug(f"DEBUG: Checking text {text_to_check} for advanced rules.")
                if_rule = advanced_rule.get('if', {})
                condition = if_rule.get('condition', '')
                value = if_rule.get('value', '')
                
                match = False
                if condition == 'contains word':
                    match = value in text_to_check.split()
                elif condition == 'contains symbol':
                    match = value in text_to_check
                elif condition == 'is in language':
                    detected_lang = detect(text_to_check)
                    match = detected_lang == value
                elif condition == 'has this amount of words':
                    match = len(text_to_check.split()) == int(value)
                
                if match:
                    then_rule = advanced_rule.get('then', {})
                    action = then_rule.get('action', '')
                    logging.debug(f"DEBUG: Advanced rule match. Action: {action}.")
                    
                    if action in ['read', 'do not read']:
                        return action, then_rule.get('words', None)
        logging.debug("DEBUG: No advanced rules applied.")
        return None, None  # No rules matched
 

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
                subprocess.run(command, shell=True)
                play_command = 'aplay /tmp/tts_output.wav'
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
                rules = self.source_rules.get(source, [0, 1])

                # Apply advanced rules
                advanced_action, advanced_words = self.apply_advanced_rule(sequential_strings, rules)
                if advanced_action is not None:
                    if advanced_action == 'read':
                        logging.debug("Reading text based on advanced rule.")
                        if advanced_words:
                            # Read only certain words
                            self.read_text(' '.join([word for word in sequential_strings if word in advanced_words.split()]), 'en')
                        else:
                            # Read all words
                            self.read_text(' '.join(sequential_strings), 'en')
                    else:
                        logging.debug("Skipping text based on advanced rule.")
                        # Code to skip reading based on advanced rule
                    continue  # Skip the rest of the loop iteration

                # Group text by language
                grouped_text = {'en': [], 'ru': []}
                
                if rules:
                    for i in rules:
                        if i < len(sequential_strings):
                            text_to_read = sequential_strings[i]
                            detected_lang = detect(text_to_read)
                            lang = 'ru' if detected_lang == 'ru' else 'en'
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
            with open("advanced_rules.json", 'r') as f:
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
            with open("advanced_rules.json", 'w') as f:
                json.dump(self.advanced_rules, f)
            logging.debug("Successfully saved advanced rules.")
        except Exception as e:
            logging.debug(f"Failed to save advanced rules. Error: {e}")



if __name__ == "__main__":
    notification_reader = NotificationReader()
    notification_reader.start()
