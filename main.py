"""
ADC Studio — Grabador y Analizador de Espectro
Funcionalidades: grabación de audio, exportación WAV/MP3, comparación de espectros
"""

import customtkinter as ctk
import threading
import numpy as np
from scipy.io import wavfile
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import time
import warnings
warnings.filterwarnings('ignore')

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

# ─── Configuración de tema ───────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg_primary":    "#0A0E1A",
    "bg_secondary":  "#0F1629",
    "bg_card":       "#141B2D",
    "bg_input":      "#1A2235",
    "accent_cyan":   "#00D4FF",
    "accent_green":  "#00FF88",
    "accent_orange": "#FF6B35",
    "accent_purple": "#7C3AED",
    "text_primary":  "#E8EDF5",
    "text_secondary":"#8892A4",
    "border":        "#1E2D45",
    "recording":     "#FF3B5C",
    "wave_orig":     "#00D4FF",
    "wave_conv":     "#00FF88",
    "wave_dig":      "#FFE033",
}


class AudioRecorder:
    """Motor de grabación y procesamiento de audio"""

    def __init__(self):
        self.original_audio = None
        self.original_sr = None
        self.digitized_audio = None
        self.digitized_sr = None
        self.exported_audio = None
        self.exported_sr = None
        self.recording = False
        self.recorded_chunks = []
        self.stream = None

    # ── Grabación ────────────────────────────────────────────────────────────
    def start_recording(self, sample_rate=44100):
        self.recorded_chunks = []
        self.recording = True
        self.original_sr = sample_rate

        def callback(indata, frames, time_info, status):
            if self.recording:
                self.recorded_chunks.append(indata.copy())

        self.stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype='float32',
            callback=callback
        )
        self.stream.start()

    def stop_recording(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.recorded_chunks:
            self.original_audio = np.concatenate(self.recorded_chunks, axis=0).flatten()
            return True
        return False

    # ── Digitalización (cuantización) ────────────────────────────────────────
    def digitize(self, bit_depth=16):
        if self.original_audio is None:
            return False
        levels = 2 ** bit_depth
        audio_clipped = np.clip(self.original_audio, -1.0, 1.0)
        audio_quantized = np.round(audio_clipped * (levels / 2)) / (levels / 2)
        self.digitized_audio = audio_quantized.astype(np.float32)
        self.digitized_sr = self.original_sr
        return True

    # ── Exportación WAV ───────────────────────────────────────────────────────
    def export_wav(self, filepath, bit_depth=16):
        if self.original_audio is None:
            return False
        audio = self.original_audio
        if bit_depth == 8:
            data = np.clip(audio * 128 + 128, 0, 255).astype(np.uint8)
        elif bit_depth == 16:
            data = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        elif bit_depth == 32:
            data = np.clip(audio * 2147483647, -2147483648, 2147483647).astype(np.int32)
        else:
            data = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        wavfile.write(filepath, self.original_sr, data)
        # Guardar referencia del audio exportado para comparación de espectros
        self.exported_audio = audio.copy()
        self.exported_sr = self.original_sr
        return True

    # ── Exportación MP3 ───────────────────────────────────────────────────────
    def export_mp3(self, filepath, bit_depth=16):
        if not PYDUB_AVAILABLE:
            return False, "pydub no disponible"
        tmp_wav = filepath.replace('.mp3', '_tmp.wav')
        self.export_wav(tmp_wav, bit_depth)
        audio_seg = AudioSegment.from_wav(tmp_wav)
        audio_seg.export(filepath, format="mp3", bitrate="192k")
        os.remove(tmp_wav)
        return True, ""

    # ── Espectros de frecuencia ───────────────────────────────────────────────
    def get_spectrum(self, audio, sr):
        if audio is None or len(audio) == 0:
            return None, None
        n = len(audio)
        freqs = np.fft.rfftfreq(n, d=1.0/sr)
        spectrum = np.abs(np.fft.rfft(audio))
        spectrum_db = 20 * np.log10(spectrum + 1e-9)
        return freqs, spectrum_db

    def get_duration(self, audio, sr):
        if audio is None:
            return 0
        return len(audio) / sr


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.is_recording = False
        self.record_start_time = None
        self._after_record_id = None
        self._setup_window()
        self._build_ui()

    # ── Configuración ventana ─────────────────────────────────────────────────
    def _setup_window(self):
        self.title("ADC Studio — Grabador y Analizador de Espectro")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.configure(fg_color=COLORS["bg_primary"])

    # ── UI principal ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        self._build_sidebar(main)
        self._build_content(main)

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"],
                           corner_radius=0, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr,
            text="◈  ADC STUDIO",
            font=ctk.CTkFont("Courier", 22, "bold"),
            text_color=COLORS["accent_cyan"]
        ).pack(side="left", padx=24, pady=16)

        self.status_label = ctk.CTkLabel(
            hdr,
            text="● IDLE",
            font=ctk.CTkFont("Courier", 12),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="right", padx=24)

        ctk.CTkLabel(
            hdr,
            text="Grabador · Exportador · Analizador de Espectro",
            font=ctk.CTkFont("Courier", 11),
            text_color=COLORS["text_secondary"]
        ).pack(side="right", padx=8)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        sb = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"],
                          corner_radius=12, width=300)
        sb.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=8)
        sb.grid_propagate(False)
        sb.pack_propagate(False)

        pad = {"padx": 16, "pady": 6}

        # ─ Sección: Grabación ─
        self._section_title(sb, "GRABACIÓN DE AUDIO")

        ctk.CTkLabel(sb, text="Sample Rate (Hz)",
                     font=ctk.CTkFont("Courier", 11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", padx=16)
        self.sr_var = ctk.StringVar(value="44100")
        self.sr_menu = ctk.CTkOptionMenu(
            sb,
            values=["8000", "11025", "16000", "22050", "44100", "48000", "96000"],
            variable=self.sr_var,
            fg_color=COLORS["bg_input"], button_color=COLORS["accent_cyan"],
            button_hover_color="#00AACC", dropdown_fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont("Courier", 12),
            corner_radius=8, height=32
        )
        self.sr_menu.pack(fill="x", **pad)

        self.btn_record = ctk.CTkButton(
            sb, text="⏺  Iniciar Grabación",
            command=self._toggle_record,
            fg_color=COLORS["accent_purple"], hover_color="#6D28D9",
            text_color="white",
            font=ctk.CTkFont("Courier", 12, "bold"),
            corner_radius=8, height=40
        )
        self.btn_record.pack(fill="x", **pad)

        self.rec_timer = ctk.CTkLabel(
            sb, text="00:00", font=ctk.CTkFont("Courier", 36, "bold"),
            text_color=COLORS["recording"]
        )
        self.rec_timer.pack(pady=4)

        # Info grabación
        self.info_duration = ctk.CTkLabel(
            sb, text="Duración: —",
            font=ctk.CTkFont("Courier", 10),
            text_color=COLORS["text_secondary"]
        )
        self.info_duration.pack(pady=(0, 2))

        self.info_sr = ctk.CTkLabel(
            sb, text="Sample Rate: —",
            font=ctk.CTkFont("Courier", 10),
            text_color=COLORS["text_secondary"]
        )
        self.info_sr.pack(pady=(0, 2))

        # ─ Sección: Reproducción ─
        self._section_title(sb, "REPRODUCCIÓN")

        self.btn_play = ctk.CTkButton(
            sb, text="▶  Reproducir original",
            command=self._play_audio,
            fg_color=COLORS["bg_input"], hover_color=COLORS["border"],
            text_color=COLORS["wave_orig"],
            font=ctk.CTkFont("Courier", 11),
            corner_radius=6, height=34
        )
        self.btn_play.pack(fill="x", **pad)

        self.btn_play_dig = ctk.CTkButton(
            sb, text="▶  Reproducir digitalizado",
            command=self._play_digitized,
            fg_color=COLORS["bg_input"], hover_color=COLORS["border"],
            text_color=COLORS["wave_dig"],
            font=ctk.CTkFont("Courier", 11),
            corner_radius=6, height=34
        )
        self.btn_play_dig.pack(fill="x", **pad)

        self.btn_stop_play = ctk.CTkButton(
            sb, text="⏹  Detener",
            command=lambda: sd.stop(),
            fg_color=COLORS["bg_input"], hover_color=COLORS["border"],
            text_color=COLORS["accent_orange"],
            font=ctk.CTkFont("Courier", 11),
            corner_radius=6, height=30
        )
        self.btn_stop_play.pack(fill="x", padx=16, pady=(0, 4))

        # ─ Sección: Exportar ─
        self._section_title(sb, "EXPORTAR AUDIO")

        ctk.CTkLabel(sb, text="Bit Depth",
                     font=ctk.CTkFont("Courier", 11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", padx=16)
        self.bit_var = ctk.StringVar(value="16")
        self.bit_menu = ctk.CTkOptionMenu(
            sb,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "16", "32"],
            variable=self.bit_var,
            fg_color=COLORS["bg_input"], button_color="#FFE033",
            button_hover_color="#CCB200", dropdown_fg_color=COLORS["bg_card"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont("Courier", 12),
            corner_radius=8, height=32
        )
        self.bit_menu.pack(fill="x", **pad)

        self.btn_digitize = ctk.CTkButton(
            sb, text="⚡  Digitalizar",
            command=self._digitize,
            fg_color=COLORS["accent_cyan"], hover_color="#00AACC",
            text_color=COLORS["bg_primary"],
            font=ctk.CTkFont("Courier", 12, "bold"),
            corner_radius=8, height=38
        )
        self.btn_digitize.pack(fill="x", **pad)

        row_exp = ctk.CTkFrame(sb, fg_color="transparent")
        row_exp.pack(fill="x", padx=16, pady=4)

        self.btn_wav = ctk.CTkButton(
            row_exp, text="💾 WAV",
            command=self._export_wav,
            fg_color=COLORS["accent_green"], hover_color="#00CC70",
            text_color=COLORS["bg_primary"],
            font=ctk.CTkFont("Courier", 11, "bold"),
            corner_radius=6, height=34
        )
        self.btn_wav.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_mp3 = ctk.CTkButton(
            row_exp, text="💾 MP3",
            command=self._export_mp3,
            fg_color=COLORS["accent_orange"], hover_color="#E55A28",
            text_color="white",
            font=ctk.CTkFont("Courier", 11, "bold"),
            corner_radius=6, height=34
        )
        self.btn_mp3.pack(side="left", expand=True, fill="x")

        self._section_title(sb, "ESPECTROS")
        ctk.CTkLabel(
            sb,
            text="Digitalizá para ver la señal\ncuantizada en tiempo y frecuencia.\nExportá para comparar espectros.",
            font=ctk.CTkFont("Courier", 9),
            text_color=COLORS["text_secondary"],
            justify="left"
        ).pack(anchor="w", padx=16, pady=4)

    def _section_title(self, parent, text):
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=28)
        frame.pack(fill="x", padx=16, pady=(10, 2))
        ctk.CTkLabel(frame, text=text,
                     font=ctk.CTkFont("Courier", 9, "bold"),
                     text_color=COLORS["accent_cyan"]).pack(side="left")
        ctk.CTkFrame(frame, fg_color=COLORS["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=12)

    # ── Área de contenido (gráficas) ──────────────────────────────────────────
    def _build_content(self, parent):
        content = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"],
                               corner_radius=12)
        content.grid(row=0, column=1, sticky="nsew", pady=8)

        # Tabs: solo FORMA DE ONDA y ESPECTRO
        tab_bar = ctk.CTkFrame(content, fg_color="transparent", height=48)
        tab_bar.pack(fill="x", padx=16, pady=(12, 0))

        self.tab_var = tk.StringVar(value="waveform")
        tabs = [("FORMA DE ONDA", "waveform"),
                ("ESPECTRO", "spectrum")]
        self.tab_buttons = {}
        for label, key in tabs:
            btn = ctk.CTkButton(
                tab_bar, text=label,
                command=lambda k=key: self._switch_tab(k),
                fg_color=COLORS["accent_cyan"] if key == "waveform" else COLORS["bg_input"],
                hover_color=COLORS["border"],
                text_color=COLORS["bg_primary"] if key == "waveform" else COLORS["text_secondary"],
                font=ctk.CTkFont("Courier", 10, "bold"),
                corner_radius=6, height=30, width=160
            )
            btn.pack(side="left", padx=(0, 6))
            self.tab_buttons[key] = btn

        # Canvas matplotlib
        self.fig = Figure(figsize=(9, 5.5), dpi=96,
                          facecolor=COLORS["bg_card"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=content)
        self.canvas.get_tk_widget().pack(fill="both", expand=True,
                                         padx=16, pady=12)
        self._draw_empty_plot()

    def _switch_tab(self, key):
        self.tab_var.set(key)
        for k, btn in self.tab_buttons.items():
            if k == key:
                btn.configure(fg_color=COLORS["accent_cyan"],
                              text_color=COLORS["bg_primary"])
            else:
                btn.configure(fg_color=COLORS["bg_input"],
                              text_color=COLORS["text_secondary"])
        self._refresh_plots()

    # ── Gráficas ──────────────────────────────────────────────────────────────
    def _draw_empty_plot(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(COLORS["bg_card"])
        ax.set_title("Grabá audio para comenzar",
                     color=COLORS["text_secondary"],
                     fontfamily="monospace", fontsize=12)
        ax.tick_params(colors=COLORS["text_secondary"])
        for spine in ax.spines.values():
            spine.set_edgecolor(COLORS["border"])
        self.canvas.draw()

    def _refresh_plots(self):
        tab = self.tab_var.get()
        self.fig.clear()
        self.fig.set_facecolor(COLORS["bg_card"])

        if tab == "waveform":
            self._plot_waveform()
        elif tab == "spectrum":
            self._plot_spectrum()

        self.canvas.draw()

    def _style_ax(self, ax, title, xlabel, ylabel):
        ax.set_facecolor(COLORS["bg_primary"])
        ax.set_title(title, color=COLORS["text_primary"],
                     fontfamily="monospace", fontsize=10, pad=8)
        ax.set_xlabel(xlabel, color=COLORS["text_secondary"],
                      fontfamily="monospace", fontsize=9)
        ax.set_ylabel(ylabel, color=COLORS["text_secondary"],
                      fontfamily="monospace", fontsize=9)
        ax.tick_params(colors=COLORS["text_secondary"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(COLORS["border"])
        ax.grid(color=COLORS["border"], alpha=0.4, linewidth=0.5)

    def _plot_waveform(self):
        has_orig = self.recorder.original_audio is not None
        has_dig  = self.recorder.digitized_audio is not None

        if not has_orig:
            ax = self.fig.add_subplot(111)
            self._style_ax(ax, "Sin audio grabado", "", "")
            return

        rows = 2 if has_dig else 1
        axes = self.fig.subplots(rows, 1, squeeze=False)
        self.fig.subplots_adjust(hspace=0.55)

        # Panel superior: señal original
        audio = self.recorder.original_audio
        sr    = self.recorder.original_sr
        t     = np.linspace(0, len(audio)/sr, len(audio))
        step  = max(1, len(t) // 8000)
        axes[0][0].plot(t[::step], audio[::step],
                        color=COLORS["wave_orig"], linewidth=0.6, alpha=0.9,
                        label="Señal grabada (analógica)")
        self._style_ax(axes[0][0], f"SEÑAL ORIGINAL  [{sr} Hz]",
                       "Tiempo (s)", "Amplitud")
        axes[0][0].legend(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"],
                          labelcolor=COLORS["text_primary"], fontsize=8)

        # Panel inferior: señal digitalizada
        if has_dig:
            daud = self.recorder.digitized_audio
            dsr  = self.recorder.digitized_sr
            td   = np.linspace(0, len(daud)/dsr, len(daud))
            step2 = max(1, len(td) // 8000)
            axes[1][0].step(td[::step2], daud[::step2],
                            color=COLORS["wave_dig"], linewidth=0.8, alpha=0.9,
                            label=f"Señal digitalizada ({self.bit_var.get()} bits)")
            self._style_ax(axes[1][0],
                           f"SEÑAL DIGITALIZADA  [{dsr} Hz / {self.bit_var.get()} bits]",
                           "Tiempo (s)", "Amplitud")
            axes[1][0].legend(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"],
                              labelcolor=COLORS["text_primary"], fontsize=8)

    def _plot_spectrum(self):
        has_orig = self.recorder.original_audio is not None
        has_dig  = self.recorder.digitized_audio is not None
        has_exp  = self.recorder.exported_audio is not None

        ax = self.fig.add_subplot(111)

        if has_orig:
            freqs, spec = self.recorder.get_spectrum(
                self.recorder.original_audio, self.recorder.original_sr)
            step = max(1, len(freqs) // 4000)
            ax.plot(freqs[::step], spec[::step],
                    color=COLORS["wave_orig"], linewidth=0.9,
                    label="Original (grabada)", alpha=0.85)

        if has_dig:
            freqs, spec = self.recorder.get_spectrum(
                self.recorder.digitized_audio, self.recorder.digitized_sr)
            step = max(1, len(freqs) // 4000)
            ax.plot(freqs[::step], spec[::step],
                    color=COLORS["wave_dig"], linewidth=0.9,
                    label=f"Digitalizada ({self.bit_var.get()} bits)",
                    alpha=0.85, linestyle="--")

        if has_exp and not has_dig:
            freqs, spec = self.recorder.get_spectrum(
                self.recorder.exported_audio, self.recorder.exported_sr)
            step = max(1, len(freqs) // 4000)
            ax.plot(freqs[::step], spec[::step],
                    color=COLORS["accent_orange"], linewidth=0.9,
                    label="Exportada", alpha=0.85, linestyle=":")

        if has_orig or has_dig or has_exp:
            sr = self.recorder.original_sr or 44100
            ax.set_xlim(0, min(22050, sr // 2))
            ax.set_ylim(bottom=-10)
            ax.legend(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"],
                      labelcolor=COLORS["text_primary"], fontsize=9)
        else:
            ax.set_title("Grabá y digitalizá audio para ver el espectro",
                         color=COLORS["text_secondary"], fontfamily="monospace")

        self._style_ax(ax, "COMPARACIÓN DE ESPECTROS DE FRECUENCIA",
                       "Frecuencia (Hz)", "Magnitud (dB)")

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _set_status(self, text, color=None):
        color = color or COLORS["text_secondary"]
        self.status_label.configure(text=text, text_color=color)

    def _toggle_record(self):
        if not self.is_recording:
            try:
                sr = int(self.sr_var.get())
                self.recorder.start_recording(sr)
                self.is_recording = True
                self.record_start_time = time.time()
                self.btn_record.configure(
                    text="⏹  Detener Grabación",
                    fg_color=COLORS["recording"], hover_color="#CC2244")
                self._set_status("● GRABANDO", COLORS["recording"])
                self._update_timer()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo iniciar grabación:\n{e}")
        else:
            self._stop_record()

    def _stop_record(self):
        if self._after_record_id:
            self.after_cancel(self._after_record_id)
        ok = self.recorder.stop_recording()
        self.is_recording = False
        self.btn_record.configure(
            text="⏺  Iniciar Grabación",
            fg_color=COLORS["accent_purple"], hover_color="#6D28D9")
        if ok:
            self._set_status("● GRABACIÓN COMPLETA", COLORS["accent_green"])
            dur = self.recorder.get_duration(
                self.recorder.original_audio, self.recorder.original_sr)
            self.info_duration.configure(
                text=f"Duración: {dur:.2f} s",
                text_color=COLORS["accent_cyan"])
            self.info_sr.configure(
                text=f"Sample Rate: {self.recorder.original_sr:,} Hz",
                text_color=COLORS["accent_cyan"])
            self._refresh_plots()
        else:
            self._set_status("● SIN AUDIO", COLORS["text_secondary"])

    def _update_timer(self):
        if self.is_recording:
            elapsed = int(time.time() - self.record_start_time)
            m, s = divmod(elapsed, 60)
            self.rec_timer.configure(text=f"{m:02d}:{s:02d}")
            self._after_record_id = self.after(500, self._update_timer)
        else:
            self.rec_timer.configure(text="00:00")

    def _digitize(self):
        if self.recorder.original_audio is None:
            messagebox.showwarning("Sin audio", "Grabá audio primero.")
            return
        bits = int(self.bit_var.get())
        self._set_status("⚙ DIGITALIZANDO...", COLORS["accent_cyan"])
        self.update()
        ok = self.recorder.digitize(bits)
        if ok:
            self._set_status(f"● DIGITALIZADO  [{bits} bits]", COLORS["accent_green"])
            self._refresh_plots()
        else:
            self._set_status("● ERROR", COLORS["accent_orange"])

    def _play_audio(self):
        if self.recorder.original_audio is None:
            messagebox.showwarning("Sin audio", "No hay audio grabado.")
            return
        sd.stop()
        sd.play(self.recorder.original_audio, self.recorder.original_sr)
        self._set_status("▶ REPRODUCIENDO ORIGINAL", COLORS["wave_orig"])

    def _play_digitized(self):
        if self.recorder.digitized_audio is None:
            messagebox.showwarning("Sin audio", "Digitalizá el audio primero.")
            return
        sd.stop()
        sd.play(self.recorder.digitized_audio, self.recorder.digitized_sr)
        self._set_status(f"▶ REPRODUCIENDO DIGITALIZADO  [{self.bit_var.get()} bits]",
                         COLORS["wave_dig"])

    def _export_wav(self):
        if self.recorder.digitized_audio is None:
            messagebox.showwarning("Sin audio", "Digitalizá el audio primero.")
            return
        bits = int(self.bit_var.get())
        path = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")])
        if not path:
            return
        try:
            # Exportar el audio digitalizado
            audio = self.recorder.digitized_audio
            sr = self.recorder.digitized_sr
            if bits == 8:
                data = np.clip(audio * 128 + 128, 0, 255).astype(np.uint8)
            elif bits == 32:
                data = np.clip(audio * 2147483647, -2147483648, 2147483647).astype(np.int32)
            else:
                data = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
            wavfile.write(path, sr, data)
            self.recorder.exported_audio = audio.copy()
            self.recorder.exported_sr = sr
            self._set_status("● WAV EXPORTADO", COLORS["accent_green"])
            messagebox.showinfo("Exportado", f"Archivo guardado:\n{path}")
            self._refresh_plots()
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar:\n{e}")

    def _export_mp3(self):
        if self.recorder.digitized_audio is None:
            messagebox.showwarning("Sin audio", "Digitalizá el audio primero.")
            return
        if not PYDUB_AVAILABLE:
            messagebox.showerror(
                "pydub no disponible",
                "Instala pydub y ffmpeg:\n  pip install pydub\n  (+ ffmpeg en PATH)")
            return
        bits = int(self.bit_var.get())
        path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 files", "*.mp3")])
        if not path:
            return
        try:
            # Guardar WAV temporal del audio digitalizado y convertir a MP3
            tmp_wav = path.replace('.mp3', '_tmp.wav')
            audio = self.recorder.digitized_audio
            sr = self.recorder.digitized_sr
            if bits == 8:
                data = np.clip(audio * 128 + 128, 0, 255).astype(np.uint8)
            elif bits == 32:
                data = np.clip(audio * 2147483647, -2147483648, 2147483647).astype(np.int32)
            else:
                data = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
            wavfile.write(tmp_wav, sr, data)
            audio_seg = AudioSegment.from_wav(tmp_wav)
            audio_seg.export(path, format="mp3", bitrate="192k")
            os.remove(tmp_wav)
            self.recorder.exported_audio = audio.copy()
            self.recorder.exported_sr = sr
            self._set_status("● MP3 EXPORTADO", COLORS["accent_green"])
            messagebox.showinfo("Exportado", f"Archivo guardado:\n{path}")
            self._refresh_plots()
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar MP3:\n{e}")


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()