import os
import re
import base64
import logging
import cv2
import numpy as np
from config import Config

logger = logging.getLogger(__name__)

class FaceService:
    _detector = None
    _recognizer = None
    _detector_size = (320, 320)

    @classmethod
    def get_models(cls):
        if cls._detector is None or cls._recognizer is None:
            yunet_path = Config.YUNET_MODEL_PATH
            sface_path = Config.SFACE_MODEL_PATH

            if not os.path.exists(yunet_path) or not os.path.exists(sface_path):
                raise FileNotFoundError(
                    f"Face models not found. Please ensure {yunet_path} and {sface_path} exist."
                )

            cls._detector = cv2.FaceDetectorYN_create(
                yunet_path,
                "",
                cls._detector_size,
                score_threshold=Config.DETECTION_CONFIDENCE,
                nms_threshold=0.3,
                top_k=5000
            )
            cls._recognizer = cv2.FaceRecognizerSF_create(sface_path, "")
            logger.info("YuNet and SFace models initialized successfully.")

        return cls._detector, cls._recognizer

    @staticmethod
    def decode_base64_image(image_b64: str) -> np.ndarray:
        """Decodes a base64 encoded data URI or string to OpenCV BGR image."""
        if not image_b64:
            raise ValueError("No image payload provided.")

        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(image_b64)
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image from provided data.")
            return img
        except Exception as e:
            raise ValueError(f"Image decode error: {str(e)}")

    @classmethod
    def evaluate_image_quality(cls, img: np.ndarray) -> dict:
        """
        Assesses image quality for lighting, blur, and contrast.
        Returns dict with passes: bool and diagnostics.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        diagnostics = {
            "brightness": round(brightness, 2),
            "blur_score": round(blur_score, 2),
            "is_dark": brightness < Config.MIN_BRIGHTNESS,
            "is_overexposed": brightness > Config.MAX_BRIGHTNESS,
            "is_blurry": blur_score < Config.BLUR_THRESHOLD,
            "passed": True,
            "message": "Quality checks passed."
        }

        if diagnostics["is_dark"]:
            diagnostics["passed"] = False
            diagnostics["message"] = f"Poor lighting: frame is too dark (brightness {brightness:.1f} < {Config.MIN_BRIGHTNESS})."
        elif diagnostics["is_overexposed"]:
            diagnostics["passed"] = False
            diagnostics["message"] = f"Poor lighting: frame is overexposed or backlit (brightness {brightness:.1f} > {Config.MAX_BRIGHTNESS})."
        elif diagnostics["is_blurry"]:
            diagnostics["passed"] = False
            diagnostics["message"] = f"Image is blurry (sharpness {blur_score:.1f} < {Config.BLUR_THRESHOLD}). Please hold still."

        return diagnostics

    @classmethod
    def detect_and_extract_face(cls, img: np.ndarray, check_quality: bool = True):
        """
        Performs quality checks, face detection, face bounding box validation,
        and extracts 128-D normalized face feature vector.
        """
        quality = {}
        if check_quality:
            quality = cls.evaluate_image_quality(img)
            if not quality["passed"]:
                return {
                    "success": False,
                    "error_code": "QUALITY_CHECK_FAILED",
                    "error": quality["message"],
                    "quality": quality
                }

        detector, recognizer = cls.get_models()
        h, w = img.shape[:2]
        detector.setInputSize((w, h))

        _, faces = detector.detect(img)

        if faces is None or len(faces) == 0:
            return {
                "success": False,
                "error_code": "NO_FACE_DETECTED",
                "error": "No face detected. Please look straight into the camera within the frame guide.",
                "quality": quality
            }

        # Filter out faces that fall below detection confidence
        valid_faces = [f for f in faces if f[-1] >= Config.DETECTION_CONFIDENCE]
        if len(valid_faces) == 0:
            return {
                "success": False,
                "error_code": "LOW_CONFIDENCE_FACE",
                "error": "Face detection confidence is too low. Ensure proper lighting and posture.",
                "quality": quality
            }

        if len(valid_faces) > 1:
            return {
                "success": False,
                "error_code": "MULTIPLE_FACES_DETECTED",
                "error": f"Multiple faces detected ({len(valid_faces)}). 1-to-1 verification requires only the student in view.",
                "quality": quality
            }

        best_face = valid_faces[0]
        face_w = float(best_face[2])
        face_h = float(best_face[3])

        if face_w < Config.MIN_FACE_SIZE or face_h < Config.MIN_FACE_SIZE:
            return {
                "success": False,
                "error_code": "FACE_TOO_SMALL",
                "error": f"Face is too far from camera ({int(face_w)}x{int(face_h)}px). Please move closer.",
                "quality": quality
            }

        # Align and crop face using 5 facial landmarks
        aligned_face = recognizer.alignCrop(img, best_face)
        feature_raw = recognizer.feature(aligned_face)

        # L2-normalize
        feat_norm = cv2.normalize(feature_raw, None, 1.0, 0, cv2.NORM_L2)
        feature_vector = feat_norm.flatten().tolist()

        return {
            "success": True,
            "feature_vector": feature_vector,
            "face_box": {
                "x": float(best_face[0]),
                "y": float(best_face[1]),
                "w": float(best_face[2]),
                "h": float(best_face[3]),
                "confidence": float(best_face[-1])
            },
            "quality": quality
        }

    @classmethod
    def compute_similarity(cls, vector1: list, vector2: list) -> float:
        """Computes Cosine Similarity between two 128-D feature vectors."""
        v1 = np.array(vector1, dtype=np.float32)
        v2 = np.array(vector2, dtype=np.float32)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0

        cosine_sim = float(np.dot(v1, v2) / (norm1 * norm2))
        return cosine_sim

    @classmethod
    def verify_identity(cls, captured_vector: list, enrolled_vector: list) -> dict:
        """
        Calibrated 1-to-1 verification with three-tier decision boundaries:
        - match (verified)
        - uncertain (manual teacher review required)
        - rejected (no-match)
        """
        cosine_sim = cls.compute_similarity(captured_vector, enrolled_vector)
        match_thresh = Config.SIMILARITY_MATCH_THRESHOLD
        uncertain_thresh = Config.SIMILARITY_UNCERTAIN_THRESHOLD

        if cosine_sim >= match_thresh:
            status = "match"
            verified = True
            requires_review = False
            msg = f"Identity verified (Cosine similarity: {cosine_sim:.3f} >= {match_thresh:.2f})."
        elif cosine_sim >= uncertain_thresh:
            status = "uncertain"
            verified = False
            requires_review = True
            msg = f"Uncertain match (Similarity: {cosine_sim:.3f}). Teacher visual confirmation required."
        else:
            status = "rejected"
            verified = False
            requires_review = False
            msg = f"Identity mismatch (Similarity: {cosine_sim:.3f} < {uncertain_thresh:.2f})."

        return {
            "similarity_score": round(cosine_sim, 4),
            "status": status,
            "verified": verified,
            "requires_review": requires_review,
            "threshold_used": match_thresh,
            "message": msg
        }
