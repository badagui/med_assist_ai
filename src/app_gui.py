import tkinter as tk
from tkinter import scrolledtext
import asyncio
from tkinter import ttk
from app_controller import AppController
from test_prompt import test_transcription
import pyaudio

class AppGUI:
    def __init__(self, app_controller: AppController, p: pyaudio.PyAudio):
        self.app_controller = app_controller
        self.p = p
        self.audio_input_dropdown = None
        self.device_map = {}
        self.capture_button = None

        # create the main window
        self.root = tk.Tk() 
        self.root.title("Med Assist AI - " + self.app_controller.language)
        self.root.protocol("WM_DELETE_WINDOW", self.close_program)
        self.create_widgets()

    def run_mainloop(self):
        self.root.mainloop()
    
    def close_program(self):
        self.app_controller.stop_app()
        # terminate GUI
        self.root.destroy()

    def create_widgets(self):
         # tabs widget
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, columnspan=4)

        # first tab
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text='Main')

        # audio input selection
        audio_input_label = tk.Label(self.tab1, text="Input:")
        audio_input_label.grid(row=0, column=0, padx=5, pady=5)

        # dropdown for audio input
        self.find_devices()
        device_names = [x for x in self.device_map.keys() if x != 'None']
        device_names.insert(0, 'None') # make 'None' first element
        self.audio_input_dropdown = DeviceSelectDropdown(self.tab1, 0, 1, device_names, self.stop_audio_recording)
        # set the default microphone
        if self.default_device_name is not None:
            self.audio_input_dropdown.selected_option.set(self.default_device_name)

        # start/stop capture button
        self.capture_button = tk.Button(self.tab1, text="Iniciar\nConsulta", command=self.toggle_capture)
        self.capture_button.grid(row=0, column=4, padx=20, pady=20, columnspan=3, rowspan=2, ipadx=20, ipady=20)

        # transcribed text label
        label_textbox_left = tk.Label(self.tab1, text="Transcrição da Consulta:", justify='left')
        label_textbox_left.grid(row=2, column=0, padx=5, pady=5)
        
        label_textbox_right = tk.Label(self.tab1, text="Resumo da Consulta:", justify='left')
        label_textbox_right.grid(row=2, column=4, padx=0, pady=0)

        label_textbox_right2 = tk.Label(self.tab1, text="Sintomas Reportados:", justify='left')
        label_textbox_right2.grid(row=4, column=4, padx=0, pady=0)

        label_textbox_right3 = tk.Label(self.tab1, text="Possíveis Diagnósticos:", justify='left')
        label_textbox_right3.grid(row=6, column=4, padx=0, pady=0)

        # LEFT text box
        self.textbox_left = scrolledtext.ScrolledText(self.tab1, wrap=tk.WORD, height=25, width=50)
        self.textbox_left.grid(row=3, column=0, padx=10, pady=10, columnspan=3, rowspan=6, sticky='nsew')

        # RIGHT text boxes
        self.textbox_right = scrolledtext.ScrolledText(self.tab1, wrap=tk.WORD, height=10, width=50)
        self.textbox_right.grid(row=3, column=4, padx=10, pady=10, columnspan=2, sticky='nsew')

        self.textbox_right2 = scrolledtext.ScrolledText(self.tab1, wrap=tk.WORD, height=10, width=50)
        self.textbox_right2.grid(row=5, column=4, padx=10, pady=10, columnspan=2, sticky='nsew')

        self.textbox_right3 = scrolledtext.ScrolledText(self.tab1, wrap=tk.WORD, height=10, width=50)
        self.textbox_right3.grid(row=7, column=4, padx=10, pady=10, columnspan=2, sticky='nsew')

        ############## second tab
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text='Results')

        # base prompt textbox
        self.textbox_base_prompt = scrolledtext.ScrolledText(self.tab2, wrap=tk.WORD, height=30, width=100, background='#f0f0f0')
        self.textbox_base_prompt.grid(row=1, column=0, padx=10, pady=10, columnspan=5,  sticky='nsew')
        
    def find_devices(self):
        # query and map audio input devices
        num_devices = self.p.get_device_count()
        default_device_index = self.p.get_default_input_device_info()['index']
        self.default_device_name = None

        for i in range(num_devices):
            device_info = self.p.get_device_info_by_index(i)
            # check if input device
            if device_info['maxInputChannels'] > 0:
                # create device name
                device_name = f"{str(device_info['index'])}. {device_info['name']}"
                # set local data
                self.device_map[device_name] = device_info
                if i == default_device_index:
                    self.default_device_name = device_name
        self.device_map['None'] = None

    def start_audio_recording(self):
        print("starting audio recording...")
        # # get selected
        device_info = self.device_map[self.audio_input_dropdown.selected_option.get()]
        source_rate = int(device_info['defaultSampleRate'])
        if device_info == None:
            print("no audio input device selected")
            return
        device_id = device_info['index']
        print('device_id', device_id)
        self.app_controller.start_audio_recording(device_id, source_rate)
        self.capture_button.config(text="Parar e\nGerar Relatório")

    def stop_audio_recording(self):
        if self.capture_button:
            self.capture_button.config(text="Iniciar\nConsulta")
        if self.app_controller.audio_recorder.stream is None:
            return
        # generate transcription
        self.tsafe_update_transcription('processing...')
        transcription = self.app_controller.stop_audio_recording_and_transcribe()
        if transcription is None:
            self.tsafe_update_transcription('error processing audio')
            return
        self.tsafe_update_transcription(transcription)
        # generate other data
        self.tsafe_update_summary("processing...")
        self.tsafe_update_symptoms("processing...")
        self.tsafe_update_diagnostics("processing...")
        self.app_controller.process_transcription_async(transcription, self.tsafe_update_summary, self.tsafe_update_symptoms, self.tsafe_update_diagnostics)

    def tsafe_update_summary(self, text):
        def task():
            self.textbox_right.delete('1.0', tk.END)
            self.textbox_right.insert(tk.END, text)
        self.root.after(0, task)

    def tsafe_update_symptoms(self, text):
        def task():
            self.textbox_right2.delete('1.0', tk.END)
            self.textbox_right2.insert(tk.END, text)
        self.root.after(0, task)

    def tsafe_update_diagnostics(self, text):
        def task():
            self.textbox_right3.delete('1.0', tk.END)
            self.textbox_right3.insert(tk.END, text)
        self.root.after(0, task)

    def tsafe_update_transcription(self, text):
        def task():
            self.textbox_left.delete('1.0', tk.END)
            self.textbox_left.insert(tk.END, text)
        self.root.after(0, task)

    def toggle_capture(self):
        if self.app_controller.audio_recorder.stream == None:
            self.start_audio_recording()
        else:
            self.stop_audio_recording()

class DeviceSelectDropdown:
    def __init__(self, master, row, col, device_names, device_changed_callback):
        self.device_changed_callback = device_changed_callback
        # creates dropdown for selecting audio input device
        self.selected_option = tk.StringVar(master)
        self.selected_option.set(device_names[0] if device_names else "")
        self.selected_option.trace_add('write', self.device_changed)
        self.audio_input_dropdown = tk.OptionMenu(master, self.selected_option, *device_names)
        self.audio_input_dropdown.grid(row=row, column=col, padx=5, pady=5)

    def device_changed(self, *args):
        # handle selected device change
        self.device_changed_callback()
