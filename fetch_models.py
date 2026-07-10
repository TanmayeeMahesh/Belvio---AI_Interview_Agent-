"""
fetch_models.py — download the local proctoring CV models into ./models for LOCAL testing.

In production the Dockerfile bakes these into the image; run this only when testing on your own
machine. Usage:  python fetch_models.py
Uses stdlib urllib only (no extra deps). Skips files that already exist.
"""
import os
import urllib.request

MODELS = {
    "face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    "yolox_nano.onnx":
        "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx",
}

def main():
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(dest, exist_ok=True)
    for name, url in MODELS.items():
        path = os.path.join(dest, name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"[skip] {name} already present ({os.path.getsize(path):,} bytes)")
            continue
        print(f"[get ] {name} …")
        urllib.request.urlretrieve(url, path)
        print(f"[ok  ] {name} → {os.path.getsize(path):,} bytes")
    print(f"\nModels ready in {dest}")

if __name__ == "__main__":
    main()
