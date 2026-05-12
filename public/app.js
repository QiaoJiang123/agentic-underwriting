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
const keyInfoList = document.querySelector("#keyInfoList");
const timelineList = document.querySelector("#timelineList");
const analyticsPanel = document.querySelector("#analyticsPanel");
const stageChecklist = document.querySelector("#stageChecklist");
const documentList = document.querySelector("#documentList");
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
let selectedSubmission = null;
let selectedFiles = new Set();
let currentChatHistoryId = null;
let autoSelectEnabled = false;
let guideItems = [];
let editingGuideIndex = null;
let noteItems = [];
let editingNoteIndex = null;
let followUpItems = [];
let analyticsModels = null;
let analyticsFeatureMetadata = null;
let currentAnalytics = null;
let currentAnalyticsFeatureLookup = null;
let activeWhatIfModel = "quote";
let whatIfValues = {};
let whatIfRawValues = {};
const initialSubmissionId = new URLSearchParams(window.location.search).get("submission");

init();

function init() {
  loadHealth();
  loadSubmissions();
}

function loadHealth() {
  fetch("/health")
    .then((response) => response.json())
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
    autoSelectEnabled = false;
    guideItems = [];
    editingGuideIndex = null;
    noteItems = [];
    editingNoteIndex = null;
    followUpItems = [];
    currentAnalytics = null;
    currentAnalyticsFeatureLookup = null;
    activeWhatIfModel = "quote";
    whatIfValues = {};
    whatIfRawValues = {};

    workspaceTitle.textContent = submission.title;
    summaryPlaceholder.textContent = buildSummaryPlaceholder(selectedSubmission.record);
    keyInfoList.innerHTML = buildKeyInfoItems(selectedSubmission)
      .map(
        (item) => `
          <div class="key-info-item" title="${escapeHtml(`${item.label}: ${item.value}`)}">
            <span title="${escapeHtml(item.label)}">${escapeHtml(item.label)}</span>
            <strong title="${escapeHtml(item.value)}">${escapeHtml(item.value)}</strong>
          </div>
        `
      )
      .join("");
    timelineList.innerHTML = buildTimelineItems(selectedSubmission.record);
    analyticsPanel.innerHTML = '<p class="empty-state">Loading analytics models...</p>';
    await loadAnalyticsModels();
    analyticsPanel.innerHTML = buildAnalyticsPanel(selectedSubmission.record);
    stageChecklist.innerHTML = buildStageChecklist(selectedSubmission.record);
    documentList.innerHTML = buildDocumentLinks(selectedSubmission.record);
    renderGuideInstructions("Loading guide...");
    renderNoteContext("Loading notes...");
    renderFollowUps("Loading tasks...");
    await loadGuideInstructions(submission.id);
    await loadNotes(submission.id);
    await loadFollowUps(submission.id);
    selectedFiles = new Set((selectedSubmission.record.documents || []).map((document) => document.file_name));
    syncFileSelectionControls();
    updateSelectionMode("all");
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
  addMessage("user", content);
  messages.push({ role: "user", content });

  setLoading(true);
  const pending = addMessage("assistant", "Thinking...");

  try {
    const visibleChatHistory = messages;
    if (autoSelectEnabled) {
      await autoSelectDocumentsForPrompt(content);
    }
    const temporaryModelMessages = buildTemporaryModelMessagesWithSelectedFiles(visibleChatHistory);
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: temporaryModelMessages,
        guides: getActiveGuideInstructions(),
        underwriter_notes: getActiveUnderwriterNotes()
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    pending.querySelector(".bubble").innerHTML = formatText(data.reply);
    messages.push({ role: "assistant", content: data.reply });
    await saveCurrentChatHistory();
  } catch (error) {
    const bubble = pending.querySelector(".bubble");
    bubble.classList.add("error");
    bubble.textContent = error.message || "Something went wrong.";
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

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

documentList.addEventListener("click", (event) => {
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
  updateSelectionMode("manual");
});

selectAllFilesButton.addEventListener("click", () => {
  autoSelectEnabled = false;
  selectedFiles = new Set(getCurrentDocumentNames());
  syncFileSelectionControls();
  updateSelectionMode("all");
});

unselectAllFilesButton.addEventListener("click", () => {
  autoSelectEnabled = false;
  selectedFiles.clear();
  syncFileSelectionControls();
  updateSelectionMode("none");
});

autoSelectFiles.addEventListener("click", async () => {
  autoSelectEnabled = !autoSelectEnabled;
  updateSelectionMode(autoSelectEnabled ? "auto" : "manual");

  if (autoSelectEnabled && input.value.trim()) {
    try {
      await autoSelectDocumentsForPrompt(input.value.trim());
    } catch (error) {
      console.warn(error);
    }
  }
});

panelTabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const tabName = button.dataset.panelTab;

    panelTabButtons.forEach((tabButton) => {
      tabButton.classList.toggle("active", tabButton === button);
    });

    panelViews.forEach((view) => {
      view.classList.toggle("active", view.dataset.panelView === tabName);
    });
  });
});

