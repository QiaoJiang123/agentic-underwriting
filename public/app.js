const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messagesEl = document.querySelector("#messages");
const sendButton = document.querySelector("#sendButton");
const clearButton = document.querySelector("#clearButton");
const newChatButton = document.querySelector("#newChatButton");
const historyList = document.querySelector("#historyList");
const modelStatus = document.querySelector("#modelStatus");
const modelCard = document.querySelector(".model-card");
const guideToggleButton = document.querySelector("#guideToggleButton");
const guidePopover = document.querySelector("#guidePopover");
const guideCloseButton = document.querySelector("#guideCloseButton");
const workspaceMenuButton = document.querySelector("#workspaceMenuButton");
const workspaceMenu = document.querySelector("#workspaceMenu");
const sopReviewModal = document.querySelector("#sopReviewModal");
const sopReviewContent = document.querySelector("#sopReviewContent");
const sopReviewCloseButton = document.querySelector("#sopReviewCloseButton");
const websiteDemoModal = document.querySelector("#websiteDemoModal");
const websiteDemoContent = document.querySelector("#websiteDemoContent");
const websiteDemoCloseButton = document.querySelector("#websiteDemoCloseButton");
const workSurface = document.querySelector(".work-surface");
const submissionList = document.querySelector("#submissionList");
const submissionCount = document.querySelector("#submissionCount");
const workspaceTitle = document.querySelector("#workspaceTitle");
const summaryPlaceholder = document.querySelector("#summaryPlaceholder");
const followUpForm = document.querySelector("#followUpForm");
const followUpTitle = document.querySelector("#followUpTitle");
const followUpDate = document.querySelector("#followUpDate");
const followUpCalendar = document.querySelector("#followUpCalendar");
const followUpList = document.querySelector("#followUpList");
const tasksDueDot = document.querySelector("#tasksDueDot");
const followUpDueDot = document.querySelector("#followUpDueDot");
const submitWorkflowButton = document.querySelector("#submitWorkflowButton");
const workflowSubmitStatus = document.querySelector("#workflowSubmitStatus");
const keyInfoList = document.querySelector("#keyInfoList");
const timelineList = document.querySelector("#timelineList");
const generateSummaryButton = document.querySelector("#generateSummaryButton");
const refreshInsightsButton = document.querySelector("#refreshInsightsButton");
const analyticsPanel = document.querySelector("#analyticsPanel");
const panelExpandRailButton = document.querySelector("#panelExpandRailButton");
const expandedPageHeader = document.querySelector("#expandedPageHeader");
const expandedPageTitle = document.querySelector("#expandedPageTitle");
const backToChatButton = document.querySelector("#backToChatButton");
const underwritingExpandButton = document.querySelector("#underwritingExpandButton");
const underwritingSummaryPanel = document.querySelector("#underwritingSummaryPanel");
const underwritingWorkbenchPanel = document.querySelector("#underwritingWorkbenchPanel");
const stageChecklist = document.querySelector("#stageChecklist");
const documentList = document.querySelector("#documentList");
const documentUploadInput = document.querySelector("#documentUploadInput");
const documentUploadButton = document.querySelector("#documentUploadButton");
const documentUploadStatus = document.querySelector("#documentUploadStatus");
const selectAllFilesButton = document.querySelector("#selectAllFilesButton");
const unselectAllFilesButton = document.querySelector("#unselectAllFilesButton");
const autoSelectFiles = document.querySelector("#autoSelectFiles");
const documentModal = document.querySelector("#documentModal");
const documentModalTitle = document.querySelector("#documentModalTitle");
const documentModalContent = document.querySelector("#documentModalContent");
const documentCloseButton = document.querySelector("#documentCloseButton");
const panelTabButtons = document.querySelectorAll("[data-panel-tab]");
const panelViews = document.querySelectorAll("[data-panel-view]");
const guideForm = document.querySelector("#guideForm");
const guideInput = document.querySelector("#guideInput");
const guideList = document.querySelector("#guideList");
const noteForm = document.querySelector("#noteForm");
const noteInput = document.querySelector("#noteInput");
const noteList = document.querySelector("#noteList");

const messages = [];
const activeChatProcesses = [];
const TASK_CALENDAR_MIN_YEAR = 2000;
const TASK_CALENDAR_MAX_YEAR = 2100;
const AGENT_SELECTED_SURFACE_CLASS = "agent-selected-surface";
const AGENT_SELECTED_TAB_CLASS = "agent-selected-tab";
const AGENT_SKILL_SURFACE_MAP = {
  account: ["details_summary", "key_info"],
  account_summary: ["details_summary", "key_info"],
  analytics: ["analytics"],
  analytics_db: ["analytics", "underwriting"],
  bind: ["analytics"],
  bind_model: ["analytics"],
  bind_probability: ["analytics"],
  broker: ["underwriting"],
  broker_table: ["underwriting"],
  claims: ["underwriting"],
  claim: ["underwriting"],
  clearance: ["underwriting"],
  decision_workflow: ["underwriting"],
  details: ["details_summary", "underwriting"],
  documents: ["documents"],
  document: ["documents"],
  document_completeness: ["documents", "underwriting"],
  evidence: ["documents", "underwriting"],
  guide: ["guide"],
  guides: ["guide"],
  external_research: ["underwriting"],
  notes: ["notes"],
  note: ["notes"],
  quote: ["analytics"],
  quote_model: ["analytics"],
  quote_probability: ["analytics"],
  portfolio: ["analytics"],
  rating_quote: ["underwriting"],
  sop: ["underwriting"],
  sop_guidance: ["underwriting"],
  stages: ["stages"],
  stage: ["stages"],
  status: ["details_summary", "underwriting", "tasks", "stages"],
  submission_update: ["details_summary", "key_info", "underwriting"],
  tasks: ["tasks"],
  task: ["tasks"],
  timeline: ["timeline"],
  underwriting: ["underwriting"]
};
const AGENT_ACTION_SURFACE_MAP = {
  broker_table: ["underwriting"],
  document_completeness: ["documents", "underwriting"],
  extract: ["underwriting"],
  guide: ["guide"],
  navigate: [],
  note: ["notes"],
  submission_update: ["details_summary", "key_info", "underwriting"],
  task: ["tasks"],
};
const AGENT_PANEL_SURFACE_MAP = {
  analytics: ["analytics"],
  details: ["details_summary", "underwriting"],
  note: ["notes"],
  tasks: ["tasks"]
};
const AGENT_SURFACE_TAB_MAP = {
  analytics: "analytics",
  details_summary: "details",
  notes: "note",
  stages: "tasks",
  tasks: "tasks",
  timeline: "details",
  underwriting: "details"
};
let selectedSubmission = null;
let selectedFiles = new Set();
let currentChatHistoryId = null;
let autoSelectEnabled = true;
let fileSelectionMode = "auto";
let guideItems = [];
let editingGuideIndex = null;
let noteItems = [];
let editingNoteIndex = null;
let followUpItems = [];
let selectedTaskDate = null;
let taskCalendarCursor = clampTaskCalendarDate(new Date());
let stageItems = [];
let workflowSubmittedAt = null;
let analyticsModels = null;
let analyticsFeatureMetadata = null;
let sopReviewRecord = null;
let underwritingSystem = null;
let decisionWorkflow = null;
let clearanceReview = null;
let externalResearch = null;
let ratingQuote = null;
let portfolioDashboard = null;
let currentAnalytics = null;
let currentAnalyticsFeatureLookup = null;
let activeWhatIfModel = "quote";
let whatIfScenarioState = createEmptyWhatIfScenarioState();
let activeFeatureTooltip = null;
let underwritingDetailsOpen = false;
let submissionUpdateEditingFields = new Set();
let activeSupplementalModelKey = "cyber_attack_prob";
const initialSubmissionId = new URLSearchParams(window.location.search).get("submission");

const SUPPLEMENTAL_MODEL_KEYS = [
  "cyber_attack_prob",
  "ransomware_prob",
  "data_breach_prob",
  "business_interruption_prob",
  "claim_severity_prob"
];

const SUPPLEMENTAL_RESULT_DEFINITIONS = {
  cyber_attack_prob: {
    label: "Cyber Attack Probability",
    detail: "Likelihood of a cyber event in the underwriting period",
    higherIsRisk: true
  },
  ransomware_prob: {
    label: "Ransomware Probability",
    detail: "Ransomware susceptibility from controls and dependency profile",
    higherIsRisk: true
  },
  data_breach_prob: {
    label: "Data Breach Probability",
    detail: "Privacy and records-driven breach exposure",
    higherIsRisk: true
  },
  business_interruption_prob: {
    label: "Business Interruption Probability",
    detail: "Operational outage and dependency exposure",
    higherIsRisk: true
  },
  claim_severity_prob: {
    label: "Claim Severity Probability",
    detail: "Chance of a materially severe cyber claim",
    higherIsRisk: true
  },
  industry_propensity: {
    label: "Industry Propensity Score",
    detail: "Industry and technology profile baseline risk",
    higherIsRisk: true
  },
  broker_placement_confidence: {
    label: "Broker Placement Confidence",
    detail: "Broker quality, speed, evidence, and model support",
    higherIsRisk: false
  },
  evidence_confidence: {
    label: "Evidence Confidence Score",
    detail: "Required evidence available for decision support",
    higherIsRisk: false
  }
};

init();

function init() {
  configureTaskDateInput();
  loadHealth();
  loadSubmissions();
}

function configureTaskDateInput() {
  if (!followUpDate) {
    return;
  }

  followUpDate.min = `${TASK_CALENDAR_MIN_YEAR}-01-01`;
  followUpDate.max = `${TASK_CALENDAR_MAX_YEAR}-12-31`;
}

function loadHealth() {
  AUApi.get("/health")
    .then((data) => {
      modelStatus.textContent = data.model || "Connected";
      modelCard.classList.add("ready");
    })
    .catch(() => {
      modelStatus.textContent = "Offline";
      modelCard.classList.add("error");
    });
}

async function loadSubmissions() {
  try {
    const response = await fetch("/api/submissions");
    const data = await response.json();
    const submissions = Array.isArray(data.submissions) ? data.submissions : [];

    if (submissionCount) {
      submissionCount.textContent = String(submissions.length);
    }

    if (submissionList) {
      submissionList.innerHTML = "";
    }

    if (!submissions.length) {
      if (submissionList) {
        submissionList.innerHTML = '<p class="empty-state">No submissions found.</p>';
      }
      return;
    }

    let initialSelection = null;

    submissions.forEach((submission) => {
      let button = null;

      if (submissionList) {
        button = document.createElement("button");
        button.className = "submission-item";
        button.type = "button";
        button.dataset.id = submission.id;
        button.innerHTML = `
          <span>${escapeHtml(submission.title)}</span>
          <small>${escapeHtml(submission.status || "New")} · ${escapeHtml(submission.coverage)}</small>
        `;
        button.addEventListener("click", () => selectSubmission(submission, button));
        submissionList.append(button);
      }

      if (submission.id === initialSubmissionId) {
        initialSelection = { submission, button };
      }
    });

    if (initialSelection) {
      selectSubmission(initialSelection.submission, initialSelection.button);
    } else if (historyList) {
      historyList.innerHTML = '<p class="empty-state">No chat history.</p>';
    }
  } catch (error) {
    if (submissionList) {
      submissionList.innerHTML = '<p class="empty-state">Unable to load submissions.</p>';
    }
  }
}

async function selectSubmission(submission, button) {
  if (button) {
    document.querySelectorAll(".submission-item").forEach((item) => {
      item.classList.remove("active");
    });
    button.classList.add("active");
  }

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(submission.id)}`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load submission.");
    }

    selectedSubmission = {
      ...submission,
      record: data.submission,
      content: formatSubmissionForPrompt(data.submission)
    };
    currentChatHistoryId = null;
    autoSelectEnabled = true;
    guideItems = [];
    editingGuideIndex = null;
    noteItems = [];
    editingNoteIndex = null;
    followUpItems = [];
    selectedTaskDate = null;
    taskCalendarCursor = clampTaskCalendarDate(new Date());
    stageItems = [];
    workflowSubmittedAt = null;
    underwritingSystem = null;
    decisionWorkflow = null;
    clearanceReview = null;
    externalResearch = null;
    ratingQuote = null;
    portfolioDashboard = null;
    currentAnalytics = null;
    currentAnalyticsFeatureLookup = null;
    activeWhatIfModel = "quote";
    activeSupplementalModelKey = "cyber_attack_prob";
    whatIfScenarioState = createEmptyWhatIfScenarioState();
    underwritingDetailsOpen = false;
    submissionUpdateEditingFields = new Set();
    setInsightExpanded(false);
    clearAgentSelectedSurfaces();

    workspaceTitle.textContent = submission.title;
    summaryPlaceholder.innerHTML = buildSummaryHtml(selectedSubmission.record);
    renderSubmissionUpdateForm(selectedSubmission.record);
    keyInfoList.innerHTML = buildKeyInfoHtml(selectedSubmission);
    timelineList.innerHTML = buildTimelineItems(selectedSubmission.record);
    analyticsPanel.innerHTML = '<p class="empty-state">Loading analytics and underwriting system...</p>';
    await Promise.all([
      loadAnalyticsModels(),
      loadUnderwritingSystem(submission.id),
      loadDecisionWorkflow(submission.id),
      loadClearanceReview(submission.id),
      loadExternalResearch(submission.id),
      loadRatingQuote(submission.id),
      loadPortfolioDashboard()
    ]);
    analyticsPanel.innerHTML = buildAnalyticsPanel(selectedSubmission.record);
    renderUnderwritingDetails();
    stageItems = buildDefaultStageItems(selectedSubmission.record);
    renderStageChecklist();
    documentList.innerHTML = buildDocumentLinks(selectedSubmission.record);
    setAutoDocumentMode();
    renderGuideInstructions("Loading guide...");
    renderNoteContext("Loading notes...");
    renderFollowUps("Loading tasks...");
    await loadGuideInstructions(submission.id);
    await loadNotes(submission.id);
    await loadFollowUps(submission.id);
    await loadStageState(submission.id);
    loadChatHistory(submission.id);

    input.value = "";
    input.focus();
  } catch (error) {
    addMessage("assistant", error.message || "Unable to load that submission.", true);
  }
}

async function loadChatHistory(submissionId) {
  if (!historyList) {
    return;
  }

  historyList.innerHTML = '<p class="empty-state">Loading chat history...</p>';

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(submissionId)}/chat-history`);
    const data = await response.json();
    const history = Array.isArray(data.chat_history) ? data.chat_history : [];

    if (!history.length) {
      historyList.innerHTML = '<p class="empty-state">No chat history yet.</p>';
      return;
    }

    historyList.innerHTML = history
      .map(
        (item, index) => `
          <button
            class="history-item ${index === 0 ? "active" : ""}"
            type="button"
            data-history-id="${escapeHtml(item.id)}"
            title="${escapeHtml(formatDateTime(item.updated_at))} · ${item.message_count} messages"
          >
            <span>${escapeHtml(item.title)}</span>
            <small>${escapeHtml(formatDateTime(item.updated_at))} · ${item.message_count} messages</small>
          </button>
        `
      )
      .join("");
  } catch (error) {
    historyList.innerHTML = '<p class="empty-state">Unable to load chat history.</p>';
  }
}

historyList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-history-id]");
  if (!button || !selectedSubmission) {
    return;
  }

  document.querySelectorAll("[data-history-id]").forEach((item) => {
    item.classList.toggle("active", item === button);
  });

  await loadChatHistoryMessages(selectedSubmission.id, button.dataset.historyId);
});

async function loadChatHistoryMessages(submissionId, historyId) {
  setAutoDocumentMode({ clearHighlights: true });
  messagesEl.innerHTML = "";
  addMessage("assistant", "Loading chat history...");

  try {
    const response = await fetch(
      `/api/submissions/${encodeURIComponent(submissionId)}/chat-history/${encodeURIComponent(historyId)}`
    );
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load chat history.");
    }

    const historyMessages = Array.isArray(data.chat_history.messages)
      ? data.chat_history.messages
      : [];

    currentChatHistoryId = data.chat_history.id || historyId;
    messages.length = 0;
    messagesEl.innerHTML = "";

    if (!historyMessages.length) {
      addMessage("assistant", "This chat history has no messages.");
      return;
    }

    historyMessages.forEach((message) => {
      const role = message.role === "assistant" ? "assistant" : "user";
      const content = String(message.content || "");
      addMessage(role, content);
      messages.push({ role, content });
    });
  } catch (error) {
    messagesEl.innerHTML = "";
    addMessage("assistant", error.message || "Unable to load chat history.", true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const content = input.value.trim();
  if (!content) {
    return;
  }

  input.value = "";
  clearAgentSelectedSurfaces();
  addMessage("user", content);
  messages.push({ role: "user", content });

  setLoading(true);
  const pending = addMessage("assistant", "");
  const chatProcess = createChatProcess(pending);
  addChatProcessStep(chatProcess, "Prompt received", "Preparing underwriting context.", "done");

  try {
    const visibleChatHistory = messages;
    const actionStep = addChatProcessStep(
      chatProcess,
      "Checking workflow actions",
      "Central router will check note, guide, task, navigation, and submission-update requests.",
      "active"
    );

    const selectionStep = addChatProcessStep(
      chatProcess,
      "Selecting underwriting information",
      describeCentralSelectionRequest(),
      "active"
    );

    const contextStep = addChatProcessStep(
      chatProcess,
      "Routing through underwriting backend",
      "Guide instructions, notes, selected data, and chat history are handled in one backend request.",
      "active"
    );

    const temporaryModelMessages = buildTemporaryModelMessagesWithSelectedFiles(visibleChatHistory);
    const data = await AUApi.post("/api/chat", {
        submission_id: selectedSubmission ? selectedSubmission.id : null,
        user_prompt: content,
        messages: temporaryModelMessages,
        selected_files: Array.from(selectedFiles),
        file_selection_mode: fileSelectionMode,
        guides: getActiveGuideInstructions(),
        underwriter_notes: getActiveUnderwriterNotes()
      });

    updateChatProcessStep(actionStep, {
      status: "done",
      detail: describeWorkflowActionCheck(data)
    });
    applyCentralDocumentSelection(data);
    updateChatProcessStep(selectionStep, {
      status: "done",
      detail: describeInformationSelection(data)
    });
    updateChatProcessStep(contextStep, {
      status: "done",
      detail: describeBackendResponse(data)
    });
    appendResponseProcessSteps(chatProcess, data);
    setChatProcessAnswer(chatProcess, data.reply, data.retrieval && data.retrieval.sources);
    messages.push({ role: "assistant", content: data.reply });
    await refreshAfterChatActions(data.actions);
    highlightAgentSelectedSurfaces(data);
    appendWorkspaceRefreshProcessStep(chatProcess, data.actions);
    await saveCurrentChatHistory();
  } catch (error) {
    markActiveChatProcessSteps(chatProcess, "error");
    setChatProcessError(chatProcess, error.message || "Something went wrong.");
  } finally {
    setLoading(false);
  }
});

clearButton.addEventListener("click", resetChat);
newChatButton.addEventListener("click", resetChat);

if (guideToggleButton && guidePopover) {
  guideToggleButton.addEventListener("click", () => {
    const isOpen = guidePopover.classList.toggle("open");
    guidePopover.setAttribute("aria-hidden", isOpen ? "false" : "true");
    guideToggleButton.classList.toggle("active", isOpen);

    if (isOpen) {
      guideInput.focus();
    }
  });
}

if (guideCloseButton && guidePopover) {
  guideCloseButton.addEventListener("click", closeGuidePopover);
}

if (workspaceMenuButton && workspaceMenu) {
  workspaceMenuButton.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleWorkspaceMenu();
  });

  workspaceMenu.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-workspace-menu-action]");
    if (!actionButton) {
      return;
    }

    closeWorkspaceMenu();
    if (actionButton.dataset.workspaceMenuAction === "sop") {
      openSopReview();
    }
    if (actionButton.dataset.workspaceMenuAction === "demo") {
      openWebsiteDemo();
    }
  });
}

if (sopReviewCloseButton) {
  sopReviewCloseButton.addEventListener("click", closeSopReview);
}

if (sopReviewModal) {
  sopReviewModal.addEventListener("click", (event) => {
    if (event.target.matches("[data-close-sop-review]")) {
      closeSopReview();
    }
  });
}

if (websiteDemoCloseButton) {
  websiteDemoCloseButton.addEventListener("click", closeWebsiteDemo);
}

if (websiteDemoModal) {
  websiteDemoModal.addEventListener("click", (event) => {
    if (event.target.matches("[data-close-website-demo]")) {
      closeWebsiteDemo();
    }
  });
}

if (websiteDemoContent) {
  websiteDemoContent.addEventListener("click", (event) => {
    const promptButton = event.target.closest("[data-demo-prompt]");
    if (!promptButton || !input) {
      return;
    }
    input.value = promptButton.dataset.demoPrompt || "";
    closeWebsiteDemo();
    input.focus();
  });
}

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

documentList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete-document]");
  if (deleteButton) {
    deleteSubmissionDocument(deleteButton.dataset.deleteDocument);
    return;
  }

  const button = event.target.closest(".document-link");
  if (!button) {
    return;
  }

  openDocumentPreview({
    name: button.dataset.name,
    type: button.dataset.type,
    url: button.dataset.url
  });
});

documentList.addEventListener("change", (event) => {
  const checkbox = event.target.closest(".file-selection-checkbox");
  if (!checkbox) {
    return;
  }

  if (checkbox.checked) {
    selectedFiles.add(checkbox.value);
  } else {
    selectedFiles.delete(checkbox.value);
  }
  autoSelectEnabled = false;
  clearAgentSelectedSurfaces();
  updateSelectionMode("manual");
});

if (documentUploadButton && documentUploadInput) {
  documentUploadButton.addEventListener("click", () => {
    if (!selectedSubmission) {
      setDocumentUploadStatus("Select a submission before uploading.");
      return;
    }

    documentUploadInput.click();
  });

  documentUploadInput.addEventListener("change", async () => {
    const files = Array.from(documentUploadInput.files || []);
    if (!files.length) {
      return;
    }

    try {
      await uploadSubmissionDocuments(files);
    } catch (error) {
      console.warn(error);
      setDocumentUploadStatus(error.message || "Unable to upload files.");
    } finally {
      documentUploadInput.value = "";
    }
  });
}

if (refreshInsightsButton) {
  refreshInsightsButton.addEventListener("click", () => {
    refreshSubmissionInsights({ source: "timeline" });
  });
}

if (generateSummaryButton) {
  generateSummaryButton.addEventListener("click", () => {
    refreshSubmissionInsights({ source: "summary" });
  });
}

selectAllFilesButton.addEventListener("click", () => {
  autoSelectEnabled = false;
  clearAgentSelectedSurfaces();
  selectedFiles = new Set(getCurrentDocumentNames());
  syncFileSelectionControls();
  updateSelectionMode("all");
});

unselectAllFilesButton.addEventListener("click", () => {
  autoSelectEnabled = false;
  clearAgentSelectedSurfaces();
  selectedFiles.clear();
  syncFileSelectionControls();
  updateSelectionMode("none");
});

autoSelectFiles.addEventListener("click", async () => {
  setAutoDocumentMode({ clearHighlights: true });
});

messagesEl.addEventListener("click", async (event) => {
  const copyButton = event.target.closest("[data-copy-assistant-response]");
  if (!copyButton) {
    return;
  }

  const answer = copyButton.closest(".assistant-answer, .bubble");
  const text = answer ? answer.dataset.copyText || "" : "";
  if (!text) {
    return;
  }

  await copyTextToClipboard(text);
  const originalLabel = copyButton.textContent;
  copyButton.textContent = "Copied";
  copyButton.classList.add("copied");
  window.setTimeout(() => {
    copyButton.textContent = originalLabel || "Copy";
    copyButton.classList.remove("copied");
  }, 1400);
});

panelTabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activatePanelTab(button.dataset.panelTab);
  });
});

if (panelExpandRailButton) {
  panelExpandRailButton.addEventListener("click", () => {
    const isExpanded = workSurface && workSurface.classList.contains("insight-expanded");
    setInsightExpanded(!isExpanded);
  });
}

if (backToChatButton) {
  backToChatButton.addEventListener("click", () => {
    setInsightExpanded(false);
    input.focus();
  });
}

if (underwritingExpandButton) {
  underwritingExpandButton.addEventListener("click", () => {
    underwritingDetailsOpen = !underwritingDetailsOpen;
    setInsightExpanded(underwritingDetailsOpen);
    renderUnderwritingDetails();
  });
}

if (underwritingWorkbenchPanel) {
  underwritingWorkbenchPanel.addEventListener("click", (event) => {
    const updateEditButton = event.target.closest("[data-submission-update-edit]");
    if (updateEditButton) {
      enableSubmissionUpdateField(updateEditButton.dataset.submissionUpdateEdit);
      return;
    }

    const promptButton = event.target.closest("[data-agent-prompt]");
    if (promptButton) {
      input.value = promptButton.dataset.agentPrompt || "";
      input.focus();
    }
  });

  underwritingWorkbenchPanel.addEventListener("submit", async (event) => {
    if (!event.target.closest("#submissionUpdateForm")) {
      return;
    }

    event.preventDefault();
    await saveSubmissionUpdates();
  });
}

