import scipy.io.wavfile as wavfile
import numpy as np
import audioop # Parche de compatibilidad Python 3.13
from pydub import AudioSegment

class DataAccessLayer:
    @staticmethod
    def export_wav(file_path, sample_rate, audio_data):
        wavfile.write(file_path, sample_rate, audio_data)

    @staticmethod
    def export_mp3(file_path, sample_rate, audio_data):
        audio_int16 = np.int16(audio_data * 32767)
        audio_segment = AudioSegment(
            audio_int16.tobytes(), 
            frame_rate=sample_rate,
            sample_width=audio_int16.dtype.itemsize, 
            channels=1
        )
        audio_segment.export(file_path, format="mp3")