if (analyticsPanel) {
  analyticsPanel.addEventListener("click", (event) => {
    const whatIfModelButton = event.target.closest("[data-what-if-model]");
    if (whatIfModelButton) {
      activeWhatIfModel = whatIfModelButton.dataset.whatIfModel === "bind" ? "bind" : "quote";
      analyticsPanel.querySelectorAll("[data-what-if-model]").forEach((button) => {
        button.classList.toggle("active", button === whatIfModelButton);
      });
      updateWhatIfResult();
      return;
    }

    const optionButton = event.target.closest("[data-what-if-option]");
    if (optionButton) {
      const key = optionButton.dataset.whatIfFeatureKey;
      whatIfValues[key] = Number(optionButton.dataset.whatIfValue);
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

    const tabName = button.dataset.analyticsSubtab;
    analyticsPanel.querySelectorAll("[data-analytics-subtab]").forEach((tabButton) => {
      tabButton.classList.toggle("active", tabButton === button);
    });
    analyticsPanel.querySelectorAll("[data-analytics-view]").forEach((view) => {
      view.classList.toggle("active", view.dataset.analyticsView === tabName);
    });
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
    const field = event.target.closest("[data-what-if-feature]");
    if (!field) {
      return;
    }

    updateWhatIfFeatureValueFromField(field);
    updateWhatIfFeatureDisplay(field.dataset.whatIfFeature);
    updateWhatIfResult();
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

    const now = new Date().toISOString();
    followUpItems.push({
      id: `follow-up-${Date.now()}`,
      title,
      due_date: dueDate,
      status: "open",
      created_at: now,
      updated_at: now
    });
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

    const index = Number(button.dataset.followUpIndex);
    if (!Number.isInteger(index)) {
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
});

function resetChat() {
  messages.length = 0;
  currentChatHistoryId = null;
  messagesEl.innerHTML = "";
  addMessage(
    "assistant",
    selectedSubmission
      ? `Chat cleared. ${selectedSubmission.title} is still selected.`
      : "Chat cleared. Choose a submission from the left or paste details below."
  );
  input.focus();
}

function buildTemporaryModelMessagesWithSelectedFiles(visibleMessages) {
  if (!selectedSubmission || !selectedSubmission.record || !selectedFiles.size) {
    return visibleMessages;
  }

  const selectedFileContext = buildSelectedFileContext();
  if (!selectedFileContext) {
    return visibleMessages;
  }

  const modelMessages = visibleMessages.map((message) => ({ ...message }));
  const lastUserIndex = findLastUserMessageIndex(modelMessages);

  if (lastUserIndex === -1) {
    return modelMessages;
  }

  modelMessages[lastUserIndex] = {
    ...modelMessages[lastUserIndex],
    content: [
      modelMessages[lastUserIndex].content,
      "",
      "Selected file context:",
      selectedFileContext
    ].join("\n")
  };

  return modelMessages;
}

async function autoSelectDocumentsForPrompt(prompt) {
  if (!selectedSubmission) {
    return;
  }

  const response = await fetch(
    `/api/submissions/${encodeURIComponent(selectedSubmission.id)}/auto-select-documents`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        prompt,
        max_documents: 6
      })
    }
  );
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Unable to auto-select documents.");
  }

  const selected = data.document_selection && Array.isArray(data.document_selection.selected_files)
    ? data.document_selection.selected_files
    : [];

  selectedFiles = new Set(selected);
  syncFileSelectionControls();
  updateSelectionMode("auto");
}

