# ADC Studio — Grabador y Analizador de Espectro de Frecuencia

> Herramienta de simulación pedagógica para el estudio de la conversión analógica-digital (ADC) en el contexto de las telecomunicaciones y el procesamiento digital de señales (DSP).

---

## Descripción general

**ADC Studio** es una aplicación de escritorio desarrollada en Python orientada al ámbito académico de las telecomunicaciones. Su propósito principal es permitir al estudiante o docente capturar una señal de audio en tiempo real mediante un micrófono, aplicar sobre ella el proceso de cuantización uniforme con profundidad de bit (bit depth) configurable, visualizar comparativamente las señales resultantes tanto en el dominio del tiempo como en el dominio de la frecuencia, y exportar el audio digitalizado en los formatos estándar WAV y MP3.

---

## Fundamentos teóricos involucrados

La aplicación implementa y hace observable la cadena completa de conversión analógica-digital:

**Muestreo (Sampling).** La señal analógica proveniente del micrófono es muestreada a una frecuencia configurable `fs` (sample rate). El teorema de Nyquist-Shannon establece que para una reconstrucción exacta se requiere `fs ≥ 2 · fmáx`. La aplicación admite frecuencias de muestreo desde 8 000 Hz hasta 96 000 Hz.

**Cuantización uniforme (Uniform Quantization).** Cada muestra es asignada al nivel discreto más próximo dentro de una grilla uniforme de `2^B` niveles, donde `B` es la profundidad de bit seleccionada. El error introducido en este proceso constituye el ruido de cuantización, cuyo SNR teórico sigue la expresión `SNR ≈ 6.02·B + 1.76 dB`. La aplicación permite valores de `B` entre 1 y 32 bits, incluyendo valores sub-byte (1–7 bits) deliberadamente para que el efecto de distorsión sea perceptible tanto visual como auditivamente.

**Análisis espectral mediante FFT.** El espectro de magnitud de las señales se obtiene aplicando la Transformada Rápida de Fourier (FFT) implementada en NumPy (`numpy.fft.rfft`). La magnitud se expresa en decibeles mediante `20·log₁₀(|X(f)|)`. La comparación superpuesta de los espectros de la señal original y la señal digitalizada permite observar los armónicos de distorsión (THD) introducidos por la cuantización.

**Codificación y almacenamiento.** El audio digitalizado se almacena sin compresión en formato WAV (PCM lineal) o con compresión perceptual en formato MP3 a 192 kbps mediante el codec MPEG-1 Audio Layer III.

---

## Requisitos del sistema

### Sistema operativo

| Sistema operativo | Compatibilidad |
|---|---|
| Windows 10 / 11 (64-bit) | Soportado |
| macOS 12 Monterey o superior | Soportado |
| Linux (Ubuntu 20.04 LTS o superior) | Soportado |

### Python

Se requiere **Python 3.9 o superior**. Se recomienda utilizar Python 3.11 por su estabilidad con las dependencias de audio.


### Dispositivo de audio

Se requiere un micrófono funcional reconocido por el sistema operativo. La aplicación accede al dispositivo de entrada de audio por defecto del sistema mediante la biblioteca `sounddevice` (interfaz sobre PortAudio).

---

## Dependencias de Python

Las siguientes bibliotecas deben estar instaladas en el entorno de Python:

| Biblioteca | Versión mínima recomendada | Función en la aplicación |
|---|---|---|
| `customtkinter` | 5.2.0 | Framework de interfaz gráfica de usuario |
| `numpy` | 1.24.0 | Procesamiento vectorial de señales y cálculo de FFT |
| `scipy` | 1.10.0 | Escritura de archivos WAV (`scipy.io.wavfile`) |
| `sounddevice` | 0.4.6 | Captura de audio en tiempo real vía PortAudio |
| `matplotlib` | 3.7.0 | Visualización de formas de onda y espectros de frecuencia |
| `pydub` | 0.25.1 | Exportación en formato MP3 *(opcional)* |

> **Nota:** `pydub` es una dependencia opcional. Si no se encuentra instalada, la funcionalidad de exportación a MP3 queda deshabilitada; el resto de la aplicación opera con normalidad.

## Flujo de uso recomendado

El siguiente flujo operativo refleja la secuencia didáctica prevista por la aplicación:

