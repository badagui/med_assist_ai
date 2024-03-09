import asyncio
from gpt_client import GPTClient
from transcriber import AudioRecorder, AudioTranscriber


class AppController:
    def __init__(self, audio_recorder: AudioRecorder, audio_transcriber: AudioTranscriber, gpt_client: GPTClient, asyncio_loop: asyncio.BaseEventLoop, terminate_event: asyncio.Event ) -> None:
        self.audio_recorder = audio_recorder
        self.audio_transcriber = audio_transcriber
        self.gpt_client = gpt_client
        self.asyncio_loop = asyncio_loop
        self.terminate_event = terminate_event
        self.language = 'en'
    
    def stop_app(self):
        # stop asyncio main loop
        self.asyncio_loop.call_soon_threadsafe(self.terminate_event.set)

    def start_audio_recording(self, device_id, source_rate, file_name="consultation_audio.wav"):
        self.audio_recorder.start(device_id, source_rate, file_name)
    
    def stop_audio_recording_and_transcribe(self):
        test_file = "oet-speaking-sample-role-play-medicine.mp3" # point to specific file for testing
        # test_file = None
        test_transcription = None # point to specific transcription for testing
        
        file_name = self.audio_recorder.stop()
        if test_file is not None:
            file_name = test_file
        if file_name is None:
            return None
        
        if test_transcription is not None:
            transcription = test_transcription
        else:
            transcription = self.audio_transcriber.transcribe(file_name, language=self.language)
        return transcription

    def process_transcription_async(self, transcription, cback_summary, cback_symptoms, cback_diagnostics):
        sys_prompts = {
            'pt-BR': {
                'summary': ('Haja como um assistente médico que possui o objetivo de resumir consultas médicas. '
                            'Essas consultas estão no formato de transcrições, geradas a partir de gravações de áudio que podem conter erros de captação. '
                            'O assistente médico deve ser capaz de resumir a transcrição da consulta em um texto curto e objetivo, mantendo as informações mais importantes. '
                            'Não explique ou faça nenhum comentário. Escreva apenas o resumo da consulta e nada mais.'),
                'symptoms': ('Haja como um assistente médico que possui o objetivo de listar todos os sintomas reportados pelo paciente em uma consulta médicas. '
                             'Essas consultas estão no formato de transcrições, geradas a partir de gravações de áudio que podem conter erros de captação. '
                             'O assistente médico deve ser capaz de reunir todos os sintomas reportados, por ordem de importância médica, em uma lista simples e objetiva. '
                             'Não explique ou faça nenhum comentário. Escreva apenas a lista e nada mais.'),
                'diagnostics': ('Haja como um assistente médico que possui o objetivo de listar todos os possíveis diagnósticos de um paciente em uma consulta médicas. '
                                'Essas consultas estão no formato de transcrições, geradas a partir de gravações de áudio que podem conter erros de captação. '
                                'O assistente médico deve ser capaz de reunir todos os possíveis diagnósticos, por ordem de importância médica, em uma lista simples e objetiva. '
                                'Não explique nem faça comentários. Apenas liste os diagnósticos com uma breve descrição do motivo.')
            },
            'en': {
                'summary': ("Act as a medical assistant whose goal is to summarize medical consultations. "
                           "These consultations are in the form of transcripts, generated from audio recordings that may contain capture errors. "
                           "The medical assistant must be able to summarize the transcript of the consultation in a short and objective text, keeping the most important information. "
                           "Do not explain or make any comments. Write only the summary of the consultation and nothing more."),
                'symptoms': ("Act as a medical assistant whose objective is to list all the symptoms reported by the patient during a medical consultation. "
                             "These consultations are in the form of transcriptions, generated from audio recordings that may contain capture errors. "
                             "The medical assistant must be capable of gathering all reported symptoms, in order of medical importance, into a simple and objective list. "
                             "Do not explain or make any comments. Write only the list and nothing more."),
                'diagnostics': ("Act as a medical assistant whose objective is to list all possible diagnoses of a patient in a medical consultation. "
                                "These consultations are in the form of transcripts, generated from audio recordings that may contain capture errors. "
                                "The medical assistant must be able to gather all possible diagnoses, in order of medical importance, in a simple and objective list. "
                                "Do not explain or make any comments. Just list the diagnoses with a brief description of the reason.")
            }
        }

        assert self.language in sys_prompts, f"Language {self.language} not found"

        messages = [
            {'role': 'system', 'content': sys_prompts[self.language]['summary']},
            {'role': 'user', 'content': transcription}
        ]
        asyncio.run_coroutine_threadsafe(self.gpt_client.send_query(messages, cback_summary), self.asyncio_loop)
    
        messages = [
            {'role': 'system', 'content': sys_prompts[self.language]['symptoms']},
            {'role': 'user', 'content': transcription}
        ]
        asyncio.run_coroutine_threadsafe(self.gpt_client.send_query(messages, cback_symptoms), self.asyncio_loop)
        
        messages = [
            {'role': 'system', 'content': sys_prompts[self.language]['diagnostics']},
            {'role': 'user', 'content': transcription}
        ]
        asyncio.run_coroutine_threadsafe(self.gpt_client.send_query(messages, cback_diagnostics), self.asyncio_loop)
