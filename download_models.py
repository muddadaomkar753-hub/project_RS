import os
import sys
import urllib.request
import hashlib

MODELS = {
    "face_detection_yunet_2023mar.onnx": {
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "min_size": 200000
    },
    "face_recognition_sface_2021dec.onnx": {
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "min_size": 30000000
    }
}

def download_models(target_dir="data/models"):
    os.makedirs(target_dir, exist_ok=True)
    success = True
    for filename, info in MODELS.items():
        filepath = os.path.join(target_dir, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) >= info["min_size"]:
            print(f"[OK] {filename} already exists ({os.path.getsize(filepath):,} bytes)")
            continue

        print(f"Downloading {filename} from {info['url']}...")
        try:
            req = urllib.request.Request(
                info["url"],
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=60) as response, open(filepath, 'wb') as out_file:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 1024 * 64
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        sys.stdout.write(f"\r  {filename}: {downloaded:,} / {total_size:,} bytes ({pct:.1f}%)")
                        sys.stdout.flush()
                print()
            
            actual_size = os.path.getsize(filepath)
            if actual_size < info["min_size"]:
                print(f"[WARN] Downloaded file too small ({actual_size} bytes). Removing...")
                os.remove(filepath)
                success = False
            else:
                print(f"[SUCCESS] Downloaded {filename} ({actual_size:,} bytes)")
        except Exception as e:
            print(f"[ERROR] Failed to download {filename}: {e}")
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            success = False
    return success

if __name__ == "__main__":
    download_models()
