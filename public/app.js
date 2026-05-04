const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messagesEl = document.querySelector("#messages");
const sendButton = document.querySelector("#sendButton");
const clearButton = document.querySelector("#clearButton");
const newChatButton = document.querySelector("#newChatButton");
const historyList = document.querySelector("#historyList");
const modelStatus = document.querySelector("#modelStatus");
const modelCard = document.querySelector(".model-card");
const promptButtons = document.querySelectorAll(".prompt-chip");
const submissionList = document.querySelector("#submissionList");
const submissionCount = document.querySelector("#submissionCount");
const workspaceTitle = document.querySelector("#workspaceTitle");
const summaryPlaceholder = document.querySelector("#summaryPlaceholder");
const keyInfoList = document.querySelector("#keyInfoList");
const timelineList = document.querySelector("#timelineList");
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

const messages = [];
let selectedSubmission = null;
let selectedFiles = new Set();
let currentChatHistoryId = null;
let guideItems = [];
let editingGuideIndex = null;
const initialSubmissionId = new URLSearchParams(window.location.search).get("submission");

const promptText = {
  Summarize:
    "Summarize the selected cyber submission for an underwriter. Include business profile, requested cyber coverage, security controls, key cyber risks, missing information, and recommended next steps.",
  "Missing Info":
    "Review the selected cyber submission and list the missing information needed before underwriting can proceed.",
  "Risk Flags":
    "Identify the key cyber underwriting risks, rank them by severity, and suggest follow-up questions."
};

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
    guideItems = [];
    editingGuideIndex = null;

    workspaceTitle.textContent = submission.title;
    summaryPlaceholder.textContent = buildSummaryPlaceholder(selectedSubmission.record);
    keyInfoList.innerHTML = buildKeyInfoItems(selectedSubmission)
      .map(
        (item) => `
          <div class="key-info-item">
            <span>${escapeHtml(item.label)}</span>
            <strong>${escapeHtml(item.value)}</strong>
          </div>
        `
      )
      .join("");
    timelineList.innerHTML = buildTimelineItems(selectedSubmission.record);
    documentList.innerHTML = buildDocumentLinks(selectedSubmission.record);
    renderGuideInstructions("Loading guide...");
    await loadGuideInstructions(submission.id);
    selectedFiles = new Set((selectedSubmission.record.documents || []).map((document) => document.file_name));
    syncFileSelectionControls();
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
    const temporaryModelMessages = buildTemporaryModelMessagesWithSelectedFiles(visibleChatHistory);
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: temporaryModelMessages,
        guides: getActiveGuideInstructions()
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

promptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const label = button.textContent.trim();
    const addition = promptText[label] || label;
    input.value = input.value ? `${input.value.trim()}\n\n${addition}` : addition;
    input.focus();
  });
});

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
});

selectAllFilesButton.addEventListener("click", () => {
  selectedFiles = new Set(getCurrentDocumentNames());
  syncFileSelectionControls();
});

unselectAllFilesButton.addEventListener("click", () => {
  selectedFiles.clear();
  syncFileSelectionControls();
});

autoSelectFiles.addEventListener("change", () => {
  autoSelectFiles.dataset.mode = autoSelectFiles.checked ? "auto" : "manual";
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

function getActiveGuideInstructions() {
  return guideItems
    .map((guide) => String(guide.text || "").trim())
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
      const label = document.description || document.category || type;
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

  if (documentInfo.type === "pdf") {
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

function closeDocumentPreview() {
  documentModal.classList.remove("open");
  documentModal.setAttribute("aria-hidden", "true");
  documentModalContent.innerHTML = "";
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