if (analyticsPanel) {
  analyticsPanel.addEventListener("click", (event) => {
    const supplementalButton = event.target.closest("[data-supplemental-model]");
    if (supplementalButton) {
      activeSupplementalModelKey = supplementalButton.dataset.supplementalModel || "cyber_attack_prob";
      updateSupplementalModelDetail();
      return;
    }

    const optionButton = event.target.closest("[data-what-if-option]");
    if (optionButton) {
      const key = optionButton.dataset.whatIfFeatureKey;
      getActiveWhatIfState().values[key] = Number(optionButton.dataset.whatIfValue);
      analyticsPanel.querySelectorAll(`[data-what-if-option][data-what-if-feature-key="${key}"]`).forEach((button) => {
        button.classList.toggle("active", button === optionButton);
      });
      updateWhatIfFeatureDisplay(key);
      updateWhatIfResult();
      return;
    }

    const button = event.target.closest("[data-analytics-subtab]");
    if (!button) {
      return;
    }

    setAnalyticsSubtab(button.dataset.analyticsSubtab);
  });

  analyticsPanel.addEventListener("input", (event) => {
    const field = event.target.closest("[data-what-if-feature]");
    if (!field) {
      return;
    }

    updateWhatIfFeatureValueFromField(field);
    updateWhatIfFeatureDisplay(field.dataset.whatIfFeature);
    updateWhatIfResult();
  });

  analyticsPanel.addEventListener("change", (event) => {
    const modelSelect = event.target.closest("[data-what-if-model-select]");
    if (modelSelect) {
      activeWhatIfModel = modelSelect.value === "bind" ? "bind" : "quote";
      updateWhatIfView();
      return;
    }

    const field = event.target.closest("[data-what-if-feature]");
    if (!field) {
      return;
    }

    updateWhatIfFeatureValueFromField(field);
    updateWhatIfFeatureDisplay(field.dataset.whatIfFeature);
    updateWhatIfResult();
  });

  analyticsPanel.addEventListener("mouseover", (event) => {
    const featureName = getFeatureNameTooltipTarget(event.target);
    if (!featureName || !analyticsPanel.contains(featureName)) {
      return;
    }

    if (featureName.contains(event.relatedTarget)) {
      return;
    }

    showFeatureTooltip(featureName, event);
  });

  analyticsPanel.addEventListener("mousemove", (event) => {
    if (activeFeatureTooltip) {
      positionFeatureTooltip(event);
    }
  });

  analyticsPanel.addEventListener("mouseout", (event) => {
    const featureName = getFeatureNameTooltipTarget(event.target);
    if (!featureName || featureName.contains(event.relatedTarget)) {
      return;
    }

    hideFeatureTooltip();
  });
}

if (guideForm) {
  guideForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!selectedSubmission) {
      renderGuideInstructions("Select a submission before adding guide instructions.");
      return;
    }

    const value = guideInput.value.trim();
    if (!value) {
      return;
    }

    const now = new Date().toISOString();
    guideItems.push({
      id: `guide-${Date.now()}`,
      text: value,
      created_at: now,
      updated_at: now
    });
    editingGuideIndex = null;
    guideInput.value = "";
    renderGuideInstructions();
    await saveGuideInstructions();
  });
}

if (guideList) {
  guideList.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-guide-action]");
    if (!button) {
      return;
    }

    const index = Number(button.dataset.guideIndex);
    if (!Number.isInteger(index)) {
      return;
    }

    if (button.dataset.guideAction === "delete") {
      guideItems.splice(index, 1);
      editingGuideIndex = null;
      renderGuideInstructions();
      await saveGuideInstructions();
      return;
    }

    if (button.dataset.guideAction === "edit") {
      editingGuideIndex = index;
      renderGuideInstructions();
      return;
    }

    if (button.dataset.guideAction === "cancel") {
      editingGuideIndex = null;
      renderGuideInstructions();
      return;
    }

    if (button.dataset.guideAction === "save") {
      const textarea = guideList.querySelector(`[data-guide-text="${index}"]`);
      const value = textarea ? textarea.value.trim() : "";

      if (!value) {
        guideItems.splice(index, 1);
      } else {
        guideItems[index] = {
          ...guideItems[index],
          text: value,
          updated_at: new Date().toISOString()
        };
      }

      editingGuideIndex = null;
      renderGuideInstructions();
      await saveGuideInstructions();
    }
  });
}

if (noteForm) {
  noteForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!selectedSubmission) {
      renderNoteContext("Select a submission before adding notes.");
      return;
    }

    const value = noteInput.value.trim();
    if (!value) {
      return;
    }

    const now = new Date().toISOString();
    noteItems.push({
      id: `note-${Date.now()}`,
      text: value,
      created_at: now,
      updated_at: now
    });
    editingNoteIndex = null;
    noteInput.value = "";
    renderNoteContext();
    await saveNotes();
  });
}

if (noteList) {
  noteList.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-note-action]");
    if (!button) {
      return;
    }

    const index = Number(button.dataset.noteIndex);
    if (!Number.isInteger(index)) {
      return;
    }

    if (button.dataset.noteAction === "delete") {
      noteItems.splice(index, 1);
      editingNoteIndex = null;
      renderNoteContext();
      await saveNotes();
      return;
    }

    if (button.dataset.noteAction === "edit") {
      editingNoteIndex = index;
      renderNoteContext();
      return;
    }

    if (button.dataset.noteAction === "cancel") {
      editingNoteIndex = null;
      renderNoteContext();
      return;
    }

    if (button.dataset.noteAction === "save") {
      const textarea = noteList.querySelector(`[data-note-text="${index}"]`);
      const value = textarea ? textarea.value.trim() : "";

      if (!value) {
        noteItems.splice(index, 1);
      } else {
        noteItems[index] = {
          ...noteItems[index],
          text: value,
          updated_at: new Date().toISOString()
        };
      }

      editingNoteIndex = null;
      renderNoteContext();
      await saveNotes();
    }
  });
}

if (followUpForm) {
  followUpForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!selectedSubmission) {
      renderFollowUps("Select a submission before adding tasks.");
      return;
    }

    const title = followUpTitle.value.trim();
    const dueDate = followUpDate.value;
    if (!title || !dueDate) {
      return;
    }
    if (!isTaskDateInRange(dueDate)) {
      renderFollowUps(`Task due date must be between ${TASK_CALENDAR_MIN_YEAR}-01-01 and ${TASK_CALENDAR_MAX_YEAR}-12-31.`);
      return;
    }

    const now = new Date().toISOString();
    followUpItems.push({
      id: `task-${Date.now()}`,
      title,
      due_date: dueDate,
      status: "open",
      created_at: now,
      updated_at: now
    });
    selectedTaskDate = dueDate;
    setTaskCalendarFromDate(dueDate, false);
    followUpTitle.value = "";
    followUpDate.value = "";
    renderFollowUps();
    await saveFollowUps();
  });
}

if (followUpList) {
  followUpList.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-follow-up-action]");
    if (!button) {
      return;
    }

    const itemId = button.dataset.followUpId;
    const index = followUpItems.findIndex((item) => item.id === itemId);
    if (index < 0) {
      return;
    }

    if (button.dataset.followUpAction === "delete") {
      followUpItems.splice(index, 1);
    }

    if (button.dataset.followUpAction === "toggle") {
      followUpItems[index] = {
        ...followUpItems[index],
        status: followUpItems[index].status === "done" ? "open" : "done",
        updated_at: new Date().toISOString()
      };
    }

    renderFollowUps();
    await saveFollowUps();
  });
}

if (followUpCalendar) {
  followUpCalendar.addEventListener("click", (event) => {
    const navButton = event.target.closest("[data-calendar-action]");
    if (navButton) {
      handleTaskCalendarAction(navButton.dataset.calendarAction);
      return;
    }

    const dayButton = event.target.closest("[data-task-date]");
    if (!dayButton) {
      return;
    }

    const date = dayButton.dataset.taskDate;
    selectedTaskDate = selectedTaskDate === date ? null : date;
    renderFollowUps();
  });

  followUpCalendar.addEventListener("change", (event) => {
    const monthSelect = event.target.closest("[data-calendar-month]");
    const yearSelect = event.target.closest("[data-calendar-year]");
    if (!monthSelect && !yearSelect) {
      return;
    }

    const month = monthSelect
      ? Number(monthSelect.value)
      : taskCalendarCursor.getMonth();
    const year = yearSelect
      ? Number(yearSelect.value)
      : taskCalendarCursor.getFullYear();
    setTaskCalendarMonth(year, month);
    renderFollowUps();
  });
}

if (stageChecklist) {
  stageChecklist.addEventListener("change", async (event) => {
    const checkbox = event.target.closest("[data-stage-key]");
    if (!checkbox) {
      return;
    }

    const stage = stageItems.find((item) => item.key === checkbox.dataset.stageKey);
    if (!stage) {
      return;
    }

    if (stage.locked) {
      checkbox.checked = true;
      renderStageChecklist("That stage has been submitted and locked.");
      return;
    }

    stage.checked = checkbox.checked;
    renderStageChecklist();
    await saveStageState();
  });
}

if (submitWorkflowButton) {
  submitWorkflowButton.addEventListener("click", async () => {
    if (!selectedSubmission || !hasUnlockedCheckedStages()) {
      return;
    }

    const proceed = window.confirm(
      "Submit checked underwriting stages? This permanently locks only the stages currently checked. Unchecked stages and scheduled tasks will remain editable."
    );
    if (!proceed) {
      return;
    }

    await submitWorkflow();
  });
}

documentCloseButton.addEventListener("click", closeDocumentPreview);
documentModal.addEventListener("click", (event) => {
  if (event.target.matches("[data-close-document]")) {
    closeDocumentPreview();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && documentModal.classList.contains("open")) {
    closeDocumentPreview();
  }

  if (event.key === "Escape" && guidePopover && guidePopover.classList.contains("open")) {
    closeGuidePopover();
  }

  if (event.key === "Escape" && sopReviewModal && sopReviewModal.classList.contains("open")) {
    closeSopReview();
  }

  if (event.key === "Escape") {
    closeWorkspaceMenu();
  }
});

document.addEventListener("click", (event) => {
  if (!workspaceMenu || !workspaceMenuButton) {
    return;
  }
  if (!workspaceMenu.hidden && !workspaceMenu.contains(event.target) && !workspaceMenuButton.contains(event.target)) {
    closeWorkspaceMenu();
  }
});

function resetChat() {
  messages.length = 0;
  currentChatHistoryId = null;
  messagesEl.innerHTML = "";
  setAutoDocumentMode({ clearHighlights: true });
  addMessage(
    "assistant",
    selectedSubmission
      ? `Chat cleared. ${selectedSubmission.title} is still selected.`
      : "Chat cleared. Choose a submission from the left or paste details below."
  );
  input.focus();
}

function buildTemporaryModelMessagesWithSelectedFiles(visibleMessages) {
  return visibleMessages.map((message) => ({ ...message }));
}

function toggleWorkspaceMenu() {
  if (!workspaceMenu || !workspaceMenuButton) {
    return;
  }
  const nextOpen = workspaceMenu.hidden;
  workspaceMenu.toggleAttribute("hidden", !nextOpen);
  workspaceMenuButton.setAttribute("aria-expanded", nextOpen ? "true" : "false");
  workspaceMenuButton.classList.toggle("active", nextOpen);
}

function closeWorkspaceMenu() {
  if (!workspaceMenu || !workspaceMenuButton) {
    return;
  }
  workspaceMenu.setAttribute("hidden", "");
  workspaceMenuButton.setAttribute("aria-expanded", "false");
  workspaceMenuButton.classList.remove("active");
}

async function openSopReview() {
  if (!sopReviewModal || !sopReviewContent) {
    return;
  }

  sopReviewModal.classList.add("open");
  sopReviewModal.setAttribute("aria-hidden", "false");
  sopReviewContent.innerHTML = '<p class="empty-state">Loading SOP...</p>';

  try {
    if (!sopReviewRecord) {
      sopReviewRecord = await AUApi.get("/api/sop");
    }
    renderSopReview(sopReviewRecord);
  } catch (error) {
    console.warn(error);
    sopReviewContent.innerHTML = `<p class="document-error">${escapeHtml(error.message || "Unable to load SOP.")}</p>`;
  }
}

function closeSopReview() {
  if (!sopReviewModal) {
    return;
  }
  sopReviewModal.classList.remove("open");
  sopReviewModal.setAttribute("aria-hidden", "true");
}

function openWebsiteDemo() {
  if (!websiteDemoModal || !websiteDemoContent) {
    return;
  }

  websiteDemoModal.classList.add("open");
  websiteDemoModal.setAttribute("aria-hidden", "false");
  websiteDemoContent.innerHTML = renderWebsiteDemoContent();
}

function closeWebsiteDemo() {
  if (!websiteDemoModal) {
    return;
  }
  websiteDemoModal.classList.remove("open");
  websiteDemoModal.setAttribute("aria-hidden", "true");
}

function renderWebsiteDemoContent() {
  return `
    <section class="website-demo-hero">
      <div>
        <span>Demo Goal</span>
        <strong>Agentic cyber underwriting workspace</strong>
        <p>Use this local app to search submissions, review evidence, chat with an information agent, inspect analytics, and manage underwriting workflow tasks.</p>
      </div>
      <div>
        <span>Data Backbone</span>
        <strong>Files + JSON + SQLite</strong>
        <p>The SQLite analytics mart keeps submission and claim rows in separate tables, then joins them by company ID for portfolio-level questions.</p>
      </div>
    </section>
    <section class="website-demo-section">
      <h3>How To Use The Demo</h3>
      <ol>
        <li><strong>Search a submission:</strong> use the search page to open an account or preview the portfolio queue.</li>
        <li><strong>Review documents:</strong> select files manually or use Auto so the information agent picks relevant evidence.</li>
        <li><strong>Ask underwriting questions:</strong> ask about missing evidence, claims, broker quality, rating, quote readiness, tasks, SOP, or portfolio statistics.</li>
        <li><strong>Open Details:</strong> expand the underwriting system for account signals, broker data, claims, clearance, rating, and research checks.</li>
        <li><strong>Open Analytics:</strong> inspect quote/bind models, What If scenarios, portfolio metrics, and model interpretations.</li>
        <li><strong>Use Tasks and Notes:</strong> save underwriter notes, schedule tasks, and lock completed underwriting stages.</li>
      </ol>
    </section>
    <section class="website-demo-section">
      <h3>Example Chat Prompts</h3>
      <div class="website-demo-prompt-grid">
        ${[
          "Show claim statistics for this broker and associated underwriting decisions.",
          "Which companies have the highest incurred losses and are they referrals?",
          "Compare average quote readiness by broker.",
          "What documents are missing for this submission?",
          "Draft broker follow-up questions based on SOP and evidence gaps.",
          "Show the rating calculation and explain the premium range."
        ].map((prompt) => `<button class="website-demo-prompt" type="button" data-demo-prompt="${escapeHtml(prompt)}">${escapeHtml(prompt)}</button>`).join("")}
      </div>
    </section>
    <section class="website-demo-section">
      <h3>Analytics DB</h3>
      <p><strong>Tables:</strong> underwriting_submission_analytics + claim_analytics</p>
      <p><strong>Join key:</strong> company_id · <strong>Claim key:</strong> CLM_CLMT_ID</p>
      <p><strong>Path:</strong> data/analytics/underwriting_claim_analytics.db</p>
      <p>It is refreshed when submissions, documents, or editable metadata change, and it is used by the chat retrieval layer for claim and underwriting decision statistics.</p>
    </section>
  `;
}

function renderSopReview(record) {
  if (!sopReviewContent) {
    return;
  }

  const sop = record && record.sop ? record.sop : {};
  const metadata = record && record.metadata ? record.metadata : {};
  const principles = Array.isArray(sop.principles) ? sop.principles : [];
  const steps = Array.isArray(sop.steps) ? sop.steps : [];
  const metadataSteps = Array.isArray(metadata.steps) ? metadata.steps : [];
  const defaultStepIds = metadata.selection_rules && Array.isArray(metadata.selection_rules.default_step_ids)
    ? metadata.selection_rules.default_step_ids
    : [];

  sopReviewContent.innerHTML = `
    <section class="sop-review-summary">
      <div>
        <span>Name</span>
        <strong>${escapeHtml(sop.name || "Commercial Cyber Underwriting SOP")}</strong>
      </div>
      <div>
        <span>Version</span>
        <strong>${escapeHtml(sop.version || "TBD")}</strong>
      </div>
      <div>
        <span>Updated</span>
        <strong>${escapeHtml(formatDateOnly(sop.updated_at || metadata.updated_at))}</strong>
      </div>
    </section>
    <section class="sop-review-section">
      <h3>Principles</h3>
      ${principles.length ? `<ul>${principles.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : '<p class="empty-state">No principles listed.</p>'}
    </section>
    <section class="sop-review-section">
      <h3>Procedure Steps</h3>
      <div class="sop-review-step-list">
        ${steps.map((step) => renderSopReviewStep(step)).join("") || '<p class="empty-state">No SOP steps listed.</p>'}
      </div>
    </section>
    <section class="sop-review-section">
      <h3>Agent Selection Metadata</h3>
      <p>Default steps: ${escapeHtml(defaultStepIds.join(", ") || "None")}</p>
      <div class="sop-metadata-grid">
        ${metadataSteps.map((step) => renderSopMetadataStep(step)).join("") || '<p class="empty-state">No metadata listed.</p>'}
      </div>
    </section>
  `;
}

function renderSopReviewStep(step) {
  return `
    <article class="sop-review-step ${escapeHtml(statusClass(step.priority))}">
      <div>
        <span>${escapeHtml(step.priority || "medium")} priority</span>
        <strong>${escapeHtml(step.label || step.step_id || "SOP Step")}</strong>
      </div>
      <p>${escapeHtml(step.goal || "")}</p>
      <small>${escapeHtml(step.suggestion_template || "")}</small>
    </article>
  `;
}

function renderSopMetadataStep(step) {
  const keywords = Array.isArray(step.keywords) ? step.keywords.slice(0, 8).join(", ") : "";
  const relatedData = Array.isArray(step.related_data) ? step.related_data.join(", ") : "";
  return `
    <article class="sop-metadata-item">
      <strong>${escapeHtml(step.label || step.step_id || "SOP Metadata")}</strong>
      <span>${escapeHtml(keywords || "No keywords")}</span>
      <small>${escapeHtml(relatedData || "No related data listed")}</small>
    </article>
  `;
}

function buildUnderwritingSystemPromptContext() {
  if (!underwritingSystem) {
    return "";
  }

  const appetite = underwritingSystem.appetite || {};
  const claimSnapshot = underwritingSystem.claim_snapshot || {};
  const actions = Array.isArray(underwritingSystem.recommended_actions)
    ? underwritingSystem.recommended_actions
    : [];
  const signals = Array.isArray(underwritingSystem.signals)
    ? underwritingSystem.signals
    : [];
  const sopGuidance = underwritingSystem.sop_guidance || {};
  const sopSuggestions = Array.isArray(sopGuidance.suggestions) ? sopGuidance.suggestions : [];
  const broker = underwritingSystem.broker || {};
  const contact = broker.submission_contact || {};

  return [
    `SOP: ${sopGuidance.name || "Commercial Cyber Underwriting SOP"} ${sopGuidance.version || ""}`,
    `Appetite Status: ${appetite.status || "TBD"}`,
    `Appetite Rationale: ${appetite.rationale || "TBD"}`,
    `Broker: ${broker.firm_name || contact.firm_name || "TBD"}; Producer: ${contact.producer_name || "TBD"}; Service Tier: ${broker.service_tier || "TBD"}`,
    `Claims: ${claimSnapshot.total_claims || 0} total, ${claimSnapshot.open_claims || 0} open, ${formatCurrency(Number(claimSnapshot.total_incurred || 0))} incurred`,
    "SOP Suggestions:",
    ...sopSuggestions.map((suggestion) => `- ${suggestion.step_label}: ${suggestion.recommendation}`),
    "Signals:",
    ...signals.map((signal) => `- ${signal.label}: ${signal.severity} - ${signal.detail}`),
    "Recommended Actions:",
    ...actions.map((action) => `- ${action}`)
  ].join("\n");
}

async function uploadSubmissionDocuments(files) {
  const validFiles = files.filter((file) => {
    const extension = String(file.name || "").split(".").pop().toLowerCase();
    return ["txt", "pdf"].includes(extension);
  });
  const invalidCount = files.length - validFiles.length;

  if (!validFiles.length) {
    setDocumentUploadStatus("Only .txt and .pdf files are supported.");
    return;
  }

  const uploadedNames = [];
  let failedCount = 0;
  for (const [index, file] of validFiles.entries()) {
    setDocumentUploadStatus(`Uploading ${index + 1}/${validFiles.length}: ${file.name}`);
    try {
      const uploadedDocument = await uploadSubmissionDocument(file, { skipRefreshPrompt: true });
      if (uploadedDocument && uploadedDocument.file_name) {
        uploadedNames.push(uploadedDocument.file_name);
      }
    } catch (error) {
      console.warn(error);
      failedCount += 1;
    }
  }

  const skippedText = invalidCount ? ` ${invalidCount} unsupported file${invalidCount === 1 ? "" : "s"} skipped.` : "";
  const failedText = failedCount ? ` ${failedCount} file${failedCount === 1 ? "" : "s"} failed.` : "";
  setDocumentUploadStatus(
    uploadedNames.length === 1
      ? `Uploaded ${uploadedNames[0]}.${skippedText}${failedText}`
      : `Uploaded ${uploadedNames.length} files.${skippedText}${failedText}`
  );
  if (uploadedNames.length) {
    await refreshAfterSubmissionFilesChanged(
      uploadedNames.length === 1
        ? `${uploadedNames[0]} uploaded. Summary, assessment, and model inputs refreshed.`
        : `${uploadedNames.length} files uploaded. Summary, assessment, and model inputs refreshed.`
    );
  }
}

async function uploadSubmissionDocument(file, options = {}) {
  if (!selectedSubmission) {
    return null;
  }

  const extension = file.name.split(".").pop().toLowerCase();
  if (!["txt", "pdf"].includes(extension)) {
    setDocumentUploadStatus("Only .txt and .pdf files are supported.");
    return null;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(selectedSubmission.id)}/files`, {
      method: "POST",
      body: formData
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to upload file.");
    }

    const uploadedDocument = data.upload && data.upload.document;
    const updatedSubmission = data.upload && data.upload.submission;
    if (updatedSubmission) {
      applyUpdatedSubmissionRecord(updatedSubmission);
    }
    if (uploadedDocument && uploadedDocument.file_name) {
      reconcileSelectionAfterFileChange({ addedFileName: uploadedDocument.file_name });
    }

    if (!options.skipRefreshPrompt) {
      setDocumentUploadStatus(uploadedDocument ? `Uploaded ${uploadedDocument.file_name}` : "Uploaded.");
      await refreshAfterSubmissionFilesChanged(
        uploadedDocument
          ? `${uploadedDocument.file_name} uploaded. Summary, assessment, and model inputs refreshed.`
          : "File uploaded. Summary, assessment, and model inputs refreshed."
      );
    }
    return uploadedDocument || null;
  } catch (error) {
    console.warn(error);
    setDocumentUploadStatus(error.message || "Unable to upload file.");
    throw error;
  }
}

async function deleteSubmissionDocument(fileName) {
  if (!selectedSubmission || !fileName) {
    return;
  }

  const shouldDelete = window.confirm(
    `Delete ${fileName}? This removes the file and its metadata from this submission.`
  );
  if (!shouldDelete) {
    return;
  }

  setDocumentUploadStatus("Deleting...");
  try {
    const response = await fetch(
      `/api/submissions/${encodeURIComponent(selectedSubmission.id)}/files/${encodeURIComponent(fileName)}`,
      {
        method: "DELETE"
      }
    );
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to delete file.");
    }

    const updatedSubmission = data.delete && data.delete.submission;
    if (updatedSubmission) {
      selectedFiles.delete(fileName);
      applyUpdatedSubmissionRecord(updatedSubmission);
      reconcileSelectionAfterFileChange();
    }

    await refreshAfterSubmissionFilesChanged(
      `${fileName} deleted. Summary, assessment, and model inputs refreshed.`
    );
  } catch (error) {
    console.warn(error);
    setDocumentUploadStatus(error.message || "Unable to delete file.");
  }
}

async function refreshAfterSubmissionFilesChanged(successMessage) {
  if (!selectedSubmission) {
    return;
  }

  setDocumentUploadStatus("Refreshing summary, assessment, and model inputs...");
  await refreshSubmissionInsights({ silent: true });
  await refreshDerivedWorkspaceData();
  setDocumentUploadStatus(successMessage || "Submission summary, assessment, and model inputs refreshed.");
}

async function refreshDerivedWorkspaceData() {
  if (!selectedSubmission) {
    return;
  }

  const submissionId = selectedSubmission.id;
  await Promise.all([
    loadUnderwritingSystem(submissionId),
    loadDecisionWorkflow(submissionId),
    loadClearanceReview(submissionId),
    loadExternalResearch(submissionId),
    loadRatingQuote(submissionId),
    loadPortfolioDashboard()
  ]);

  analyticsPanel.innerHTML = buildAnalyticsPanel(selectedSubmission.record);
  renderUnderwritingDetails();
}

