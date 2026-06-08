# 🎛️ ADC Studio - Conversor A/D

Aplicación de escritorio nativa desarrollada en Python para la materia Comunicación de Datos. Permite grabar audio en tiempo real o cargar señales analógicas, simular el proceso de cuantización (ADC) a diferentes profundidades de bits y comparar los espectros de frecuencia.

## 🚀 Requisitos Previos

1. **Python 3.10+** instalado en tu sistema.
2. **FFmpeg:** Es estrictamente necesario tener instalado FFmpeg en las variables de entorno de Windows para poder exportar a MP3 o leer audios comprimidos. 
   * *Instalación rápida en Windows (desde terminal):* `winget install ffmpeg`

## 🛠️ Instalación

1. Clona este repositorio o descarga los archivos en tu PC.
2. Abre la terminal de **PowerShell** o el **Símbolo del sistema (CMD)** dentro de la carpeta del proyecto.
3. Instala todas las librerías de Python necesarias ejecutando el siguiente comando:
   ```powershell
   pip install -r requirements.txt