function updateSelectionMode(mode) {
  selectAllFilesButton.classList.toggle("active", mode === "all");
  unselectAllFilesButton.classList.toggle("active", mode === "none");
  autoSelectFiles.classList.toggle("active", mode === "auto");
  autoSelectFiles.setAttribute("aria-pressed", mode === "auto" ? "true" : "false");
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
    const response = await fetch(`/api/submissions/${encodeURIComponent(submissionId)}/follow-ups`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to load tasks.");
    }

    followUpItems = normalizeFollowUps(data.follow_up && data.follow_up.follow_ups);
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
    const response = await fetch(`/api/submissions/${encodeURIComponent(selectedSubmission.id)}/follow-ups`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ follow_ups: followUpItems })
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Unable to save tasks.");
    }

    followUpItems = normalizeFollowUps(data.follow_up && data.follow_up.follow_ups);
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
      id: String(item.id || `follow-up-${Date.now()}-${index}`),
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

  if (!followUpList) {
    return;
  }

  if (statusMessage) {
    followUpList.innerHTML = `<p>${escapeHtml(statusMessage)}</p>`;
    return;
  }

  if (!followUpItems.length) {
    followUpList.innerHTML = "<p>No scheduled tasks.</p>";
    return;
  }

  followUpList.innerHTML = followUpItems
    .map((item, index) => {
      const dueState = getFollowUpDueState(item);
      return `
        <div class="follow-up-item ${item.status === "done" ? "done" : ""} ${dueState}">
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(formatDateOnly(item.due_date))}</small>
          </div>
          <div class="follow-up-actions">
            <button class="selection-action" type="button" data-follow-up-action="toggle" data-follow-up-index="${index}">
              ${item.status === "done" ? "Reopen" : "Done"}
            </button>
            <button class="icon-button small-icon-button" type="button" data-follow-up-action="delete" data-follow-up-index="${index}" aria-label="Delete follow-up">&times;</button>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderFollowUpCalendar() {
  if (!followUpCalendar) {
    return;
  }

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const offset = firstDay.getDay();
  const itemsByDate = new Map();

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
    cells.push(`
      <span class="calendar-day ${hasItem ? "has-follow-up" : ""} ${hasDueAlert ? "due-alert" : ""}">
        ${day}
      </span>
    `);
  }

  followUpCalendar.innerHTML = `
    <div class="calendar-heading">${today.toLocaleString([], { month: "long", year: "numeric" })}</div>
    <div class="calendar-weekdays">
      <span>S</span><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span>
    </div>
    <div class="calendar-grid">${cells.join("")}</div>
  `;
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
  bubble.innerHTML = formatText(content);

  article.append(avatar, bubble);
  messagesEl.append(article);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  return article;
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
    </div>

    <div class="analytics-view active" data-analytics-view="quote">
      ${renderModelView("Quote Probability", currentAnalytics.quote, "Likelihood the account receives quotable terms")}
    </div>

    <div class="analytics-view" data-analytics-view="bind">
      ${renderModelView("Bind Probability", currentAnalytics.bind, "Likelihood quoted terms bind")}
    </div>

    <div class="analytics-view" data-analytics-view="what-if">
      ${renderWhatIfView()}
    </div>
  `;
}

function buildLogisticAnalytics(record, existingFeatureLookup) {
  const featureLookup = existingFeatureLookup || buildAnalyticsFeatureLookup(record);
  const quoteModel = analyticsModels && analyticsModels.quote ? analyticsModels.quote : getFallbackQuoteModel();
  const bindModel = analyticsModels && analyticsModels.bind ? analyticsModels.bind : getFallbackBindModel();

  return {
    quote: scoreStoredModel(quoteModel, featureLookup),
    bind: scoreStoredModel(bindModel, featureLookup)
  };
}

async function loadAnalyticsModels() {
  if (analyticsModels) {
    return analyticsModels;
  }

  const [quoteResponse, bindResponse, metadataResponse] = await Promise.all([
    fetch("/api/models/quote_prob"),
    fetch("/api/models/bind_prob"),
    fetch("/api/models/feature_metadata")
  ]);
  const [quoteData, bindData, metadataData] = await Promise.all([
    quoteResponse.json(),
    bindResponse.json(),
    metadataResponse.json()
  ]);

  if (!quoteResponse.ok) {
    throw new Error(quoteData.error || "Unable to load quote model.");
  }

  if (!bindResponse.ok) {
    throw new Error(bindData.error || "Unable to load bind model.");
  }

  if (!metadataResponse.ok) {
    throw new Error(metadataData.error || "Unable to load feature metadata.");
  }

  analyticsModels = {
    quote: quoteData.model,
    bind: bindData.model
  };
  analyticsFeatureMetadata = metadataData.model;
  return analyticsModels;
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
    }
  ];

  return featureInputs.reduce((lookup, feature) => {
    lookup[feature.key] = feature;
    return lookup;
  }, {});
}