async function refreshSubmissionInsights(options = {}) {
  if (!selectedSubmission) {
    setDocumentUploadStatus("Select a submission before refreshing.");
    return;
  }

  const silent = Boolean(options.silent);
  const activeButton = options.source === "summary" ? generateSummaryButton : refreshInsightsButton;
  const originalLabel = activeButton ? activeButton.textContent.trim() : "";

  if (!silent && activeButton) {
    activeButton.disabled = true;
    activeButton.textContent = options.source === "summary" ? "Generating..." : "Refreshing...";
  }
  if (!silent) {
    setDocumentUploadStatus(
      options.source === "summary"
        ? "Generating submission summary..."
        : "Refreshing summary and timeline..."
    );
  }

  try {
    const response = await fetch(
      `/api/submissions/${encodeURIComponent(selectedSubmission.id)}/insights/refresh`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({})
      }
    );
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to refresh summary and timeline.");
    }

    const updatedSubmission = data.refresh && data.refresh.submission;
    if (updatedSubmission) {
      applyUpdatedSubmissionRecord(updatedSubmission);
    }
    if (!silent) {
      setDocumentUploadStatus(
        options.source === "summary"
          ? "Submission summary regenerated."
          : "Summary and timeline refreshed."
      );
      await refreshDerivedWorkspaceData();
    }
  } catch (error) {
    console.warn(error);
    if (!silent) {
      setDocumentUploadStatus(error.message || "Unable to refresh summary and timeline.");
    }
  } finally {
    if (!silent && activeButton) {
      activeButton.disabled = false;
      activeButton.textContent = originalLabel || (options.source === "summary" ? "Generate" : "Refresh");
    }
  }
}

function applyUpdatedSubmissionRecord(updatedSubmission) {
  if (!selectedSubmission || !updatedSubmission) {
    return;
  }

  selectedSubmission = {
    ...selectedSubmission,
    record: updatedSubmission,
    content: formatSubmissionForPrompt(updatedSubmission)
  };

  summaryPlaceholder.innerHTML = buildSummaryHtml(updatedSubmission);
  renderSubmissionUpdateForm(updatedSubmission);
  timelineList.innerHTML = buildTimelineItems(updatedSubmission);
  documentList.innerHTML = buildDocumentLinks(updatedSubmission);
  keyInfoList.innerHTML = buildKeyInfoHtml(selectedSubmission);
  analyticsPanel.innerHTML = buildAnalyticsPanel(updatedSubmission);
  renderUnderwritingDetails();
  selectedFiles = new Set(
    Array.from(selectedFiles).filter((fileName) => getCurrentDocumentNames().includes(fileName))
  );
}

function renderSubmissionUpdateForm(record) {
  const container = document.querySelector("#submissionUpdateEditorContainer");
  if (!container || !record) {
    return;
  }

  container.innerHTML = renderSubmissionUpdateEditorContent(record);
}

function renderSubmissionUpdateEditor(record) {
  return `
    <section class="uw-panel submission-update-panel" id="submissionUpdateEditorContainer">
      ${renderSubmissionUpdateEditorContent(record)}
    </section>
  `;
}

function renderSubmissionUpdateEditorContent(record) {
  const fields = getSubmissionUpdateFields(record);

  return `
    <div class="card-heading">
      <div>
        <h4>Submission Update</h4>
        <p class="uw-section-note">Edit metadata cells used by the underwriting system, then submit all changes together.</p>
      </div>
      <span class="form-status" id="submissionUpdateStatus"></span>
    </div>
    <form class="submission-update-form uw-submission-update-form" id="submissionUpdateForm">
      ${fields.map(renderSubmissionUpdateField).join("")}
      <div class="submission-update-submit-row">
        <span>${submissionUpdateEditingFields.size ? `${submissionUpdateEditingFields.size} field${submissionUpdateEditingFields.size === 1 ? "" : "s"} unlocked` : "Choose Edit beside any value before submitting."}</span>
        <button class="selection-action" id="submissionUpdateSaveButton" type="submit">Submit Changes</button>
      </div>
    </form>
  `;
}

function getSubmissionUpdateFields(record) {
  const applicant = record.applicant || {};

  return [
    {
      key: "status",
      label: "Status",
      type: "select",
      value: record.status || "New",
      options: ["New", "In Review", "Referral Needed", "Quoted", "Bound", "Declined"]
    },
    {
      key: "industry",
      label: "Industry",
      type: "text",
      value: applicant.industry || ""
    },
    {
      key: "industry_bucket",
      label: "Industry Bucket",
      type: "select",
      value: applicant.industry_bucket || applicant.industry_group || "Professional Services",
      options: [
        "Construction",
        "Education",
        "Fintech / Payments",
        "Food Distribution / Logistics",
        "Healthcare / Pharmacy",
        "Hospitality / Retail",
        "Manufacturing / OT",
        "Marina / Recreation",
        "Professional Services",
        "SaaS / Software"
      ]
    },
    {
      key: "annual_revenue",
      label: "Revenue",
      type: "number",
      value: applicant.annual_revenue || "",
      min: 0,
      step: 10000
    },
    {
      key: "records_count",
      label: "Records",
      type: "number",
      value: applicant.records_count || "",
      min: 0,
      step: 1000
    },
    {
      key: "employee_count",
      label: "Employees",
      type: "number",
      value: applicant.employee_count || "",
      min: 0,
      step: 1
    },
    {
      key: "technology_profile",
      label: "Technology Profile",
      type: "textarea",
      value: applicant.technology_profile || "",
      rows: 2,
      wide: true
    },
    {
      key: "risk_flags",
      label: "Risk Flags",
      type: "textarea",
      value: Array.isArray(record.risk_flags) ? record.risk_flags.join("\n") : "",
      rows: 3,
      placeholder: "One risk flag per line",
      wide: true
    },
    {
      key: "open_questions",
      label: "Open Questions",
      type: "textarea",
      value: Array.isArray(record.open_questions) ? record.open_questions.join("\n") : "",
      rows: 3,
      placeholder: "One open question per line",
      wide: true
    }
  ];
}

function renderSubmissionUpdateField(field) {
  const isEditing = submissionUpdateEditingFields.has(field.key);
  const disabledAttribute = isEditing ? "" : " disabled";
  const editLabel = isEditing ? "Editing" : "Edit";
  const inputId = `submissionUpdate_${field.key}`;

  return `
    <label class="submission-update-field ${field.wide ? "wide-field" : ""} ${isEditing ? "editing" : ""}" data-submission-update-field="${escapeHtml(field.key)}">
      <span>${escapeHtml(field.label)}</span>
      <div class="submission-update-control-row">
        ${renderSubmissionUpdateControl(field, inputId, disabledAttribute)}
        <button class="cell-edit-button" type="button" data-submission-update-edit="${escapeHtml(field.key)}"${isEditing ? " disabled" : ""}>${editLabel}</button>
      </div>
    </label>
  `;
}

function renderSubmissionUpdateControl(field, inputId, disabledAttribute) {
  const common = `id="${escapeHtml(inputId)}" data-submission-update-control="${escapeHtml(field.key)}"${disabledAttribute}`;

  if (field.type === "select") {
    const options = Array.from(new Set([...(field.options || []), field.value].filter(Boolean)));
    return `
      <select ${common}>
        ${options.map((option) => `<option value="${escapeHtml(option)}"${String(option) === String(field.value) ? " selected" : ""}>${escapeHtml(option)}</option>`).join("")}
      </select>
    `;
  }

  if (field.type === "textarea") {
    return `
      <textarea ${common} rows="${escapeHtml(field.rows || 2)}" placeholder="${escapeHtml(field.placeholder || "")}">${escapeHtml(field.value)}</textarea>
    `;
  }

  const minAttribute = field.min == null ? "" : ` min="${escapeHtml(field.min)}"`;
  const stepAttribute = field.step == null ? "" : ` step="${escapeHtml(field.step)}"`;
  return `<input ${common} type="${escapeHtml(field.type || "text")}" value="${escapeHtml(field.value)}"${minAttribute}${stepAttribute} />`;
}

function enableSubmissionUpdateField(fieldKey) {
  if (!fieldKey) {
    return;
  }

  submissionUpdateEditingFields.add(fieldKey);
  const field = Array.from(document.querySelectorAll("[data-submission-update-field]"))
    .find((item) => item.dataset.submissionUpdateField === fieldKey);
  const control = field ? field.querySelector("[data-submission-update-control]") : null;
  const editButton = field ? field.querySelector("[data-submission-update-edit]") : null;

  if (field) {
    field.classList.add("editing");
  }
  if (control) {
    control.disabled = false;
    control.focus();
  }
  if (editButton) {
    editButton.textContent = "Editing";
    editButton.disabled = true;
  }
  refreshSubmissionUpdateEditCount();
}

function refreshSubmissionUpdateEditCount() {
  const row = document.querySelector(".submission-update-submit-row span");
  if (!row) {
    return;
  }

  row.textContent = submissionUpdateEditingFields.size
    ? `${submissionUpdateEditingFields.size} field${submissionUpdateEditingFields.size === 1 ? "" : "s"} unlocked`
    : "Choose Edit beside any value before submitting.";
}

function getSubmissionUpdateElements() {
  return {
    form: document.querySelector("#submissionUpdateForm"),
    status: document.querySelector("#submissionUpdateStatus"),
    saveButton: document.querySelector("#submissionUpdateSaveButton"),
    statusInput: document.querySelector("#submissionUpdate_status"),
    industryInput: document.querySelector("#submissionUpdate_industry"),
    industryBucketInput: document.querySelector("#submissionUpdate_industry_bucket"),
    revenueInput: document.querySelector("#submissionUpdate_annual_revenue"),
    recordsInput: document.querySelector("#submissionUpdate_records_count"),
    employeesInput: document.querySelector("#submissionUpdate_employee_count"),
    technologyInput: document.querySelector("#submissionUpdate_technology_profile"),
    riskFlagsInput: document.querySelector("#submissionUpdate_risk_flags"),
    openQuestionsInput: document.querySelector("#submissionUpdate_open_questions")
  };
}

async function saveSubmissionUpdates() {
  if (!selectedSubmission) {
    setSubmissionUpdateStatus("Select a submission first.", true);
    return;
  }

  const elements = getSubmissionUpdateElements();
  if (!elements.form) {
    return;
  }

  if (!submissionUpdateEditingFields.size) {
    setSubmissionUpdateStatus("Choose Edit on at least one value before submitting.", true);
    return;
  }

  if (elements.saveButton) {
    elements.saveButton.disabled = true;
  }
  setSubmissionUpdateStatus("Saving...");

  const payload = {
    status: elements.statusInput ? elements.statusInput.value : "",
    applicant: {
      industry: elements.industryInput ? elements.industryInput.value : "",
      industry_bucket: elements.industryBucketInput ? elements.industryBucketInput.value : "",
      industry_group: elements.industryBucketInput ? elements.industryBucketInput.value : "",
      annual_revenue: elements.revenueInput ? elements.revenueInput.value : "",
      records_count: elements.recordsInput ? elements.recordsInput.value : "",
      employee_count: elements.employeesInput ? elements.employeesInput.value : "",
      technology_profile: elements.technologyInput ? elements.technologyInput.value : ""
    },
    risk_flags: splitTextareaLines(elements.riskFlagsInput ? elements.riskFlagsInput.value : ""),
    open_questions: splitTextareaLines(elements.openQuestionsInput ? elements.openQuestionsInput.value : "")
  };

  try {
    const response = await fetch(
      `/api/submissions/${encodeURIComponent(selectedSubmission.id)}/metadata-cells`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      }
    );
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to save submission updates.");
    }

    if (data.submission) {
      submissionUpdateEditingFields = new Set();
      await Promise.all([
        loadUnderwritingSystem(selectedSubmission.id),
        loadDecisionWorkflow(selectedSubmission.id),
        loadClearanceReview(selectedSubmission.id),
        loadExternalResearch(selectedSubmission.id),
        loadRatingQuote(selectedSubmission.id),
        loadPortfolioDashboard()
      ]);
      applyUpdatedSubmissionRecord(data.submission);
    }
    setSubmissionUpdateStatus("Saved.");
  } catch (error) {
    console.warn(error);
    setSubmissionUpdateStatus(error.message || "Unable to save.", true);
  } finally {
    const latestElements = getSubmissionUpdateElements();
    if (latestElements.saveButton) {
      latestElements.saveButton.disabled = false;
    }
  }
}

function splitTextareaLines(value) {
  return String(value || "")
    .split(/\n|;/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function setSubmissionUpdateStatus(message, isError = false) {
  const status = document.querySelector("#submissionUpdateStatus");
  if (!status) {
    return;
  }
  status.textContent = message || "";
  status.classList.toggle("error", Boolean(isError));
}

function setInsightExpanded(expanded) {
  if (!workSurface || !panelExpandRailButton) {
    return;
  }

  const shouldExpand = Boolean(expanded);
  const activeTab = getActivePanelTab();
  const wasUnderwritingOpen = underwritingDetailsOpen;

  if (shouldExpand && activeTab === "details") {
    underwritingDetailsOpen = true;
  }

  if (!shouldExpand && underwritingDetailsOpen) {
    underwritingDetailsOpen = false;
  }

  workSurface.classList.toggle("insight-expanded", shouldExpand);
  workSurface.classList.toggle("details-expanded", shouldExpand && activeTab === "details");
  workSurface.classList.toggle("analytics-expanded", shouldExpand && activeTab === "analytics");
  workSurface.classList.toggle("tasks-expanded", shouldExpand && activeTab === "tasks");
  panelExpandRailButton.innerHTML = shouldExpand ? "&raquo;" : "&laquo;";
  panelExpandRailButton.setAttribute("aria-label", shouldExpand ? "Shrink expanded panel" : "Expand right panel");
  updateExpandedPageHeader();

  if (activeTab === "details" || wasUnderwritingOpen !== underwritingDetailsOpen) {
    renderUnderwritingDetails();
  }
}

function activatePanelTab(tabName, options = {}) {
  const targetName = tabName || "details";
  const targetButton = Array.from(panelTabButtons).find((button) => button.dataset.panelTab === targetName);
  if (!targetButton) {
    return;
  }

  panelTabButtons.forEach((button) => {
    button.classList.toggle("active", button === targetButton);
  });

  panelViews.forEach((view) => {
    view.classList.toggle("active", view.dataset.panelView === targetName);
  });

  if (!["analytics", "details", "tasks"].includes(targetName)) {
    setInsightExpanded(false);
    return;
  }

  if (options.expand) {
    setInsightExpanded(true);
    return;
  }

  updateExpandedPageHeader();
}

function setAnalyticsSubtab(tabName) {
  if (!analyticsPanel) {
    return;
  }

  const targetName = tabName || "quote";
  analyticsPanel.querySelectorAll("[data-analytics-subtab]").forEach((tabButton) => {
    tabButton.classList.toggle("active", tabButton.dataset.analyticsSubtab === targetName);
  });
  analyticsPanel.querySelectorAll("[data-analytics-view]").forEach((view) => {
    view.classList.toggle("active", view.dataset.analyticsView === targetName);
  });
  if (targetName === "what-if") {
    updateWhatIfView();
  }
}

function getActivePanelTab() {
  const activeButton = Array.from(panelTabButtons).find((button) => button.classList.contains("active"));
  return activeButton ? activeButton.dataset.panelTab : "details";
}

function updateExpandedPageHeader() {
  if (!workSurface || !expandedPageHeader || !expandedPageTitle) {
    return;
  }

  const activeTab = getActivePanelTab();
  const isExpanded = workSurface.classList.contains("insight-expanded");
  const title = activeTab === "analytics"
    ? "Analytics Dashboard"
    : activeTab === "tasks"
      ? "Task Calendar"
      : "Underwriting System";

  expandedPageTitle.textContent = title;
  expandedPageHeader.setAttribute("aria-hidden", isExpanded ? "false" : "true");
}

function setDocumentUploadStatus(message) {
  if (documentUploadStatus) {
    documentUploadStatus.textContent = message || "";
  }
}

function updateSelectionMode(mode) {
  fileSelectionMode = mode;
  selectAllFilesButton.classList.toggle("active", mode === "all");
  unselectAllFilesButton.classList.toggle("active", mode === "none");
  autoSelectFiles.classList.toggle("active", mode === "auto");
  autoSelectFiles.setAttribute("aria-pressed", mode === "auto" ? "true" : "false");
}

function setAutoDocumentMode(options = {}) {
  autoSelectEnabled = true;
  selectedFiles.clear();
  syncFileSelectionControls();
  updateSelectionMode("auto");

  if (options.clearHighlights) {
    clearAgentSelectedSurfaces();
  }
}

function getActiveGuideInstructions() {
  return guideItems
    .map((guide) => String(guide.text || "").trim())
    .filter(Boolean);
}

function getActiveUnderwriterNotes() {
  return noteItems
    .map((note) => String(note.text || "").trim())
    .filter(Boolean);
}

async function refreshAfterChatActions(actions) {
  if (!selectedSubmission || !Array.isArray(actions) || !actions.length) {
    return;
  }

  applyChatUiActions(actions);

  const actionTypes = new Set(actions.map((action) => action && action.type));
  const refreshes = [];
  if (actionTypes.has("guide")) {
    refreshes.push(loadGuideInstructions(selectedSubmission.id));
  }
  if (actionTypes.has("note")) {
    refreshes.push(loadNotes(selectedSubmission.id));
  }
  if (actionTypes.has("task")) {
    refreshes.push(loadFollowUps(selectedSubmission.id));
    refreshes.push(loadDecisionWorkflow(selectedSubmission.id));
  }
  const submissionUpdateAction = actions.find((action) => action && action.type === "submission_update" && action.record);
  if (submissionUpdateAction) {
    await Promise.all([
      loadUnderwritingSystem(selectedSubmission.id),
      loadDecisionWorkflow(selectedSubmission.id),
      loadClearanceReview(selectedSubmission.id),
      loadExternalResearch(selectedSubmission.id),
      loadRatingQuote(selectedSubmission.id),
      loadPortfolioDashboard()
    ]);
    applyUpdatedSubmissionRecord(submissionUpdateAction.record);
  }

  await Promise.all(refreshes);
  renderUnderwritingDetails();
}

function applyChatUiActions(actions) {
  actions.forEach((action) => {
    const uiAction = action && action.ui_action;
    if (!uiAction) {
      return;
    }

    if (uiAction.panel) {
      activatePanelTab(uiAction.panel, { expand: Boolean(uiAction.expand) });
    }

    if (uiAction.analytics_tab) {
      setAnalyticsSubtab(uiAction.analytics_tab);
    }
  });
}

function highlightAgentSelectedSurfaces(data) {
  const surfaces = new Set();
  const retrieval = data && data.retrieval ? data.retrieval : {};
  const plan = Array.isArray(retrieval.plan) ? retrieval.plan : [];
  const sources = Array.isArray(retrieval.sources) ? retrieval.sources : [];
  const actions = Array.isArray(data && data.actions) ? data.actions : [];

  plan.forEach((skill) => addAgentSurfacesForKey(surfaces, skill));
  sources.forEach((source) => addAgentSurfacesForKey(surfaces, source && source.skill));
  actions.forEach((action) => addAgentSurfacesForAction(surfaces, action));

  surfaces.delete("documents");
  surfaces.forEach((surface) => markAgentSurface(surface));
  highlightDocumentFiles(getSelectedDocumentNamesFromRetrieval(retrieval));
}

function applyCentralDocumentSelection(data) {
  if (fileSelectionMode !== "auto") {
    return;
  }

  const retrieval = data && data.retrieval ? data.retrieval : {};
  const selection = retrieval.selection || {};
  const documentSelection = selection.document_selection || {};
  const selected = Array.isArray(documentSelection.selected_files)
    ? documentSelection.selected_files
    : getDocumentSourceNames(retrieval.sources);

  selectedFiles = new Set(selected);
  syncFileSelectionControls();
  updateSelectionMode("auto");
}

function clearAgentSelectedSurfaces() {
  document.querySelectorAll(`.${AGENT_SELECTED_SURFACE_CLASS}`).forEach((element) => {
    element.classList.remove(AGENT_SELECTED_SURFACE_CLASS);
  });
  document.querySelectorAll(`.${AGENT_SELECTED_TAB_CLASS}`).forEach((element) => {
    element.classList.remove(AGENT_SELECTED_TAB_CLASS);
  });
}

function addAgentSurfacesForAction(surfaces, action) {
  const type = normalizeAgentSurfaceKey(action && action.type);
  (AGENT_ACTION_SURFACE_MAP[type] || []).forEach((surface) => surfaces.add(surface));

  const uiAction = action && action.ui_action ? action.ui_action : {};
  addAgentSurfacesForPanel(surfaces, uiAction.panel);
}

function addAgentSurfacesForKey(surfaces, value) {
  const key = normalizeAgentSurfaceKey(value);
  (AGENT_SKILL_SURFACE_MAP[key] || []).forEach((surface) => surfaces.add(surface));
}

function addAgentSurfacesForPanel(surfaces, panelName) {
  const panelKey = normalizeAgentSurfaceKey(panelName);
  (AGENT_PANEL_SURFACE_MAP[panelKey] || []).forEach((surface) => surfaces.add(surface));
}

function markAgentSurface(surfaceName) {
  const surface = normalizeAgentSurfaceKey(surfaceName);
  getAgentSurfaceTargets(surface).forEach((target) => {
    target.classList.add(AGENT_SELECTED_SURFACE_CLASS);
  });

  const tabName = AGENT_SURFACE_TAB_MAP[surface];
  if (tabName) {
    const tab = Array.from(panelTabButtons).find((button) => button.dataset.panelTab === tabName);
    if (tab) {
      tab.classList.add(AGENT_SELECTED_TAB_CLASS);
    }
  }
}

function getAgentSurfaceTargets(surface) {
  const selectorsBySurface = {
    analytics: ['[data-agent-surface="analytics"]'],
    documents: [],
    details_summary: ['[data-agent-surface="details-summary"]'],
    guide: ['[data-agent-surface="guide"]', "#guideToggleButton"],
    key_info: ['[data-agent-surface="key-info"]'],
    notes: ['[data-agent-surface="notes"]'],
    stages: ['[data-agent-surface="stages"]'],
    tasks: ['[data-agent-surface="tasks"]'],
    timeline: ['[data-agent-surface="timeline"]'],
    underwriting: ['[data-agent-surface="underwriting"]']
  };

  return (selectorsBySurface[surface] || [])
    .flatMap((selector) => Array.from(document.querySelectorAll(selector)));
}

function highlightDocumentFiles(fileNames) {
  const names = Array.isArray(fileNames) ? fileNames.filter(Boolean) : [];
  names.forEach((fileName) => {
    const row = getDocumentRowByFileName(fileName);
    if (row) {
      row.classList.add(AGENT_SELECTED_SURFACE_CLASS);
    }
  });
}

function getSelectedDocumentNamesFromRetrieval(retrieval) {
  const selection = retrieval && retrieval.selection ? retrieval.selection : {};
  const documentSelection = selection.document_selection || {};
  if (Array.isArray(documentSelection.selected_files)) {
    return documentSelection.selected_files;
  }

  return getDocumentSourceNames(retrieval && retrieval.sources);
}

function getDocumentSourceNames(sources) {
  if (!Array.isArray(sources)) {
    return [];
  }

  return sources
    .filter((source) => source && normalizeAgentSurfaceKey(source.skill) === "documents")
    .map((source) => String(source.source || "").split("/").pop())
    .filter(Boolean);
}

function getDocumentRowByFileName(fileName) {
  return Array.from(documentList.querySelectorAll(".document-link"))
    .find((button) => button.dataset.name === fileName)
    ?.closest(".document-row") || null;
}

function normalizeAgentSurfaceKey(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

async function loadGuideInstructions(submissionId) {
  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(submissionId)}/guides`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load guide.");
    }

    guideItems = normalizeGuideItems(data.guide && data.guide.guides);
    renderGuideInstructions();
  } catch (error) {
    console.warn(error);
    guideItems = [];
    renderGuideInstructions("Unable to load guide.");
  }
}

async function saveGuideInstructions() {
  if (!selectedSubmission) {
    return;
  }

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(selectedSubmission.id)}/guides`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ guides: guideItems })
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to save guide.");
    }

    guideItems = normalizeGuideItems(data.guide && data.guide.guides);
    renderGuideInstructions();
  } catch (error) {
    console.warn(error);
    renderGuideInstructions(error.message || "Unable to save guide.");
  }
}

function normalizeGuideItems(guides) {
  if (!Array.isArray(guides)) {
    return [];
  }

  return guides
    .map((guide, index) => {
      if (typeof guide === "string") {
        return {
          id: `guide-${Date.now()}-${index}`,
          text: guide,
          created_at: null,
          updated_at: null
        };
      }

      return {
        id: String(guide.id || `guide-${Date.now()}-${index}`),
        text: String(guide.text || ""),
        created_at: guide.created_at || null,
        updated_at: guide.updated_at || null
      };
    })
    .filter((guide) => guide.text.trim());
}

function renderGuideInstructions(statusMessage) {
  if (!guideList) {
    return;
  }

  if (statusMessage) {
    guideList.innerHTML = `<p class="empty-state">${escapeHtml(statusMessage)}</p>`;
    return;
  }

  if (!guideItems.length) {
    guideList.innerHTML = '<p class="empty-state">No guide instructions yet.</p>';
    return;
  }

  guideList.innerHTML = guideItems
    .map((guide, index) => renderGuideItem(guide, index))
    .join("");
}

