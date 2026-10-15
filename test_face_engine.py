import numpy as np
import pytest
from services.face_service import FaceService
from config import Config

def test_image_quality_dark_frame_rejection():
    # Synthetic pitch black image (mean brightness = 0.0)
    dark_img = np.zeros((200, 200, 3), dtype=np.uint8)
    quality = FaceService.evaluate_image_quality(dark_img)
    assert quality["passed"] is False
    assert quality["is_dark"] is True
    assert "too dark" in quality["message"].lower()

def test_image_quality_blurry_frame_rejection():
    # Synthetic flat uniform gray image (Laplacian variance = 0.0)
    flat_img = np.full((200, 200, 3), 128, dtype=np.uint8)
    quality = FaceService.evaluate_image_quality(flat_img)
    assert quality["passed"] is False
    assert quality["is_blurry"] is True
    assert "blurry" in quality["message"].lower()

def test_cosine_similarity_calculation():
    # Perfectly identical normalized vectors
    v1 = [1.0] + [0.0] * 127
    v2 = [1.0] + [0.0] * 127
    sim = FaceService.compute_similarity(v1, v2)
    assert pytest.approx(sim, 0.001) == 1.0

    # Orthogonal vectors (completely different identities)
    v3 = [0.0, 1.0] + [0.0] * 126
    sim_ortho = FaceService.compute_similarity(v1, v3)
    assert pytest.approx(sim_ortho, 0.001) == 0.0

def test_verification_decision_boundaries():
    # 1. High match (score >= 0.38)
    v_base = np.random.RandomState(42).randn(128)
    v_base = (v_base / np.linalg.norm(v_base)).tolist()
    
    # Self comparison -> 1.0
    res_match = FaceService.verify_identity(v_base, v_base)
    assert res_match["status"] == "match"
    assert res_match["verified"] is True
    assert res_match["requires_review"] is False

    # 2. Unknown face / mismatch (orthogonal or random opposite identity)
    v_other = np.random.RandomState(999).randn(128)
    v_other = (v_other / np.linalg.norm(v_other)).tolist()
    res_mismatch = FaceService.verify_identity(v_base, v_other)
    assert res_mismatch["status"] == "rejected"
    assert res_mismatch["verified"] is False
