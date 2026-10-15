import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "alphabetai-secret-key-edutech-2026-production")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/alphabetai_db")
    DB_NAME = os.getenv("DB_NAME", "alphabetai_db")
    
    # Face AI Verification Parameters (Calibrated for SFace & YuNet)
    YUNET_MODEL_PATH = os.path.abspath(os.getenv("YUNET_MODEL_PATH", "data/models/face_detection_yunet_2023mar.onnx"))
    SFACE_MODEL_PATH = os.path.abspath(os.getenv("SFACE_MODEL_PATH", "data/models/face_recognition_sface_2021dec.onnx"))
    
    # Thresholds
    DETECTION_CONFIDENCE = float(os.getenv("DETECTION_CONFIDENCE", "0.70"))
    SIMILARITY_MATCH_THRESHOLD = float(os.getenv("SIMILARITY_MATCH_THRESHOLD", "0.38"))     # Above this: verified
    SIMILARITY_UNCERTAIN_THRESHOLD = float(os.getenv("SIMILARITY_UNCERTAIN_THRESHOLD", "0.30")) # Between uncertain & match: requires review
    
    # Image Quality Thresholds
    BLUR_THRESHOLD = float(os.getenv("BLUR_THRESHOLD", "30.0"))        # Laplacian variance
    MIN_BRIGHTNESS = float(os.getenv("MIN_BRIGHTNESS", "35.0"))        # Average grayscale luminance
    MAX_BRIGHTNESS = float(os.getenv("MAX_BRIGHTNESS", "230.0"))       # Overexposed threshold
    MIN_FACE_SIZE = int(os.getenv("MIN_FACE_SIZE", "60"))              # Pixels width/height
    
    # Session and Token Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    TOKEN_EXPIRY_SECONDS = int(os.getenv("TOKEN_EXPIRY_SECONDS", "86400"))  # 24 hours
