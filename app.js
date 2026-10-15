// AlphabetAI Attendance - Master Frontend Application
document.addEventListener("DOMContentLoaded", () => {
  // --- Global State ---
  const state = {
    currentUser: null,
    currentView: "login",
    activeSessionId: null,
    activeQueueData: null,
    skippedStudentIds: [],
    enrollCamera: null,
    queueCamera: null,
    selectedStudentForModal: null
  };

  // --- DOM Elements ---
  const views = document.querySelectorAll(".view-container");
  const navItems = document.querySelectorAll(".nav-item");
  const mobileToggle = document.getElementById("mobileToggle");
  const sidebar = document.getElementById("sidebar");
  const toastContainer = document.getElementById("toastContainer");

  // --- Notification System ---
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    let icon = "ℹ️";
    if (type === "success") icon = "✅";
    if (type === "danger") icon = "❌";
    if (type === "warning") icon = "⚠️";

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  }

  // --- View Switching ---
  function switchView(viewName) {
    // 1. Clean up active camera hardware immediately
    if (state.enrollCamera) {
      state.enrollCamera.stop();
    }
    if (state.queueCamera) {
      state.queueCamera.stop();
    }

    views.forEach((v) => v.classList.remove("active"));
    navItems.forEach((n) => n.classList.remove("active"));

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) {
      targetView.classList.add("active");
      state.currentView = viewName;
    }

    const targetNav = document.querySelector(`[data-view="${viewName}"]`);
    if (targetNav) {
      targetNav.parentElement.classList.add("active");
    }

    // Close mobile drawer if open
    if (sidebar) sidebar.classList.remove("open");

    // Route Actions
    if (viewName === "dashboard") loadDashboard();
    if (viewName === "students") loadStudentsList();
    if (viewName === "sessions") loadSessionsList();
    if (viewName === "enroll") setupEnrollmentView();
    if (viewName === "attendance-queue") {
      if (state.activeSessionId) {
        loadQueueEngine(state.activeSessionId);
      } else {
        showToast("Please select or start an attendance session first.", "warning");
        switchView("sessions");
      }
    }
    if (viewName === "reports") loadReportsView();
    if (viewName === "audit") loadAuditLogs();
  }

  // Navigation Click Handlers
  document.querySelectorAll("[data-view]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const target = btn.getAttribute("data-view");
      switchView(target);
    });
  });

  if (mobileToggle) {
    mobileToggle.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // --- Authentication Management ---
  async function checkAuth() {
    if (!ApiClient.token) {
      switchView("login");
      return;
    }
    try {
      const res = await ApiClient.getMe();
      if (res.success && res.user) {
        state.currentUser = res.user;
        updateUserUI();
        switchView("dashboard");
      } else {
        ApiClient.token = "";
        switchView("login");
      }
    } catch (err) {
      ApiClient.token = "";
      switchView("login");
    }
  }

  function updateUserUI() {
    const userNameEl = document.getElementById("userNameDisplay");
    const userRoleEl = document.getElementById("userRoleDisplay");
    const adminItems = document.querySelectorAll(".admin-only");

    if (state.currentUser) {
      if (userNameEl) userNameEl.textContent = state.currentUser.full_name || state.currentUser.username;
      if (userRoleEl) userRoleEl.textContent = state.currentUser.role;

      adminItems.forEach((item) => {
        item.style.display = state.currentUser.role === "admin" ? "block" : "none";
      });
    }
  }

  // Login Form
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("loginUsername").value.trim();
      const password = document.getElementById("loginPassword").value;
      const submitBtn = loginForm.querySelector("button[type='submit']");
      const errEl = document.getElementById("loginError");

      if (errEl) errEl.style.display = "none";
      submitBtn.disabled = true;
      submitBtn.textContent = "Authenticating...";

      try {
        const res = await ApiClient.login(username, password);
        if (res.success && res.token) {
          ApiClient.token = res.token;
          state.currentUser = res.user;
          updateUserUI();
          showToast(`Welcome back, ${res.user.full_name}!`, "success");
          switchView("dashboard");
        }
      } catch (err) {
        if (errEl) {
          errEl.textContent = err.message;
          errEl.style.display = "block";
        }
        showToast(err.message, "danger");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Log In";
      }
    });
  }

  // Logout Button
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await ApiClient.logout();
      } catch (e) {}
      ApiClient.token = "";
      state.currentUser = null;
      showToast("Logged out successfully.", "info");
      switchView("login");
    });
  }

  // --- Dashboard Controller ---
  async function loadDashboard() {
    try {
      const res = await ApiClient.getDashboard();
      if (res.success && res.stats) {
        const s = res.stats;
        document.getElementById("statTotalStudents").textContent = s.total_students;
        document.getElementById("statPresentToday").textContent = s.present_today;
        document.getElementById("statAbsentToday").textContent = s.absent_today;
        document.getElementById("statAttendancePct").textContent = `${s.attendance_percentage_today}%`;
        document.getElementById("statEnrolledFaces").textContent = `${s.enrolled_faces} (${s.face_enrollment_rate}%)`;

        // Render recent activity
        const tbody = document.getElementById("recentActivityBody");
        if (tbody) {
          if (!s.recent_activity || s.recent_activity.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted" style="text-align:center; padding:1.5rem;">No recent attendance activity recorded yet.</td></tr>`;
          } else {
            tbody.innerHTML = s.recent_activity.map((a) => `
              <tr>
                <td><strong>${escapeHtml(a.student_name)}</strong><br><small class="text-muted">${a.student_id}</small></td>
                <td>${escapeHtml(a.class_id)}-${escapeHtml(a.section)} (Roll ${a.roll_number})</td>
                <td><span class="badge badge-${a.status === 'present' ? 'success' : a.status === 'absent' ? 'danger' : 'warning'}">${a.status}</span></td>
                <td><small>${escapeHtml(a.verification_method)}</small></td>
                <td><small>${formatTime(a.timestamp)}</small></td>
              </tr>
            `).join("");
          }
        }
      }
    } catch (err) {
      showToast("Failed to load dashboard data: " + err.message, "danger");
    }
  }

  // --- Students Management ---
  const studentSearchInput = document.getElementById("studentSearch");
  const studentClassFilter = document.getElementById("studentClassFilter");
  const studentSortSelect = document.getElementById("studentSortSelect");

  if (studentSearchInput) studentSearchInput.addEventListener("input", debounce(loadStudentsList, 300));
  if (studentClassFilter) studentClassFilter.addEventListener("change", loadStudentsList);
  if (studentSortSelect) studentSortSelect.addEventListener("change", loadStudentsList);

  async function loadStudentsList() {
    const classId = studentClassFilter ? studentClassFilter.value : "";
    const search = studentSearchInput ? studentSearchInput.value.trim() : "";
    const sortBy = studentSortSelect ? studentSortSelect.value : "alphabetical";

    try {
      const res = await ApiClient.getStudents({
        class_id: classId,
        search: search,
        sort_by: sortBy
      });

      const tbody = document.getElementById("studentsTableBody");
      const countEl = document.getElementById("studentTotalCount");
      if (countEl) countEl.textContent = res.count;

      if (!tbody) return;

      if (!res.students || res.students.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem;">No students found matching current criteria.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.students.map((s, idx) => `
        <tr>
          <td><span class="letter-pill">${s.full_name.charAt(0).toUpperCase()}</span></td>
          <td><strong>${escapeHtml(s.full_name)}</strong></td>
          <td><code>${s.student_id}</code></td>
          <td>${s.roll_number}</td>
          <td>${s.class_id}-${s.section}</td>
          <td>
            ${s.has_face_enrolled 
              ? `<span class="badge badge-success">Enrolled</span>`
              : `<span class="badge badge-warning">Not Enrolled</span>`}
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="window.app.viewStudentDetails('${s.student_id}')">View</button>
            ${!s.has_face_enrolled 
              ? `<button class="btn btn-primary btn-sm" onclick="window.app.startEnrollmentFor('${s.student_id}')">Enroll Face</button>`
              : `<button class="btn btn-danger btn-sm" onclick="window.app.revokeFace('${s.student_id}')">Revoke Face</button>`}
          </td>
        </tr>
      `).join("");
    } catch (err) {
      showToast("Error loading students: " + err.message, "danger");
    }
  }

  // Register Student Form
  const registerStudentForm = document.getElementById("registerStudentForm");
  if (registerStudentForm) {
    registerStudentForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        student_id: document.getElementById("regStudentId").value.trim(),
        full_name: document.getElementById("regFullName").value.trim(),
        roll_number: parseInt(document.getElementById("regRollNumber").value),
        class_id: document.getElementById("regClassId").value.trim(),
        section: document.getElementById("regSection").value.trim(),
        academic_year: document.getElementById("regAcademicYear").value.trim(),
        consent_status: document.getElementById("regConsentCheckbox").checked,
        contact_email: document.getElementById("regEmail").value.trim(),
        contact_phone: document.getElementById("regPhone").value.trim()
      };

      try {
        const res = await ApiClient.registerStudent(payload);
        if (res.success) {
          showToast(`Student '${payload.full_name}' registered successfully!`, "success");
          registerStudentForm.reset();
          switchView("students");
        }
      } catch (err) {
        showToast(err.message, "danger");
      }
    });
  }

  // --- Face Enrollment Controller ---
  async function setupEnrollmentView() {
    const studentSelect = document.getElementById("enrollStudentSelect");
    if (!studentSelect) return;

    try {
      const res = await ApiClient.getStudents({ sort_by: "alphabetical" });
      studentSelect.innerHTML = `<option value="">-- Choose Student to Enroll --</option>` +
        res.students.map((s) => `
          <option value="${s.student_id}" ${s.has_face_enrolled ? "data-enrolled='true'" : ""}>
            ${escapeHtml(s.full_name)} (Roll ${s.roll_number}, ${s.class_id}-${s.section}) ${s.has_face_enrolled ? '✓ [Already Enrolled]' : ''}
          </option>
        `).join("");
    } catch (e) {
      console.error(e);
    }
  }

  const startEnrollCameraBtn = document.getElementById("startEnrollCameraBtn");
  const flipEnrollCameraBtn = document.getElementById("flipEnrollCameraBtn");
  const captureEnrollBtn = document.getElementById("captureEnrollBtn");
  const enrollVideo = document.getElementById("enrollVideo");
  const enrollConsent = document.getElementById("enrollConsentCheckbox");

  if (startEnrollCameraBtn && enrollVideo) {
    state.enrollCamera = new CameraManager(enrollVideo);

    startEnrollCameraBtn.addEventListener("click", async () => {
      try {
        await state.enrollCamera.start("user");
        startEnrollCameraBtn.style.display = "none";
        captureEnrollBtn.style.display = "inline-flex";
        flipEnrollCameraBtn.style.display = "inline-flex";
        showToast("Camera started. Align student face inside the guide.", "info");
      } catch (err) {
        showToast(err.message, "danger");
      }
    });

    if (flipEnrollCameraBtn) {
      flipEnrollCameraBtn.addEventListener("click", async () => {
        try {
          await state.enrollCamera.toggleCamera();
          showToast("Switched camera orientation.", "info");
        } catch (err) {
          showToast(err.message, "danger");
        }
      });
    }

    if (captureEnrollBtn) {
      captureEnrollBtn.addEventListener("click", async () => {
        const studentId = document.getElementById("enrollStudentSelect").value;
        if (!studentId) {
          showToast("Please select a student first.", "warning");
          return;
        }

        if (!enrollConsent || !enrollConsent.checked) {
          showToast("Consent check is mandatory before saving biometric representation.", "warning");
          return;
        }

        try {
          captureEnrollBtn.disabled = true;
          captureEnrollBtn.textContent = "Analyzing Face...";
          const frameData = state.enrollCamera.captureFrame();

          const res = await ApiClient.enrollFace(studentId, frameData, true);
          if (res.success) {
            showToast(res.message, "success");
            state.enrollCamera.stop();
            startEnrollCameraBtn.style.display = "inline-flex";
            captureEnrollBtn.style.display = "none";
            flipEnrollCameraBtn.style.display = "none";
            switchView("students");
          }
        } catch (err) {
          showToast(err.message, "danger");
        } finally {
          captureEnrollBtn.disabled = false;
          captureEnrollBtn.textContent = "Capture & Enroll Face";
        }
      });
    }
  }

  // --- Attendance Sessions Management ---
  async function loadSessionsList() {
    try {
      const res = await ApiClient.getSessions();
      const tbody = document.getElementById("sessionsTableBody");
      if (!tbody) return;

      if (!res.sessions || res.sessions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem;">No attendance sessions created yet. Start a new session above!</td></tr>`;
        return;
      }

      tbody.innerHTML = res.sessions.map((sess) => `
        <tr>
          <td><strong>${escapeHtml(sess.session_name || 'Regular')}</strong></td>
          <td>${sess.class_id}-${sess.section}</td>
          <td>${sess.session_date}</td>
          <td><span class="badge badge-${sess.status === 'active' ? 'primary' : 'secondary'}">${sess.status}</span></td>
          <td><small>${formatTime(sess.created_at)}</small></td>
          <td>
            ${sess.status === 'active'
              ? `<button class="btn btn-primary btn-sm" onclick="window.app.launchQueue('${sess._id}')">Resume Queue</button>`
              : `<button class="btn btn-secondary btn-sm" onclick="window.app.viewSessionReport('${sess._id}')">View Report</button>`}
          </td>
        </tr>
      `).join("");
    } catch (err) {
      showToast("Error loading sessions: " + err.message, "danger");
    }
  }

  // Create Session Form
  const newSessionForm = document.getElementById("newSessionForm");
  if (newSessionForm) {
    newSessionForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        class_id: document.getElementById("sessClassId").value.trim(),
        section: document.getElementById("sessSection").value.trim(),
        session_name: document.getElementById("sessName").value.trim(),
        session_date: document.getElementById("sessDate").value
      };

      try {
        const res = await ApiClient.createSession(payload);
        if (res.success && res.session) {
          showToast("Session created! Launching Alphabetical Queue...", "success");
          state.activeSessionId = res.session._id;
          switchView("attendance-queue");
        }
      } catch (err) {
        showToast(err.message, "danger");
      }
    });
  }

  // --- Signature Alphabetical Attendance Queue Engine ---
  const queueVideo = document.getElementById("queueVideo");
  const startQueueCameraBtn = document.getElementById("startQueueCameraBtn");
  const verifyFaceBtn = document.getElementById("verifyFaceBtn");
  const skipStudentBtn = document.getElementById("skipStudentBtn");
  const manualOverrideBtn = document.getElementById("manualOverrideBtn");
  const endSessionBtn = document.getElementById("endSessionBtn");
  const faceGuideOverlay = document.getElementById("faceGuideOverlay");

  if (queueVideo) {
    state.queueCamera = new CameraManager(queueVideo);
  }

  if (startQueueCameraBtn) {
    startQueueCameraBtn.addEventListener("click", async () => {
      try {
        await state.queueCamera.start("user");
        startQueueCameraBtn.style.display = "none";
        verifyFaceBtn.style.display = "inline-flex";
        showToast("Live camera active. Ready for A-Z verification.", "info");
      } catch (err) {
        showToast(err.message, "danger");
      }
    });
  }

  async function loadQueueEngine(sessionId, currentStudentId = null) {
    state.activeSessionId = sessionId;
    const sortSelect = document.getElementById("queueSortSelect");
    const sortBy = sortSelect ? sortSelect.value : "alphabetical";

    try {
      const res = await ApiClient.getSessionQueue(sessionId, {
        sort_by: sortBy,
        current_student_id: currentStudentId || "",
        skipped_ids: state.skippedStudentIds.join(",")
      });

      if (!res.success || !res.queue_data) {
        showToast("Could not load queue.", "danger");
        return;
      }

      state.activeQueueData = res.queue_data;
      renderQueueUI(res.queue_data);
    } catch (err) {
      showToast("Error updating queue: " + err.message, "danger");
    }
  }

  function renderQueueUI(qData) {
    // 1. Session Header
    const sess = qData.session;
    document.getElementById("queueSessionTitle").textContent = `${sess.session_name} (${sess.class_id}-${sess.section})`;
    document.getElementById("queueSessionDate").textContent = sess.session_date;

    // 2. Progress Bar & Counts
    document.getElementById("queueProgressFill").style.width = `${qData.progress_percentage}%`;
    document.getElementById("queueProgressPct").textContent = `${qData.progress_percentage}%`;
    document.getElementById("queueVerifiedCount").textContent = qData.verified_count;
    document.getElementById("queuePendingCount").textContent = qData.pending_count;
    document.getElementById("queueSkippedCount").textContent = qData.skipped_count;
    document.getElementById("queueTotalCount").textContent = qData.total_students;

    // 3. Current Active Student
    const current = qData.current_student;
    const letterCircle = document.getElementById("activeStudentLetter");
    const nameEl = document.getElementById("activeStudentName");
    const metaEl = document.getElementById("activeStudentMeta");
    const enrollBadge = document.getElementById("activeStudentEnrollBadge");

    if (current) {
      letterCircle.textContent = current.letter;
      nameEl.textContent = current.full_name;
      metaEl.textContent = `Roll No: ${current.roll_number} | ID: ${current.student_id}`;
      enrollBadge.className = `badge badge-${current.has_face_enrolled ? 'success' : 'warning'}`;
      enrollBadge.textContent = current.has_face_enrolled ? "Face Enrolled" : "No Face Enrolled";

      verifyFaceBtn.disabled = !current.has_face_enrolled;
      if (!current.has_face_enrolled) {
        verifyFaceBtn.title = "Student has no biometric face enrolled. Use Manual Override.";
      } else {
        verifyFaceBtn.title = "";
      }
    } else {
      letterCircle.textContent = "✓";
      nameEl.textContent = "Attendance Completed!";
      metaEl.textContent = "All students in the class have been processed or marked.";
      enrollBadge.textContent = "Done";
      verifyFaceBtn.disabled = true;
    }

    // 4. Render A-Z Student Queue List
    const listContainer = document.getElementById("queueListItems");
    if (listContainer) {
      listContainer.innerHTML = qData.queue.map((item) => {
        const isCurrent = current && current.student_id === item.student_id;
        let statusBadge = `<span class="badge badge-secondary">Pending</span>`;
        if (item.status === "present") statusBadge = `<span class="badge badge-success">✓ Present</span>`;
        else if (item.status === "absent") statusBadge = `<span class="badge badge-danger">✗ Absent</span>`;
        else if (item.status === "skipped") statusBadge = `<span class="badge badge-warning">⤿ Skipped</span>`;

        return `
          <div class="queue-item ${isCurrent ? 'is-current' : ''}" onclick="window.app.selectQueueStudent('${item.student_id}')" style="cursor:pointer;">
            <div class="queue-item-left">
              <span class="letter-pill">${item.letter}</span>
              <div>
                <strong>${escapeHtml(item.full_name)}</strong>
                <div style="font-size:0.75rem; color:#64748b;">Roll ${item.roll_number} | ${item.student_id}</div>
              </div>
            </div>
            <div>
              ${statusBadge}
            </div>
          </div>
        `;
      }).join("");
    }
  }

  // Face Verification Click
  if (verifyFaceBtn) {
    verifyFaceBtn.addEventListener("click", async () => {
      if (!state.activeQueueData || !state.activeQueueData.current_student) return;
      const current = state.activeQueueData.current_student;

      if (!state.queueCamera.isStreaming) {
        showToast("Please start camera before verifying.", "warning");
        return;
      }

      verifyFaceBtn.disabled = true;
      verifyFaceBtn.textContent = "Verifying...";
      if (faceGuideOverlay) faceGuideOverlay.className = "face-guide";

      try {
        const frameData = state.queueCamera.captureFrame();
        const res = await ApiClient.verifyFace(current.student_id, state.activeSessionId, frameData, true);

        if (res.success) {
          const v = res.verification;
          if (v.verified) {
            // Verified match!
            if (faceGuideOverlay) faceGuideOverlay.className = "face-guide verified";
            showToast(`Verified! Marked ${current.full_name} as Present (Cosine: ${v.similarity_score}).`, "success");
            // Remove from skipped list if present
            state.skippedStudentIds = state.skippedStudentIds.filter((id) => id !== current.student_id);
            // Auto advance
            setTimeout(() => {
              if (faceGuideOverlay) faceGuideOverlay.className = "face-guide";
              loadQueueEngine(state.activeSessionId);
            }, 900);
          } else if (v.requires_review) {
            // Uncertain match - requires review
            if (faceGuideOverlay) faceGuideOverlay.className = "face-guide uncertain";
            if (confirm(`Uncertain similarity (${v.similarity_score}). Would you like to confirm ${current.full_name} as Present?`)) {
              await ApiClient.recordAttendance(state.activeSessionId, {
                student_id: current.student_id,
                status: "present",
                verification_method: "teacher_review_confirmed",
                verification_outcome: `teacher_confirmed_uncertain_${v.similarity_score}`,
                confidence_score: v.similarity_score
              });
              showToast(`Teacher confirmed ${current.full_name} as Present.`, "success");
              loadQueueEngine(state.activeSessionId);
            }
          } else {
            // Rejected / mismatch
            if (faceGuideOverlay) faceGuideOverlay.className = "face-guide rejected";
            showToast(`Verification Failed: ${v.message}`, "danger");
          }
        }
      } catch (err) {
        if (faceGuideOverlay) faceGuideOverlay.className = "face-guide rejected";
        showToast(`Verification Error: ${err.message}`, "danger");
      } finally {
        verifyFaceBtn.disabled = false;
        verifyFaceBtn.textContent = "Capture & Verify";
      }
    });
  }

  // Skip Student Click
  if (skipStudentBtn) {
    skipStudentBtn.addEventListener("click", () => {
      if (!state.activeQueueData || !state.activeQueueData.current_student) return;
      const current = state.activeQueueData.current_student;
      if (!state.skippedStudentIds.includes(current.student_id)) {
        state.skippedStudentIds.push(current.student_id);
      }
      showToast(`Temporarily skipped ${current.full_name}. Advancing queue...`, "info");
      loadQueueEngine(state.activeSessionId);
    });
  }

  // Manual Override Click
  if (manualOverrideBtn) {
    manualOverrideBtn.addEventListener("click", () => {
      if (!state.activeQueueData || !state.activeQueueData.current_student) return;
      const current = state.activeQueueData.current_student;
      document.getElementById("overrideStudentName").textContent = current.full_name;
      document.getElementById("overrideModal").classList.add("show");
    });
  }

  // Manual Override Form Submit
  const overrideForm = document.getElementById("overrideForm");
  if (overrideForm) {
    overrideForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const current = state.activeQueueData.current_student;
      const status = document.getElementById("overrideStatus").value;
      const reason = document.getElementById("overrideReason").value.trim();

      if (!reason) {
        showToast("Please provide a reason for manual attendance record.", "warning");
        return;
      }

      try {
        await ApiClient.recordAttendance(state.activeSessionId, {
          student_id: current.student_id,
          status: status,
          verification_method: "teacher_manual_override",
          verification_outcome: `manual_${status}: ${reason}`
        });

        showToast(`Marked ${current.full_name} as ${status}.`, "success");
        state.skippedStudentIds = state.skippedStudentIds.filter((id) => id !== current.student_id);
        document.getElementById("overrideModal").classList.remove("show");
        overrideForm.reset();
        loadQueueEngine(state.activeSessionId);
      } catch (err) {
        showToast(err.message, "danger");
      }
    });
  }

  // Close / End Session Click
  if (endSessionBtn) {
    endSessionBtn.addEventListener("click", () => {
      document.getElementById("closeSessionModal").classList.add("show");
    });
  }

  const confirmCloseSessionBtn = document.getElementById("confirmCloseSessionBtn");
  if (confirmCloseSessionBtn) {
    confirmCloseSessionBtn.addEventListener("click", async () => {
      const policy = document.getElementById("closingPolicySelect").value;
      try {
        await ApiClient.closeSession(state.activeSessionId, policy);
        showToast("Attendance session closed successfully.", "success");
        document.getElementById("closeSessionModal").classList.remove("show");
        const sessId = state.activeSessionId;
        state.activeSessionId = null;
        state.skippedStudentIds = [];
        window.app.viewSessionReport(sessId);
      } catch (err) {
        showToast(err.message, "danger");
      }
    });
  }

  // Sorting Switcher in Queue
  const queueSortSelect = document.getElementById("queueSortSelect");
  if (queueSortSelect) {
    queueSortSelect.addEventListener("change", () => {
      if (state.activeSessionId) {
        loadQueueEngine(state.activeSessionId);
      }
    });
  }

  // --- Reports & Analytics Controller ---
  async function loadReportsView() {
    const reportSelect = document.getElementById("reportSessionSelect");
    if (!reportSelect) return;

    try {
      const res = await ApiClient.getSessions();
      reportSelect.innerHTML = `<option value="">-- Select Attendance Session --</option>` +
        res.sessions.map((s) => `
          <option value="${s._id}">${escapeHtml(s.session_name || 'Regular')} - ${s.class_id}-${s.section} (${s.session_date}) [${s.status}]</option>
        `).join("");
    } catch (e) {
      console.error(e);
    }
  }

  const loadReportBtn = document.getElementById("loadReportBtn");
  if (loadReportBtn) {
    loadReportBtn.addEventListener("click", () => {
      const sessId = document.getElementById("reportSessionSelect").value;
      if (!sessId) {
        showToast("Please choose a session to view report.", "warning");
        return;
      }
      window.app.viewSessionReport(sessId);
    });
  }

  const downloadCsvBtn = document.getElementById("downloadCsvBtn");
  if (downloadCsvBtn) {
    downloadCsvBtn.addEventListener("click", async () => {
      const sessId = document.getElementById("reportSessionSelect").value;
      if (!sessId) return;
      try {
        await ApiClient.downloadSessionCsv(sessId);
        showToast("CSV report downloaded.", "success");
      } catch (err) {
        showToast(err.message, "danger");
      }
    });
  }

  const printReportBtn = document.getElementById("printReportBtn");
  if (printReportBtn) {
    printReportBtn.addEventListener("click", () => {
      window.print();
    });
  }

  // --- Audit Logs Controller ---
  async function loadAuditLogs() {
    try {
      const res = await ApiClient.getAuditLogs(50);
      const tbody = document.getElementById("auditTableBody");
      if (!tbody) return;

      if (!res.logs || res.logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem;">No audit logs recorded yet.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.logs.map((l) => `
        <tr>
          <td><small>${formatTime(l.timestamp)}</small></td>
          <td><strong>${escapeHtml(l.actor_id)}</strong></td>
          <td><code>${escapeHtml(l.action)}</code></td>
          <td><small>${escapeHtml(JSON.stringify(l.details || {}))}</small></td>
          <td><small>${escapeHtml(l.reason || "-")}</small></td>
        </tr>
      `).join("");
    } catch (err) {
      showToast("Error loading audit logs: " + err.message, "danger");
    }
  }

  // Modal Closers
  document.querySelectorAll(".modal-close, .modal-cancel").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".modal-backdrop").forEach((m) => m.classList.remove("show"));
    });
  });

  // --- Global Window Helpers for inline buttons ---
  window.app = {
    launchQueue: (sessionId) => {
      state.activeSessionId = sessionId;
      switchView("attendance-queue");
    },
    selectQueueStudent: (studentId) => {
      loadQueueEngine(state.activeSessionId, studentId);
    },
    startEnrollmentFor: (studentId) => {
      switchView("enroll");
      const sel = document.getElementById("enrollStudentSelect");
      if (sel) sel.value = studentId;
    },
    revokeFace: async (studentId) => {
      if (confirm(`Are you sure you want to permanently revoke and purge biometric data for student '${studentId}'?`)) {
        try {
          await ApiClient.revokeFace(studentId);
          showToast("Biometric representation permanently purged.", "success");
          loadStudentsList();
        } catch (err) {
          showToast(err.message, "danger");
        }
      }
    },
    viewStudentDetails: async (studentId) => {
      try {
        const res = await ApiClient.getStudent(studentId);
        if (res.success && res.student) {
          const s = res.student;
          document.getElementById("modalStudentName").textContent = s.full_name;
          document.getElementById("modalStudentId").textContent = s.student_id;
          document.getElementById("modalStudentRoll").textContent = s.roll_number;
          document.getElementById("modalStudentClass").textContent = `${s.class_id}-${s.section}`;
          document.getElementById("modalStudentYear").textContent = s.academic_year;
          document.getElementById("modalStudentConsent").textContent = s.consent_status ? "Consented (Signed)" : "No Consent";
          document.getElementById("modalStudentFace").textContent = s.has_face_enrolled ? "Enrolled (Protected 128D)" : "Not Enrolled";
          document.getElementById("studentDetailsModal").classList.add("show");
        }
      } catch (err) {
        showToast(err.message, "danger");
      }
    },
    viewSessionReport: async (sessionId) => {
      switchView("reports");
      const sel = document.getElementById("reportSessionSelect");
      if (sel) sel.value = sessionId;

      try {
        const res = await ApiClient.getSessionReport(sessionId);
        if (res.success && res.report) {
          const r = res.report;
          document.getElementById("reportContentContainer").style.display = "block";
          document.getElementById("repSessName").textContent = `${r.session.session_name} (${r.session.class_id}-${r.session.section})`;
          document.getElementById("repSessDate").textContent = r.session.session_date;
          document.getElementById("repTotal").textContent = r.total_students;
          document.getElementById("repPresent").textContent = r.present_count;
          document.getElementById("repAbsent").textContent = r.absent_count;
          document.getElementById("repPct").textContent = `${r.attendance_percentage}%`;

          const tbody = document.getElementById("reportTableBody");
          tbody.innerHTML = r.rows.map((row) => `
            <tr>
              <td>${row.roll_number}</td>
              <td><strong>${escapeHtml(row.full_name)}</strong><br><small class="text-muted">${row.student_id}</small></td>
              <td><span class="badge badge-${row.status === 'present' ? 'success' : row.status === 'absent' ? 'danger' : 'secondary'}">${row.status}</span></td>
              <td><small>${escapeHtml(row.verification_method)}</small></td>
              <td><small>${formatTime(row.timestamp)}</small></td>
              <td>
                ${row.record_id ? `<button class="btn btn-secondary btn-sm" onclick="window.app.promptCorrection('${row.record_id}', '${row.full_name}', '${row.status}')">Edit</button>` : '-'}
              </td>
            </tr>
          `).join("");
        }
      } catch (err) {
        showToast(err.message, "danger");
      }
    },
    promptCorrection: async (recordId, studentName, currentStatus) => {
      const newStatus = prompt(`Correct attendance status for ${studentName} (currently: ${currentStatus}).\nEnter: present, absent, or late:`, currentStatus === "present" ? "absent" : "present");
      if (!newStatus) return;
      const reason = prompt(`Please provide mandatory documented reason for correcting ${studentName}'s attendance:`);
      if (!reason) {
        alert("A reason is mandatory for any manual attendance correction.");
        return;
      }
      try {
        await ApiClient.correctRecord(recordId, newStatus.trim().toLowerCase(), reason.trim());
        showToast(`Record updated to ${newStatus}. Audit trail updated.`, "success");
        const sessId = document.getElementById("reportSessionSelect").value;
        if (sessId) window.app.viewSessionReport(sessId);
      } catch (err) {
        showToast(err.message, "danger");
      }
    }
  };

  // Utilities
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatTime(isoStr) {
    if (!isoStr || isoStr === "-") return "-";
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return isoStr;
    }
  }

  function debounce(fn, delay) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  }

  // Initialize
  checkAuth();
});
