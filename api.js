class ApiClient {
  static get token() {
    return localStorage.getItem("alphabetai_token") || "";
  }

  static set token(val) {
    if (val) {
      localStorage.setItem("alphabetai_token", val);
    } else {
      localStorage.removeItem("alphabetai_token");
    }
  }

  static async request(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(endpoint, {
        ...options,
        headers
      });

      if (response.status === 401) {
        this.token = "";
        window.dispatchEvent(new CustomEvent("auth:unauthorized"));
      }

      // Check if response is CSV download or JSON
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("text/csv")) {
        const blob = await response.blob();
        return { success: true, blob };
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMsg = data.error || `HTTP ${response.status}: Request failed`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`API Error on [${options.method || "GET"} ${endpoint}]:`, err);
      throw err;
    }
  }

  // Auth
  static login(username, password) {
    return this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
  }

  static logout() {
    return this.request("/api/auth/logout", { method: "POST" });
  }

  static getMe() {
    return this.request("/api/auth/me");
  }

  // Students
  static getStudents(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request(`/api/students${qs ? "?" + qs : ""}`);
  }

  static registerStudent(studentData) {
    return this.request("/api/students", {
      method: "POST",
      body: JSON.stringify(studentData)
    });
  }

  static getStudent(studentId) {
    return this.request(`/api/students/${studentId}`);
  }

  static updateStudent(studentId, updates) {
    return this.request(`/api/students/${studentId}`, {
      method: "PATCH",
      body: JSON.stringify(updates)
    });
  }

  static deactivateStudent(studentId) {
    return this.request(`/api/students/${studentId}/deactivate`, { method: "POST" });
  }

  // Face Biometrics
  static enrollFace(studentId, imageData, consentSigned = true) {
    return this.request("/api/face/enroll", {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        image_data: imageData,
        consent_signed: consentSigned
      })
    });
  }

  static verifyFace(studentId, sessionId, imageData, autoRecord = true) {
    return this.request("/api/face/verify", {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        session_id: sessionId,
        image_data: imageData,
        auto_record: autoRecord
      })
    });
  }

  static revokeFace(studentId) {
    return this.request(`/api/face/enroll/${studentId}`, { method: "DELETE" });
  }

  // Attendance
  static createSession(sessionData) {
    return this.request("/api/attendance/sessions", {
      method: "POST",
      body: JSON.stringify(sessionData)
    });
  }

  static getSessions(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request(`/api/attendance/sessions${qs ? "?" + qs : ""}`);
  }

  static getSessionQueue(sessionId, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request(`/api/attendance/sessions/${sessionId}/queue${qs ? "?" + qs : ""}`);
  }

  static recordAttendance(sessionId, recordData) {
    return this.request(`/api/attendance/sessions/${sessionId}/records`, {
      method: "POST",
      body: JSON.stringify(recordData)
    });
  }

  static correctRecord(recordId, newStatus, reason) {
    return this.request(`/api/attendance/records/${recordId}`, {
      method: "PATCH",
      body: JSON.stringify({ new_status: newStatus, reason })
    });
  }

  static closeSession(sessionId, closingPolicy = "mark_unprocessed_absent") {
    return this.request(`/api/attendance/sessions/${sessionId}/close`, {
      method: "POST",
      body: JSON.stringify({ closing_policy: closingPolicy })
    });
  }

  // Reports & Stats
  static getDashboard() {
    return this.request("/api/reports/dashboard");
  }

  static getSessionReport(sessionId) {
    return this.request(`/api/reports/session/${sessionId}`);
  }

  static async downloadSessionCsv(sessionId) {
    const res = await this.request(`/api/reports/session/${sessionId}/csv`);
    if (res.blob) {
      const url = window.URL.createObjectURL(res.blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `attendance_session_${sessionId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }
  }

  static getStudentHistory(studentId) {
    return this.request(`/api/reports/student/${studentId}`);
  }

  static getAuditLogs(limit = 50) {
    return this.request(`/api/reports/audit?limit=${limit}`);
  }
}

window.ApiClient = ApiClient;
