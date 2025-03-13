import speech_recognition as sr

def convertir_audio_a_texto(audio_bytes):
    recognizer = sr.Recognizer()
    audio = sr.AudioData(audio_bytes, sample_rate=16000, sample_width=2)

    try:
        texto = recognizer.recognize_google(audio, language="es-ES")
        return texto
    except sr.UnknownValueError:
        return "No entendí lo que dijiste."
    except sr.RequestError:
        return "Hubo un problema con el reconocimiento."
