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
    
    # 1. If it's a web link, download up to 1.5MB (more than enough for a 10s sample)
    if is_url:
        try:
            response = requests.get(file_path_or_url, stream=True, timeout=8)
            response.raise_for_status()
            
            suffix = ".mp3" if "mp3" in file_path_or_url.lower() else ".wav"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            
            # ⚡ SPEED FIX: Cap stream at 1.5MB instead of downloading the whole multi-MB file
            bytes_written = 0
            max_bytes = 1024 * 1024 * 2  # 2 MB limit
            
            for chunk in response.iter_content(chunk_size=16384):
                if chunk:
                    temp_file.write(chunk)
                    bytes_written += len(chunk)
                if bytes_written >= max_bytes:
                    break
                    
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

        # ⚡ SPEED FIX: res_type='kaiser_fast' and sr=11025 avoids CPU-heavy sinc interpolation
        y, sr = librosa.load(
            local_path, 
            sr=11025, 
            mono=True, 
            duration=10.0, 
            res_type="kaiser_fast"
        )
        
        if len(y) == 0:
            return None

        # Feature Group 1: Rhythm (1 Feature)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if tempo.size > 0 else 120.0
        else:
            tempo = float(tempo)

        # Feature Group 2: Timbre - MFCCs (20 Features)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, n_fft=1024, hop_length=512)
        mfcc_means = np.mean(mfcc, axis=1)

        # Feature Group 3: Harmony - Chroma STFT (12 Features)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_chroma=12, n_fft=1024, hop_length=512)
        chroma_means = np.mean(chroma, axis=1)

        # Output exact 33-dimensional float array
        feature_vector = [tempo] + mfcc_means.tolist() + chroma_means.tolist()
        return [float(x) for x in feature_vector]

    except Exception as e:
        print(f"Librosa analysis extraction engine crash: {str(e)}")
        return None
        
    finally:
        if is_url and local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass