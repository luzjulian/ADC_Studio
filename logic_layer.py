import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wavfile
import audioop # Parche de compatibilidad Python 3.13
from pydub import AudioSegment

class BusinessLogicLayer:
    def __init__(self):
        self.sample_rate = 44100
        self.bit_depth = 16
        self.audio_original = None
        self.audio_convertido = None
        self.recording = None

    def start_recording(self, duration=5):
        self.recording = sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype='float32')

    def stop_recording(self):
        sd.wait()
        if self.recording is not None:
            self.audio_original = self.recording.flatten()
        return self.audio_original

    def load_audio_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.wav':
            sr, data = wavfile.read(file_path)
            if len(data.shape) > 1:
                data = data[:, 0]
                
            if data.dtype == np.int16:
                data = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                data = data.astype(np.float32) / 2147483648.0
            elif data.dtype == np.uint8:
                data = (data.astype(np.float32) - 128.0) / 128.0
            else:
                data = data.astype(np.float32)
                
            self.sample_rate = sr
            self.audio_original = data

        elif ext == '.mp3':
            audio_segment = AudioSegment.from_mp3(file_path)
            if audio_segment.channels > 1:
                audio_segment = audio_segment.set_channels(1)
                
            self.sample_rate = audio_segment.frame_rate
            raw_data = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
            max_possible_value = 2 ** (8 * audio_segment.sample_width - 1)
            self.audio_original = raw_data / max_possible_value
            
        else:
            raise ValueError("Formato no soportado.")
            
        self.audio_convertido = None 
        return self.sample_rate

    def calculate_spectrum(self, audio_signal):
        if audio_signal is None:
            return None, None
            
        n = len(audio_signal)
        fft_y = np.fft.fft(audio_signal)
        fft_x = np.fft.fftfreq(n, 1 / self.sample_rate)
        
        half_n = n // 2
        magnitud = np.abs(fft_y[:half_n])
        magnitud_db = 20 * np.log10(magnitud + 1e-10) 
        
        return fft_x[:half_n], magnitud_db

    def quantize_signal(self):
        if self.audio_original is None:
            return None
            
        levels = 2 ** self.bit_depth
        signal_normalized = np.clip(self.audio_original, -1.0, 1.0)
        quantized = np.round((signal_normalized + 1.0) / 2.0 * (levels - 1))
        self.audio_convertido = (quantized / (levels - 1)) * 2.0 - 1.0
        return self.audio_convertido