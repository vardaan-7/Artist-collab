import os
import tempfile
import librosa
import numpy as np
import requests

def extract_audio_features(file_path_or_url: str) -> list:
    """
    Accepts either a local file path or a MinIO web URL, downloads it if necessary,
    and extracts 33 distinct acoustic features using librosa. Optimized for low-memory environments.
    """
    local_path = file_path_or_url
    is_url = file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://")
    
    # 1. Download the full file so container headers (MP3/WAV) stay valid
    if is_url:
        try:
            response = requests.get(file_path_or_url, timeout=15)
            response.raise_for_status()
            
            suffix = ".mp3" if ".mp3" in file_path_or_url.lower() else ".wav"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(response.content)
            temp_file.close()
            local_path = temp_file.name
        except Exception as e:
            print(f"Failed to download track for feature extraction: {str(e)}")
            return None

    # 2. Extract features using Librosa
    try:
        if not os.path.exists(local_path):
            print(f"Target path does not exist: {local_path}")
            return None

        # Load first 10 seconds at 16kHz
        y, sr = librosa.load(local_path, sr=16000, mono=True, duration=10.0)
        
        if len(y) == 0:
            return None

        # Feature Group 1: Rhythm (1 Feature)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if tempo.size > 0 else 120.0
        else:
            tempo = float(tempo)

        # Feature Group 2: Timbre - MFCCs (20 Features)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        mfcc_means = np.mean(mfcc, axis=1)

        # Feature Group 3: Harmony - Chroma STFT (12 Features)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_chroma=12, n_fft=1024)
        chroma_means = np.mean(chroma, axis=1)

        # Output strict 33-dimensional float array
        feature_vector = [tempo] + mfcc_means.tolist() + chroma_means.tolist()
        return [float(x) for x in feature_vector]

    except Exception as e:
        print(f"Librosa analysis extraction engine crash: {str(e)}")
        return None
        
    finally:
        # Clean up the temporary file from local disk immediately
        if is_url and local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass