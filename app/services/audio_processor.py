import os
import tempfile
import librosa
import numpy as np
import requests

def extract_audio_features(file_path_or_url: str) -> list:
    """
    Accepts either a local file path or a MinIO web URL, downloads it if necessary,
    and extracts 33 distinct acoustic features using librosa.
    """
    local_path = file_path_or_url
    is_url = file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://")
    
    # 1. If it's a web link from MinIO, download it safely to a temporary local file
    if is_url:
        try:
            response = requests.get(file_path_or_url, stream=True, timeout=10)
            response.raise_for_status()
            
            # Create a temporary file with the right extension that works cleanly on Windows
            suffix = ".mp3" if "mp3" in file_path_or_url.lower() else ".wav"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
            temp_file.close()
            local_path = temp_file.name
        except Exception as e:
            print(f"Failed to download MinIO track for feature extraction: {str(e)}")
            return None

    # 2. Extract features using Librosa
    try:
        if not os.path.exists(local_path):
            print(f"Target path does not exist: {local_path}")
            return None

        # Load the track (limited to the first 60 seconds for processing speed)
        y, sr = librosa.load(local_path, sr=22050, mono=True, duration=60.0)
        
        # Guardrail against empty or corrupted files
        if len(y) == 0:
            return None

        # Feature Group 1: Rhythm (1 Feature)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        # Handle librosa version array wrapping formatting variations cleanly
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if tempo.size > 0 else 120.0
        else:
            tempo = float(tempo)

        # Feature Group 2: Timbre - MFCCs (20 Features)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        mfcc_means = np.mean(mfcc, axis=1)

        # Feature Group 3: Harmony - Chroma STFT (12 Features)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_chroma=12)
        chroma_means = np.mean(chroma, axis=1)

        # Combine all parts into our strict 33-dimension float array profile map
        feature_vector = [tempo] + mfcc_means.tolist() + chroma_means.tolist()
        return feature_vector

    except Exception as e:
        print(f"Librosa analysis extraction engine crash: {str(e)}")
        return None
        
    finally:
        # Clean up the temporary file from your local disk immediately
        if is_url and local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass