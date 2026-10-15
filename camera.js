class CameraManager {
  constructor(videoElement, canvasElement = null) {
    this.video = videoElement;
    this.canvas = canvasElement || document.createElement("canvas");
    this.stream = null;
    this.currentFacingMode = "user"; // "user" (front) or "environment" (rear)
    this.isStreaming = false;
  }

  static isSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  async start(facingMode = "user") {
    this.stop(); // Stop any existing stream
    this.currentFacingMode = facingMode;

    if (!CameraManager.isSupported()) {
      const isHttps = window.location.protocol === "https:" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
      if (!isHttps) {
        throw new Error("Camera access requires HTTPS or localhost on Android mobile browsers.");
      }
      throw new Error("Your browser does not support WebRTC camera access (navigator.mediaDevices.getUserMedia missing).");
    }

    const constraints = {
      audio: false,
      video: {
        facingMode: { ideal: this.currentFacingMode },
        width: { ideal: 640 },
        height: { ideal: 480 }
      }
    };

    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = this.stream;
      this.video.setAttribute("playsinline", "true"); // Critical for mobile browser autoplay
      this.video.muted = true;

      // Wait until metadata is loaded to ensure dimensions are known
      await new Promise((resolve) => {
        this.video.onloadedmetadata = () => {
          this.video.play().then(resolve).catch(resolve);
        };
      });

      this.isStreaming = true;
      if (this.currentFacingMode === "environment") {
        this.video.classList.add("environment");
      } else {
        this.video.classList.remove("environment");
      }
      return true;
    } catch (err) {
      this.isStreaming = false;
      let humanMsg = "Failed to access camera.";

      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        humanMsg = "Camera permission was denied. Please allow camera access in browser site settings.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        humanMsg = "No camera hardware detected on this device.";
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        humanMsg = "Camera is currently in use by another application or tab.";
      } else if (err.name === "OverconstrainedError") {
        // Fallback with looser constraints
        try {
          this.stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
          this.video.srcObject = this.stream;
          await this.video.play();
          this.isStreaming = true;
          return true;
        } catch (retryErr) {
          humanMsg = "Requested camera resolution is not supported by your camera.";
        }
      }

      throw new Error(humanMsg);
    }
  }

  toggleCamera() {
    const nextMode = this.currentFacingMode === "user" ? "environment" : "user";
    return this.start(nextMode);
  }

  captureFrame(quality = 0.90) {
    if (!this.isStreaming || !this.video) {
      throw new Error("Camera is not actively streaming.");
    }

    const vw = this.video.videoWidth || 640;
    const vh = this.video.videoHeight || 480;

    this.canvas.width = vw;
    this.canvas.height = vh;
    const ctx = this.canvas.getContext("2d");

    // If front camera, we flip back so the captured image is normal orientation
    if (this.currentFacingMode === "user") {
      ctx.translate(vw, 0);
      ctx.scale(-1, 1);
    }

    ctx.drawImage(this.video, 0, 0, vw, vh);

    // Return as JPEG base64 data URL
    return this.canvas.toDataURL("image/jpeg", quality);
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (e) {
          console.warn("Track stop error:", e);
        }
      });
      this.stream = null;
    }
    if (this.video) {
      this.video.srcObject = null;
    }
    this.isStreaming = false;
  }
}

window.CameraManager = CameraManager;
