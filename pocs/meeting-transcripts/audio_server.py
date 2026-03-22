import asyncio
import os
import struct
import threading
import wave

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")

SAMPLE_RATE = 16000
CHANNELS = 1


class AudioServer:
    def __init__(self, port=0):
        self._requested_port = port
        self.port = None
        self._chunks = []
        self._loop = None
        self._thread = None
        self._server = None
        self._audio_file = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # Wait until server is ready
        while self.port is None:
            pass

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        import websockets

        self._stop_event = asyncio.Event()

        async def handler(websocket):
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Float32 PCM data
                        n_samples = len(message) // 4
                        samples = struct.unpack(f"{n_samples}f", message)
                        self._chunks.append(np.array(samples, dtype=np.float32))
            except Exception as e:
                print(f"[audio_server] Connection error: {e}")

        server = await websockets.serve(handler, "localhost", self._requested_port)
        self.port = server.sockets[0].getsockname()[1]
        print(f"[audio_server] Listening on ws://localhost:{self.port}")

        await self._stop_event.wait()
        server.close()
        await server.wait_closed()

    def stop(self):
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread:
            self._thread.join(timeout=5)

    def get_audio_file(self, filename="recording.wav"):
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        filepath = os.path.join(RECORDINGS_DIR, filename)

        if not self._chunks:
            print("[audio_server] No audio data captured")
            return None

        audio = np.concatenate(self._chunks)
        # Convert float32 [-1, 1] to int16
        audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        duration = len(audio_int16) / SAMPLE_RATE
        print(f"[audio_server] Saved {duration:.1f}s of audio to {filepath}")
        self._audio_file = filepath
        return filepath
