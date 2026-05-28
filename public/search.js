const searchInput = document.querySelector("#submissionSearch");
const searchForm = document.querySelector("#searchForm");
const searchResults = document.querySelector("#searchResults");
const exampleResults = document.querySelector("#exampleResults");
const queueDashboard = document.querySelector("#queueDashboard");
const addSubmissionToggle = document.querySelector("#addSubmissionToggle");
const addSubmissionPanel = document.querySelector("#addSubmissionPanel");
const addSubmissionForm = document.querySelector("#addSubmissionForm");
const autoPopulateSubmission = document.querySelector("#autoPopulateSubmission");
const intakeStatus = document.querySelector("#intakeStatus");
const intakeModeButtons = Array.from(document.querySelectorAll("[data-intake-mode]"));
const submissionFormPanel = document.querySelector("#submissionFormPanel");
const saveIntakeStatusButton = document.querySelector("#saveIntakeStatusButton");
const intakeDocumentList = document.querySelector("#intakeDocumentList");
const overallStatusInput = document.querySelector("#newOverallStatus");
const applicationFormUploadInput = document.querySelector("#applicationFormUploadInput");
const applicationFormUploadButton = document.querySelector("#applicationFormUploadButton");
const applicationFormUploadStatus = document.querySelector("#applicationFormUploadStatus");
const fillFromDocumentsButton = document.querySelector("#fillFromDocumentsButton");
const stagedDocumentList = document.querySelector("#stagedDocumentList");
const intakeReviewPanel = document.querySelector("#intakeReviewPanel");
const intakeReviewPolicy = document.querySelector("#intakeReviewPolicy");
const intakeReviewStatus = document.querySelector("#intakeReviewStatus");
const intakeReviewSteps = document.querySelector("#intakeReviewSteps");
const moveToUnderwritingButton = document.querySelector("#moveToUnderwritingButton");
const reviseIntakeButton = document.querySelector("#reviseIntakeButton");

let submissions = [];
let brokers = [];
let portfolioQueue = null;
let intakeMode = "manual";
let intakeDocuments = [];
let stagedIntakeDocuments = [];
let pendingSubmissionPayload = null;
let pendingIntakeReview = null;
const ADD_SUBMISSION_VIEW = "add-submission";
const INTAKE_REVIEW_VIEW = "intake-review";
const PENDING_INTAKE_PAYLOAD_KEY = "auPendingIntakePayload";
const PENDING_INTAKE_REVIEW_KEY = "auPendingIntakeReview";

const defaultIntakeDocuments = [
  ["cyber_application", "Cyber application"],
  ["ransomware_supplemental_application", "Ransomware supplemental application"],
  ["prior_cyber_insurance_policy", "Prior cyber insurance policy"],
  ["loss_runs_claims_history", "Loss runs / claims history"],
  ["financial_information_revenue_breakdown", "Financial information or revenue breakdown"],
  ["it_security_controls_questionnaire", "IT/security controls questionnaire"],
  ["mfa_edr_backup_documentation", "MFA/EDR/backup documentation"],
  ["incident_response_plan", "Incident response plan"],
  ["vendor_security_assessment", "Vendor/security assessment"],
  ["compliance_documents", "Compliance documents"]
].map(([key, label]) => ({ key, label, status: "needed", note: "" }));

initSearch();

async function initSearch() {
  try {
    await loadIntakeBootstrap();
    await loadPortfolioQueue();
    renderMatches([]);
    renderExamples(submissions.slice(0, 3));
    renderQueueDashboard();
    renderBrokerOptions();
    renderIntakeDocuments();
    const currentView = getCurrentSearchView();
    if (
      (currentView === ADD_SUBMISSION_VIEW || currentView === INTAKE_REVIEW_VIEW)
      && !(await ensureSearchLogin("Opening add submission requires a local login session."))
    ) {
      updateSearchView("");
    }
    applyAddSubmissionUrlState();
    const activeView = getCurrentSearchView();
    if (activeView === ADD_SUBMISSION_VIEW || activeView === INTAKE_REVIEW_VIEW) {
      focusAddSubmissionTarget();
    } else {
      searchInput.focus();
    }
  } catch (error) {
    searchResults.innerHTML = '<p class="empty-state">Unable to load submission index.</p>';
    intakeDocuments = defaultIntakeDocuments.map((item) => ({ ...item }));
    renderIntakeDocuments();
    renderQueueDashboard("Unable to load submission queue.");
  }
}

async function loadIntakeBootstrap({ showStatus = false } = {}) {
  if (showStatus) {
    setIntakeStatus("Loading intake data from API...");
  }

  const data = await AUApi.get("/api/intake/bootstrap");
  submissions = Array.isArray(data.submissions) ? data.submissions : [];
  brokers = Array.isArray(data.brokers) ? data.brokers : [];
  applySavedIntakeStatus(data.intake_status || {});
  renderBrokerOptions();
  renderIntakeDocuments();

  if (showStatus) {
    setIntakeStatus("Intake data loaded from API.");
  }
}