```
1. Seleccionar frecuencia de muestreo (sample rate)
        ↓
2. Iniciar grabación → capturar señal analógica
        ↓
3. Detener grabación → observar forma de onda original (cyan)
        ↓
4. Seleccionar profundidad de bit (bit depth)
        ↓
5. Ejecutar ⚡ Digitalizar → aplicar cuantización uniforme
        ↓
6. Comparar señal original vs. digitalizada en:
   · Tab FORMA DE ONDA  → dominio del tiempo
   · Tab ESPECTRO       → dominio de la frecuencia (FFT)
        ↓
7. Reproducir ambas versiones para contraste auditivo
        ↓
8. Exportar el audio digitalizado en formato WAV o MP3
```

---

## Descripción de la interfaz

### Panel lateral (sidebar)

**Sección GRABACIÓN DE AUDIO**
- *Sample Rate (Hz):* selector de frecuencia de muestreo. Opciones disponibles: 8 000, 11 025, 16 000, 22 050, 44 100, 48 000 y 96 000 Hz.
- *Iniciar / Detener Grabación:* inicia o detiene la captura de audio mediante `sounddevice.InputStream`. Un cronómetro indica el tiempo transcurrido en tiempo real.
- *Duración y Sample Rate:* indicadores numéricos actualizados al finalizar la grabación.

**Sección REPRODUCCIÓN**
- *Reproducir original:* reproduce la señal tal como fue capturada por el micrófono (señal analógica muestreada, representada en cyan).
- *Reproducir digitalizado:* reproduce la señal cuantizada según el bit depth seleccionado (representada en amarillo). Permite la comparación auditiva directa del efecto de la cuantización.
- *Detener:* interrumpe la reproducción en curso.

**Sección EXPORTAR AUDIO**
- *Bit Depth:* selector de profundidad de bit para la cuantización. Opciones: 1, 2, 3, 4, 5, 6, 7, 8, 16 y 32 bits.
- *⚡ Digitalizar:* aplica la cuantización uniforme sobre la señal grabada según el bit depth seleccionado. Actualiza automáticamente las visualizaciones.
- *💾 WAV:* exporta el audio digitalizado en formato PCM lineal sin compresión.
- *💾 MP3:* exporta el audio digitalizado en formato MPEG-1 Audio Layer III a 192 kbps (requiere `pydub` y FFmpeg).

### Panel de visualización

**Tab FORMA DE ONDA**
Muestra la representación de la señal en el dominio del tiempo. Cuando se ha ejecutado la digitalización, se presentan dos subgráficas superpuestas: la señal original muestreada (cyan) y la señal cuantizada (amarillo, representada con trazado escalonado `step` para evidenciar los niveles de cuantización).

**Tab ESPECTRO**
Muestra el espectro de magnitud en dB calculado mediante FFT (`numpy.fft.rfft`) sobre el eje de frecuencia en Hz. Permite observar simultáneamente la señal original (cyan) y la señal digitalizada (amarillo punteado). Los picos espectrales adicionales presentes en la señal digitalizada corresponden a los armónicos de distorsión introducidos por la cuantización, cuya energía relativa es directamente proporcional al error de cuantización e inversamente proporcional al bit depth.

---

## Convención de colores en las visualizaciones

| Color | Señal representada |
|---|---|
| Cyan `#00D4FF` | Señal analógica original (capturada por el micrófono) |
| Amarillo `#FFE033` | Señal digitalizada (post-cuantización) |
| Naranja `#FF6B35` | Señal exportada (cuando no existe señal digitalizada) |

---

## Parámetros técnicos de la aplicación

| Parámetro | Valor / Rango |
|---|---|
| Frecuencias de muestreo disponibles | 8 000 – 96 000 Hz |
| Profundidades de bit disponibles | 1 – 8, 16, 32 bits |
| Niveles de cuantización (rango) | 2 – 4 294 967 296 |
| Canales de audio | Mono (1 canal) |
| Tipo de dato interno | `float32` normalizado en [−1.0, +1.0] |
| Tipo de cuantización | Uniforme de punto medio |
| Cálculo espectral | `numpy.fft.rfft`, magnitud en dB |
| Bitrate de exportación MP3 | 192 kbps (CBR) |
| Resolución mínima de ventana | 1100 × 700 px |
