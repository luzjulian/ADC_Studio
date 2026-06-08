import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import os
from tkinter import messagebox, filedialog

# ¡Aquí importamos nuestros otros archivos!
from data_layer import DataAccessLayer
from logic_layer import BusinessLogicLayer

class PresentationLayer(ctk.CTk):
    def __init__(self, logic, data):
        super().__init__()
        self.logic = logic
        self.data = data
        
        self.title("ADC STUDIO")
        self.geometry("1000x600")
        ctk.set_appearance_mode("dark")
        
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="FUENTE DE AUDIO", text_color="#00FFFF", anchor="w").pack(fill="x", pady=(10, 5), padx=10)
        
        self.btn_load = ctk.CTkButton(self.sidebar, text="📂 Cargar Audio (WAV/MP3)", fg_color="#333344", hover_color="#444455", command=self.load_audio)
        self.btn_load.pack(fill="x", padx=10, pady=(0, 10))
        
        self.btn_record = ctk.CTkButton(self.sidebar, text="Iniciar Grabación", fg_color="#8A2BE2", command=self.start_recording)
        self.btn_record.pack(fill="x", padx=10, pady=0)
        
        self.lbl_timer = ctk.CTkLabel(self.sidebar, text="00:00", font=("Courier", 24, "bold"), text_color="#FF4500")
        self.lbl_timer.pack(pady=5)

        ctk.CTkLabel(self.sidebar, text="PARÁMETROS ADC", text_color="#00FFFF", anchor="w").pack(fill="x", pady=(20, 5), padx=10)
        self.cb_samplerate = ctk.CTkComboBox(self.sidebar, values=["44100", "48000", "96000"])
        self.cb_samplerate.pack(fill="x", padx=10, pady=5)
        
        self.cb_bitdepth = ctk.CTkComboBox(self.sidebar, values=["4", "8", "16", "24"])
        self.cb_bitdepth.set("16")
        self.cb_bitdepth.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.sidebar, text="CONVERSIÓN", text_color="#00FFFF", anchor="w").pack(fill="x", pady=(20, 5), padx=10)
        self.btn_convert = ctk.CTkButton(self.sidebar, text="Convertir", fg_color="#00BFFF", command=self.convert_audio)
        self.btn_convert.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.sidebar, text="EXPORTAR", text_color="#00FFFF", anchor="w").pack(fill="x", pady=(20, 5), padx=10)
        btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        self.btn_export_wav = ctk.CTkButton(btn_frame, text="WAV", fg_color="#00FF7F", width=90, command=lambda: self.export("wav"))
        self.btn_export_wav.pack(side="left", padx=(0, 5))
        self.btn_export_mp3 = ctk.CTkButton(btn_frame, text="MP3", fg_color="#FF7F50", width=90, command=lambda: self.export("mp3"))
        self.btn_export_mp3.pack(side="right", padx=(5, 0))

        self.main_panel = ctk.CTkFrame(self)
        self.main_panel.grid(row=0, column=1, sticky="wew", padx=10, pady=10)
        self.main_panel.pack_propagate(False)
        self.main_panel.grid_configure(sticky="nsew")
        
        self.fig, self.ax = plt.subplots(facecolor='#1E1E2E')
        self.ax.set_facecolor('#1E1E2E')
        self.ax.tick_params(colors='white')
        self.ax.set_title("Espectro de Frecuencias", color='white')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def load_audio(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar señal analógica (WAV o MP3)",
            filetypes=[("Archivos de Audio Soportados", "*.wav *.mp3"), ("Formato WAV", "*.wav"), ("Formato MP3", "*.mp3")]
        )
        if file_path:
            try:
                sr = self.logic.load_audio_file(file_path)
                self.cb_samplerate.set(str(sr))
                self.plot_spectrum(compare=False)
                messagebox.showinfo("Carga Exitosa", f"Archivo analógico cargado correctamente.\nFrecuencia detectada: {sr} Hz")
            except Exception as e:
                messagebox.showerror("Error de lectura", f"No se pudo cargar el archivo de audio:\n{e}")

    def start_recording(self):
        self.btn_record.configure(text="Grabando...", state="disabled")
        self.logic.sample_rate = int(self.cb_samplerate.get())
        threading.Thread(target=self._record_task, daemon=True).start()

    def _record_task(self):
        try:
            self.logic.start_recording(duration=5)
            for i in range(5, 0, -1):
                self.after(0, lambda val=i: self.lbl_timer.configure(text=f"00:0{val}"))
                time.sleep(1)
            self.logic.stop_recording()
        except Exception as e:
            self.after(0, lambda err=e: messagebox.showerror("Error", f"Fallo al grabar: {err}"))
        finally:
            self.after(0, lambda: self.lbl_timer.configure(text="00:00"))
            self.after(0, lambda: self.btn_record.configure(text="Iniciar Grabación", state="normal"))
            self.after(0, lambda: self.plot_spectrum(compare=False))

    def convert_audio(self):
        if self.logic.audio_original is None:
            messagebox.showwarning("Atención", "Debe grabar o cargar un audio primero.")
            return
        self.logic.bit_depth = int(self.cb_bitdepth.get())
        self.logic.quantize_signal()
        self.plot_spectrum(compare=True)

    def plot_spectrum(self, compare=False):
        self.ax.clear()
        self.ax.set_title("Espectro de Frecuencias", color='white')
        self.ax.set_xlabel("Frecuencia (Hz)", color='white')
        self.ax.set_ylabel("Magnitud (dB)", color='white')
        self.ax.set_xlim(0, 4000)
        self.ax.set_ylim(-80, 60)
        
        freq_x, freq_y = self.logic.calculate_spectrum(self.logic.audio_original)
        if freq_x is not None:
            self.ax.fill_between(freq_x, freq_y, -100, color='#00BFFF', alpha=0.2, label='Original')
            self.ax.plot(freq_x, freq_y, color='#00BFFF', alpha=0.7, linewidth=1)
            
        if compare and self.logic.audio_convertido is not None:
            freq_x_conv, freq_y_conv = self.logic.calculate_spectrum(self.logic.audio_convertido)
            self.ax.plot(freq_x_conv, freq_y_conv, color='#FF4500', label='Cuantizado', alpha=0.9, linewidth=1.2, linestyle='--')
            self.ax.legend(facecolor='#1E1E2E', labelcolor='white')

        self.canvas.draw()

    def export(self, format_type):
        if self.logic.audio_convertido is None:
            messagebox.showwarning("Atención", "debe convertir el audio inicialmente")
            return 
            
        file_path = filedialog.asksaveasfilename(
            title=f"Exportar archivo {format_type.upper()}",
            defaultextension=f".{format_type}",
            filetypes=[(f"Archivo {format_type.upper()}", f"*.{format_type}")],
            initialfile=f"audio_digitalizado.{format_type}"
        )
        
        if not file_path:
            return
        
        try:
            if format_type == "wav":
                self.data.export_wav(file_path, self.logic.sample_rate, self.logic.audio_convertido)
            elif format_type == "mp3":
                self.data.export_mp3(file_path, self.logic.sample_rate, self.logic.audio_convertido)
            
            messagebox.showinfo("Éxito", "se ha exportado exitosamente")

        except FileNotFoundError as error:
            if format_type == "mp3":
                messagebox.showerror("Dependencia faltante", "Para exportar a MP3, necesitas tener instalado 'FFmpeg' en tu sistema.\n\nInstálalo, reinicia el editor y vuelve a intentarlo.")
            else:
                messagebox.showerror("Error de Archivo", f"No se pudo guardar:\n{error}")
        except Exception as error:
            messagebox.showerror("Error", f"Ocurrió un error inesperado:\n{error}")

if __name__ == "__main__":
    # La aplicación se orquesta desde aquí uniendo las 3 piezas
    data_layer = DataAccessLayer()
    logic_layer = BusinessLogicLayer()
    app = PresentationLayer(logic_layer, data_layer)
    app.mainloop()