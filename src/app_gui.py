import tkinter as tk
from tkinter import scrolledtext
import asyncio
from tkinter import ttk
from gpt_controller import GPTController
from transcriber import AudioRecorder, AudioTranscriber
from test_prompt import test_transcription

class AppGUI:
    def __init__(self, audio_recorder: AudioRecorder, audio_transcriber: AudioTranscriber, gpt_controller: GPTController, asyncio_loop: asyncio.BaseEventLoop, terminate_event: asyncio.Event):
        self.audio_recorder = audio_recorder
        self.audio_transcriber = audio_transcriber
        self.gpt_controller = gpt_controller
        self.asyncio_loop = asyncio_loop
        self.terminate_event = terminate_event
        self.audio_input_dropdown = None
        self.device_map = {}

        # create the main window
        self.root = tk.Tk() 
        self.root.title("Med Assist AI")
        self.root.protocol("WM_DELETE_WINDOW", self.close_program)
        self.create_widgets()

    def run_mainloop(self):
        self.root.mainloop()
    
    def close_program(self):
        print("performing cleanup...")
        
        # stop asyncio main loop
        self.asyncio_loop.call_soon_threadsafe(self.terminate_event.set)
        
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
        audio_input_label = tk.Label(self.tab1, text="Microfone:")
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
        
        label_textbox_right = tk.Label(self.tab1, text="Resumo do atendimento:", justify='left')
        label_textbox_right.grid(row=2, column=4, padx=0, pady=0)

        label_textbox_right2 = tk.Label(self.tab1, text="Sintomas Relatados:", justify='left')
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
        num_devices = self.audio_recorder.p.get_device_count()
        default_device_index = self.audio_recorder.p.get_default_input_device_info()['index']
        self.default_device_name = None

        for i in range(num_devices):
            device_info = self.audio_recorder.p.get_device_info_by_index(i)
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
        if device_info == None:
            print("no audio input device selected")
            return
        device_id = device_info['index']
        print('device_id', device_id)
        self.audio_recorder.start(device_id, 48000, file_name="consulta_audio.wav")
        self.capture_button.config(text="Parar e\nGerar Relatório")

    def stop_audio_recording(self):
        print("stopping audio recording...")
        file_name = self.audio_recorder.stop()
        self.capture_button.config(text="Iniciar Consulta")
        if file_name is None:
            return
        # file_name = "consulta_simulada_GiovannaSchmidt.mp3" # TEST: use test audio
        transcription = self.audio_transcriber.transcribe(file_name, language='pt-BR')
        # transcription = test_transcription # TEST: use test transcription
        if transcription is None:
            return
        self.update_log(transcription)
        
        self.update_ui_with_resume("processando...")
        self.update_ui_with_symptoms("processando...")
        self.update_ui_with_diagnostics("processando...")

        print("sending resume query...")
        messages = [
            {'role': 'system', 'content': ('Haja como um assistente médico que possui o objetivo de resumir consultas médicas. '
                                           'Essas consultas estão no formato de transcrições, geradas a partir de gravações de áudio que podem conter erros de captação. '
                                           'O assistente médico deve ser capaz de resumir a transcrição da consulta em um texto curto e objetivo, mantendo as informações mais importantes. '
                                           'Não explique ou faça nenhum comentário. Escreva apenas o resumo da consulta e nada mais.')},
            {'role': 'user', 'content': transcription}
        ]
        asyncio.run_coroutine_threadsafe(self.gpt_controller.send_query(messages, self.set_resume_callback), self.asyncio_loop)
    
        print("sending symptoms query...")
        messages = [
            {'role': 'system', 'content': ('Haja como um assistente médico que possui o objetivo de listar todos os sintomas reportados pelo paciente em uma consulta médicas. '
                                           'Essas consultas estão no formato de transcrições, geradas a partir de gravações de áudio que podem conter erros de captação. '
                                           'O assistente médico deve ser capaz de reunir todos os sintomas reportados, por ordem de importância médica, em uma lista simples e objetiva. '
                                           'Não explique ou faça nenhum comentário. Escreva apenas a lista e nada mais.')},
            {'role': 'user', 'content': transcription}
        ]
        asyncio.run_coroutine_threadsafe(self.gpt_controller.send_query(messages, self.set_symptoms_callback), self.asyncio_loop)
        
        print("sending diagnostics query...")
        messages = [
            {'role': 'system', 'content': ('Haja como um assistente médico que possui o objetivo de listar todos os possíveis diagnósticos de um paciente em uma consulta médicas. '
                                           'Essas consultas estão no formato de transcrições, geradas a partir de gravações de áudio que podem conter erros de captação. '
                                           'O assistente médico deve ser capaz de reunir todos os possíveis diagnósticos, por ordem de importância médica, em uma lista simples e objetiva. '
                                           'Não explique ou faça nenhum comentário. Apenas liste os diagnósticos com uma breve descrição do motivo.')},
            {'role': 'user', 'content': transcription}
        ]
        asyncio.run_coroutine_threadsafe(self.gpt_controller.send_query(messages, self.set_diagnostics_callback), self.asyncio_loop)

    def set_resume_callback(self, resume_msg):
        print("setting resume callback...")
        self.root.after(0, self.update_ui_with_resume, resume_msg.content)
    def update_ui_with_resume(self, resume):
        print("updating UI with resume...")
        self.textbox_right.delete('1.0', tk.END)
        self.textbox_right.insert(tk.END, resume)
        self.textbox_right.see(tk.END)

    def set_symptoms_callback(self, symptoms_msg):
        print("setting symptoms callback...")
        self.root.after(0, self.update_ui_with_symptoms, symptoms_msg.content)
    def update_ui_with_symptoms(self, symptoms):
        print("updating UI with symptoms...")
        self.textbox_right2.delete('1.0', tk.END)
        self.textbox_right2.insert(tk.END, symptoms)
        self.textbox_right2.see(tk.END)

    def set_diagnostics_callback(self, diagnostics_msg):
        print("setting diagnostics callback...")
        self.root.after(0, self.update_ui_with_diagnostics, diagnostics_msg.content)
    def update_ui_with_diagnostics(self, diagnostics):
        print("updating UI with diagnostics...")
        self.textbox_right3.delete('1.0', tk.END)
        self.textbox_right3.insert(tk.END, diagnostics)
        self.textbox_right3.see(tk.END)

    def toggle_capture(self):
        print("toggling capture...")
        if self.audio_recorder.stream == None:
            self.start_audio_recording()
        else:
            self.stop_audio_recording()

    def update_log(self, message, color='black'):
        print (f"updating log with message: {message}")
        def task():
            self.textbox_left.insert(tk.END, message)
            self.textbox_left.see(tk.END)
        self.root.after(0, task)

    def clear_log(self):
        self.textbox_left.configure(state='normal')
        self.textbox_left.delete('1.0', tk.END)

    def fill_results(self, results):
        # clear guru textbox
        self.textbox_right.delete('1.0', tk.END)
        self.textbox_right.insert(tk.END, results)
        self.textbox_right.see(tk.END)

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