function renderGuideItem(guide, index) {
  if (editingGuideIndex === index) {
    return `
      <div class="guide-item editing">
        <span class="guide-label">Guide ${index + 1}</span>
        <textarea data-guide-text="${index}" aria-label="Guide instruction">${escapeHtml(guide.text)}</textarea>
        <div class="guide-item-actions">
          <button class="selection-action" type="button" data-guide-action="save" data-guide-index="${index}">Save</button>
          <button class="selection-action muted-action" type="button" data-guide-action="cancel" data-guide-index="${index}">Cancel</button>
          <button class="icon-button small-icon-button" type="button" data-guide-action="delete" data-guide-index="${index}" aria-label="Delete guide">&times;</button>
        </div>
      </div>
    `;
  }

  return `
    <div class="guide-item">
      <span class="guide-label">Guide ${index + 1}</span>
      <p>${escapeHtml(guide.text)}</p>
      <div class="guide-item-actions">
        <button class="selection-action" type="button" data-guide-action="edit" data-guide-index="${index}">Edit</button>
        <button class="icon-button small-icon-button" type="button" data-guide-action="delete" data-guide-index="${index}" aria-label="Delete guide">&times;</button>
      </div>
    </div>
  `;
}

async function loadNotes(submissionId) {
  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(submissionId)}/notes`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load notes.");
    }

    noteItems = normalizeContextItems(data.note && data.note.notes, "note");
    renderNoteContext();
  } catch (error) {
    console.warn(error);
    noteItems = [];
    renderNoteContext("Unable to load notes.");
  }
}

async function saveNotes() {
  if (!selectedSubmission) {
    return;
  }

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(selectedSubmission.id)}/notes`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ notes: noteItems })
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to save notes.");
    }

    noteItems = normalizeContextItems(data.note && data.note.notes, "note");
    renderNoteContext();
  } catch (error) {
    console.warn(error);
    renderNoteContext(error.message || "Unable to save notes.");
  }
}

function normalizeContextItems(items, prefix) {
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .map((item, index) => {
      if (typeof item === "string") {
        return {
          id: `${prefix}-${Date.now()}-${index}`,
          text: item,
          created_at: null,
          updated_at: null
        };
      }

      return {
        id: String(item.id || `${prefix}-${Date.now()}-${index}`),
        text: String(item.text || ""),
        created_at: item.created_at || null,
        updated_at: item.updated_at || null
      };
    })
    .filter((item) => item.text.trim());
}

function renderNoteContext(statusMessage) {
  if (!noteList) {
    return;
  }

  if (statusMessage) {
    noteList.innerHTML = `<p class="empty-state">${escapeHtml(statusMessage)}</p>`;
    return;
  }

  if (!noteItems.length) {
    noteList.innerHTML = '<p class="empty-state">No underwriter notes yet.</p>';
    return;
  }

  noteList.innerHTML = noteItems
    .map((note, index) => renderNoteItem(note, index))
    .join("");
}

function renderNoteItem(note, index) {
  if (editingNoteIndex === index) {
    return `
      <div class="context-item editing">
        <span class="context-label">Note ${index + 1}</span>
        <textarea data-note-text="${index}" aria-label="Underwriter note">${escapeHtml(note.text)}</textarea>
        <div class="context-item-actions">
          <button class="selection-action" type="button" data-note-action="save" data-note-index="${index}">Save</button>
          <button class="selection-action muted-action" type="button" data-note-action="cancel" data-note-index="${index}">Cancel</button>
          <button class="icon-button small-icon-button" type="button" data-note-action="delete" data-note-index="${index}" aria-label="Delete note">&times;</button>
        </div>
      </div>
    `;
  }

  return `
    <div class="context-item">
      <span class="context-label">Note ${index + 1}</span>
      <p>${escapeHtml(note.text)}</p>
      <div class="context-item-actions">
        <button class="selection-action" type="button" data-note-action="edit" data-note-index="${index}">Edit</button>
        <button class="icon-button small-icon-button" type="button" data-note-action="delete" data-note-index="${index}" aria-label="Delete note">&times;</button>
      </div>
    </div>
  `;
}

async function loadFollowUps(submissionId) {
  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(submissionId)}/tasks`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load tasks.");
    }

    followUpItems = normalizeFollowUps(data.task && data.task.tasks);
    renderFollowUps();
  } catch (error) {
    console.warn(error);
    followUpItems = [];
    renderFollowUps("Unable to load tasks.");
  }
}

async function saveFollowUps() {
  if (!selectedSubmission) {
    return;
  }

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(selectedSubmission.id)}/tasks`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ tasks: followUpItems })
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to save tasks.");
    }

    followUpItems = normalizeFollowUps(data.task && data.task.tasks);
    renderFollowUps();
  } catch (error) {
    console.warn(error);
    renderFollowUps(error.message || "Unable to save tasks.");
  }
}

function normalizeFollowUps(items) {
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .map((item, index) => ({
      id: String(item.id || `task-${Date.now()}-${index}`),
      title: String(item.title || ""),
      due_date: String(item.due_date || ""),
      status: item.status === "done" ? "done" : "open",
      created_at: item.created_at || null,
      updated_at: item.updated_at || null
    }))
    .filter((item) => item.title.trim() && /^\d{4}-\d{2}-\d{2}$/.test(item.due_date));
}

function renderFollowUps(statusMessage) {
  updateFollowUpDots();
  renderFollowUpCalendar();
  syncWorkflowSubmitControls();

  if (!followUpList) {
    return;
  }

  if (statusMessage) {
    followUpList.innerHTML = `<p>${escapeHtml(statusMessage)}</p>`;
    return;
  }

  const visibleItems = getVisibleFollowUpItems();
  if (!visibleItems.length) {
    followUpList.innerHTML = selectedTaskDate
      ? `<p>No scheduled tasks for ${escapeHtml(formatDateOnly(selectedTaskDate))}.</p>`
      : "<p>No scheduled tasks.</p>";
    return;
  }

  followUpList.innerHTML = `
    <div class="task-list-heading">
      ${selectedTaskDate ? `Tasks for ${escapeHtml(formatDateOnly(selectedTaskDate))}` : "All Scheduled Tasks"}
    </div>
    ${visibleItems
    .map((item) => {
      const dueState = getFollowUpDueState(item);
      return `
        <div class="follow-up-item ${item.status === "done" ? "done" : ""} ${dueState}">
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(formatDateOnly(item.due_date))}</small>
          </div>
          <div class="follow-up-actions">
            <button class="selection-action" type="button" data-follow-up-action="toggle" data-follow-up-id="${escapeHtml(item.id)}">
              ${item.status === "done" ? "Reopen" : "Done"}
            </button>
            <button class="icon-button small-icon-button" type="button" data-follow-up-action="delete" data-follow-up-id="${escapeHtml(item.id)}" aria-label="Delete task">&times;</button>
          </div>
        </div>
      `;
    })
    .join("")}
  `;
}

function getVisibleFollowUpItems() {
  if (!selectedTaskDate) {
    return followUpItems;
  }

  return followUpItems.filter((item) => item.due_date === selectedTaskDate);
}

function handleTaskCalendarAction(action) {
  if (action === "previous") {
    shiftTaskCalendarMonth(-1);
  } else if (action === "next") {
    shiftTaskCalendarMonth(1);
  } else if (action === "today") {
    taskCalendarCursor = clampTaskCalendarDate(new Date());
    clearSelectedTaskDateOutsideCalendar();
  }

  renderFollowUps();
}

function shiftTaskCalendarMonth(delta) {
  setTaskCalendarMonth(
    taskCalendarCursor.getFullYear(),
    taskCalendarCursor.getMonth() + Number(delta || 0)
  );
}

function setTaskCalendarMonth(year, monthIndex) {
  taskCalendarCursor = clampTaskCalendarMonth(year, monthIndex);
  clearSelectedTaskDateOutsideCalendar();
}

function setTaskCalendarFromDate(value, clearSelection = true) {
  const parts = parseIsoDateParts(value);
  if (!parts) {
    return;
  }

  taskCalendarCursor = clampTaskCalendarMonth(parts.year, parts.monthIndex);
  if (clearSelection) {
    clearSelectedTaskDateOutsideCalendar();
  }
}

function clearSelectedTaskDateOutsideCalendar() {
  if (selectedTaskDate && !isDateInTaskCalendarMonth(selectedTaskDate)) {
    selectedTaskDate = null;
  }
}

function isDateInTaskCalendarMonth(value) {
  const parts = parseIsoDateParts(value);
  if (!parts) {
    return false;
  }

  return parts.year === taskCalendarCursor.getFullYear()
    && parts.monthIndex === taskCalendarCursor.getMonth();
}

function isTaskDateInRange(value) {
  const parts = parseIsoDateParts(value);
  return Boolean(parts && parts.year >= TASK_CALENDAR_MIN_YEAR && parts.year <= TASK_CALENDAR_MAX_YEAR);
}

function clampTaskCalendarDate(value) {
  const date = value instanceof Date && !Number.isNaN(value.getTime())
    ? value
    : new Date();
  return clampTaskCalendarMonth(date.getFullYear(), date.getMonth());
}

function clampTaskCalendarMonth(year, monthIndex) {
  let normalizedYear = Number(year);
  let normalizedMonth = Number(monthIndex);

  if (!Number.isFinite(normalizedYear)) {
    normalizedYear = new Date().getFullYear();
  }
  if (!Number.isFinite(normalizedMonth)) {
    normalizedMonth = new Date().getMonth();
  }

  while (normalizedMonth < 0) {
    normalizedYear -= 1;
    normalizedMonth += 12;
  }
  while (normalizedMonth > 11) {
    normalizedYear += 1;
    normalizedMonth -= 12;
  }

  if (normalizedYear < TASK_CALENDAR_MIN_YEAR) {
    return new Date(TASK_CALENDAR_MIN_YEAR, 0, 1);
  }
  if (normalizedYear > TASK_CALENDAR_MAX_YEAR) {
    return new Date(TASK_CALENDAR_MAX_YEAR, 11, 1);
  }

  return new Date(normalizedYear, normalizedMonth, 1);
}

function parseIsoDateParts(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return null;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!year || month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }

  return {
    year,
    monthIndex: month - 1,
    day
  };
}

function renderFollowUpCalendar() {
  if (!followUpCalendar) {
    return;
  }

  const year = taskCalendarCursor.getFullYear();
  const month = taskCalendarCursor.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const offset = firstDay.getDay();
  const itemsByDate = new Map();
  const canGoPrevious = year > TASK_CALENDAR_MIN_YEAR || month > 0;
  const canGoNext = year < TASK_CALENDAR_MAX_YEAR || month < 11;

  followUpItems.forEach((item) => {
    if (!itemsByDate.has(item.due_date)) {
      itemsByDate.set(item.due_date, []);
    }
    itemsByDate.get(item.due_date).push(item);
  });

  const cells = [];
  for (let index = 0; index < offset; index += 1) {
    cells.push('<span class="calendar-day empty"></span>');
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const dayItems = itemsByDate.get(date) || [];
    const hasDueAlert = dayItems.some((item) => getFollowUpDueState(item) === "due-alert");
    const hasItem = dayItems.length > 0;
    const previewItems = dayItems.slice(0, 3);
    cells.push(`
      <button
        class="calendar-day ${hasItem ? "has-task" : ""} ${hasDueAlert ? "due-alert" : ""} ${selectedTaskDate === date ? "selected" : ""}"
        type="button"
        data-task-date="${escapeHtml(date)}"
      >
        <span class="calendar-day-number">${day}</span>
        ${hasItem ? `
          <span class="calendar-task-count">${escapeHtml(String(dayItems.length))}</span>
          <span class="calendar-task-preview">
            ${previewItems.map((item) => `<em title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</em>`).join("")}
            ${dayItems.length > previewItems.length ? `<em>${escapeHtml(`+${dayItems.length - previewItems.length} more`)}</em>` : ""}
          </span>
        ` : ""}
      </button>
    `);
  }

  followUpCalendar.innerHTML = `
    <div class="calendar-heading">
      <div class="calendar-title">${taskCalendarCursor.toLocaleString([], { month: "long", year: "numeric" })}</div>
      <div class="calendar-controls" aria-label="Task calendar controls">
        <button class="calendar-nav-button" type="button" data-calendar-action="previous" ${canGoPrevious ? "" : "disabled"} aria-label="Previous month">&lt;</button>
        <select class="calendar-select" data-calendar-month aria-label="Calendar month">
          ${buildCalendarMonthOptions(month)}
        </select>
        <select class="calendar-select calendar-year-select" data-calendar-year aria-label="Calendar year">
          ${buildCalendarYearOptions(year)}
        </select>
        <button class="calendar-nav-button" type="button" data-calendar-action="next" ${canGoNext ? "" : "disabled"} aria-label="Next month">&gt;</button>
        <button class="calendar-nav-button calendar-today-button" type="button" data-calendar-action="today">Today</button>
      </div>
    </div>
    <div class="calendar-weekdays">
      <span>S</span><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span>
    </div>
    <div class="calendar-grid">${cells.join("")}</div>
  `;
}

function buildCalendarMonthOptions(activeMonth) {
  return Array.from({ length: 12 }, (_item, index) => {
    const label = new Date(2026, index, 1).toLocaleString([], { month: "short" });
    return `<option value="${index}" ${index === activeMonth ? "selected" : ""}>${escapeHtml(label)}</option>`;
  }).join("");
}

function buildCalendarYearOptions(activeYear) {
  const options = [];
  for (let year = TASK_CALENDAR_MIN_YEAR; year <= TASK_CALENDAR_MAX_YEAR; year += 1) {
    options.push(`<option value="${year}" ${year === activeYear ? "selected" : ""}>${year}</option>`);
  }
  return options.join("");
}

function updateFollowUpDots() {
  const hasDueAlert = followUpItems.some((item) => getFollowUpDueState(item) === "due-alert");
  [tasksDueDot, followUpDueDot].forEach((dot) => {
    if (dot) {
      dot.classList.toggle("visible", hasDueAlert);
    }
  });
}

function getFollowUpDueState(item) {
  if (!item || item.status === "done") {
    return "";
  }

  const today = new Date();
  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return item.due_date <= todayKey ? "due-alert" : "";
}

function buildSelectedFileContext() {
  const documents = selectedSubmission && selectedSubmission.record
    ? selectedSubmission.record.documents || []
    : [];

  return documents
    .filter((document) => selectedFiles.has(document.file_name))
    .map((document) => {
      const content = document.content || "[PDF or binary file selected; use document metadata shown here.]";
      return [
        `--- ${document.file_name} ---`,
        `Type: ${document.file_type}`,
        `Category: ${document.category}`,
        `Document Types: ${formatMetadataList(document.document_types)}`,
        `Major Categories: ${formatMetadataList(document.major_categories)}`,
        `Created: ${document.file_created_at}`,
        `Received: ${document.received_at}`,
        `Description: ${document.description}`,
        content
      ].join("\n");
    })
    .join("\n\n");
}

function findLastUserMessageIndex(modelMessages) {
  for (let index = modelMessages.length - 1; index >= 0; index -= 1) {
    if (modelMessages[index].role === "user") {
      return index;
    }
  }

  return -1;
}

async function saveCurrentChatHistory() {
  if (!selectedSubmission || !messages.length) {
    return;
  }

  try {
    const response = await fetch(
      `/api/submissions/${encodeURIComponent(selectedSubmission.id)}/chat-history`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          history_id: currentChatHistoryId,
          messages
        })
      }
    );
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to save chat history.");
    }

    currentChatHistoryId = data.chat_history.id;
    await loadChatHistory(selectedSubmission.id);
  } catch (error) {
    console.warn(error);
  }
}

function addMessage(role, content, isError = false) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "assistant" ? "AI" : "You";

  const bubble = document.createElement("div");
  bubble.className = isError ? "bubble error" : "bubble";
  if (role === "assistant" && !isError) {
    renderAssistantContent(bubble, content);
  } else {
    bubble.innerHTML = formatText(content);
  }

  article.append(avatar, bubble);
  messagesEl.append(article);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  return article;
}

function createChatProcess(messageArticle) {
  const bubble = messageArticle.querySelector(".bubble");
  bubble.innerHTML = "";

  const panel = document.createElement("section");
  panel.className = "chat-process-panel";

  const heading = document.createElement("div");
  heading.className = "chat-process-heading";
  heading.innerHTML = `
    <span class="process-pulse" aria-hidden="true"></span>
    <strong>Process</strong>
  `;

  const list = document.createElement("ol");
  list.className = "chat-process-list";

  const answer = document.createElement("div");
  answer.className = "assistant-answer";

  panel.append(heading, list);
  bubble.append(panel, answer);

  const process = {
    bubble,
    panel,
    list,
    answer,
    steps: []
  };
  activeChatProcesses.push(process);
  return process;
}

function addChatProcessStep(process, title, detail, status = "active") {
  const step = {
    title: String(title || "Working"),
    detail: String(detail || ""),
    status
  };
  process.steps.push(step);
  renderChatProcess(process);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return step;
}

function updateChatProcessStep(step, updates = {}) {
  Object.assign(step, updates);
  const process = activeChatProcesses.find((item) => item.steps.includes(step));
  if (process) {
    renderChatProcess(process);
  }
}

function renderChatProcess(process) {
  if (!process || !process.list) {
    return;
  }

  process.list.innerHTML = process.steps
    .map((step) => `
      <li class="chat-process-step ${escapeHtml(step.status || "active")}">
        <span class="process-dot" aria-hidden="true"></span>
        <div>
          <strong>${escapeHtml(step.title)}</strong>
          ${step.detail ? `<small>${escapeHtml(step.detail)}</small>` : ""}
        </div>
      </li>
    `)
    .join("");
}

function markActiveChatProcessSteps(process, status) {
  if (!process) {
    return;
  }

  process.steps.forEach((step) => {
    if (step.status === "active") {
      step.status = status;
    }
  });
  renderChatProcess(process);
}

