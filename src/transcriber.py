import asyncio
import wave
import pyaudio
from deepgram import DeepgramClient, DeepgramClientOptions, PrerecordedOptions, FileSource
import numpy as np
import queue
import logging

# single audio stream that generate audio slices from an input device
class AudioRecorder:
    def __init__(self, pyaudio_obj: pyaudio.PyAudio):
        self.p = pyaudio_obj
        self.file_name = 'consulta_audio.wav'
        self.stream = None
        self.wave_file = None

    def start(self, device_id, source_rate, file_name = 'consulta_audio.wav'):
        try:
            self.file_name = file_name
            self.stream = self.p.open(format=pyaudio.paInt16,
                                    channels=1,
                                    rate=int(source_rate),
                                    input=True,
                                    input_device_index=device_id,
                                    frames_per_buffer=int(1024*4),
                                    stream_callback=self._fill_file)
            self.wave_file = wave.open(self.file_name, 'wb')
            self.wave_file.setnchannels(1)
            self.wave_file.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
            self.wave_file.setframerate(source_rate)
        except Exception as e:
            print(f"start audio recording exception {e}")

    def stop(self):
        try:
            if self.stream is None:
                return None
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            if self.wave_file is None:
                return None
            self.wave_file.close()
            self.wave_file = None
            return self.file_name
        except Exception as e:
            print(f"stop audio recording exception {e}")
            return None

    def _fill_file(self, in_data, frame_count, time_info, status):
        try:
            self.wave_file.writeframes(in_data)
            return (None, pyaudio.paContinue)
        except Exception as e:
            print ("fill buffer exception", e)
    
class AudioTranscriber:
    def __init__(self, DEEPGRAM_API_KEY: str):
        # config: DeepgramClientOptions = DeepgramClientOptions(verbose=logging.SPAM)
        self.client = DeepgramClient(api_key=DEEPGRAM_API_KEY)

    def transcribe(self, file_name: str, language: str = "pt-BR"):
        try:
            print('transcribing', file_name)
            with open(file_name, "rb") as file:
                buffer_data = file.read()
            print('file read...')
            payload = {"buffer": buffer_data}
            options = PrerecordedOptions(model="nova-2", language=language, smart_format=True, diarize=True) # nova-2-medical is [en, en-US] only
            print('sending to deepgram...')
            response = self.client.listen.prerecorded.v("1").transcribe_file(payload, options)
            print('checking response and returning...')
            if response and response.results and response.results.channels and response.results.channels[0].alternatives and response.results.channels[0].alternatives[0].transcript:
                print('valid response!')
                return response.results.channels[0].alternatives[0].transcript
            print('Invalid response!')
            return None
        except Exception as e:
            print(f"transcription exception: {e}")
            return None


# # accept audio slices and sends them to deepgram returning transcriptions
# class DeepgramTranscriber:
#     def __init__(self, DEEPGRAM_API_KEY):
#         self.client = Deepgram(DEEPGRAM_API_KEY)
#         self.deepgram_live = None
#         self.results_queue = None
#         self.last_speaker = ""

#     async def initialize(self, results_queue: queue.Queue, language: str, channels: int, multichannel: bool):
#         self.results_queue = results_queue
#         try:
#             # create a websocket connection to deepgram
#             self.deepgram_live = await self.client.transcription.live(
#                 { 
#                     "smart_format": True, 
#                     "model": "nova-2", 
#                     "language": language,
#                     "encoding": "linear16",
#                     "multichannel": multichannel,
#                     "channels": channels,
#                     "sample_rate": 16000
#                 }
#             )
#             print("transcription live")
#         except Exception as e:
#             print(f'could not open deepgram socket: {e}')
        
#         # deepgram events
#         self.deepgram_live.register_handler(
#             self.deepgram_live.event.TRANSCRIPT_RECEIVED, 
#             self._transcript_received
#         )

#         self.deepgram_live.register_handler(
#             self.deepgram_live.event.CLOSE,
#             lambda _: print('deepgram connection closed')
#         )
    
#     # put transcription results on queue appending the speaker prefix when needed.
#     async def _transcript_received(self, transcript_json: dict):
#         if not 'channel' in transcript_json:
#             return
        
#         transcription: str = transcript_json['channel']['alternatives'][0]['transcript']
        
#         # stop propagation if empty
#         if not transcription:
#             return
        
#         # clear new lines
#         transcription = transcription.replace('\n', '').replace('\r', '')

#         # check need for prefix and speaker identifier
#         is_channel_0 = transcript_json['channel_index'][0] == 0
#         msg_type = 'user_msg' if is_channel_0 else 'system_msg'
#         speaker = 'user: ' if is_channel_0 else 'system: '
#         if self.last_speaker == "":
#             # first message
#             transcription = speaker + transcription
#         elif speaker != self.last_speaker:
#             # new speaker
#             transcription = "\n" + speaker + transcription
#         else:
#             # same speaker
#             transcription = " " + transcription
        
#         # put message in queue for consumption
#         try:
#             self.results_queue.put_nowait((msg_type, transcription))
#         except queue.Full:
#             print("results queue full")
#         except Exception as e:
#             print(f"results queue exception {e}")
        
#         # update last speaker
#         self.last_speaker = speaker
    
#     # sends audio chunk to live transcription API
#     def send_audio(self, chunk):
#         try:
#             self.deepgram_live.send(chunk)
#         except Exception as e:
#             print(f"deepgram send audio exception {e}")
    
#     async def close(self):
#         # check if deepgram connection is open before finishing
#         if self.deepgram_live is None:
#             return
#         try:
#             await self.deepgram_live.finish()
#             self.deepgram_live = None
#         except:
#             print("exception when closing deepgram")
