import asyncio
from threading import Thread
import pyaudio
import os
from app_controller import AppController
from app_gui import AppGUI
from transcriber import AudioRecorder, AudioTranscriber
from dotenv import load_dotenv
from gpt_client import GPTClient
load_dotenv()

DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# asyncio event wrapper
class EventAsyncio:
    def __init__(self):
        self.event = None
    
    def create(self):
        self.event = asyncio.Event()

    def set(self):
        if self.event is not None:
            self.event.set()
    
    def wait(self):
        if self.event is not None:
            return self.event.wait()

# start asyncio loop in current thread
def start_asyncio_loop(loop, terminate_event: EventAsyncio):
    asyncio.set_event_loop(loop)
    terminate_event.create()
    loop.run_until_complete(asyncio_main(terminate_event))
    loop.close()

# keep asyncio loop running
async def asyncio_main(terminate_event: EventAsyncio):
    try:
        await terminate_event.wait()
        print('asyncio_main() terminating...')
    except Exception as e:
        print(f'main routine exception {e}')
        
def main():
    p = pyaudio.PyAudio()
    audio_recorder = AudioRecorder(p)
    audio_transcriber = AudioTranscriber(DEEPGRAM_API_KEY)
    gpt_controller = GPTClient(OPENAI_API_KEY)
    
    terminate_event = EventAsyncio()
    asyncio_loop = asyncio.new_event_loop()

    # start the asyncio loop in a separate thread
    asyncio_thread = Thread(target=start_asyncio_loop, args=(asyncio_loop, terminate_event), daemon=True)
    asyncio_thread.start()

    app_controller = AppController(audio_recorder, audio_transcriber, gpt_controller, asyncio_loop, terminate_event)

    # start GUI loop in mainthread
    app_gui = AppGUI(app_controller, p)
    app_gui.run_mainloop()

    p.terminate()

    asyncio_thread.join()

if __name__ == '__main__':
    main()