function ensureWhatIfValues(featureLookup) {
  Object.values(featureLookup || {}).forEach((feature) => {
    if (typeof whatIfValues[feature.key] !== "number") {
      whatIfValues[feature.key] = Number(feature.value || 0);
    }
    if (isNumericWhatIfFeature(feature.key) && typeof whatIfRawValues[feature.key] !== "number") {
      whatIfRawValues[feature.key] = Number(feature.rawValue || 0);
    }
  });
}

function renderWhatIfView() {
  const configs = getWhatIfFeatureConfigs();

  return `
    <section class="what-if-workspace">
      <div class="what-if-sticky">
        <div class="what-if-switch" aria-label="What If model">
          <button class="analytics-subtab ${activeWhatIfModel === "quote" ? "active" : ""}" type="button" data-what-if-model="quote">Quote</button>
          <button class="analytics-subtab ${activeWhatIfModel === "bind" ? "active" : ""}" type="button" data-what-if-model="bind">Bind</button>
        </div>
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

function updateWhatIfFeatureDisplay(key) {
  const display = analyticsPanel && analyticsPanel.querySelector(`[data-what-if-display="${key}"]`);
  if (display) {
    display.textContent = formatWhatIfFeatureValue(key, whatIfValues[key]);
  }
}

function buildWhatIfFeatureLookup() {
  return Object.values(currentAnalyticsFeatureLookup || {}).reduce((lookup, feature) => {
    let value = typeof whatIfValues[feature.key] === "number" ? whatIfValues[feature.key] : feature.value;
    let displayValue = formatWhatIfFeatureValue(feature.key, value);

    if (isNumericWhatIfFeature(feature.key)) {
      const rawValue = typeof whatIfRawValues[feature.key] === "number" ? whatIfRawValues[feature.key] : feature.rawValue;
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
  const value = typeof whatIfValues[config.key] === "number" ? whatIfValues[config.key] : current.value;

  if (config.type === "binary") {
    return `
      <div class="what-if-control">
        <div class="what-if-control-heading">
          <strong>${escapeHtml(config.label)}</strong>
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
          <strong>${escapeHtml(config.label)}</strong>
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

  return `
    <label class="what-if-control">
      <div class="what-if-control-heading">
        <strong>${escapeHtml(config.label)}</strong>
        <small>Current: ${escapeHtml(current.displayValue)}</small>
      </div>
      <input
        type="range"
        min="${config.min}"
        max="${config.max}"
        step="${config.step}"
        value="${value}"
        data-what-if-feature="${escapeHtml(config.key)}"
      />
      <span class="what-if-value" data-what-if-display="${escapeHtml(config.key)}">${escapeHtml(formatWhatIfFeatureValue(config.key, value))}</span>
    </label>
  `;
}

