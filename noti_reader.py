import os
import re
import subprocess
import tempfile
import torch
import torchaudio
import json
import sys
import logging
from omegaconf import OmegaConf
from langdetect import detect
from scipy.io.wavfile import write

# sys.stdout = open("logs/output.log", "w")
# sys.stderr = open("error.log", "w")
# logging.basicConfig(filename='logs/debug.log', level=logging.DEBUG)

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

        # Database for notification sources and their corresponding rules

        self.json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source_rules.json')  # Absolute path
        print(f"DEBUG: JSON Path: {self.json_path}")  # Debug line
        self.load_rules()
        print("Application is loaded and ready")
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
            logging.debug("source_rules.json not found, initializing empty rules.")    

    def update_rules(self, new_rules):
        self.source_rules.update(new_rules)
        with open(self.json_path, 'w') as f:  # Use absolute path
            json.dump(self.source_rules, f)
        logging.debug(f"Updated rules saved to {self.json_path}")

    def start(self):
        self.running = True
        self.run()

    def stop(self):
        self.running = False

    def read_text(self, text, lang):
        if self.callback:
            self.callback(text)
        logging.debug(' Reading text: {text} Language: {lang}')
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
        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)

        sequential_strings = []
        current_time = None
        is_new_notification = False

        while self.running:
            line = process.stdout.readline().decode('utf-8').strip()
            logging.debug(' Intercepted line: {line}')

            time_match = re.search(r'signal time=(\d+\.\d+)', line)
            if time_match:
                current_time = time_match.group(1)

            if "member=Notify" in line:
                print('DEBUG: Starting to process a new notification.')
                sequential_strings = []
                is_new_notification = True

            string_match = re.search(r'string "([^"]+)"', line)
            if string_match:
                captured_string = string_match.group(1)
                sequential_strings.append(captured_string)
                logging.debug(' Captured sequential string: {captured_string}')

            if "signal time=" in line and "member=NotificationClosed" in line:
                if not is_new_notification:
                    print('DEBUG: Ignoring closed notification.')
                    continue

                print('DEBUG: Finished processing the notification.')
                logging.debug(' Sequential strings: {sequential_strings}')

                source = sequential_strings[0] if sequential_strings else ''
                rules = self.source_rules.get(source, [0, 1])
                
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
                            logging.debug(' Proceeding to TTS for language: {lang}.')
                            self.read_text(combined_text, lang)
                else:
                    logging.debug(' No rules found for source: {source}. Skipping.')

                is_new_notification = False  # Reset the flag

if __name__ == "__main__":
    notification_reader = NotificationReader()
    notification_reader.start()