function setChatProcessAnswer(process, reply, sources = []) {
  markActiveChatProcessSteps(process, "done");
  process.answer.classList.remove("error");
  renderAssistantContent(process.answer, reply, sources);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setChatProcessError(process, message) {
  process.answer.classList.add("error");
  process.answer.textContent = message;
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderAssistantContent(container, content, sources = []) {
  const text = String(content || "");
  const citations = window.AUCitations ? window.AUCitations.render(sources) : "";
  const isCopyableEmail = isEmailDraftResponse(text);

  container.classList.toggle("has-response-copy", isCopyableEmail);
  if (isCopyableEmail) {
    container.dataset.copyText = text;
  } else {
    delete container.dataset.copyText;
  }

  container.innerHTML = `${isCopyableEmail ? renderResponseCopyToolbar() : ""}${formatText(text)}${citations}`;
}

function renderResponseCopyToolbar() {
  return `
    <div class="response-copy-toolbar">
      <span>Email draft</span>
      <button class="response-copy-button" type="button" data-copy-assistant-response>Copy</button>
    </div>
  `;
}

function isEmailDraftResponse(value) {
  const text = String(value || "").trim();
  const lower = text.toLowerCase();
  if (!text) {
    return false;
  }

  if (/\bsubject\s*:/.test(lower)) {
    return true;
  }

  const hasGreeting = /(^|\n)\s*(dear|hi|hello)\s+[^,\n]{2,80},/i.test(text);
  const hasClosing = /(^|\n)\s*(best|regards|sincerely|thank you|thanks),?/i.test(text);
  if (hasGreeting && hasClosing) {
    return true;
  }

  return /\b(email draft|draft email|broker follow[- ]?up email)\b/i.test(text)
    && /\b(please provide|attached|subject|dear|hi|hello)\b/i.test(text);
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function describeManualFileSelection() {
  if (fileSelectionMode === "none") {
    return "No files are selected for this request.";
  }

  const selected = Array.from(selectedFiles);
  if (fileSelectionMode === "manual") {
    return selected.length
      ? `Manual selection includes ${formatProcessFileList(selected)}.`
      : "Manual selection is empty.";
  }

  return selected.length
    ? `All selected mode has ${selected.length} checked files; the agent will use that fixed selection.`
    : "All selected mode is active, but no files are checked.";
}

function describeCentralSelectionRequest() {
  if (fileSelectionMode === "auto") {
    return "Auto is on; the centralized agent will choose only the relevant workspace data for this prompt.";
  }

  return describeManualFileSelection();
}

function describeWorkflowActionCheck(data) {
  const actions = Array.isArray(data && data.actions) ? data.actions : [];
  if (!actions.length) {
    return "No direct workspace action was needed; continuing with data retrieval and model response.";
  }

  return `Handled ${actions.map((action) => formatLabel(action.type || "action")).join(", ")} through the workflow router.`;
}

function describeInformationSelection(data) {
  const actions = Array.isArray(data && data.actions) ? data.actions : [];
  const retrieval = data && data.retrieval ? data.retrieval : {};
  const selection = retrieval.selection || {};
  const plan = Array.isArray(selection.selected_skills) && selection.selected_skills.length
    ? selection.selected_skills
    : Array.isArray(retrieval.plan)
      ? retrieval.plan
      : [];
  const documentSelection = selection.document_selection || {};
  const documentCompleteness = selection.document_completeness || {};
  const selectedDocuments = Array.isArray(documentSelection.selected_files)
    ? documentSelection.selected_files
    : getDocumentSourceNames(retrieval.sources);

  if (actions.length && !plan.length) {
    return "No additional data retrieval was needed for this workflow action.";
  }

  const skillText = plan.length
    ? `Selected ${plan.map(formatLabel).join(", ")}`
    : "No supporting data was selected";
  const documentText = selectedDocuments.length
    ? `documents: ${formatProcessFileList(selectedDocuments)}`
    : documentCompleteness.missing_count !== undefined
      ? `document checklist: ${documentCompleteness.received_count || 0}/${documentCompleteness.required_count || 0} received, ${documentCompleteness.missing_count || 0} missing`
    : fileSelectionMode === "none"
      ? "documents: none by user selection"
      : "documents: none";
  const agentName = selection.agent ? formatLabel(selection.agent) : "Centralized Information Agent";

  return `${agentName}: ${skillText}; ${documentText}.`;
}

function describeBackendResponse(data) {
  const trace = getAgentTrace(data);
  if (trace && trace.trace_id) {
    const confidence = trace.confidence || {};
    const confidenceText = confidence.label
      ? `${formatLabel(confidence.label)} confidence${confidence.score !== undefined ? ` (${Math.round(Number(confidence.score) * 100)}%)` : ""}`
      : "confidence checked";
    return `Agent trace ${trace.trace_id} persisted; ${confidenceText}; ${trace.attempt_count || 1} attempt(s).`;
  }

  if (Array.isArray(data.actions) && data.actions.length) {
    return `Handled by ${data.framework || "local action router"}.`;
  }

  const model = data.model || "GPT model";
  const framework = data.framework ? ` via ${data.framework}` : "";
  return `Model request completed with ${model}${framework}.`;
}

function appendResponseProcessSteps(process, data) {
  appendAgentTraceProcessSteps(process, getAgentTrace(data));

  const actions = Array.isArray(data.actions) ? data.actions : [];
  if (actions.length) {
    actions.forEach((action) => {
      addChatProcessStep(process, getActionProcessTitle(action), getActionProcessDetail(action), "done");
    });
    return;
  }

  const retrieval = data.retrieval || {};
  const plan = Array.isArray(retrieval.plan) ? retrieval.plan : [];
  const sources = Array.isArray(retrieval.sources) ? retrieval.sources : [];
  if (plan.length) {
    addChatProcessStep(
      process,
      "Retrieved underwriting data",
      `Skills used: ${plan.map(formatLabel).join(", ")}.`,
      "done"
    );
  }

  const documentSources = sources.filter((source) => source && source.skill === "documents");
  if (documentSources.length) {
    addChatProcessStep(
      process,
      "Read document context",
      formatProcessFileList(documentSources.map((source) => source.source.split("/").pop())),
      "done"
    );
  }

  const completenessSources = sources.filter((source) => source && source.skill === "document_completeness");
  if (completenessSources.length) {
    addChatProcessStep(
      process,
      "Compared document checklist",
      "Required cyber documents were compared with submitted file metadata.",
      "done"
    );
  }

  const nonDocumentSources = sources.filter((source) => source && source.skill !== "documents");
  if (nonDocumentSources.length) {
    const grouped = Array.from(new Set(nonDocumentSources.map((source) => formatLabel(source.skill || "data"))));
    addChatProcessStep(process, "Pulled supporting data", grouped.join(", "), "done");
  }
}

function getAgentTrace(data) {
  return data && data.agent_trace ? data.agent_trace : null;
}

function appendAgentTraceProcessSteps(process, trace) {
  if (!trace || !Array.isArray(trace.steps) || !trace.steps.length) {
    return;
  }

  trace.steps.forEach((step) => {
    const title = step.title || formatLabel(step.phase || "agent step");
    const detail = buildTraceStepDetail(step, trace);
    const status = step.status === "error" ? "error" : "done";
    addChatProcessStep(process, title, detail, status);
  });
}

function buildTraceStepDetail(step, trace) {
  const pieces = [];
  if (step.phase) {
    pieces.push(formatLabel(step.phase));
  }
  if (step.detail) {
    pieces.push(step.detail);
  }
  if (step.phase === "trace" && trace.trace_id) {
    pieces.push(`Trace id: ${trace.trace_id}`);
  }
  return pieces.join(" - ");
}

function appendWorkspaceRefreshProcessStep(process, actions) {
  const actionTypes = Array.isArray(actions)
    ? Array.from(new Set(actions.map((action) => action && action.type).filter(Boolean)))
    : [];
  const refreshTypes = actionTypes.filter((type) => ["note", "guide", "task", "submission_update"].includes(type));
  if (!refreshTypes.length) {
    return;
  }

  addChatProcessStep(
    process,
    "Updated workspace",
    `Refreshed ${refreshTypes.map(formatLabel).join(", ")} data after the chat action.`,
    "done"
  );
}

function getActionProcessTitle(action) {
  const type = action && action.type;
  if (type === "note") return "Added underwriter note";
  if (type === "guide") return "Added guide instruction";
  if (type === "task") return action.record ? "Added scheduled task" : "Checked scheduled task request";
  if (type === "submission_update") return "Updated submission fields";
  if (type === "broker_table") return "Queried broker table";
  if (type === "document_completeness") return "Compared required documents";
  if (type === "navigate") return "Navigated workspace";
  if (type === "extract") return "Retrieved underwriting summary";
  return "Applied chat action";
}

function getActionProcessDetail(action) {
  const type = action && action.type;
  if (type === "note") return "Saved to this submission's note JSON file.";
  if (type === "guide") return "Saved to this submission's guide JSON file and future system prompts.";
  if (type === "task") {
    const tasks = action.record && Array.isArray(action.record.tasks) ? action.record.tasks : [];
    const latest = tasks[tasks.length - 1];
    return latest
      ? `${latest.title} due ${formatDateOnly(latest.due_date)}.`
      : "No task was saved because more information is needed.";
  }
  if (type === "submission_update") {
    return `Submission status is now ${action.record && action.record.status ? action.record.status : "updated"}.`;
  }
  if (type === "broker_table") {
    return "Pulled broker rows from data/brokers/brokers.json.";
  }
  if (type === "document_completeness") {
    return "Compared data/document_requirements/cyber_required_documents.json against submitted document metadata.";
  }
  if (type === "navigate") {
    const uiAction = action.ui_action || {};
    return `Opened ${formatLabel(uiAction.panel || "workspace")}.`;
  }
  if (type === "extract") {
    return "Used stored underwriting, broker, claim, or evidence records.";
  }
  return "Processed by the local workflow router.";
}

function formatProcessFileList(files, maxItems = 4) {
  const values = files.filter(Boolean).map((file) => String(file).split("/").pop());
  if (!values.length) {
    return "No files";
  }

  const visible = values.slice(0, maxItems).join(", ");
  const remaining = values.length - maxItems;
  return remaining > 0 ? `${visible}, +${remaining} more` : visible;
}

function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  clearButton.disabled = isLoading;
  sendButton.textContent = isLoading ? "Sending" : "Send";
}

function buildKeyInfoItems(submission) {
  const record = submission.record || {};
  const applicant = record.applicant || {};
  const coverage = record.coverage || {};
  const limits = coverage.requested_limits || {};

  return [
    { label: "Insured", value: applicant.insured_name || "TBD" },
    { label: "Industry", value: applicant.industry || "TBD" },
    { label: "Records", value: applicant.records_count ? applicant.records_count.toLocaleString() : "TBD" },
    { label: "Status", value: record.status || "TBD" },
    {
      label: "Coverage",
      value: Array.isArray(coverage.lines_requested) ? coverage.lines_requested.join(", ") : "TBD"
    },
    { label: "Effective", value: coverage.requested_effective_date || "TBD" },
    { label: "Received", value: formatDateTime(record.received_at) },
    { label: "Limits", value: Object.values(limits).join(", ") || "TBD" }
  ];
}

function buildTimelineItems(record) {
  const timeline = Array.isArray(record.timeline) ? record.timeline : [];

  if (!timeline.length) {
    return "<p>No timeline events found.</p>";
  }

  return timeline
    .map(
      (item) => `
        <div class="timeline-item">
          <time>${escapeHtml(formatDateTime(item.date))}</time>
          <div>
            <strong>${escapeHtml(item.event)}</strong>
            <p>${escapeHtml(item.description || "")}</p>
          </div>
        </div>
      `
    )
    .join("");
}

function buildAnalyticsPanel(record) {
  currentAnalyticsFeatureLookup = buildAnalyticsFeatureLookup(record);
  ensureWhatIfValues(currentAnalyticsFeatureLookup);
  currentAnalytics = buildLogisticAnalytics(record, currentAnalyticsFeatureLookup);

  return `
    <div class="analytics-subtabs" aria-label="Analytics model views">
      <button class="analytics-subtab active" type="button" data-analytics-subtab="quote">Quote</button>
      <button class="analytics-subtab" type="button" data-analytics-subtab="bind">Bind</button>
      <button class="analytics-subtab" type="button" data-analytics-subtab="what-if">What If</button>
      <button class="analytics-subtab" type="button" data-analytics-subtab="portfolio">Portfolio</button>
    </div>

    <div class="analytics-view active" data-analytics-view="quote">
      ${renderModelView("Quote Probability", currentAnalytics.quote, "Likelihood the account receives quotable terms", record, "quote")}
    </div>

    <div class="analytics-view" data-analytics-view="bind">
      ${renderModelView("Bind Probability", currentAnalytics.bind, "Likelihood quoted terms bind", record, "bind")}
    </div>

    <div class="analytics-view" data-analytics-view="what-if">
      ${renderWhatIfView()}
    </div>

    <div class="analytics-view" data-analytics-view="portfolio">
      ${renderPortfolioAnalyticsView()}
    </div>
  `;
}

function buildLogisticAnalytics(record, existingFeatureLookup) {
  const featureLookup = existingFeatureLookup || buildAnalyticsFeatureLookup(record);
  const quoteModel = analyticsModels && analyticsModels.quote ? analyticsModels.quote : getFallbackQuoteModel();
  const bindModel = analyticsModels && analyticsModels.bind ? analyticsModels.bind : getFallbackBindModel();
  const supplementalModels = analyticsModels && analyticsModels.supplemental ? analyticsModels.supplemental : {};

  return {
    quote: scoreStoredModel(quoteModel, featureLookup),
    bind: scoreStoredModel(bindModel, featureLookup),
    supplemental: SUPPLEMENTAL_MODEL_KEYS.reduce((models, key) => {
      if (supplementalModels[key]) {
        models[key] = scoreStoredModel(supplementalModels[key], featureLookup);
      }
      return models;
    }, {})
  };
}

async function loadAnalyticsModels() {
  if (analyticsModels) {
    return analyticsModels;
  }

  const modelNames = [
    "quote_prob",
    "bind_prob",
    ...SUPPLEMENTAL_MODEL_KEYS,
    "industry_propensity",
    "feature_metadata"
  ];
  const responses = await Promise.all(modelNames.map((modelName) => fetch(`/api/models/${modelName}`)));
  const payloads = await Promise.all(responses.map((response) => response.json()));
  responses.forEach((response, index) => {
    if (!response.ok) {
      throw new Error(payloads[index].error || `Unable to load ${modelNames[index]} model.`);
    }
  });
  const modelPayloads = modelNames.reduce((lookup, modelName, index) => {
    lookup[modelName] = payloads[index].model;
    return lookup;
  }, {});

  analyticsModels = {
    quote: modelPayloads.quote_prob,
    bind: modelPayloads.bind_prob,
    supplemental: SUPPLEMENTAL_MODEL_KEYS.reduce((lookup, key) => {
      lookup[key] = modelPayloads[key];
      return lookup;
    }, {}),
    industryPropensity: modelPayloads.industry_propensity
  };
  analyticsFeatureMetadata = modelPayloads.feature_metadata;
  return analyticsModels;
}

async function loadUnderwritingSystem(submissionId) {
  try {
    const data = await AUApi.get(`/api/submissions/${encodeURIComponent(submissionId)}/underwriting`);
    underwritingSystem = data.underwriting_system || null;
  } catch (error) {
    console.warn(error);
    underwritingSystem = null;
  }

  return underwritingSystem;
}

async function loadDecisionWorkflow(submissionId) {
  try {
    const data = await AUApi.get(`/api/submissions/${encodeURIComponent(submissionId)}/decision-workflow`);
    decisionWorkflow = data.decision_workflow || null;
  } catch (error) {
    console.warn(error);
    decisionWorkflow = null;
  }

  return decisionWorkflow;
}

async function loadClearanceReview(submissionId) {
  try {
    const data = await AUApi.get(`/api/submissions/${encodeURIComponent(submissionId)}/clearance`);
    clearanceReview = data.clearance || null;
  } catch (error) {
    console.warn(error);
    clearanceReview = null;
  }

  return clearanceReview;
}

async function loadExternalResearch(submissionId) {
  try {
    const data = await AUApi.get(`/api/submissions/${encodeURIComponent(submissionId)}/external-research`);
    externalResearch = data.external_research || null;
  } catch (error) {
    console.warn(error);
    externalResearch = null;
  }

  return externalResearch;
}

async function loadRatingQuote(submissionId) {
  try {
    const data = await AUApi.get(`/api/submissions/${encodeURIComponent(submissionId)}/rating-quote`);
    ratingQuote = data.rating_quote || null;
  } catch (error) {
    console.warn(error);
    ratingQuote = null;
  }

  return ratingQuote;
}

async function loadPortfolioDashboard() {
  try {
    const data = await AUApi.get("/api/portfolio/queue");
    portfolioDashboard = data.portfolio || null;
  } catch (error) {
    console.warn(error);
    portfolioDashboard = null;
  }

  return portfolioDashboard;
}

function renderUnderwritingSystemView() {
  if (!underwritingSystem) {
    return '<p class="empty-state">Underwriting system is not available for this submission.</p>';
  }

  const appetite = underwritingSystem.appetite || {};
  const claimSnapshot = underwritingSystem.claim_snapshot || {};
  const ingredients = Array.isArray(underwritingSystem.ingredients) ? underwritingSystem.ingredients : [];
  const signals = Array.isArray(underwritingSystem.signals) ? underwritingSystem.signals : [];
  const evidence = Array.isArray(underwritingSystem.evidence_status) ? underwritingSystem.evidence_status : [];
  const actions = Array.isArray(underwritingSystem.recommended_actions) ? underwritingSystem.recommended_actions : [];
  const claims = Array.isArray(underwritingSystem.claims) ? underwritingSystem.claims : [];
  const sopGuidance = underwritingSystem.sop_guidance || {};
  const sopSuggestions = Array.isArray(sopGuidance.suggestions) ? sopGuidance.suggestions : [];
  const components = Array.isArray(underwritingSystem.components) && underwritingSystem.components.length
    ? underwritingSystem.components
    : buildUnderwritingComponents(appetite, claimSnapshot, ingredients, signals, evidence, actions);
  const claimReview = underwritingSystem.claim_review || {};
  const broker = underwritingSystem.broker || null;
  const record = selectedSubmission && selectedSubmission.record ? selectedSubmission.record : {};
  const claimsUrl = selectedSubmission
    ? `/api/submissions/${encodeURIComponent(selectedSubmission.id)}/claims`
    : "#";

  return `
    <section class="uw-system-grid">
      <article class="uw-card uw-card-primary">
        <span>Appetite</span>
        <strong>${escapeHtml(appetite.status || "TBD")}</strong>
        <p>${escapeHtml(appetite.rationale || "No appetite rationale available.")}</p>
        <small>Authority: ${escapeHtml(formatLabel(appetite.recommended_authority || "TBD"))}</small>
      </article>

      <article class="uw-card">
        <span>Claim Snapshot</span>
        <strong>${escapeHtml(String(claimSnapshot.total_claims ?? 0))} claims</strong>
        <p>
          ${escapeHtml(String(claimSnapshot.open_claims ?? 0))} open ·
          ${escapeHtml(formatCurrency(Number(claimSnapshot.total_incurred || 0)))} incurred
        </p>
        <a class="inline-data-link" href="${escapeHtml(claimsUrl)}" target="_blank" rel="noreferrer">Open claims source</a>
      </article>

      <article class="uw-card">
        <span>Evidence Readiness</span>
        <strong>${evidence.filter((item) => item.status === "available").length}/${evidence.length || 0}</strong>
        <p>${escapeHtml(evidence.filter((item) => item.status === "missing").length)} required evidence categories missing.</p>
      </article>
    </section>

    ${renderUnderwritingWorkflowRibbon(record, appetite, evidence, actions)}
    ${renderUnderwritingDecisionConsole(record, appetite, claimSnapshot, evidence, signals, broker)}
    ${renderSopSuggestionPanel(sopGuidance, sopSuggestions)}
    ${renderDecisionWorkflowPanel()}
    ${renderClearanceReviewPanel()}
    ${renderRatingQuotePanel()}
    ${renderExternalResearchPanel()}
    ${renderSubmissionUpdateEditor(record)}
    ${renderBrokerSection(broker)}

    <section class="uw-panel uw-components-panel">
      <div class="card-heading">
        <h4>Underwriting Components</h4>
        <span class="claim-system-tag">Decision workbench</span>
      </div>
      <div class="uw-component-grid">
        ${components.map(renderUnderwritingComponent).join("")}
      </div>
    </section>

    <section class="uw-workbench-grid">
      <article class="uw-panel">
        <h4>System Ingredients</h4>
        <div class="ingredient-list">
          ${ingredients.map(renderIngredientItem).join("")}
        </div>
      </article>

      <article class="uw-panel">
        <h4>Underwriting Signals</h4>
        <div class="signal-list">
          ${signals.map(renderSignalItem).join("")}
        </div>
      </article>

      <article class="uw-panel">
        <h4>Recommended Actions</h4>
        <ol class="uw-action-list">
          ${actions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}
        </ol>
      </article>

      <article class="uw-panel">
        <h4>Evidence Coverage</h4>
        <div class="evidence-list">
          ${evidence.map(renderEvidenceItem).join("")}
        </div>
      </article>
    </section>

    <section class="uw-panel">
      <div class="card-heading">
        <h4>Historical Claim Information</h4>
        <span class="claim-system-tag">${escapeHtml(underwritingSystem.system_name || "Underwriting System")}</span>
      </div>
      <p class="uw-section-note">
        ${escapeHtml(claimReview.summary || "Linked claims are pulled from the dummy claims system.")}
        ${escapeHtml(claimReview.review_focus || "Review loss dates, claim type, status, severity, paid amounts, and reserves before quote or referral decisions.")}
      </p>
      ${renderClaimHistoryTable(claims)}
    </section>
  `;
}

function renderDecisionWorkflowPanel() {
  if (window.AUDecisionWorkflow) {
    return window.AUDecisionWorkflow.render(decisionWorkflow);
  }

  return '<section class="uw-panel"><h4>Underwriting Decision Workflow</h4><p class="empty-state">Decision workflow renderer is unavailable.</p></section>';
}

function renderClearanceReviewPanel() {
  if (!clearanceReview) {
    return `
      <section class="uw-panel clearance-panel">
        <h4>Clearance Review</h4>
        <p class="empty-state">Clearance review is not available.</p>
      </section>
    `;
  }

  const checks = Array.isArray(clearanceReview.checks) ? clearanceReview.checks : [];
  const matches = Array.isArray(clearanceReview.possible_matches) ? clearanceReview.possible_matches : [];
  return `
    <section class="uw-panel clearance-panel">
      <div class="card-heading">
        <h4>Clearance Review</h4>
        <span class="status-chip ${escapeHtml(workbenchStatusClass(clearanceReview.status))}">${escapeHtml(formatLabel(clearanceReview.status || "Review"))}</span>
      </div>
      <p class="uw-section-note">${escapeHtml(clearanceReview.summary || "")}</p>
      <div class="clearance-check-grid">
        ${checks.map((check) => `
          <article class="${escapeHtml(workbenchStatusClass(check.status))}">
            <strong>${escapeHtml(check.label || "Check")}</strong>
            <span>${escapeHtml(formatLabel(check.status || "review"))}</span>
            <small>${escapeHtml(check.detail || "")}</small>
          </article>
        `).join("")}
      </div>
      ${matches.length ? `
        <div class="clearance-match-list">
          <strong>Possible matches</strong>
          ${matches.map((match) => `
            <small>${escapeHtml(match.id)}, ${escapeHtml(match.insured_name || match.title || "Account")} | ${escapeHtml(match.status || "TBD")} | similarity ${escapeHtml(String(match.similarity || 0))}</small>
          `).join("")}
        </div>
      ` : ""}
    </section>
  `;
}

function renderRatingQuotePanel() {
  if (!ratingQuote) {
    return `
      <section class="uw-panel rating-panel">
        <h4>Rating And Quote</h4>
        <p class="empty-state">Rating package is not available.</p>
      </section>
    `;
  }

  const premiumRange = ratingQuote.premium_range || {};
  const modifiers = Array.isArray(ratingQuote.modifiers) ? ratingQuote.modifiers : [];
  const terms = Array.isArray(ratingQuote.coverage_terms) ? ratingQuote.coverage_terms : [];
  const subjectivities = Array.isArray(ratingQuote.subjectivities) ? ratingQuote.subjectivities : [];
  const calculation = ratingQuote.calculation || {};
  const calculationInputs = calculation.inputs || {};
  const referralReasons = Array.isArray(ratingQuote.referral_reasons) ? ratingQuote.referral_reasons : [];
  return `
    <section class="uw-panel rating-panel">
      <div class="card-heading">
        <h4>Rating And Quote</h4>
        <span class="claim-system-tag">${escapeHtml(ratingQuote.rating_engine || "demo")}</span>
      </div>
      <div class="rating-summary-grid">
        ${renderRatingMetric("Indicated Premium", formatCurrency(Number(ratingQuote.indicated_premium || 0)))}
        ${renderRatingMetric("Premium Range", `${formatCurrency(Number(premiumRange.low || 0))} - ${formatCurrency(Number(premiumRange.high || 0))}`)}
        ${renderRatingMetric("Quote Readiness", `${Math.round(Number(ratingQuote.quote_readiness || 0))}%`)}
        ${renderRatingMetric("Recommended Limit", formatCurrency(Number(ratingQuote.recommended_limit || 0)))}
        ${renderRatingMetric("Recommended Retention", ratingQuote.recommended_retention || "TBD")}
        ${renderRatingMetric("Authority Path", ratingQuote.authority_path || "Underwriter delegated review")}
      </div>
      <div class="rating-calculation-panel">
        <div>
          <strong>Calculation</strong>
          <small>${escapeHtml(calculation.formula || "Demo factor formula not available.")}</small>
        </div>
        <div class="rating-calculation-grid">
          <span>Base ${escapeHtml(formatCurrency(Number(calculation.base_premium || 0)))}</span>
          <span>Modifier product ${escapeHtml(String(calculation.modifier_product || "TBD"))}</span>
          <span>Range ${escapeHtml(String(Math.round(Number(calculation.range_low_factor || 0.9) * 100)))}%-${escapeHtml(String(Math.round(Number(calculation.range_high_factor || 1.15) * 100)))}%</span>
          <span>Revenue ${escapeHtml(formatCurrency(Number(calculationInputs.annual_revenue || 0)))}</span>
          <span>Records ${escapeHtml(Number(calculationInputs.records_count || 0).toLocaleString("en-US"))}</span>
          <span>Evidence ${escapeHtml(String(Math.round(Number(calculationInputs.evidence_ratio || 0) * 100)))}%</span>
        </div>
        ${referralReasons.length ? `
          <div class="rating-referral-reasons">
            <strong>Referral Triggers</strong>
            ${referralReasons.map((reason) => `<small>${escapeHtml(reason)}</small>`).join("")}
          </div>
        ` : ""}
      </div>
      <div class="rating-columns">
        <div>
          <strong>Modifiers</strong>
          ${modifiers.map((item) => `<small>${escapeHtml(item.label)}: ${escapeHtml(String(item.factor))} | ${escapeHtml(item.rationale || "")}</small>`).join("")}
        </div>
        <div>
          <strong>Coverage Terms</strong>
          ${terms.map((item) => `<small>${escapeHtml(item.coverage)}: ${escapeHtml(formatCurrency(Number(item.limit || 0)))} | ${escapeHtml(item.condition || "")}</small>`).join("")}
        </div>
        <div>
          <strong>Subjectivities</strong>
          ${subjectivities.length ? subjectivities.map((item) => `<small>${escapeHtml(item)}</small>`).join("") : "<small>No subjectivities generated.</small>"}
        </div>
      </div>
    </section>
  `;
}

function renderRatingMetric(label, value) {
  return `
    <article>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderExternalResearchPanel() {
  if (!externalResearch) {
    return `
      <section class="uw-panel external-research-panel">
        <h4>External Research</h4>
        <p class="empty-state">External research is not available.</p>
      </section>
    `;
  }

  const profile = externalResearch.profile || {};
  const tasks = Array.isArray(externalResearch.research_tasks) ? externalResearch.research_tasks : [];
  const signals = Array.isArray(externalResearch.signals_from_submission) ? externalResearch.signals_from_submission : [];
  return `
    <section class="uw-panel external-research-panel">
      <div class="card-heading">
        <h4>External Research</h4>
        <span class="claim-system-tag">${escapeHtml(formatLabel(externalResearch.research_status || "connector ready"))}</span>
      </div>
      <p class="uw-section-note">${escapeHtml(externalResearch.research_note || "")}</p>
      <div class="external-research-grid">
        <article>
          <strong>${escapeHtml(profile.insured_name || "Insured TBD")}</strong>
          <small>${escapeHtml([profile.industry_bucket || profile.industry, profile.location, profile.broker].filter(Boolean).join(" | "))}</small>
          ${signals.map((signal) => `<small>${escapeHtml(signal)}</small>`).join("")}
        </article>
        <div class="external-task-list">
          ${tasks.map((task) => `
            <div class="${escapeHtml(workbenchStatusClass(task.status))}">
              <strong>${escapeHtml(task.label || "Research task")}</strong>
              <span>${escapeHtml(formatLabel(task.status || "not connected"))}</span>
              <small>${escapeHtml(task.detail || "")}</small>
            </div>
          `).join("")}
        </div>
      </div>
    </section>
  `;
}

function renderSopSuggestionPanel(sopGuidance, suggestions) {
  if (!suggestions.length) {
    return `
      <section class="uw-panel sop-panel">
        <div class="card-heading">
          <h4>SOP Suggestions</h4>
          <span class="claim-system-tag">${escapeHtml(sopGuidance.version || "SOP")}</span>
        </div>
        <p class="uw-section-note">No SOP-triggered suggestions are currently active.</p>
      </section>
    `;
  }

  return `
    <section class="uw-panel sop-panel">
      <div class="card-heading">
        <h4>SOP Suggestions</h4>
        <span class="claim-system-tag">${escapeHtml(sopGuidance.version || "SOP")}</span>
      </div>
      <div class="sop-suggestion-list">
        ${suggestions.map((suggestion) => `
          <article class="sop-suggestion-item ${escapeHtml(statusClass(suggestion.priority))}">
            <div>
              <span>${escapeHtml(suggestion.step_label || "SOP")}</span>
              <strong>${escapeHtml(suggestion.title || "Suggestion")}</strong>
            </div>
            <p>${escapeHtml(suggestion.recommendation || "")}</p>
            <small>${escapeHtml(suggestion.rationale || "")}</small>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderUnderwritingWorkflowRibbon(record, appetite, evidence, actions) {
  const hasMissingEvidence = evidence.some((item) => item.status === "missing");
  const statusText = String(record.status || "").toLowerCase();
  const appetiteText = String(appetite.status || "").toLowerCase();
  const steps = [
    {
      label: "Intake",
      detail: "Submission received",
      state: "complete"
    },
    {
      label: "Triage",
      detail: hasMissingEvidence ? "Evidence gap" : "Ready",
      state: hasMissingEvidence ? "watch" : "complete"
    },
    {
      label: "Risk Review",
      detail: appetite.status || "In review",
      state: appetiteText.includes("referral") ? "alert" : "active"
    },
    {
      label: "Pricing",
      detail: "Models ready",
      state: "active"
    },
    {
      label: "Referral",
      detail: appetiteText.includes("referral") ? "Required" : "As needed",
      state: appetiteText.includes("referral") ? "alert" : "idle"
    },
    {
      label: "Quote / Bind",
      detail: statusText.includes("bound") ? "Bound" : actions[0] || "Pending terms",
      state: statusText.includes("bound") ? "complete" : "idle"
    }
  ];

  return `
    <section class="uw-panel uw-workflow-panel">
      <div class="card-heading">
        <h4>Submission Workflow</h4>
        <span class="claim-system-tag">Intake to bind</span>
      </div>
      <div class="uw-workflow-ribbon">
        ${steps.map((step) => `
          <div class="workflow-step ${escapeHtml(step.state)}">
            <span>${escapeHtml(step.label)}</span>
            <small>${escapeHtml(step.detail)}</small>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function renderUnderwritingDecisionConsole(record, appetite, claimSnapshot, evidence, signals, broker) {
  const documents = Array.isArray(record.documents) ? record.documents : [];
  const availableEvidence = evidence.filter((item) => item.status === "available").length;
  const highSignals = signals.filter((signal) => signal.severity === "high");
  const moderateSignals = signals.filter((signal) => signal.severity === "moderate");
  const authority = formatLabel(appetite.recommended_authority || "standard_underwriter");
  const brokerQuality = broker && broker.relationship_metrics
    ? `${Math.round(Number(broker.relationship_metrics.data_quality_score || 0))}/100`
    : "TBD";
  const referralTrigger = highSignals.length
    ? highSignals[0].label
    : Number(claimSnapshot.open_claims || 0)
      ? "Open claims"
      : moderateSignals.length
        ? moderateSignals[0].label
        : "None";

  const tiles = [
    { label: "Priority", value: moderateSignals.length || highSignals.length ? "Medium" : "Low", detail: `${moderateSignals.length + highSignals.length} review signals` },
    { label: "Quality", value: evidence.length ? `${availableEvidence}/${evidence.length}` : "TBD", detail: "Required evidence" },
    { label: "Appetite", value: appetite.status || "TBD", detail: appetite.rationale || "No rationale available" },
    { label: "Authority", value: authority, detail: `Trigger: ${referralTrigger}` },
    { label: "Broker", value: broker ? broker.firm_name : "TBD", detail: `Data quality ${brokerQuality}` },
    { label: "Documents", value: String(documents.length), detail: "Submission files" }
  ];

  return `
    <section class="uw-panel uw-decision-console">
      <div class="card-heading">
        <h4>Decision Console</h4>
        <span class="claim-system-tag">Account-level view</span>
      </div>
      <div class="decision-tile-grid">
        ${tiles.map((tile) => `
          <article class="decision-tile">
            <span>${escapeHtml(tile.label)}</span>
            <strong>${escapeHtml(tile.value)}</strong>
            <small>${escapeHtml(tile.detail)}</small>
          </article>
        `).join("")}
      </div>
    </section>
  `;
}

function renderBrokerSection(broker) {
  if (!broker) {
    return `
      <section class="uw-panel broker-panel">
        <div class="card-heading">
          <h4>Broker</h4>
          <span class="status-chip watch">Missing</span>
        </div>
        <p class="uw-section-note">No broker profile is linked to this submission.</p>
      </section>
    `;
  }

  const contact = broker.submission_contact || {};
  const metrics = broker.relationship_metrics || {};
  const producer = broker.contacts && broker.contacts.producer ? broker.contacts.producer : {};
  const accountManager = broker.contacts && broker.contacts.account_manager ? broker.contacts.account_manager : {};

  return `
    <section class="uw-panel broker-panel">
      <div class="card-heading">
        <h4>Broker</h4>
        <span class="status-chip good">${escapeHtml(broker.service_tier || "Linked")}</span>
      </div>
      <div class="broker-profile-grid">
        <div class="broker-main">
          <span>${escapeHtml(broker.broker_type || "Broker")}</span>
          <strong>${escapeHtml(broker.firm_name || contact.firm_name || "Broker TBD")}</strong>
          <p>${escapeHtml(broker.placement_notes || contact.broker_notes || "")}</p>
        </div>
        <div class="broker-contact-card">
          <span>Producer</span>
          <strong>${escapeHtml(contact.producer_name || producer.name || "TBD")}</strong>
          <small>${escapeHtml(contact.producer_email || producer.email || "")}</small>
          <small>${escapeHtml(contact.producer_phone || producer.phone || "")}</small>
        </div>
        <div class="broker-contact-card">
          <span>Account Manager</span>
          <strong>${escapeHtml(contact.account_manager_name || accountManager.name || "TBD")}</strong>
          <small>${escapeHtml(contact.account_manager_email || accountManager.email || "")}</small>
          <small>${escapeHtml(contact.account_manager_phone || accountManager.phone || "")}</small>
        </div>
      </div>
      <div class="broker-metric-grid">
        ${renderBrokerMetric("Quote Ratio", formatPercent(Number(metrics.quote_ratio_12m || 0)))}
        ${renderBrokerMetric("Bind Ratio", formatPercent(Number(metrics.bind_ratio_12m || 0)))}
        ${renderBrokerMetric("Data Quality", `${Math.round(Number(metrics.data_quality_score || 0))}/100`)}
        ${renderBrokerMetric("Avg Response", `${Math.round(Number(metrics.avg_response_hours || 0))}h`)}
      </div>
      <p class="uw-section-note">${escapeHtml(contact.broker_notes || "")}</p>
    </section>
  `;
}

function renderBrokerMetric(label, value) {
  return `
    <div class="broker-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function buildUnderwritingComponents(appetite, claimSnapshot, ingredients, signals, evidence, actions) {
  const missingEvidence = evidence.filter((item) => item.status === "missing");
  const highSignals = signals.filter((signal) => signal.severity === "high");
  const moderateSignals = signals.filter((signal) => signal.severity === "moderate");
  const availableIngredients = ingredients.filter((item) => item.status === "available").length;
  const openClaims = Number(claimSnapshot.open_claims || 0);
  const totalIncurred = Number(claimSnapshot.total_incurred || 0);
  const recommendedAction = actions[0] || "Prepare terms after document review.";

  return [
    {
      name: "Intake & Eligibility",
      status: appetite.status || "TBD",
      tone: highSignals.length ? "alert" : "watch",
      detail: appetite.rationale || "Review account appetite, authority path, and requested coverage fit."
    },
    {
      name: "Evidence Review",
      status: missingEvidence.length ? `${missingEvidence.length} missing` : "Complete",
      tone: missingEvidence.length ? "watch" : "good",
      detail: missingEvidence.length
        ? `Missing evidence includes ${missingEvidence.slice(0, 3).map((item) => item.label).join(", ")}.`
        : "Core cyber underwriting evidence is available for review."
    },
    {
      name: "Controls Review",
      status: moderateSignals.length || highSignals.length ? "Review" : "Stable",
      tone: highSignals.length ? "alert" : moderateSignals.length ? "watch" : "good",
      detail: signals.map((signal) => signal.label).slice(0, 3).join(", ") || "No control signals available."
    },
    {
      name: "Claim Review",
      status: `${claimSnapshot.total_claims ?? 0} claims`,
      tone: openClaims || totalIncurred >= 75000 ? "alert" : totalIncurred > 0 ? "watch" : "good",
      detail: `${openClaims} open and ${formatCurrency(totalIncurred)} total incurred in linked historical claims.`
    },
    {
      name: "Pricing & Terms",
      status: "Model-ready",
      tone: "good",
      detail: "Quote and bind probability models are available in the Analytic Dashboard."
    },
    {
      name: "Authority & Next Action",
      status: formatLabel(appetite.recommended_authority || "TBD"),
      tone: highSignals.length ? "alert" : "watch",
      detail: recommendedAction
    },
    {
      name: "System Coverage",
      status: `${availableIngredients}/${ingredients.length || 0} inputs`,
      tone: availableIngredients === ingredients.length ? "good" : "watch",
      detail: "Submission documents, metadata, notes, guides, models, and claims are connected for review."
    }
  ];
}

function renderUnderwritingComponent(component) {
  const sources = Array.isArray(component.data_sources) && component.data_sources.length
    ? component.data_sources.join(", ")
    : "";

  return `
    <article class="uw-component-card ${escapeHtml(component.tone || "neutral")}">
      <div>
        <strong>${escapeHtml(component.name || "Underwriting Component")}</strong>
        <span class="status-chip ${escapeHtml(component.tone || "neutral")}">${escapeHtml(component.status || "TBD")}</span>
      </div>
      <small>${escapeHtml([component.stage, component.owner].filter(Boolean).join(" · "))}</small>
      <p>${escapeHtml(component.detail || "")}</p>
      ${sources ? `<small>Sources: ${escapeHtml(sources)}</small>` : ""}
    </article>
  `;
}

function renderUnderwritingDetails() {
  if (!underwritingSummaryPanel || !underwritingWorkbenchPanel || !underwritingExpandButton) {
    return;
  }

  if (!underwritingSystem) {
    underwritingSummaryPanel.innerHTML = "<p>Underwriting system signals are not available.</p>";
    underwritingWorkbenchPanel.innerHTML = "";
    underwritingWorkbenchPanel.classList.remove("open");
    underwritingExpandButton.textContent = "Open";
    return;
  }

  const appetite = underwritingSystem.appetite || {};
  const claimSnapshot = underwritingSystem.claim_snapshot || {};
  const evidence = Array.isArray(underwritingSystem.evidence_status)
    ? underwritingSystem.evidence_status
    : [];
  const availableEvidence = evidence.filter((item) => item.status === "available").length;

  underwritingSummaryPanel.innerHTML = `
    <div class="underwriting-summary-grid">
      <div>
        <span>Appetite</span>
        <strong>${escapeHtml(appetite.status || "TBD")}</strong>
      </div>
      <div>
        <span>Claims</span>
        <strong>${escapeHtml(String(claimSnapshot.total_claims ?? 0))}</strong>
      </div>
      <div>
        <span>Evidence</span>
        <strong>${availableEvidence}/${evidence.length || 0}</strong>
      </div>
    </div>
    <p>${escapeHtml(appetite.rationale || "Open the underwriting system to view appetite, claims, evidence, and recommended actions.")}</p>
  `;

  underwritingWorkbenchPanel.classList.toggle("open", underwritingDetailsOpen);
  underwritingWorkbenchPanel.innerHTML = underwritingDetailsOpen ? renderUnderwritingSystemView() : "";
  underwritingExpandButton.textContent = underwritingDetailsOpen ? "Close" : "Open";
}

function renderIngredientItem(item) {
  return `
    <div class="ingredient-item">
      <strong>${escapeHtml(item.name || "Ingredient")}</strong>
      <span class="status-chip ${escapeHtml(statusClass(item.status))}">${escapeHtml(formatLabel(item.status || "unknown"))}</span>
      <p>${escapeHtml(item.detail || "")}</p>
    </div>
  `;
}

function renderSignalItem(signal) {
  return `
    <div class="signal-item ${escapeHtml(statusClass(signal.severity))}">
      <strong>${escapeHtml(signal.label || "Signal")}</strong>
      <span>${escapeHtml(formatLabel(signal.severity || "unknown"))}</span>
      <p>${escapeHtml(signal.detail || "")}</p>
    </div>
  `;
}

function renderEvidenceItem(item) {
  const files = Array.isArray(item.source_files) && item.source_files.length
    ? item.source_files.join(", ")
    : "No linked file";
  return `
    <div class="evidence-item">
      <strong>${escapeHtml(item.label || "Evidence")}</strong>
      <span class="status-chip ${escapeHtml(statusClass(item.status))}">${escapeHtml(formatLabel(item.status || "unknown"))}</span>
      <small>${escapeHtml(files)}</small>
    </div>
  `;
}

function renderClaimHistoryTable(claims) {
  if (!claims.length) {
    return '<p class="empty-state">No linked claim history.</p>';
  }

  return `
    <div class="claims-table-wrap">
      <table class="claims-table">
        <thead>
          <tr>
            <th>Claim</th>
            <th>Loss Date</th>
            <th>Type</th>
            <th>Status</th>
            <th>Severity</th>
            <th>Paid</th>
            <th>Reserve</th>
          </tr>
        </thead>
        <tbody>
          ${claims.map((claim) => `
            <tr>
              <td>
                <strong>${escapeHtml(claim.claim_id)}</strong>
                <small>${escapeHtml(claim.description || claim.cause || "")}</small>
              </td>
              <td>${escapeHtml(formatDateOnly(claim.loss_date))}</td>
              <td>${escapeHtml(formatLabel(claim.claim_type))}</td>
              <td>${escapeHtml(formatLabel(claim.status))}</td>
              <td><span class="status-chip ${escapeHtml(statusClass(claim.severity))}">${escapeHtml(formatLabel(claim.severity))}</span></td>
              <td>${escapeHtml(formatCurrency(Number(claim.amount_paid || 0)))}</td>
              <td>${escapeHtml(formatCurrency(Number(claim.amount_reserved || 0)))}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function statusClass(value) {
  const normalized = String(value || "").toLowerCase();
  if (["available", "low", "closed"].includes(normalized)) {
    return "good";
  }
  if (["partial", "moderate", "open"].includes(normalized)) {
    return "watch";
  }
  if (["missing", "high"].includes(normalized)) {
    return "alert";
  }
  return "neutral";
}

function workbenchStatusClass(value) {
  const normalized = String(value || "").toLowerCase();
  if (["pass", "clear", "ready", "derived"].includes(normalized)) {
    return "good";
  }
  if (["warn", "review", "connector_ready", "not_connected"].includes(normalized)) {
    return "watch";
  }
  if (["hold", "referral", "fail", "blocked"].includes(normalized)) {
    return "alert";
  }
  return statusClass(value);
}

function scoreStoredModel(model, featureLookup) {
  const averageProbability = clamp(Number(model.average_probability || 0.5), 0.01, 0.99);
  const baseLogit = logit(averageProbability);
  const featureSteps = [];

  (model.features || []).forEach((modelFeature) => {
    const feature = featureLookup[modelFeature.key] || {
      value: Number(modelFeature.baseline_value || 0.5),
      displayValue: "TBD",
      label: modelFeature.label || modelFeature.key
    };
    const baselineValue = Number(modelFeature.baseline_value ?? 0.5);
    const coefficient = Number(modelFeature.coefficient || 0);
    const logitContribution = coefficient * (Number(feature.value || 0) - baselineValue);

    featureSteps.push({
      key: modelFeature.key,
      label: modelFeature.label || feature.label || modelFeature.key,
      displayValue: feature.displayValue,
      value: feature.value,
      logitContribution
    });
  });

  const finalLogit = baseLogit + featureSteps.reduce(
    (total, step) => total + step.logitContribution,
    0
  );

  return {
    modelName: model.model_name,
    modelType: model.model_type || "logistic_regression",
    averageProbability,
    baseLogit,
    probability: sigmoid(finalLogit),
    logit: finalLogit,
    steps: featureSteps
  };
}

function buildAnalyticsFeatureLookup(record) {
  const applicant = record.applicant || {};
  const coverage = record.coverage || {};
  const controls = record.security_controls || {};
  const riskFlags = Array.isArray(record.risk_flags) ? record.risk_flags : [];
  const openQuestions = Array.isArray(record.open_questions) ? record.open_questions : [];
  const revenue = typeof applicant.annual_revenue === "number" ? applicant.annual_revenue : 0;
  const recordsCount = typeof applicant.records_count === "number" ? applicant.records_count : 0;
  const requestedLimits = Object.values(coverage.requested_limits || {})
    .map(parseMoney)
    .filter((value) => value > 0);
  const maxLimit = requestedLimits.length ? Math.max(...requestedLimits) : 0;
  const mfaText = String(controls.mfa || "").toLowerCase();
  const edrText = String(controls.edr || "").toLowerCase();
  const backupText = String(controls.backup || "").toLowerCase();
  const patchingText = String(controls.patching || "").toLowerCase();
  const trainingText = String(controls.security_training || "").toLowerCase();
  const techText = String(applicant.technology_profile || "").toLowerCase();
  const industryText = String(applicant.industry || "").toLowerCase();
  const industryBucket = getApplicantIndustryBucket(applicant);
  const claimSnapshot = underwritingSystem && underwritingSystem.claim_snapshot ? underwritingSystem.claim_snapshot : {};
  const brokerMetrics = underwritingSystem && underwritingSystem.broker && underwritingSystem.broker.relationship_metrics
    ? underwritingSystem.broker.relationship_metrics
    : {};
  const evidence = underwritingSystem && Array.isArray(underwritingSystem.evidence_status)
    ? underwritingSystem.evidence_status
    : [];
  const availableEvidence = evidence.filter((item) => item.status === "available").length;
  const evidenceRatio = evidence.length ? availableEvidence / evidence.length : 0.75;
  const totalIncurred = Number(claimSnapshot.total_incurred || 0);
  const openClaims = Number(claimSnapshot.open_claims || 0);
  const brokerQuality = clamp(Number(brokerMetrics.data_quality_score || 70) / 100, 0, 1);
  const brokerResponseQuality = clamp(1 - Number(brokerMetrics.avg_response_hours || 18) / 48, 0, 1);
  const operationalDependency = /edi|portal|payment|reservation|warehouse|telematics|property management|ot|remote access|api/.test(techText)
    ? 0.78
    : 0.32;
  const industryPropensity = getIndustryPropensityScore(industryText, techText, industryBucket);
  const riskFlagLoad = clamp(riskFlags.length / 5, 0, 1);

  const featureInputs = [
    {
      key: "revenue_scale",
      label: "Revenue Scale",
      value: normalize(revenue, 5_000_000, 500_000_000),
      displayValue: formatCurrency(revenue),
      rawValue: revenue
    },
    {
      key: "records_exposure",
      label: "Records Exposure",
      value: normalize(recordsCount, 10_000, 1_000_000),
      displayValue: recordsCount ? recordsCount.toLocaleString() : "TBD",
      rawValue: recordsCount
    },
    {
      key: "mfa_maturity",
      label: "MFA Maturity",
      value: mfaText.includes("partial") ? 0.45 : mfaText ? 0.82 : 0.2,
      displayValue: controls.mfa || "TBD"
    },
    {
      key: "edr_coverage",
      label: "EDR Coverage",
      value: edrText.includes("crowdstrike") || edrText.includes("deployed") ? 0.84 : edrText ? 0.58 : 0.25,
      displayValue: controls.edr || "TBD"
    },
    {
      key: "backup_resilience",
      label: "Backup Resilience",
      value: backupText.includes("restore") ? 0.78 : backupText.includes("daily") ? 0.64 : 0.3,
      displayValue: controls.backup || "TBD"
    },
    {
      key: "patch_discipline",
      label: "Patch Discipline",
      value: patchingText.includes("15") ? 0.76 : patchingText.includes("30") ? 0.58 : patchingText ? 0.48 : 0.3,
      displayValue: controls.patching || "TBD"
    },
    {
      key: "security_training",
      label: "Security Training",
      value: trainingText.includes("phishing") ? 0.72 : trainingText ? 0.56 : 0.28,
      displayValue: controls.security_training || "TBD"
    },
    {
      key: "prior_claims",
      label: "Prior Claims Signal",
      value: riskFlags.some((flag) => /claim|loss|ransom/i.test(flag)) ? 0.72 : 0.28,
      displayValue: riskFlags.some((flag) => /claim|loss|ransom/i.test(flag)) ? "Elevated" : "Low / clean"
    },
    {
      key: "vendor_dependency",
      label: "Vendor Dependency",
      value: techText.includes("edi") || techText.includes("portal") || openQuestions.some((question) => /third-party|vendor|provider/i.test(question)) ? 0.7 : 0.35,
      displayValue: techText.includes("edi") || techText.includes("portal") ? "Material third-party dependency" : "Limited dependency"
    },
    {
      key: "limit_fit",
      label: "Requested Limit Fit",
      value: maxLimit && revenue ? clamp(1 - Math.abs(maxLimit / revenue - 0.1) * 2, 0.18, 0.86) : 0.5,
      displayValue: maxLimit ? `${formatCurrency(maxLimit)} max requested` : "TBD",
      rawValue: maxLimit
    },
    {
      key: "industry_propensity",
      label: "Industry Propensity",
      value: industryPropensity,
      displayValue: industryBucket
    },
    {
      key: "risk_flag_load",
      label: "Risk Flag Load",
      value: riskFlagLoad,
      displayValue: `${riskFlags.length} flags`
    },
    {
      key: "operational_dependency",
      label: "Operational Dependency",
      value: operationalDependency,
      displayValue: operationalDependency >= 0.7 ? "High dependency" : "Lower dependency"
    },
    {
      key: "claim_load",
      label: "Historical Claim Load",
      value: clamp(totalIncurred / 125000, 0, 1),
      displayValue: formatCurrency(totalIncurred)
    },
    {
      key: "open_claim_signal",
      label: "Open Claim Signal",
      value: openClaims ? 0.82 : 0.2,
      displayValue: openClaims ? `${openClaims} open` : "None open"
    },
    {
      key: "evidence_ratio",
      label: "Evidence Confidence",
      value: evidenceRatio,
      displayValue: evidence.length ? `${availableEvidence}/${evidence.length} available` : "Evidence TBD"
    },
    {
      key: "broker_quality",
      label: "Broker Data Quality",
      value: brokerQuality,
      displayValue: `${Math.round(brokerQuality * 100)}/100`
    },
    {
      key: "broker_response_quality",
      label: "Broker Response Quality",
      value: brokerResponseQuality,
      displayValue: `${Math.round(brokerResponseQuality * 100)}% response score`
    }
  ];

  return featureInputs.reduce((lookup, feature) => {
    lookup[feature.key] = feature;
    return lookup;
  }, {});
}

function ensureWhatIfValues(featureLookup) {
  Object.values(featureLookup || {}).forEach((feature) => {
    Object.values(whatIfScenarioState).forEach((state) => {
      if (typeof state.values[feature.key] !== "number") {
        state.values[feature.key] = Number(feature.value || 0);
      }
      if (isNumericWhatIfFeature(feature.key) && typeof state.rawValues[feature.key] !== "number") {
        state.rawValues[feature.key] = Number(feature.rawValue || 0);
      }
    });
  });
}

function renderWhatIfView() {
  const configs = getWhatIfFeatureConfigs();

  return `
    <section class="what-if-workspace">
      <div class="what-if-sticky">
        <label class="what-if-model-picker">
          <span>Scenario Model</span>
          <select data-what-if-model-select>
            <option value="quote" ${activeWhatIfModel === "quote" ? "selected" : ""}>Quote</option>
            <option value="bind" ${activeWhatIfModel === "bind" ? "selected" : ""}>Bind</option>
          </select>
        </label>
        <div class="what-if-summary" id="whatIfSummary">
          ${renderWhatIfSummary()}
        </div>
      </div>
      <div class="what-if-waterfall" id="whatIfWaterfall">
        ${renderWhatIfWaterfall()}
      </div>
      <div class="what-if-controls">
        ${Object.values(configs)
          .map((config) => renderWhatIfControl(config))
          .join("")}
      </div>
    </section>
  `;
}

function getWhatIfScenario() {
  if (!currentAnalytics || !currentAnalyticsFeatureLookup) {
    return null;
  }

  const model = getWhatIfModel(activeWhatIfModel);
  const currentModel = activeWhatIfModel === "bind" ? currentAnalytics.bind : currentAnalytics.quote;
  const scenarioModel = scoreStoredModel(model, buildWhatIfFeatureLookup());
  const delta = scenarioModel.probability - currentModel.probability;
  const label = activeWhatIfModel === "bind" ? "Bind Scenario" : "Quote Scenario";

  return { currentModel, scenarioModel, delta, label };
}

function renderWhatIfSummary() {
  const scenario = getWhatIfScenario();
  if (!scenario) {
    return '<p class="empty-state">Select a submission to run What If scenarios.</p>';
  }

  return `
    ${renderScoreCard(scenario.label, scenario.scenarioModel, "Recalculated from the scenario values below")}
    <div class="scenario-delta ${scenario.delta >= 0 ? "positive" : "negative"}">
      Scenario change vs current: ${formatPercentContribution(scenario.delta)}
    </div>
  `;
}

function renderWhatIfWaterfall() {
  const scenario = getWhatIfScenario();
  if (!scenario) {
    return "";
  }

  return `
    <div class="model-section compact-model-section">
      <h4>${escapeHtml(scenario.scenarioModel.modelName || "Scenario Model")}</h4>
      ${renderProbabilityWaterfall(scenario.scenarioModel)}
    </div>
  `;
}

function updateWhatIfResult() {
  const summary = analyticsPanel && analyticsPanel.querySelector("#whatIfSummary");
  const waterfall = analyticsPanel && analyticsPanel.querySelector("#whatIfWaterfall");
  if (summary) {
    summary.innerHTML = renderWhatIfSummary();
  }
  if (waterfall) {
    waterfall.innerHTML = renderWhatIfWaterfall();
  }
}

function updateWhatIfView() {
  const view = analyticsPanel && analyticsPanel.querySelector('[data-analytics-view="what-if"]');
  if (view) {
    view.innerHTML = renderWhatIfView();
    return;
  }

  updateWhatIfResult();
}

function updateWhatIfFeatureDisplay(key) {
  const display = analyticsPanel && analyticsPanel.querySelector(`[data-what-if-display="${key}"]`);
  const state = getActiveWhatIfState();
  if (display) {
    display.textContent = isNumericWhatIfFeature(key)
      ? formatRawWhatIfValue(key, state.rawValues[key])
      : formatWhatIfFeatureValue(key, state.values[key]);
  }
}

function buildWhatIfFeatureLookup() {
  const state = getActiveWhatIfState();
  return Object.values(currentAnalyticsFeatureLookup || {}).reduce((lookup, feature) => {
    let value = typeof state.values[feature.key] === "number" ? state.values[feature.key] : feature.value;
    let displayValue = formatWhatIfFeatureValue(feature.key, value);

    if (isNumericWhatIfFeature(feature.key)) {
      const rawValue = typeof state.rawValues[feature.key] === "number" ? state.rawValues[feature.key] : feature.rawValue;
      value = rawToModelValue(feature.key, rawValue);
      displayValue = formatRawWhatIfValue(feature.key, rawValue);
    }

    lookup[feature.key] = {
      ...feature,
      value,
      displayValue
    };
    return lookup;
  }, {});
}

function getWhatIfModel(modelName) {
  if (modelName === "bind") {
    return analyticsModels && analyticsModels.bind ? analyticsModels.bind : getFallbackBindModel();
  }

  return analyticsModels && analyticsModels.quote ? analyticsModels.quote : getFallbackQuoteModel();
}

function renderWhatIfControl(config) {
  const current = currentAnalyticsFeatureLookup && currentAnalyticsFeatureLookup[config.key]
    ? currentAnalyticsFeatureLookup[config.key]
    : { value: 0, displayValue: "TBD" };
  const state = getActiveWhatIfState();
  const value = typeof state.values[config.key] === "number" ? state.values[config.key] : current.value;

  const definition = getFeatureDefinition(config.key);
  const labelHtml = renderFeatureNameWithHelp(config.key, config.label, definition);

  if (config.type === "binary") {
    return `
      <div class="what-if-control">
        <div class="what-if-control-heading">
          <strong>${labelHtml}</strong>
          <small>Current: ${escapeHtml(current.displayValue)}</small>
        </div>
        <div class="binary-option-row">
          ${config.options
            .map((option) => `
              <button
                class="binary-option ${nearlyEqual(value, option.value) ? "active" : ""}"
                type="button"
                data-what-if-option
                data-what-if-feature-key="${escapeHtml(config.key)}"
                data-what-if-value="${option.value}"
              >
                ${escapeHtml(option.label)}
              </button>
            `)
            .join("")}
        </div>
        <span class="what-if-value" data-what-if-display="${escapeHtml(config.key)}">${escapeHtml(formatWhatIfFeatureValue(config.key, value))}</span>
      </div>
    `;
  }

  if (config.type === "select") {
    return `
      <label class="what-if-control">
        <div class="what-if-control-heading">
          <strong>${labelHtml}</strong>
          <small>Current: ${escapeHtml(current.displayValue)}</small>
        </div>
        <select data-what-if-feature="${escapeHtml(config.key)}">
          ${config.options
            .map((option) => `
              <option value="${option.value}" ${nearlyEqual(value, option.value) ? "selected" : ""}>${escapeHtml(option.label)}</option>
            `)
            .join("")}
        </select>
        <span class="what-if-value" data-what-if-display="${escapeHtml(config.key)}">${escapeHtml(formatWhatIfFeatureValue(config.key, value))}</span>
      </label>
    `;
  }

  const rawValue = typeof state.rawValues[config.key] === "number" ? state.rawValues[config.key] : current.rawValue;
  const sliderValue = rawValue;
  const currentPercent = getLinearRawPercent(config.key, getFeatureCurrentRaw(config.key));

  return `
    <label class="what-if-control">
      <div class="what-if-control-heading">
        <strong>${labelHtml}</strong>
      </div>
      <div class="range-reference">
        <span>${escapeHtml(formatRawReferenceValue(config.key, getFeatureRawMin(config.key)))}</span>
        <span>${escapeHtml(formatRawReferenceValue(config.key, getFeatureRawMax(config.key)))}</span>
      </div>
      <div class="range-input-wrap">
        <input
          type="range"
          min="${getFeatureRawMin(config.key)}"
          max="${getFeatureRawMax(config.key)}"
          step="${getNumericStep(config.key)}"
          value="${sliderValue}"
          data-what-if-control="numeric"
          data-what-if-feature="${escapeHtml(config.key)}"
        />
        <span
          class="range-current-marker"
          style="--current-position: ${currentPercent}%"
          aria-label="Current ${escapeHtml(formatRawReferenceValue(config.key, getFeatureCurrentRaw(config.key)))}"
        ></span>
      </div>
      <span class="what-if-value" data-what-if-display="${escapeHtml(config.key)}">${escapeHtml(formatRawWhatIfValue(config.key, rawValue))}</span>
    </label>
  `;
}

function getWhatIfFeatureConfigs() {
  const metadataFeatures = analyticsFeatureMetadata && analyticsFeatureMetadata.features
    ? analyticsFeatureMetadata.features
    : {};
  const configs = {
    revenue_scale: {
      key: "revenue_scale",
      label: getFeatureMetadata("revenue_scale").label || "Revenue Scale",
      type: "range",
      rawMin: getFeatureRawMin("revenue_scale"),
      rawMax: getFeatureRawMax("revenue_scale")
    },
    records_exposure: {
      key: "records_exposure",
      label: getFeatureMetadata("records_exposure").label || "Records Exposure",
      type: "range",
      rawMin: getFeatureRawMin("records_exposure"),
      rawMax: getFeatureRawMax("records_exposure")
    },
    mfa_maturity: {
      key: "mfa_maturity",
      label: getFeatureMetadata("mfa_maturity").label || "MFA Maturity",
      type: "select",
      options: metadataFeatures.mfa_maturity && metadataFeatures.mfa_maturity.options || [
        { label: "No MFA", value: 0.2 },
        { label: "Partial MFA", value: 0.45 },
        { label: "Full MFA", value: 0.82 }
      ]
    },
    edr_coverage: {
      key: "edr_coverage",
      label: getFeatureMetadata("edr_coverage").label || "EDR Coverage",
      type: "select",
      options: metadataFeatures.edr_coverage && metadataFeatures.edr_coverage.options || [
        { label: "No EDR", value: 0.25 },
        { label: "Partial EDR", value: 0.58 },
        { label: "Broad EDR", value: 0.84 }
      ]
    },
    backup_resilience: {
      key: "backup_resilience",
      label: getFeatureMetadata("backup_resilience").label || "Backup Resilience",
      type: "select",
      options: metadataFeatures.backup_resilience && metadataFeatures.backup_resilience.options || [
        { label: "Weak", value: 0.3 },
        { label: "Daily Backup", value: 0.64 },
        { label: "Restore Tested", value: 0.78 }
      ]
    },
    patch_discipline: {
      key: "patch_discipline",
      label: getFeatureMetadata("patch_discipline").label || "Patch Discipline",
      type: "select",
      options: metadataFeatures.patch_discipline && metadataFeatures.patch_discipline.options || [
        { label: "Slow", value: 0.3 },
        { label: "30 Days", value: 0.58 },
        { label: "15 Days", value: 0.76 }
      ]
    },
    security_training: {
      key: "security_training",
      label: getFeatureMetadata("security_training").label || "Security Training",
      type: "select",
      options: metadataFeatures.security_training && metadataFeatures.security_training.options || [
        { label: "None", value: 0.28 },
        { label: "Annual", value: 0.56 },
        { label: "Phishing Sim", value: 0.72 }
      ]
    },
    prior_claims: {
      key: "prior_claims",
      label: getFeatureMetadata("prior_claims").label || "Prior Claims Signal",
      type: "binary",
      options: metadataFeatures.prior_claims && metadataFeatures.prior_claims.options || [
        { label: "No", value: 0.28 },
        { label: "Yes", value: 0.72 }
      ]
    },
    vendor_dependency: {
      key: "vendor_dependency",
      label: getFeatureMetadata("vendor_dependency").label || "Vendor Dependency",
      type: "binary",
      options: metadataFeatures.vendor_dependency && metadataFeatures.vendor_dependency.options || [
        { label: "Limited", value: 0.35 },
        { label: "Material", value: 0.7 }
      ]
    },
    limit_fit: {
      key: "limit_fit",
      label: getFeatureMetadata("limit_fit").label || "Requested Limit Fit",
      type: "range",
      rawMin: getFeatureRawMin("limit_fit"),
      rawMax: getFeatureRawMax("limit_fit")
    }
  };

  return configs;
}

function updateWhatIfFeatureValueFromField(field) {
  const key = field.dataset.whatIfFeature;
  const state = getActiveWhatIfState();

  if (field.dataset.whatIfControl === "numeric") {
    const rawValue = Number(field.value);
    const normalizedRawValue = normalizeScenarioRawValue(key, rawValue);
    state.rawValues[key] = normalizedRawValue;
    state.values[key] = rawToModelValue(key, normalizedRawValue);
    field.value = normalizedRawValue;
    return;
  }

  state.values[key] = Number(field.value);
}

function createEmptyWhatIfScenarioState() {
  return {
    quote: { values: {}, rawValues: {} },
    bind: { values: {}, rawValues: {} }
  };
}

function getActiveWhatIfState() {
  if (!whatIfScenarioState[activeWhatIfModel]) {
    whatIfScenarioState[activeWhatIfModel] = { values: {}, rawValues: {} };
  }

  return whatIfScenarioState[activeWhatIfModel];
}

function getFeatureMetadata(key) {
  return analyticsFeatureMetadata && analyticsFeatureMetadata.features && analyticsFeatureMetadata.features[key]
    ? analyticsFeatureMetadata.features[key]
    : {};
}

function getFeatureDefinition(key) {
  return getFeatureMetadata(key).definition || "Model feature used to calculate quote and bind probability.";
}

function isNumericWhatIfFeature(key) {
  return getFeatureMetadata(key).control_type === "numeric" || ["revenue_scale", "records_exposure", "limit_fit"].includes(key);
}

function getFeatureRawMin(key) {
  const metadata = getFeatureMetadata(key);
  return Number(metadata.raw_min ?? 0);
}

function getFeatureRawMax(key) {
  const metadata = getFeatureMetadata(key);
  return Number(metadata.raw_max ?? 1);
}

function getFeatureCurrentRaw(key) {
  const feature = currentAnalyticsFeatureLookup && currentAnalyticsFeatureLookup[key];
  return Number(feature && typeof feature.rawValue === "number" ? feature.rawValue : getFeatureRawMin(key));
}

function getLinearRawPercent(key, rawValue) {
  const raw = Number(rawValue || 0);
  const min = getFeatureRawMin(key);
  const max = getFeatureRawMax(key);
  if (max === min) {
    return 0;
  }

  return clamp(((raw - min) / (max - min)) * 100, 0, 100);
}

function getNumericStep(key) {
  const span = Math.abs(getFeatureRawMax(key) - getFeatureRawMin(key));
  if (!span) {
    return 1;
  }

  return 1;
}

function normalizeScenarioRawValue(key, rawValue) {
  const min = getFeatureRawMin(key);
  const max = getFeatureRawMax(key);
  const value = clamp(Number(rawValue || 0), min, max);

  if (nearlyEqual(value, min) || nearlyEqual(value, max)) {
    return value;
  }

  return clamp(roundToSecondHighestPlace(value), min, max);
}

function rawToModelValue(key, rawValue) {
  const raw = Number(rawValue || 0);

  if (key === "revenue_scale") {
    const normalization = getFeatureMetadata(key).normalization || {};
    return normalize(raw, Number(normalization.min || 5_000_000), Number(normalization.max || 500_000_000));
  }

  if (key === "records_exposure") {
    const normalization = getFeatureMetadata(key).normalization || {};
    return normalize(raw, Number(normalization.min || 10_000), Number(normalization.max || 1_000_000));
  }

  if (key === "limit_fit") {
    const normalization = getFeatureMetadata(key).normalization || {};
    const rawValues = getActiveWhatIfState().rawValues;
    const revenue = typeof rawValues.revenue_scale === "number"
      ? rawValues.revenue_scale
      : getFeatureCurrentRaw("revenue_scale");
    const targetRatio = Number(normalization.target_ratio || 0.1);
    const min = Number(normalization.min || 0.18);
    const max = Number(normalization.max || 0.86);
    return revenue ? clamp(1 - Math.abs(raw / revenue - targetRatio) * 2, min, max) : 0.5;
  }

  return raw;
}

function roundToSecondHighestPlace(value) {
  const numericValue = Number(value || 0);
  if (!Number.isFinite(numericValue) || numericValue === 0) {
    return numericValue;
  }

  const magnitude = Math.floor(Math.log10(Math.abs(numericValue)));
  const unit = 10 ** Math.max(magnitude - 1, 0);
  return Math.round(numericValue / unit) * unit;
}

function formatRawWhatIfValue(key, rawValue) {
  const metadata = getFeatureMetadata(key);
  const numericValue = Number(rawValue || 0);
  const value = nearlyEqual(numericValue, getFeatureRawMin(key)) || nearlyEqual(numericValue, getFeatureRawMax(key))
    ? numericValue
    : roundToSecondHighestPlace(numericValue);

  if (metadata.raw_format === "currency") {
    return formatCurrency(value);
  }

  return Number.isFinite(value) ? value.toLocaleString() : "TBD";
}

function formatRawReferenceValue(key, rawValue) {
  const metadata = getFeatureMetadata(key);
  const value = Number(rawValue || 0);

  if (metadata.raw_format === "currency") {
    return formatCurrency(value);
  }

  return Number.isFinite(value) ? value.toLocaleString() : "TBD";
}

function formatWhatIfFeatureValue(key, value) {
  const numericValue = Number(value || 0);
  const config = getWhatIfFeatureConfigs()[key];
  if (config && Array.isArray(config.options)) {
    const option = config.options.find((item) => nearlyEqual(item.value, numericValue));
    if (option) {
      return option.label;
    }
  }

  return `${Math.round(numericValue * 100)}%`;
}

function renderFeatureNameWithHelp(key, label, definition = null) {
  const tooltip = `${label}: ${definition || getFeatureDefinition(key)}`;
  return `
    <span class="feature-name" data-help-text="${escapeHtml(tooltip)}" title="${escapeHtml(tooltip)}">
      <span class="feature-label-text">${escapeHtml(label)}</span>
    </span>
  `;
}

function getFeatureNameTooltipTarget(target) {
  const element = target instanceof Element ? target : target && target.parentElement;
  return element ? element.closest(".feature-name[data-help-text]") : null;
}

function showFeatureTooltip(featureName, event) {
  if (!activeFeatureTooltip) {
    activeFeatureTooltip = document.createElement("div");
    activeFeatureTooltip.className = "floating-feature-tooltip";
    document.body.appendChild(activeFeatureTooltip);
  }

  activeFeatureTooltip.textContent = featureName.dataset.helpText || "";
  activeFeatureTooltip.classList.add("visible");
  positionFeatureTooltip(event);
}

function positionFeatureTooltip(event) {
  if (!activeFeatureTooltip) {
    return;
  }

  const gap = 12;
  const tooltipRect = activeFeatureTooltip.getBoundingClientRect();
  const left = Math.min(
    Math.max(event.clientX + gap, 8),
    window.innerWidth - tooltipRect.width - 8
  );
  const top = Math.min(
    Math.max(event.clientY - tooltipRect.height - gap, 8),
    window.innerHeight - tooltipRect.height - 8
  );

  activeFeatureTooltip.style.left = `${left}px`;
  activeFeatureTooltip.style.top = `${top}px`;
}

function hideFeatureTooltip() {
  if (!activeFeatureTooltip) {
    return;
  }

  activeFeatureTooltip.classList.remove("visible");
}

function renderModelView(label, model, description, record = null, modelKey = "quote") {
  return `
    ${renderScoreCard(label, model, description)}
    ${renderSupplementalModelResults(record, modelKey)}
    <div class="model-section">
      <h4>${escapeHtml(model.modelName || "Logistic Regression")}</h4>
      <div class="model-caption">
        Starts at average probability, applies each feature's marginal contribution, and ends at current probability.
      </div>
      ${renderProbabilityWaterfall(model)}
      ${renderModelInterpretationSummary(model)}
    </div>
  `;
}

function renderSupplementalModelResults(record, modelKey) {
  const results = buildSupplementalModelResults(record, modelKey);
  return `
    <section class="supplemental-model-section">
      <div class="card-heading">
        <h4>Supplemental Modeling Results</h4>
        <span class="claim-system-tag">${escapeHtml(modelKey === "bind" ? "Bind support" : "Quote support")}</span>
      </div>
      <div class="supplemental-model-list">
        ${results.map((result) => `
          <button
            class="model-result-row ${escapeHtml(result.tone)} ${result.modelKey === activeSupplementalModelKey ? "active" : ""}"
            type="button"
            data-supplemental-model="${escapeHtml(result.modelKey)}"
          >
            <div>
              <strong>${escapeHtml(result.label)}</strong>
              <small>${escapeHtml(result.detail)}</small>
            </div>
            <div class="model-result-score">
              <span>${escapeHtml(result.value)}</span>
              <i style="width: ${Math.round(result.score * 100)}%"></i>
            </div>
          </button>
        `).join("")}
      </div>
      <div class="supplemental-model-detail" id="supplementalModelDetail">
        ${renderSupplementalModelDetail(activeSupplementalModelKey)}
      </div>
    </section>
  `;
}

function buildSupplementalModelResults(record, modelKey) {
  const supplementalScores = currentAnalytics && currentAnalytics.supplemental
    ? currentAnalytics.supplemental
    : {};
  const brokerMetrics = underwritingSystem && underwritingSystem.broker && underwritingSystem.broker.relationship_metrics
    ? underwritingSystem.broker.relationship_metrics
    : {};
  const evidence = underwritingSystem && Array.isArray(underwritingSystem.evidence_status)
    ? underwritingSystem.evidence_status
    : [];
  const brokerQuality = clamp(Number(brokerMetrics.data_quality_score || 70) / 100, 0, 1);
  const brokerResponse = clamp(1 - Number(brokerMetrics.avg_response_hours || 18) / 48, 0, 1);
  const evidenceRatio = evidence.length
    ? evidence.filter((item) => item.status === "available").length / evidence.length
    : 0.7;
  const industryScore = currentAnalyticsFeatureLookup && currentAnalyticsFeatureLookup.industry_propensity
    ? Number(currentAnalyticsFeatureLookup.industry_propensity.value || 0)
    : 0.5;
  const placementConfidence = clamp(
    (currentAnalytics && currentAnalytics[modelKey] ? currentAnalytics[modelKey].probability : 0.5) * 0.5
      + brokerQuality * 0.25 + brokerResponse * 0.15 + evidenceRatio * 0.1,
    0,
    1
  );

  return [
    ...SUPPLEMENTAL_MODEL_KEYS
      .filter((key) => supplementalScores[key])
      .map((key) => makeSupplementalResult(key, supplementalScores[key].probability)),
    makeSupplementalResult("industry_propensity", industryScore),
    makeSupplementalResult("broker_placement_confidence", placementConfidence),
    makeSupplementalResult("evidence_confidence", evidenceRatio)
  ];
}

function makeSupplementalResult(modelKey, score) {
  const definition = SUPPLEMENTAL_RESULT_DEFINITIONS[modelKey] || {
    label: formatLabel(modelKey),
    detail: "Supplemental underwriting model result",
    higherIsRisk: true
  };
  const value = formatPercent(score);
  let tone = "watch";
  if (definition.higherIsRisk) {
    tone = score >= 0.62 ? "alert" : score >= 0.38 ? "watch" : "good";
  } else {
    tone = score >= 0.72 ? "good" : score >= 0.48 ? "watch" : "alert";
  }

  return {
    modelKey,
    label: definition.label,
    value,
    detail: definition.detail,
    score: clamp(score, 0, 1),
    tone
  };
}

function updateSupplementalModelDetail() {
  if (!analyticsPanel) {
    return;
  }

  analyticsPanel.querySelectorAll("[data-supplemental-model]").forEach((button) => {
    button.classList.toggle("active", button.dataset.supplementalModel === activeSupplementalModelKey);
  });

  const detail = analyticsPanel.querySelector("#supplementalModelDetail");
  if (detail) {
    detail.innerHTML = renderSupplementalModelDetail(activeSupplementalModelKey);
  }
}

function renderSupplementalModelDetail(modelKey) {
  if (modelKey === "industry_propensity") {
    return renderIndustryPropensityDetail();
  }

  if (["broker_placement_confidence", "evidence_confidence"].includes(modelKey)) {
    return renderSupportMetricDetail(modelKey);
  }

  const model = currentAnalytics && currentAnalytics.supplemental
    ? currentAnalytics.supplemental[modelKey]
    : null;
  const definition = SUPPLEMENTAL_RESULT_DEFINITIONS[modelKey] || {};

  if (!model) {
    return '<p class="empty-state">Select a model result to view details.</p>';
  }

  return `
    <div class="model-section supplemental-waterfall-section">
      <h4>${escapeHtml(definition.label || model.modelName || "Supplemental GLM")}</h4>
      <div class="model-caption">
        Stored GLM result. Starts at average probability, applies the feature coefficients, and ends at current probability.
      </div>
      ${renderProbabilityWaterfall(model)}
      ${renderModelInterpretationSummary(model)}
    </div>
  `;
}

function renderSupportMetricDetail(modelKey) {
  const definition = SUPPLEMENTAL_RESULT_DEFINITIONS[modelKey] || {};
  const featureKey = modelKey === "evidence_confidence" ? "evidence_ratio" : "broker_quality";
  const feature = currentAnalyticsFeatureLookup && currentAnalyticsFeatureLookup[featureKey];

  return `
    <div class="support-metric-detail">
      <h4>${escapeHtml(definition.label || "Support Metric")}</h4>
      <p>${escapeHtml(definition.detail || "")}</p>
      <strong>${escapeHtml(feature ? feature.displayValue : "TBD")}</strong>
      <small>This is a decision-support metric rather than a stored GLM model.</small>
    </div>
  `;
}

function renderIndustryPropensityDetail() {
  const model = analyticsModels && analyticsModels.industryPropensity ? analyticsModels.industryPropensity : {};
  const history = Array.isArray(model.industry_history) ? model.industry_history : [];
  const applicant = selectedSubmission && selectedSubmission.record && selectedSubmission.record.applicant
    ? selectedSubmission.record.applicant
    : {};
  const currentBucket = getApplicantIndustryBucket(applicant);
  const maxScore = Math.max(...history.map((item) => Number(item.score || 0)), 0.01);
  const portfolio = model.portfolio || {};

  return `
    <div class="industry-propensity-detail">
      <div class="card-heading">
        <h4>Industry Propensity Benchmark</h4>
        <span class="claim-system-tag">${escapeHtml(currentBucket)}</span>
      </div>
      <p class="model-caption">
        Calculated from ${escapeHtml(String(portfolio.submission_count || history.reduce((sum, item) => sum + Number(item.submission_count || 0), 0)))} submissions and linked claims in the dummy claim system.
      </p>
      <div class="industry-bar-chart">
        ${history.map((item) => {
          const score = Number(item.score || 0);
          const isCurrent = item.industry === currentBucket;
          const claimCompanyCount = Number(item.claim_company_count || 0);
          const submissionCount = Number(item.submission_count || 0);
          const claimRate = submissionCount ? claimCompanyCount / submissionCount : 0;
          return `
            <div class="industry-bar-row ${isCurrent ? "current" : ""}">
              <span>${escapeHtml(item.industry)}</span>
              <div class="industry-bar-track">
                <i style="width: ${Math.max(score / maxScore * 100, 4)}%"></i>
              </div>
              <strong>${formatPercent(score)}</strong>
              <small>${escapeHtml(String(submissionCount))} submissions · ${escapeHtml(String(claimCompanyCount))} with claims · ${formatPercent(claimRate)} claim rate · ${formatCurrency(Number(item.average_claim_severity || 0))} avg severity</small>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

function renderPortfolioAnalyticsView() {
  if (!portfolioDashboard) {
    return '<p class="empty-state">Portfolio analytics are not available.</p>';
  }

  const overview = portfolioDashboard.overview || {};
  const dashboard = portfolioDashboard.dashboard || {};
  const queue = Array.isArray(portfolioDashboard.queue) ? portfolioDashboard.queue : [];
  const currentRow = selectedSubmission
    ? queue.find((row) => row.id === selectedSubmission.id)
    : null;
  const industryMix = Array.isArray(dashboard.industry_mix) ? dashboard.industry_mix.slice(0, 8) : [];
  const brokerMix = Array.isArray(dashboard.broker_mix) ? dashboard.broker_mix.slice(0, 6) : [];
  const maxIndustryIncurred = Math.max(...industryMix.map((row) => Number(row.total_incurred || 0)), 1);

  return `
    <section class="portfolio-analytics-view">
      <div class="portfolio-hero-row">
        <article class="portfolio-focus-card">
          <span>Current Account Queue Position</span>
          <strong>${escapeHtml(currentRow ? currentRow.priority : "TBD")}</strong>
          <p>${escapeHtml(currentRow ? currentRow.next_action : "Select a submission to view queue context.")}</p>
        </article>
        <div class="portfolio-metric-grid">
          ${renderPortfolioMetric("Submissions", overview.submission_count)}
          ${renderPortfolioMetric("Ready", overview.ready_count)}
          ${renderPortfolioMetric("Referral", overview.referral_count)}
          ${renderPortfolioMetric("Avg Readiness", `${Math.round(Number(overview.avg_quote_readiness || 0))}%`)}
        </div>
      </div>

      <section class="portfolio-section">
        <div class="card-heading">
          <h4>Industry Loss And Readiness</h4>
          <span class="claim-system-tag">${escapeHtml(String(industryMix.length))} industries</span>
        </div>
        <div class="portfolio-industry-list">
          ${industryMix.map((row) => `
            <div class="portfolio-bar-row">
              <span>${escapeHtml(row.industry)}</span>
              <div class="portfolio-bar-track">
                <i style="width: ${Math.max(Number(row.total_incurred || 0) / maxIndustryIncurred * 100, 4)}%"></i>
              </div>
              <strong>${escapeHtml(formatCurrency(Number(row.total_incurred || 0)))}</strong>
              <small>${escapeHtml(String(row.submission_count || 0))} submissions | ${escapeHtml(String(row.claim_count || 0))} claims | ${Math.round(Number(row.avg_readiness || 0))}% readiness</small>
            </div>
          `).join("")}
        </div>
      </section>

      <section class="portfolio-section">
        <div class="card-heading">
          <h4>Broker Pipeline Mix</h4>
          <span class="claim-system-tag">Demo portfolio</span>
        </div>
        <div class="broker-pipeline-grid">
          ${brokerMix.map((broker) => `
            <article>
              <strong>${escapeHtml(broker.broker_name)}</strong>
              <small>${escapeHtml(String(broker.submission_count || 0))} submissions | ${escapeHtml(String(broker.ready || 0))} ready | ${escapeHtml(String(broker.referral || 0))} referral</small>
              <div class="score-meter"><i style="width: ${Math.round(Number(broker.avg_readiness || 0))}%"></i></div>
            </article>
          `).join("")}
        </div>
      </section>
    </section>
  `;
}

function renderPortfolioMetric(label, value) {
  return `
    <article>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value ?? 0))}</strong>
    </article>
  `;
}

function getIndustryPropensityScore(industryText, techText, industryBucket = "") {
  const bucket = industryBucket || resolveIndustryBucket(industryText, techText);
  const history = analyticsModels && analyticsModels.industryPropensity && Array.isArray(analyticsModels.industryPropensity.industry_history)
    ? analyticsModels.industryPropensity.industry_history
    : [];
  const match = history.find((item) => item.industry === bucket);
  return match ? Number(match.score || 0.5) : 0.5;
}

function getApplicantIndustryBucket(applicant = {}) {
  return applicant.industry_bucket
    || applicant.industry_group
    || resolveIndustryBucket(
      String(applicant.industry || "").toLowerCase(),
      String(applicant.technology_profile || "").toLowerCase()
    );
}

function resolveIndustryBucket(industryText, techText = "") {
  const combined = `${industryText} ${techText}`.toLowerCase();
  if (/fintech|payment/.test(combined)) {
    return "Fintech / Payments";
  }
  if (/saas|software|api|technology/.test(combined)) {
    return "SaaS / Software";
  }
  if (/health|senior|pharmacy|phi|hipaa/.test(combined)) {
    return "Healthcare / Pharmacy";
  }
  if (/university|education/.test(combined)) {
    return "Education";
  }
  if (/manufacturing|industrial|ot|remote access/.test(combined)) {
    return "Manufacturing / OT";
  }
  if (/food distribution|warehouse|edi|logistics/.test(combined)) {
    return "Food Distribution / Logistics";
  }
  if (/hospitality|hotel|retail|pci/.test(combined)) {
    return "Hospitality / Retail";
  }
  if (/marina|recreation/.test(combined)) {
    return "Marina / Recreation";
  }
  if (/construction|contracting/.test(combined)) {
    return "Construction";
  }
  if (/professional|law|consulting|accounting|managed service|architecture/.test(combined)) {
    return "Professional Services";
  }
  return "Professional Services";
}

function renderScoreCard(label, model, description) {
  const percent = Math.round(model.probability * 100);
  const averagePercent = Math.round(model.averageProbability * 100);
  return `
    <div class="score-card">
      <span>${escapeHtml(label)}</span>
      <strong>${percent}%</strong>
      <div class="score-meter" aria-hidden="true">
        <i style="width: ${percent}%"></i>
      </div>
      <small>${escapeHtml(description)}</small>
      <em>Average ${averagePercent}% -> Current ${percent}%</em>
    </div>
  `;
}

function renderProbabilityWaterfall(model) {
  const sortedSteps = getDisplayProbabilitySteps(model);
  const maxContribution = Math.max(
    ...sortedSteps.map((step) => Math.abs(step.probabilityContribution)),
    Math.abs(model.probability - model.averageProbability),
    0.01
  );

  return `
    <div class="probability-waterfall">
      ${renderProbabilityAnchor("Average Probability", model.averageProbability)}
      ${sortedSteps
        .map((step) => {
          const contribution = step.probabilityContribution;
          const width = Math.max(Math.abs(contribution) / maxContribution * 48, 3);
          const direction = contribution >= 0 ? "positive" : "negative";
          const intensity = Math.abs(contribution) / maxContribution;
          return `
            <div class="waterfall-row marginal-row">
              ${renderFeatureNameWithHelp(step.key, step.label)}
              <div class="waterfall-track" title="Current value: ${escapeHtml(step.displayValue)}">
                <i class="${direction}" style="width: ${width}%; ${direction === "positive" ? "left: 50%" : `right: 50%`}; background: ${getContributionColor(direction, intensity)}"></i>
              </div>
              <strong>${formatPercentContribution(contribution)}</strong>
            </div>
          `;
        })
        .join("")}
      ${renderProbabilityAnchor("Current Probability", model.probability)}
    </div>
  `;
}

function getDisplayProbabilitySteps(model) {
  const sortedRawSteps = [...model.steps].sort(
    (left, right) => right.logitContribution - left.logitContribution
  );
  return buildOrderedProbabilitySteps(
    sortedRawSteps,
    model.baseLogit || logit(model.averageProbability)
  );
}

function renderModelInterpretationSummary(model) {
  const steps = getDisplayProbabilitySteps(model);
  const positiveDrivers = [...steps]
    .filter((step) => step.probabilityContribution > 0)
    .sort((left, right) => right.probabilityContribution - left.probabilityContribution)
    .slice(0, 3);
  const negativeDrivers = [...steps]
    .filter((step) => step.probabilityContribution < 0)
    .sort((left, right) => left.probabilityContribution - right.probabilityContribution)
    .slice(0, 3);
  const direction = model.probability >= model.averageProbability ? "above" : "below";

  return `
    <section class="interpretation-summary">
      <h4>Model Interpretation</h4>
      <p>
        This account is ${formatPercent(model.probability)} versus a model average of ${formatPercent(model.averageProbability)},
        placing it ${direction} the average by ${formatPercent(Math.abs(model.probability - model.averageProbability))}.
      </p>
      <p>
        Largest positive drivers: ${formatDriverList(positiveDrivers)}.
        Largest negative drivers: ${formatDriverList(negativeDrivers)}.
      </p>
    </section>
  `;
}

function formatDriverList(steps) {
  if (!steps.length) {
    return "none";
  }

  return steps
    .map((step) => `${step.label} (${formatPercentContribution(step.probabilityContribution)})`)
    .join(", ");
}

function buildOrderedProbabilitySteps(steps, startingLogit) {
  let runningLogit = startingLogit;

  return steps.map((step) => {
    const beforeProbability = sigmoid(runningLogit);
    runningLogit += step.logitContribution;
    const afterProbability = sigmoid(runningLogit);

    return {
      ...step,
      probabilityContribution: afterProbability - beforeProbability,
      probabilityAfter: afterProbability
    };
  });
}

function renderProbabilityAnchor(label, probability) {
  const percent = Math.round(probability * 100);
  return `
    <div class="waterfall-row anchor-row">
      <span>${escapeHtml(label)}</span>
      <div class="anchor-track">
        <i style="width: ${percent}%"></i>
      </div>
      <strong>${percent}%</strong>
    </div>
  `;
}

function sigmoid(value) {
  return 1 / (1 + Math.exp(-value));
}

function logit(probability) {
  const bounded = clamp(probability, 0.01, 0.99);
  return Math.log(bounded / (1 - bounded));
}

function normalize(value, min, max) {
  if (!Number.isFinite(value) || max <= min) {
    return 0.5;
  }

  return clamp((value - min) / (max - min), 0, 1);
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function nearlyEqual(left, right) {
  return Math.abs(Number(left) - Number(right)) < 0.005;
}

function parseMoney(value) {
  const number = Number(String(value || "").replace(/[^0-9.]/g, ""));
  return Number.isFinite(number) ? number : 0;
}

function formatSignedNumber(value) {
  const number = Number(value || 0);
  const sign = number >= 0 ? "+" : "";
  return `${sign}${number.toFixed(2)}`;
}

function formatPercentContribution(value) {
  const number = Number(value || 0) * 100;
  const sign = number >= 0 ? "+" : "";
  return `${sign}${number.toFixed(1)}%`;
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function getContributionColor(direction, intensity) {
  const boundedIntensity = clamp(Number(intensity || 0), 0, 1);
  const lightness = Math.round(72 - boundedIntensity * 34);
  const saturation = Math.round(62 + boundedIntensity * 28);
  const hue = direction === "positive" ? 221 : 345;
  return `hsl(${hue} ${saturation}% ${lightness}%)`;
}

function getFallbackQuoteModel() {
  return {
    model_name: "quote_prob",
    model_type: "logistic_regression",
    average_probability: 0.58,
    features: [
      { key: "revenue_scale", label: "Revenue Scale", coefficient: 0.36, baseline_value: 0.5 },
      { key: "records_exposure", label: "Records Exposure", coefficient: -0.28, baseline_value: 0.5 },
      { key: "mfa_maturity", label: "MFA Maturity", coefficient: 0.55, baseline_value: 0.5 },
      { key: "edr_coverage", label: "EDR Coverage", coefficient: 0.42, baseline_value: 0.5 },
      { key: "backup_resilience", label: "Backup Resilience", coefficient: 0.38, baseline_value: 0.5 },
      { key: "patch_discipline", label: "Patch Discipline", coefficient: 0.34, baseline_value: 0.5 },
      { key: "security_training", label: "Security Training", coefficient: 0.18, baseline_value: 0.5 },
      { key: "prior_claims", label: "Prior Claims Signal", coefficient: -0.45, baseline_value: 0.5 },
      { key: "vendor_dependency", label: "Vendor Dependency", coefficient: -0.25, baseline_value: 0.5 },
      { key: "limit_fit", label: "Requested Limit Fit", coefficient: 0.32, baseline_value: 0.5 }
    ]
  };
}

function getFallbackBindModel() {
  return {
    model_name: "bind_prob",
    model_type: "logistic_regression",
    average_probability: 0.47,
    features: [
      { key: "revenue_scale", label: "Revenue Scale", coefficient: 0.25, baseline_value: 0.5 },
      { key: "records_exposure", label: "Records Exposure", coefficient: -0.36, baseline_value: 0.5 },
      { key: "mfa_maturity", label: "MFA Maturity", coefficient: 0.72, baseline_value: 0.5 },
      { key: "edr_coverage", label: "EDR Coverage", coefficient: 0.48, baseline_value: 0.5 },
      { key: "backup_resilience", label: "Backup Resilience", coefficient: 0.46, baseline_value: 0.5 },
      { key: "patch_discipline", label: "Patch Discipline", coefficient: 0.32, baseline_value: 0.5 },
      { key: "security_training", label: "Security Training", coefficient: 0.22, baseline_value: 0.5 },
      { key: "prior_claims", label: "Prior Claims Signal", coefficient: -0.52, baseline_value: 0.5 },
      { key: "vendor_dependency", label: "Vendor Dependency", coefficient: -0.3, baseline_value: 0.5 },
      { key: "limit_fit", label: "Requested Limit Fit", coefficient: 0.44, baseline_value: 0.5 }
    ]
  };
}

async function loadStageState(submissionId) {
  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(submissionId)}/states`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load underwriting stages.");
    }

    workflowSubmittedAt = data.state && data.state.submitted_at ? data.state.submitted_at : null;
    mergeSavedStageState(data.state && data.state.stages);
    renderStageChecklist();
    renderFollowUps();
  } catch (error) {
    console.warn(error);
    renderStageChecklist("Unable to load saved stage state.");
  }
}

async function saveStageState() {
  if (!selectedSubmission) {
    return;
  }

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(selectedSubmission.id)}/states`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ stages: stageItems })
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to save underwriting stages.");
    }

    workflowSubmittedAt = data.state && data.state.submitted_at ? data.state.submitted_at : null;
    mergeSavedStageState(data.state && data.state.stages);
    renderStageChecklist();
    renderFollowUps();
  } catch (error) {
    console.warn(error);
    renderStageChecklist(error.message || "Unable to save underwriting stages.");
  }
}

async function submitWorkflow() {
  if (!selectedSubmission || !hasUnlockedCheckedStages()) {
    return;
  }

  try {
    const response = await fetch(`/api/submissions/${encodeURIComponent(selectedSubmission.id)}/states/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ stages: stageItems })
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to submit stages.");
    }

    workflowSubmittedAt = data.state && data.state.submitted_at ? data.state.submitted_at : new Date().toISOString();
    mergeSavedStageState(data.state && data.state.stages);
    renderStageChecklist();
    renderFollowUps();
  } catch (error) {
    console.warn(error);
    renderFollowUps(error.message || "Unable to submit stages.");
  }
}

function mergeSavedStageState(savedStages) {
  if (!Array.isArray(savedStages) || !savedStages.length) {
    return;
  }

  const savedByKey = new Map(savedStages.map((stage) => [stage.key, stage]));
  stageItems = stageItems.map((stage) => {
    const saved = savedByKey.get(stage.key);
    return saved
      ? {
          ...stage,
          checked: Boolean(saved.checked),
          locked: Boolean(saved.locked)
        }
      : stage;
  });
}

function renderStageChecklist(statusMessage) {
  syncWorkflowSubmitControls();

  if (!stageChecklist) {
    return;
  }

  if (statusMessage) {
    stageChecklist.innerHTML = `<p class="empty-state">${escapeHtml(statusMessage)}</p>`;
    return;
  }

  if (!stageItems.length) {
    stageChecklist.innerHTML = '<p class="empty-state">No underwriting stages found.</p>';
    return;
  }

  stageChecklist.innerHTML = stageItems
    .map((stage) => {
      const stateLabel = stage.checked ? "Completed" : stage.isCurrent ? "Current stage" : "Pending";
      return `
        <label class="stage-item ${stage.isCurrent ? "current" : ""} ${stage.checked ? "checked" : ""}">
          <input
            type="checkbox"
            data-stage-key="${escapeHtml(stage.key)}"
            ${stage.checked ? "checked" : ""}
            ${stage.locked ? "disabled" : ""}
          />
          <span>
            <strong>${escapeHtml(stage.label)}</strong>
            <small>${stage.locked ? "Submitted and locked" : stateLabel}</small>
          </span>
        </label>
      `;
    })
    .join("");
}

function syncWorkflowSubmitControls() {
  const canSubmitCheckedStages = Boolean(selectedSubmission) && hasUnlockedCheckedStages();
  if (submitWorkflowButton) {
    submitWorkflowButton.disabled = !canSubmitCheckedStages;
    submitWorkflowButton.textContent = "Submit Checked Stages";
  }

  if (workflowSubmitStatus) {
    workflowSubmitStatus.textContent = workflowSubmittedAt
      ? `Checked stages were last submitted on ${formatDateTime(workflowSubmittedAt)}. Unchecked stages and scheduled tasks remain editable.`
      : "Submitting permanently locks checked stages only. Unchecked stages and scheduled tasks remain editable.";
  }
}

function hasUnlockedCheckedStages() {
  return stageItems.some((stage) => stage.checked && !stage.locked);
}

function buildDefaultStageItems(record) {
  const currentStage = getCurrentStageKey(record);
  const stages = getUnderwritingStages();
  const currentIndex = stages.findIndex((stage) => stage.key === currentStage);

  return stages.map((stage, index) => ({
    ...stage,
    checked: currentIndex > index,
    isCurrent: currentIndex === index,
    locked: false
  }));
}

function getUnderwritingStages() {
  return [
    ["intake", "Intake"],
    ["document_collection", "Document Collection"],
    ["data_extraction", "Data Extraction"],
    ["initial_review", "Initial Review"],
    ["risk_assessment", "Risk Assessment"],
    ["clarification", "Clarification"],
    ["referral_approval", "Referral / Approval"],
    ["terms_conditions", "Terms & Conditions"],
    ["quote", "Quote"],
    ["bind_close", "Bind / Close"]
  ].map(([key, label]) => ({ key, label }));
}

function getCurrentStageKey(record) {
  const status = String(record && record.status ? record.status : "").toLowerCase();

  if (status.includes("referral")) {
    return "referral_approval";
  }

  if (status.includes("quote")) {
    return "quote";
  }

  if (status.includes("bind")) {
    return "bind_close";
  }

  if (status.includes("review")) {
    return "risk_assessment";
  }

  return "initial_review";
}

function buildKeyInfoHtml(submission) {
  return buildKeyInfoItems(submission)
    .map(
      (item) => `
        <div class="key-info-item" title="${escapeHtml(`${item.label}: ${item.value}`)}">
          <span title="${escapeHtml(item.label)}">${escapeHtml(item.label)}</span>
          <strong title="${escapeHtml(item.value)}">${escapeHtml(item.value)}</strong>
        </div>
      `
    )
    .join("");
}

function buildSummaryHtml(record) {
  if (!record) {
    return "Reserved for an AI-generated account summary, appetite fit, and recommended next action.";
  }

  if (record.summary && typeof record.summary === "object") {
    const summary = record.summary;
    const considerations = Array.isArray(summary.key_considerations)
      ? summary.key_considerations
      : [];

    return `
      <div class="summary-block">
        <p><strong>Account overview:</strong> ${escapeHtml(summary.account_overview || "Not available.")}</p>
        <p><strong>Appetite fit:</strong> ${escapeHtml(summary.appetite_fit || "Not available.")}</p>
        ${
          considerations.length
            ? `<ul>${considerations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
            : ""
        }
        <p><strong>Next action:</strong> ${escapeHtml(summary.recommended_next_action || "Review submission documents.")}</p>
      </div>
    `;
  }

  const applicant = record.applicant || {};
  return escapeHtml([
    `${applicant.insured_name || record.title} · ${applicant.industry || "Industry TBD"}`,
    `Status: ${record.status || "New"}.`,
    "Ask the chat to generate a formal cyber underwriting summary, key risks, alerts, and guidance."
  ].join(" "));
}

function buildDocumentLinks(record) {
  const documents = Array.isArray(record.documents) ? record.documents : [];

  if (!documents.length) {
    return "<p>No documents found.</p>";
  }

  return documents
    .map((document) => {
      const type = document.file_type || "file";
      const categories = formatMetadataList(document.major_categories || document.category);
      const label = categories || document.description || type;
      const target = document.url || "#";

      return `
        <div class="document-row">
          <input
            class="file-selection-checkbox"
            type="checkbox"
            value="${escapeHtml(document.file_name)}"
            checked
          />
          <button
            class="document-link"
            type="button"
            data-name="${escapeHtml(document.file_name)}"
            data-type="${escapeHtml(type)}"
            data-url="${escapeHtml(target)}"
          >
            <span>${escapeHtml(document.file_name)}</span>
            <small>${escapeHtml(type)} · ${escapeHtml(label)}</small>
          </button>
          <button
            class="document-delete-button"
            type="button"
            data-delete-document="${escapeHtml(document.file_name)}"
            aria-label="Delete ${escapeHtml(document.file_name)}"
            title="Delete file"
          >
            &times;
          </button>
        </div>
      `;
    })
    .join("");
}

function getCurrentDocumentNames() {
  const documents = selectedSubmission && selectedSubmission.record
    ? selectedSubmission.record.documents || []
    : [];

  return documents.map((document) => document.file_name);
}

function reconcileSelectionAfterFileChange(options = {}) {
  const currentNames = getCurrentDocumentNames();
  const currentNameSet = new Set(currentNames);

  if (fileSelectionMode === "auto" || fileSelectionMode === "none") {
    selectedFiles.clear();
  } else if (fileSelectionMode === "all") {
    selectedFiles = new Set(currentNames);
  } else {
    selectedFiles = new Set(
      Array.from(selectedFiles).filter((fileName) => currentNameSet.has(fileName))
    );

    if (options.addedFileName && currentNameSet.has(options.addedFileName)) {
      selectedFiles.add(options.addedFileName);
    }
  }

  autoSelectEnabled = fileSelectionMode === "auto";
  syncFileSelectionControls();
  updateSelectionMode(fileSelectionMode);
}

function syncFileSelectionControls() {
  document.querySelectorAll(".file-selection-checkbox").forEach((checkbox) => {
    checkbox.checked = selectedFiles.has(checkbox.value);
  });
}

async function openDocumentPreview(documentInfo) {
  documentModalTitle.textContent = documentInfo.name || "Document";
  documentModalContent.innerHTML = '<p class="document-loading">Loading document...</p>';
  documentModal.classList.add("open");
  documentModal.setAttribute("aria-hidden", "false");

  if (isPdfDocument(documentInfo)) {
    documentModalContent.innerHTML = `
      <iframe
        class="pdf-viewer"
        src="${escapeHtml(documentInfo.url)}"
        title="${escapeHtml(documentInfo.name)}"
      ></iframe>
    `;
    return;
  }

  try {
    const response = await fetch(documentInfo.url);
    const text = await response.text();

    if (!response.ok) {
      throw new Error(text || "Unable to load document.");
    }

    documentModalContent.innerHTML = `<pre class="text-viewer">${escapeHtml(text)}</pre>`;
  } catch (error) {
    documentModalContent.innerHTML = `<p class="document-error">${escapeHtml(error.message || "Unable to load document.")}</p>`;
  }
}

function isPdfDocument(documentInfo) {
  const name = String(documentInfo.name || "").toLowerCase();
  const url = String(documentInfo.url || "").toLowerCase();
  const type = String(documentInfo.type || "").toLowerCase();
  return type === "pdf" || name.endsWith(".pdf") || url.includes(".pdf");
}

function closeDocumentPreview() {
  documentModal.classList.remove("open");
  documentModal.setAttribute("aria-hidden", "true");
  documentModalContent.innerHTML = "";
}

function closeGuidePopover() {
  guidePopover.classList.remove("open");
  guidePopover.setAttribute("aria-hidden", "true");
  guideToggleButton.classList.remove("active");
}

function formatSubmissionForPrompt(record) {
  const applicant = record.applicant || {};
  const coverage = record.coverage || {};
  const limits = coverage.requested_limits || {};
  const documents = Array.isArray(record.documents) ? record.documents : [];
  const controls = record.security_controls || {};

  return [
    `Submission: ${record.title}`,
    `Submission ID: ${record.id}`,
    `Line of Business: ${record.line_of_business}`,
    `Status: ${record.status}`,
    `File Created At: ${record.file_created_at}`,
    `Received At: ${record.received_at}`,
    `Updated At: ${record.updated_at}`,
    "",
    "Applicant:",
    `- Insured: ${applicant.insured_name}`,
    `- Industry: ${applicant.industry}`,
    `- Location: ${applicant.location}`,
    `- Annual Revenue: ${formatCurrency(applicant.annual_revenue)}`,
    `- Employees: ${applicant.employee_count}`,
    `- Records: ${applicant.records_count ? applicant.records_count.toLocaleString() : "TBD"}`,
    `- Technology Profile: ${applicant.technology_profile}`,
    "",
    "Coverage:",
    `- Lines Requested: ${(coverage.lines_requested || []).join(", ")}`,
    `- Effective Date: ${coverage.requested_effective_date}`,
    `- Retention Requested: ${coverage.retention_requested}`,
    `- Requested Limits: ${Object.entries(limits)
      .map(([key, value]) => `${key}: ${value}`)
      .join("; ")}`,
    "",
    "Security Controls:",
    ...Object.entries(controls).map(([key, value]) => `- ${key}: ${value}`),
    "",
    "Documents:",
    ...documents.flatMap((document) => [
      `--- ${document.file_name} ---`,
      `Type: ${document.file_type}`,
      `Category: ${document.category}`,
      `Document Types: ${formatMetadataList(document.document_types)}`,
      `Major Categories: ${formatMetadataList(document.major_categories)}`,
      `File Created At: ${document.file_created_at}`,
      `Received At: ${document.received_at}`,
      `Description: ${document.description}`,
      document.content || "[PDF or binary file available in document viewer]"
    ]),
    "",
    "Open Questions:",
    ...(record.open_questions || []).map((question) => `- ${question}`),
    "",
    "Risk Flags:",
    ...(record.risk_flags || []).map((flag) => `- ${flag}`)
  ].join("\n");
}

function formatMetadataList(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean).join(", ");
  }

  return value || "";
}

function formatLabel(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase()) || "TBD";
}

function formatDateTime(value) {
  if (!value) {
    return "TBD";
  }

  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function formatDateOnly(value) {
  if (!value) {
    return "TBD";
  }

  const [year, month, day] = String(value).split("-").map(Number);
  if (!year || !month || !day) {
    return value;
  }

  return new Date(year, month - 1, day).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric"
  });
}

function formatCurrency(value) {
  if (typeof value !== "number") {
    return "TBD";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

function formatText(text) {
  const lines = String(text || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let listType = null;
  let listItems = [];

  const flushList = () => {
    if (!listType) {
      return;
    }

    html.push(`<${listType}>${listItems.map((item) => `<li>${formatInlineMarkdown(item)}</li>`).join("")}</${listType}>`);
    listType = null;
    listItems = [];
  };

  lines.forEach((line) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      return;
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length + 2;
      html.push(`<h${level}>${formatInlineMarkdown(headingMatch[2])}</h${level}>`);
      return;
    }

    const unorderedMatch = trimmed.match(/^[-*]\s+(.+)$/);
    if (unorderedMatch) {
      if (listType !== "ul") {
        flushList();
        listType = "ul";
      }
      listItems.push(unorderedMatch[1]);
      return;
    }

    const orderedMatch = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (orderedMatch) {
      if (listType !== "ol") {
        flushList();
        listType = "ol";
      }
      listItems.push(orderedMatch[1]);
      return;
    }

    flushList();
    html.push(`<p>${formatInlineMarkdown(trimmed)}</p>`);
  });

  flushList();
  return html.join("");
}

function formatInlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