function getWhatIfFeatureConfigs() {
  return {
    revenue_scale: {
      key: "revenue_scale",
      label: "Revenue Scale",
      type: "range",
      min: 0,
      max: 1,
      step: 0.01
    },
    records_exposure: {
      key: "records_exposure",
      label: "Records Exposure",
      type: "range",
      min: 0,
      max: 1,
      step: 0.01
    },
    mfa_maturity: {
      key: "mfa_maturity",
      label: "MFA Maturity",
      type: "select",
      options: [
        { label: "No MFA", value: 0.2 },
        { label: "Partial MFA", value: 0.45 },
        { label: "Full MFA", value: 0.82 }
      ]
    },
    edr_coverage: {
      key: "edr_coverage",
      label: "EDR Coverage",
      type: "select",
      options: [
        { label: "No EDR", value: 0.25 },
        { label: "Partial EDR", value: 0.58 },
        { label: "Broad EDR", value: 0.84 }
      ]
    },
    backup_resilience: {
      key: "backup_resilience",
      label: "Backup Resilience",
      type: "select",
      options: [
        { label: "Weak", value: 0.3 },
        { label: "Daily Backup", value: 0.64 },
        { label: "Restore Tested", value: 0.78 }
      ]
    },
    patch_discipline: {
      key: "patch_discipline",
      label: "Patch Discipline",
      type: "select",
      options: [
        { label: "Slow", value: 0.3 },
        { label: "30 Days", value: 0.58 },
        { label: "15 Days", value: 0.76 }
      ]
    },
    security_training: {
      key: "security_training",
      label: "Security Training",
      type: "select",
      options: [
        { label: "None", value: 0.28 },
        { label: "Annual", value: 0.56 },
        { label: "Phishing Sim", value: 0.72 }
      ]
    },
    prior_claims: {
      key: "prior_claims",
      label: "Prior Claims Signal",
      type: "binary",
      options: [
        { label: "No", value: 0.28 },
        { label: "Yes", value: 0.72 }
      ]
    },
    vendor_dependency: {
      key: "vendor_dependency",
      label: "Vendor Dependency",
      type: "binary",
      options: [
        { label: "Limited", value: 0.35 },
        { label: "Material", value: 0.7 }
      ]
    },
    limit_fit: {
      key: "limit_fit",
      label: "Requested Limit Fit",
      type: "range",
      min: 0,
      max: 1,
      step: 0.01
    }
  };
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

function renderModelView(label, model, description) {
  return `
    ${renderScoreCard(label, model, description)}
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
              <span title="${escapeHtml(step.displayValue)}">${escapeHtml(step.label)}</span>
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

function buildStageChecklist(record) {
  const currentStage = getCurrentStageKey(record);
  const stages = [
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
  ];
  const currentIndex = stages.findIndex(([key]) => key === currentStage);

  return stages
    .map(([key, label], index) => {
      const isComplete = currentIndex > index;
      const isCurrent = currentIndex === index;
      return `
        <label class="stage-item ${isCurrent ? "current" : ""}">
          <input type="checkbox" disabled ${isComplete ? "checked" : ""} />
          <span>
            <strong>${escapeHtml(label)}</strong>
            <small>${isCurrent ? "Current stage" : isComplete ? "Completed" : "Pending"}</small>
          </span>
        </label>
      `;
    })
    .join("");
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

function buildSummaryPlaceholder(record) {
  if (!record) {
    return "Reserved for an AI-generated account summary, appetite fit, and recommended next action.";
  }

  const applicant = record.applicant || {};
  return [
    `${applicant.insured_name || record.title} · ${applicant.industry || "Industry TBD"}`,
    `Status: ${record.status || "New"}.`,
    "Ask the chat to generate a formal cyber underwriting summary, key risks, alerts, and guidance."
  ].join(" ");
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