async function loadPortfolioQueue() {
  try {
    const data = await AUApi.get("/api/portfolio/queue");
    portfolioQueue = data.portfolio || null;
  } catch (error) {
    console.warn(error);
    portfolioQueue = null;
  }
}

searchInput.addEventListener("input", async () => {
  const query = searchInput.value.trim().toLowerCase();

  if (!query) {
    renderMatches([]);
    return;
  }

  if (!(await ensureSearchLogin("Searching submissions requires a local login session."))) {
    searchInput.value = "";
    renderMatches([]);
    return;
  }

  renderMatches(getMatchingSubmissions(query));
});

if (searchForm) {
  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = searchInput.value.trim().toLowerCase();
    if (!query) {
      renderMatches([]);
      return;
    }
    if (!(await ensureSearchLogin("Searching submissions requires a local login session."))) {
      return;
    }
    renderMatches(getMatchingSubmissions(query));
  });
}

document.addEventListener("click", async (event) => {
  const submissionLink = event.target.closest('a[href^="/chat.html?submission="]');
  if (!submissionLink) {
    return;
  }
  event.preventDefault();
  if (await ensureSearchLogin("Opening a submission requires a local login session.")) {
    window.location.href = submissionLink.href;
  }
});

if (addSubmissionToggle && addSubmissionPanel) {
  addSubmissionToggle.addEventListener("click", async () => {
    const shouldOpen = addSubmissionPanel.hasAttribute("hidden");
    if (shouldOpen && !(await ensureSearchLogin("Adding a submission requires a local login session."))) {
      return;
    }
    setAddSubmissionPanelOpen(shouldOpen, { updateUrl: true });
    if (shouldOpen) {
      addSubmissionToggle.disabled = true;
      try {
        await loadIntakeBootstrap({ showStatus: true });
      } catch (error) {
        console.warn(error);
        setIntakeStatus(error.message || "Unable to load intake data from API.", true);
      } finally {
        addSubmissionToggle.disabled = false;
      }
      focusAddSubmissionTarget();
    }
  });
}

window.addEventListener("popstate", applyAddSubmissionUrlState);

intakeModeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setIntakeMode(button.dataset.intakeMode || "manual");
  });
});

if (autoPopulateSubmission) {
  autoPopulateSubmission.addEventListener("click", autoPopulateIntake);
}

if (addSubmissionForm) {
  addSubmissionForm.addEventListener("submit", createSubmission);
}

if (moveToUnderwritingButton) {
  moveToUnderwritingButton.addEventListener("click", moveToUnderwritingAgent);
}

if (reviseIntakeButton) {
  reviseIntakeButton.addEventListener("click", reviseSubmissionIntakeForm);
}

if (saveIntakeStatusButton) {
  saveIntakeStatusButton.addEventListener("click", saveIntakeStatus);
}

if (applicationFormUploadButton && applicationFormUploadInput) {
  applicationFormUploadButton.addEventListener("click", () => {
    applicationFormUploadInput.click();
  });
  applicationFormUploadInput.addEventListener("change", () => {
    const files = Array.from(applicationFormUploadInput.files || []);
    if (files.length) {
      uploadApplicationDocuments(files);
    }
    applicationFormUploadInput.value = "";
  });
}

if (fillFromDocumentsButton) {
  fillFromDocumentsButton.addEventListener("click", fillInformationFromDocuments);
}

if (intakeDocumentList) {
  intakeDocumentList.addEventListener("change", updateDocumentChecklistValue);
  intakeDocumentList.addEventListener("input", updateDocumentChecklistValue);
}

if (stagedDocumentList) {
  stagedDocumentList.addEventListener("click", (event) => {
    const removeButton = event.target.closest("[data-remove-staged-document]");
    if (!removeButton) {
      return;
    }
    removeStagedDocument(removeButton.dataset.removeStagedDocument);
  });
}

function getMatchingSubmissions(query) {
  const normalizedQuery = String(query || "").trim().toLowerCase();
  if (!normalizedQuery) {
    return [];
  }

  return submissions.filter((submission) => {
    const haystack = [
      submission.id,
      submission.title,
      submission.insured_name,
      submission.industry,
      submission.status,
      ...(submission.keywords || [])
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(normalizedQuery);
  });
}

function renderMatches(results) {
  const query = searchInput.value.trim();

  if (!query) {
    searchResults.innerHTML = "";
    searchResults.classList.remove("open");
    return;
  }

  if (!results.length) {
    searchResults.innerHTML = '<p class="empty-state">No matching submissions found.</p>';
    searchResults.classList.add("open");
    return;
  }

  searchResults.innerHTML = `
    ${renderSubmissionLinks(results)}
  `;
  searchResults.classList.add("open");
}

function renderExamples(results) {
  if (!results.length) {
    exampleResults.innerHTML = "";
    return;
  }

  exampleResults.innerHTML = `
    <p class="examples-label">Submission Examples</p>
    ${renderSubmissionLinks(results)}
  `;
}

function renderSubmissionLinks(results) {
  return results
    .map(
      (submission) => `
      <a class="search-result-card" href="/chat.html?submission=${encodeURIComponent(submission.id)}">
        <strong>${escapeHtml(submission.id)}, ${escapeHtml(submission.title)}</strong>
      </a>
    `
    )
    .join("");
}

function renderQueueDashboard(errorMessage = "") {
  if (!queueDashboard) {
    return;
  }

  if (errorMessage) {
    queueDashboard.innerHTML = `<p class="empty-state">${escapeHtml(errorMessage)}</p>`;
    return;
  }

  const overview = portfolioQueue && portfolioQueue.overview ? portfolioQueue.overview : {};
  const rows = getQueuePreviewRows(portfolioQueue && Array.isArray(portfolioQueue.queue) ? portfolioQueue.queue : []);
  if (!rows.length) {
    queueDashboard.innerHTML = '<p class="empty-state">No queue records available.</p>';
    return;
  }

  queueDashboard.innerHTML = `
    <div class="queue-dashboard-heading">
      <div>
        <p class="eyebrow">Portfolio Queue</p>
        <h2>Submission Work Queue</h2>
      </div>
      <span>${escapeHtml(formatNumber(overview.submission_count))} accounts</span>
    </div>
    <div class="queue-metric-grid">
      ${renderQueueMetric("Ready", overview.ready_count, "No hard escalation trigger is active and the account can move toward quote work.")}
      ${renderQueueMetric("Review", overview.review_count, "Underwriter delegated review. The underwriter should validate evidence, controls, claims, and authority.")}
      ${renderQueueMetric("Referral", overview.referral_count, "Senior underwriting escalation for hard triggers such as open claims, high incurred losses, very low readiness, or large unresolved evidence gaps.")}
      ${renderQueueMetric("Avg Readiness", `${Math.round(Number(overview.avg_quote_readiness || 0))}%`, "Average Quote Readiness across the portfolio. This is not referral probability.")}
    </div>
    <div class="queue-definition-panel">
      <strong>Definition</strong>
      <span><b>Referral</b> means senior underwriting escalation is required.</span>
      <span><b>Quote Readiness</b> is how prepared the account is for quote terms based on evidence, broker quality, claims, controls, risk flags, exposure, and demo variance.</span>
    </div>
    <div class="queue-list">
      ${rows.map(renderQueueRow).join("")}
    </div>
  `;
}

function getQueuePreviewRows(queue) {
  const selected = [];
  const selectedIds = new Set();
  ["Referral", "Review", "Ready"].forEach((priority) => {
    queue
      .filter((row) => row.priority === priority)
      .slice(0, 2)
      .forEach((row) => {
        selected.push(row);
        selectedIds.add(row.id);
      });
  });

  if (selected.length < 6) {
    queue.forEach((row) => {
      if (selected.length < 6 && !selectedIds.has(row.id)) {
        selected.push(row);
        selectedIds.add(row.id);
      }
    });
  }

  return selected.slice(0, 6);
}

function renderQueueMetric(label, value, definition = "") {
  return `
    <article title="${escapeHtml(definition)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value ?? 0))}</strong>
    </article>
  `;
}

function renderQueueRow(row) {
  const readiness = `${Math.round(Number(row.quote_readiness || 0))}%`;
  return `
    <a class="queue-row" href="/chat.html?submission=${encodeURIComponent(row.id)}" title="Quote Readiness is not referral probability. It measures how ready this account is for quote terms.">
      <div>
        <strong>${escapeHtml(row.id)}, ${escapeHtml(row.title || row.insured_name || "Untitled")}</strong>
        <small>${escapeHtml([row.industry_bucket, row.broker_name, row.next_action].filter(Boolean).join(" | "))}</small>
      </div>
      <span class="queue-priority ${escapeHtml(String(row.priority || "").toLowerCase())}">${escapeHtml(row.priority || "Review")}</span>
      <span class="queue-readiness">
        <small>Quote Readiness</small>
        <em>${escapeHtml(readiness)}</em>
      </span>
    </a>
  `;
}

function applyAddSubmissionUrlState() {
  const currentView = getCurrentSearchView();
  const shouldOpen = currentView === ADD_SUBMISSION_VIEW || currentView === INTAKE_REVIEW_VIEW;
  setAddSubmissionPanelOpen(shouldOpen, { updateUrl: false });
  if (!shouldOpen) {
    return;
  }
  if (currentView === INTAKE_REVIEW_VIEW && restorePendingIntakeReview()) {
    showIntakeReview();
  } else {
    showIntakeForm();
  }
}

function setAddSubmissionPanelOpen(isOpen, { updateUrl = false } = {}) {
  if (!addSubmissionPanel || !addSubmissionToggle) {
    return;
  }

  addSubmissionPanel.toggleAttribute("hidden", !isOpen);
  addSubmissionToggle.textContent = isOpen ? "Close Intake" : "Add Submission";
  if (!isOpen) {
    showIntakeForm({ preserveUrl: true });
  }

  if (updateUrl) {
    updateSearchView(isOpen ? ADD_SUBMISSION_VIEW : "");
  }
}

function getCurrentSearchView() {
  return new URLSearchParams(window.location.search).get("view");
}

function updateSearchView(view) {
  const url = new URL(window.location.href);
  if (view) {
    url.searchParams.set("view", view);
  } else {
    url.searchParams.delete("view");
  }

  window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

async function ensureSearchLogin(reason) {
  if (!window.AUAuth) {
    return true;
  }
  await window.AUAuth.ready.catch(() => null);
  if (window.AUAuth.isLoggedIn()) {
    return true;
  }
  return window.AUAuth.requireLogin({ reason });
}

function showIntakeReview() {
  if (intakeReviewPanel) {
    intakeReviewPanel.removeAttribute("hidden");
  }
  if (addSubmissionForm) {
    addSubmissionForm.setAttribute("hidden", "");
  }
  if (submissionFormPanel) {
    submissionFormPanel.setAttribute("hidden", "");
  }
  document.querySelector(".intake-mode-control")?.setAttribute("hidden", "");
  renderIntakeReview(pendingIntakeReview);
}

function showIntakeForm({ preserveUrl = false } = {}) {
  if (intakeReviewPanel) {
    intakeReviewPanel.setAttribute("hidden", "");
  }
  if (addSubmissionForm) {
    addSubmissionForm.removeAttribute("hidden");
  }
  document.querySelector(".intake-mode-control")?.removeAttribute("hidden");
  setIntakeMode(intakeMode);
  if (!preserveUrl && getCurrentSearchView() === INTAKE_REVIEW_VIEW) {
    updateSearchView(ADD_SUBMISSION_VIEW);
  }
}

function renderIntakeReview(review) {
  if (!intakeReviewPanel || !intakeReviewSteps) {
    return;
  }

  if (!review) {
    intakeReviewSteps.innerHTML = '<p class="empty-state">No intake review is ready yet.</p>';
    if (intakeReviewPolicy) {
      intakeReviewPolicy.textContent = "";
    }
    return;
  }

  if (intakeReviewStatus) {
    intakeReviewStatus.textContent = formatReviewStatus(review.status);
  }
  if (intakeReviewPolicy) {
    intakeReviewPolicy.textContent = review.data_policy || "";
  }

  intakeReviewSteps.innerHTML = (review.steps || [])
    .map((step, index) => `
      <article class="intake-review-step ${escapeHtml(step.status || "pending")}" data-review-step="${escapeHtml(step.key || "")}">
        <div class="intake-review-step-index">${index + 1}</div>
        <div class="intake-review-step-body">
          <div class="intake-review-step-title">
            <div>
              <span>${escapeHtml(step.heading || "Review Step")}</span>
              <strong>${escapeHtml(step.action || "")}</strong>
            </div>
            <em>${escapeHtml(formatReviewStatus(step.status))}</em>
          </div>
          <p>${escapeHtml(step.detail || "")}</p>
          ${renderReviewItems(step.items)}
          ${step.recommendation ? `<small>${escapeHtml(step.recommendation)}</small>` : ""}
          ${step.source ? `<footer>${escapeHtml(step.source)}</footer>` : ""}
        </div>
      </article>
    `)
    .join("");
}

function renderReviewItems(items) {
  if (!Array.isArray(items) || !items.length) {
    return "";
  }
  return `
    <ul class="intake-review-items">
      ${items.slice(0, 8).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function formatReviewStatus(value) {
  return String(value || "pending")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function savePendingIntakeReview() {
  try {
    window.sessionStorage.setItem(PENDING_INTAKE_PAYLOAD_KEY, JSON.stringify(pendingSubmissionPayload));
    window.sessionStorage.setItem(PENDING_INTAKE_REVIEW_KEY, JSON.stringify(pendingIntakeReview));
  } catch (error) {
    console.warn("Unable to save pending intake review.", error);
  }
}

function restorePendingIntakeReview() {
  try {
    const payload = window.sessionStorage.getItem(PENDING_INTAKE_PAYLOAD_KEY);
    const review = window.sessionStorage.getItem(PENDING_INTAKE_REVIEW_KEY);
    pendingSubmissionPayload = payload ? JSON.parse(payload) : null;
    pendingIntakeReview = review ? JSON.parse(review) : null;
  } catch (error) {
    console.warn("Unable to restore pending intake review.", error);
    pendingSubmissionPayload = null;
    pendingIntakeReview = null;
  }
  return Boolean(pendingSubmissionPayload && pendingIntakeReview);
}

function clearPendingIntakeReview() {
  pendingSubmissionPayload = null;
  pendingIntakeReview = null;
  try {
    window.sessionStorage.removeItem(PENDING_INTAKE_PAYLOAD_KEY);
    window.sessionStorage.removeItem(PENDING_INTAKE_REVIEW_KEY);
  } catch (error) {
    console.warn("Unable to clear pending intake review.", error);
  }
}

function focusAddSubmissionTarget() {
  if (getCurrentSearchView() === INTAKE_REVIEW_VIEW) {
    moveToUnderwritingButton?.focus();
    return;
  }
  const focusTarget = intakeMode === "submission_form"
    ? document.querySelector("#intakeText")
    : document.querySelector("#newTitle");
  if (focusTarget) {
    focusTarget.focus();
  }
}

function renderBrokerOptions() {
  const select = document.querySelector("#newBrokerId");
  if (!select) {
    return;
  }

  select.innerHTML = `
    <option value="">No linked broker</option>
    ${brokers.map((broker) => `
      <option value="${escapeHtml(broker.broker_id)}">${escapeHtml(broker.firm_name)}</option>
    `).join("")}
  `;
}

function applySavedIntakeStatus(record) {
  intakeMode = record.intake_mode || "manual";
  intakeDocuments = Array.isArray(record.documents) && record.documents.length
    ? record.documents.map((item) => ({
        key: item.key,
        label: item.label,
        status: item.status || "needed",
        note: item.note || ""
      }))
    : defaultIntakeDocuments.map((item) => ({ ...item }));

  if (overallStatusInput && record.overall_status) {
    overallStatusInput.value = record.overall_status;
  }

  setIntakeMode(intakeMode);
}

function setIntakeMode(mode) {
  intakeMode = mode === "submission_form" ? "submission_form" : "manual";
  intakeModeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.intakeMode === intakeMode);
  });
  if (submissionFormPanel) {
    submissionFormPanel.toggleAttribute("hidden", intakeMode !== "submission_form");
  }
}

function renderIntakeDocuments() {
  if (!intakeDocumentList) {
    return;
  }

  const documents = intakeDocuments.length
    ? intakeDocuments
    : defaultIntakeDocuments.map((item) => ({ ...item }));
  intakeDocuments = documents;

  intakeDocumentList.innerHTML = documents
    .map((document) => `
      <div class="intake-document-row" data-document-key="${escapeHtml(document.key)}">
        <strong>${escapeHtml(document.label)}</strong>
        <select data-document-status="${escapeHtml(document.key)}" aria-label="${escapeHtml(document.label)} status">
          ${renderDocumentStatusOptions(document.status)}
        </select>
        <input
          type="text"
          data-document-note="${escapeHtml(document.key)}"
          value="${escapeHtml(document.note || "")}"
          placeholder="Note"
          aria-label="${escapeHtml(document.label)} note"
        />
      </div>
    `)
    .join("");
}

function renderDocumentStatusOptions(currentStatus) {
  const options = [
    ["needed", "Needed"],
    ["received", "Received"],
    ["waived", "Waived"],
    ["not_applicable", "N/A"]
  ];
  return options
    .map(([value, label]) => `<option value="${value}"${value === currentStatus ? " selected" : ""}>${label}</option>`)
    .join("");
}

function updateDocumentChecklistValue(event) {
  const statusKey = event.target.dataset.documentStatus;
  const noteKey = event.target.dataset.documentNote;
  const key = statusKey || noteKey;
  if (!key) {
    return;
  }

  intakeDocuments = intakeDocuments.map((document) => {
    if (document.key !== key) {
      return document;
    }
    if (statusKey) {
      return { ...document, status: event.target.value };
    }
    return { ...document, note: event.target.value };
  });
}

async function saveIntakeStatus() {
  setIntakeStatus("Saving intake status...");
  if (saveIntakeStatusButton) {
    saveIntakeStatusButton.disabled = true;
  }

  try {
    const data = await AUApi.put("/api/intake/status", collectIntakeStatusPayload());
    applySavedIntakeStatus(data.intake_status || {});
    renderIntakeDocuments();
    setIntakeStatus("Intake status saved.");
  } catch (error) {
    console.warn(error);
    setIntakeStatus(error.message || "Unable to save intake status.", true);
  } finally {
    if (saveIntakeStatusButton) {
      saveIntakeStatusButton.disabled = false;
    }
  }
}

async function autoPopulateIntake() {
  setIntakeMode("submission_form");
  const intakeText = document.querySelector("#intakeText").value.trim();
  if (!intakeText) {
    setIntakeStatus("Paste intake text first.", true);
    return;
  }

  setIntakeStatus("Auto-populating...");
  autoPopulateSubmission.disabled = true;
  try {
    const data = await AUApi.post("/api/intake/draft", { intake_text: intakeText });

    applyDraftToForm(data.draft || {});
    setIntakeStatus("Draft populated.");
  } catch (error) {
    console.warn(error);
    setIntakeStatus(error.message || "Unable to auto-populate.", true);
  } finally {
    autoPopulateSubmission.disabled = false;
  }
}

async function uploadApplicationDocuments(files) {
  setIntakeMode("submission_form");
  const validFiles = files.filter((file) => ["txt", "pdf"].includes(file.name.split(".").pop().toLowerCase()));
  if (!validFiles.length) {
    setApplicationFormUploadStatus("Only .txt and .pdf files are supported.", true);
    return;
  }

  setApplicationFormUploadStatus(`Reading ${validFiles.length} document${validFiles.length === 1 ? "" : "s"}...`);
  if (applicationFormUploadButton) {
    applicationFormUploadButton.disabled = true;
  }
  if (fillFromDocumentsButton) {
    fillFromDocumentsButton.disabled = true;
  }

  try {
    for (const file of validFiles) {
      const formData = new FormData();
      formData.append("file", file);
      const data = await AUApi.post("/api/intake/draft-file", formData);

      const applicationForm = data.application_form || {};
      addStagedDocument({
        upload_id: applicationForm.upload_id || "",
        file_name: applicationForm.file_name || file.name,
        extracted_text: applicationForm.extracted_text || "",
        draft: applicationForm.draft || {}
      });
      markChecklistFromDocument(applicationForm.file_name || file.name, applicationForm.extracted_text || "");
    }
    updateCombinedIntakeTextFromDocuments();
    renderIntakeDocuments();
    renderStagedDocuments();
    setApplicationFormUploadStatus(`Loaded ${validFiles.length} document${validFiles.length === 1 ? "" : "s"}.`);
    setIntakeStatus("Documents uploaded. Click Fill Out Information when ready.");
  } catch (error) {
    console.warn(error);
    setApplicationFormUploadStatus(error.message || "Unable to read uploaded documents.", true);
  } finally {
    if (applicationFormUploadButton) {
      applicationFormUploadButton.disabled = false;
    }
    if (fillFromDocumentsButton) {
      fillFromDocumentsButton.disabled = false;
    }
  }
}

async function fillInformationFromDocuments() {
  setIntakeMode("submission_form");
  const combinedText = buildCombinedIntakeText();
  if (!combinedText.trim()) {
    setIntakeStatus("Upload documents or paste intake text first.", true);
    return;
  }

  setIntakeStatus("Filling out information...");
  if (fillFromDocumentsButton) {
    fillFromDocumentsButton.disabled = true;
  }
  try {
    const data = await AUApi.post("/api/intake/draft", { intake_text: combinedText });
    applyDraftToForm(data.draft || {});
    setValue("#intakeText", combinedText);
    setIntakeStatus(stagedIntakeDocuments.length ? "Information filled from uploaded documents." : "Information filled from intake text.");
  } catch (error) {
    console.warn(error);
    setIntakeStatus(error.message || "Unable to fill out information.", true);
  } finally {
    if (fillFromDocumentsButton) {
      fillFromDocumentsButton.disabled = false;
    }
  }
}

async function createSubmission(event) {
  event.preventDefault();
  const payload = collectSubmissionPayload();
  if (!payload.draft.title || !payload.draft.insured_name) {
    setIntakeStatus("Title and insured name are required.", true);
    return;
  }

  setIntakeStatus("Preparing intake review...");
  const submitButton = addSubmissionForm.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
  }

  try {
    const data = await AUApi.post("/api/intake/review", payload);
    pendingSubmissionPayload = payload;
    pendingIntakeReview = data.review || null;
    savePendingIntakeReview();
    renderIntakeReview(pendingIntakeReview);
    showIntakeReview();
    updateSearchView(INTAKE_REVIEW_VIEW);
    setIntakeStatus("Review the generated intake checks before creating the underwriting record.");
  } catch (error) {
    console.warn(error);
    setIntakeStatus(error.message || "Unable to prepare intake review.", true);
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
    }
  }
}

async function moveToUnderwritingAgent() {
  if (!pendingSubmissionPayload) {
    setIntakeStatus("No reviewed submission is ready to create.", true);
    return;
  }

  setIntakeStatus("Creating confirmed submission...");
  if (moveToUnderwritingButton) {
    moveToUnderwritingButton.disabled = true;
  }
  if (reviseIntakeButton) {
    reviseIntakeButton.disabled = true;
  }

  try {
    const data = await AUApi.post("/api/intake/submissions", pendingSubmissionPayload);
    const submissionId = data.submission && data.submission.id;
    if (!submissionId) {
      throw new Error("Submission was created, but the id was not returned.");
    }

    clearPendingIntakeReview();
    window.location.href = `/chat.html?submission=${encodeURIComponent(submissionId)}`;
  } catch (error) {
    console.warn(error);
    setIntakeStatus(error.message || "Unable to create submission.", true);
    if (moveToUnderwritingButton) {
      moveToUnderwritingButton.disabled = false;
    }
    if (reviseIntakeButton) {
      reviseIntakeButton.disabled = false;
    }
  }
}

function reviseSubmissionIntakeForm() {
  showIntakeForm();
  updateSearchView(ADD_SUBMISSION_VIEW);
  setIntakeStatus("Revise the intake form, then create the submission again.");
}

function markIntakeDocumentReceived(key, note) {
  intakeDocuments = intakeDocuments.map((document) => (
    document.key === key
      ? { ...document, status: "received", note: note || document.note || "Uploaded intake document" }
      : document
  ));
}

function addStagedDocument(document) {
  const extractedText = String(document.extracted_text || "").trim();
  if (!extractedText) {
    return;
  }
  const fileName = document.file_name || "uploaded-document.txt";
  const existingIndex = stagedIntakeDocuments.findIndex((item) => item.file_name === fileName);
  const stagedDocument = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    upload_id: document.upload_id || "",
    file_name: fileName,
    extracted_text: extractedText,
    draft: document.draft || {}
  };
  if (existingIndex >= 0) {
    stagedIntakeDocuments.splice(existingIndex, 1, stagedDocument);
  } else {
    stagedIntakeDocuments.push(stagedDocument);
  }
}

function removeStagedDocument(documentId) {
  stagedIntakeDocuments = stagedIntakeDocuments.filter((document) => document.id !== documentId);
  updateCombinedIntakeTextFromDocuments();
  renderStagedDocuments();
}

function renderStagedDocuments() {
  if (!stagedDocumentList) {
    return;
  }

  if (!stagedIntakeDocuments.length) {
    stagedDocumentList.innerHTML = "";
    return;
  }

  stagedDocumentList.innerHTML = stagedIntakeDocuments
    .map((document) => `
      <article class="staged-document-card">
        <div>
          <strong>${escapeHtml(document.file_name)}</strong>
          <small>${escapeHtml(formatCharacterCount(document.extracted_text.length))}</small>
        </div>
        <p>${escapeHtml(makeDocumentPreview(document.extracted_text))}</p>
        <button class="icon-button small-icon-button staged-document-remove" type="button" data-remove-staged-document="${escapeHtml(document.id)}" aria-label="Remove ${escapeHtml(document.file_name)}">&times;</button>
      </article>
    `)
    .join("");
}

function updateCombinedIntakeTextFromDocuments() {
  const combinedText = buildCombinedIntakeText();
  if (combinedText) {
    setValue("#intakeText", combinedText);
  }
}

function buildCombinedIntakeText() {
  if (stagedIntakeDocuments.length) {
    return stagedIntakeDocuments
      .map((document) => [
        `--- ${document.file_name} ---`,
        document.extracted_text
      ].join("\n"))
      .join("\n\n");
  }
  return getValue("#intakeText");
}

function markChecklistFromDocument(fileName, text) {
  const haystack = `${fileName || ""} ${text || ""}`.toLowerCase();
  const rules = [
    ["ransomware_supplemental_application", ["ransomware", "supplement"]],
    ["prior_cyber_insurance_policy", ["prior policy", "expiring policy", "policy"]],
    ["loss_runs_claims_history", ["loss run", "claim", "loss history"]],
    ["financial_information_revenue_breakdown", ["financial", "revenue", "sales"]],
    ["it_security_controls_questionnaire", ["security questionnaire", "controls questionnaire", "it controls"]],
    ["mfa_edr_backup_documentation", ["mfa", "edr", "backup"]],
    ["incident_response_plan", ["incident response", "ir plan"]],
    ["vendor_security_assessment", ["vendor", "third party", "security assessment"]],
    ["compliance_documents", ["soc 2", "hipaa", "pci", "compliance"]],
    ["cyber_application", ["application", "applicant", "submission form", "company"]]
  ];

  const matched = rules.find(([, keywords]) => keywords.some((keyword) => haystack.includes(keyword)));
  if (matched) {
    markIntakeDocumentReceived(matched[0], fileName);
  }
}

function makeDocumentPreview(text) {
  const cleaned = String(text || "").replace(/\s+/g, " ").trim();
  return cleaned.length > 190 ? `${cleaned.slice(0, 190)}...` : cleaned;
}

function formatCharacterCount(count) {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k characters`;
  }
  return `${count} characters`;
}

function applyDraftToForm(draft) {
  setValue("#newTitle", draft.title);
  setValue("#newInsuredName", draft.insured_name);
  setValue("#newIndustry", draft.industry);
  setValue("#newIndustryBucket", draft.industry_bucket);
  setValue("#newLocation", draft.location);
  setValue("#newRevenue", draft.annual_revenue);
  setValue("#newEmployees", draft.employee_count);
  setValue("#newRecords", draft.records_count);
  setValue("#newEffectiveDate", normalizeDate(draft.requested_effective_date));
  setValue("#newCoverageLimit", draft.coverage_limit);
  setValue("#newRetention", draft.retention_requested);
  setValue("#newTechnologyProfile", draft.technology_profile);
  setValue("#newMfa", draft.mfa);
  setValue("#newEdr", draft.edr);
  setValue("#newBackup", draft.backup);
  setValue("#newPatching", draft.patching);
  setValue("#newSecurityTraining", draft.security_training);
  setValue("#newRiskFlags", Array.isArray(draft.risk_flags) ? draft.risk_flags.join("\n") : draft.risk_flags);
  setValue("#newOpenQuestions", Array.isArray(draft.open_questions) ? draft.open_questions.join("\n") : draft.open_questions);

  const brokerSelect = document.querySelector("#newBrokerId");
  if (brokerSelect) {
    const matchedBroker = matchBroker(draft.broker_id, draft.broker_name);
    brokerSelect.value = matchedBroker ? matchedBroker.broker_id : "";
  }
}

function collectSubmissionPayload() {
  const broker = matchBroker(document.querySelector("#newBrokerId").value, "");
  return {
    intake_text: document.querySelector("#intakeText").value.trim(),
    uploaded_documents: stagedIntakeDocuments.map((document) => ({
      upload_id: document.upload_id || "",
      file_name: document.file_name,
      extracted_text: document.extracted_text
    })),
    intake_status: collectIntakeStatusPayload(),
    draft: {
      title: getValue("#newTitle"),
      insured_name: getValue("#newInsuredName"),
      industry: getValue("#newIndustry"),
      industry_bucket: getValue("#newIndustryBucket"),
      location: getValue("#newLocation"),
      annual_revenue: getValue("#newRevenue"),
      employee_count: getValue("#newEmployees"),
      records_count: getValue("#newRecords"),
      requested_effective_date: getValue("#newEffectiveDate"),
      coverage_limit: getValue("#newCoverageLimit"),
      retention_requested: getValue("#newRetention"),
      broker_id: broker ? broker.broker_id : "",
      broker_name: broker ? broker.firm_name : "",
      technology_profile: getValue("#newTechnologyProfile"),
      mfa: getValue("#newMfa"),
      edr: getValue("#newEdr"),
      backup: getValue("#newBackup"),
      patching: getValue("#newPatching"),
      security_training: getValue("#newSecurityTraining"),
      risk_flags: splitLines(getValue("#newRiskFlags")),
      open_questions: splitLines(getValue("#newOpenQuestions"))
    }
  };
}

function collectIntakeStatusPayload() {
  return {
    intake_mode: intakeMode,
    overall_status: overallStatusInput ? overallStatusInput.value : "draft",
    documents: intakeDocuments.map((document) => ({
      key: document.key,
      label: document.label,
      status: document.status || "needed",
      note: document.note || ""
    })),
    draft: collectDraftSnapshot()
  };
}

function collectDraftSnapshot() {
  return {
    title: getValue("#newTitle"),
    insured_name: getValue("#newInsuredName"),
    industry: getValue("#newIndustry"),
    industry_bucket: getValue("#newIndustryBucket"),
    location: getValue("#newLocation"),
    annual_revenue: getValue("#newRevenue"),
    employee_count: getValue("#newEmployees"),
    records_count: getValue("#newRecords"),
    requested_effective_date: getValue("#newEffectiveDate"),
    coverage_limit: getValue("#newCoverageLimit"),
    retention_requested: getValue("#newRetention"),
    technology_profile: getValue("#newTechnologyProfile")
  };
}

function matchBroker(brokerId, brokerName) {
  const id = String(brokerId || "").trim();
  const name = String(brokerName || "").trim().toLowerCase();
  return brokers.find((broker) => broker.broker_id === id)
    || brokers.find((broker) => broker.firm_name && broker.firm_name.toLowerCase() === name)
    || null;
}

function setValue(selector, value) {
  const element = document.querySelector(selector);
  if (!element || value === undefined || value === null || value === "") {
    return;
  }
  element.value = value;
}

function getValue(selector) {
  const element = document.querySelector(selector);
  return element ? element.value.trim() : "";
}

function splitLines(value) {
  return String(value || "")
    .split(/\n|;/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeDate(value) {
  const text = String(value || "").trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : "";
}

function setIntakeStatus(message, isError = false) {
  if (!intakeStatus) {
    return;
  }
  intakeStatus.textContent = message;
  intakeStatus.style.color = isError ? "#991b1b" : "";
}

function setApplicationFormUploadStatus(message, isError = false) {
  if (!applicationFormUploadStatus) {
    return;
  }
  applicationFormUploadStatus.textContent = message;
  applicationFormUploadStatus.style.color = isError ? "#991b1b" : "";
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
