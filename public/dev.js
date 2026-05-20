const devDataSearch = document.querySelector("#devDataSearch");
const devDeleteList = document.querySelector("#devDeleteList");
const devSubmissionCount = document.querySelector("#devSubmissionCount");
const devOverviewGrid = document.querySelector("#devOverviewGrid");
const devDataSourceGrid = document.querySelector("#devDataSourceGrid");
const devDataSourceCount = document.querySelector("#devDataSourceCount");
const devBrokerTable = document.querySelector("#devBrokerTable");
const devBrokerCount = document.querySelector("#devBrokerCount");
const devClaimSummary = document.querySelector("#devClaimSummary");
const devClaimList = document.querySelector("#devClaimList");
const devClaimCount = document.querySelector("#devClaimCount");
const devWorkflowVisual = document.querySelector("#devWorkflowVisual");
const devSkillCount = document.querySelector("#devSkillCount");
const devTraceViewer = document.querySelector("#devTraceViewer");
const devTraceCount = document.querySelector("#devTraceCount");
const devTabs = Array.from(document.querySelectorAll("[data-dev-tab]"));
const devPanels = Array.from(document.querySelectorAll("[data-dev-panel]"));

const VALID_DEV_TABS = new Set(["support", "delete", "brokers", "claims", "workflow", "traces"]);

let devCatalog = emptyDevCatalog();
let activeDevTab = "support";

initDevTools();

async function initDevTools() {
  bindDevEvents();
  applyDevUrlState();
  await loadDevCatalog();
}

function bindDevEvents() {
  if (devDataSearch) {
    devDataSearch.addEventListener("input", () => {
      updateDevUrlState({ query: devDataSearch.value, tab: activeDevTab });
      renderDevConsole();
    });
  }

  devTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      activeDevTab = tab.dataset.devTab || "support";
      updateDevUrlState({ query: getDevQuery(), tab: activeDevTab });
      activateDevTab(activeDevTab);
      renderDevConsole();
    });
  });

  if (devDeleteList) {
    devDeleteList.addEventListener("click", handleDeleteSubmission);
  }

  window.addEventListener("popstate", () => {
    applyDevUrlState();
    renderDevConsole();
  });
  window.addEventListener("hashchange", () => {
    applyDevUrlState();
    renderDevConsole();
  });
}

async function loadDevCatalog() {
  try {
    devCatalog = normalizeDevCatalog(await AUApi.get("/api/dev/catalog"));
    renderDevConsole();
    if (devDataSearch) {
      devDataSearch.focus();
    }
  } catch (error) {
    console.warn(error);
    showDevLoadError();
  }
}

function normalizeDevCatalog(catalog) {
  return {
    overview: catalog.overview || {},
    submissions: Array.isArray(catalog.submissions) ? catalog.submissions : [],
    brokers: Array.isArray(catalog.brokers) ? catalog.brokers : [],
    claims: {
      records: Array.isArray(catalog.claims?.records) ? catalog.claims.records : [],
      totals: catalog.claims?.totals || {}
    },
    agent_skills: {
      ...(catalog.agent_skills || {}),
      skills: Array.isArray(catalog.agent_skills?.skills) ? catalog.agent_skills.skills : []
    },
    agent_traces: Array.isArray(catalog.agent_traces) ? catalog.agent_traces : [],
    workflow: catalog.workflow || {},
    data_sources: Array.isArray(catalog.data_sources) ? catalog.data_sources : []
  };
}

function emptyDevCatalog() {
  return normalizeDevCatalog({});
}

function showDevLoadError() {
  if (devDataSourceGrid) {
    devDataSourceGrid.innerHTML = '<p class="empty-state">Unable to load developer catalog.</p>';
  }
  if (devDeleteList) {
    devDeleteList.innerHTML = '<p class="empty-state">Unable to load submissions.</p>';
  }
  if (devBrokerTable) {
    devBrokerTable.innerHTML = '<p class="empty-state">Unable to load brokers.</p>';
  }
  if (devClaimList) {
    devClaimList.innerHTML = '<p class="empty-state">Unable to load claims.</p>';
  }
  if (devWorkflowVisual) {
    devWorkflowVisual.innerHTML = '<p class="empty-state">Unable to load agent workflow.</p>';
  }
  if (devTraceViewer) {
    devTraceViewer.innerHTML = '<p class="empty-state">Unable to load agent traces.</p>';
  }
}

function renderDevConsole() {
  const query = getDevQuery();
  renderOverview();
  renderDataSources(query);
  renderDevSubmissionList(filterSubmissions(query));
  renderBrokerTable(filterBrokers(query));
  renderClaimInformation(filterClaims(query));
  renderWorkflow(query);
  renderTraceViewer(query);
  activateDevTab(activeDevTab);
}

function renderOverview() {
  if (!devOverviewGrid) {
    return;
  }

  const overview = devCatalog.overview || {};
  const cards = [
    ["Submissions", formatNumber(overview.submission_count), "Searchable account records"],
    ["Brokers", formatNumber(overview.broker_count), "Firms in broker database"],
    ["Claims", formatNumber(overview.total_claims), `${formatNumber(overview.companies_with_claims)} companies with claims`],
    ["Agent Skills", formatNumber(overview.agent_skill_count), `${formatNumber(overview.agent_trace_count)} persisted traces`],
  ];

  devOverviewGrid.innerHTML = cards
    .map(([label, value, caption]) => `
      <article class="dev-overview-card">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
        <small>${escapeHtml(caption)}</small>
      </article>
    `)
    .join("");
}

function renderDataSources(query) {
  if (!devDataSourceGrid) {
    return;
  }

  const sources = devCatalog.data_sources.filter((source) => matchesQuery(source, query));
  if (devDataSourceCount) {
    devDataSourceCount.textContent = `${sources.length} of ${devCatalog.data_sources.length} stores`;
  }

  if (!sources.length) {
    devDataSourceGrid.innerHTML = '<p class="empty-state">No matching data stores.</p>';
    return;
  }

  devDataSourceGrid.innerHTML = sources
    .map((source) => `
      <article class="dev-source-card">
        <div class="dev-source-card-head">
          <div>
            <strong>${escapeHtml(source.label)}</strong>
            <small>${escapeHtml(source.path)}</small>
          </div>
          <span>${escapeHtml(formatNumber(source.record_count))}</span>
        </div>
        <p>${escapeHtml(source.description)}</p>
        <code>${escapeHtml(source.api)}</code>
      </article>
    `)
    .join("");
}

function renderDevSubmissionList(results) {
  if (!devDeleteList) {
    return;
  }

  if (devSubmissionCount) {
    devSubmissionCount.textContent = `${results.length} of ${devCatalog.submissions.length} submissions`;
  }

  if (!results.length) {
    devDeleteList.innerHTML = '<p class="empty-state">No matching submissions.</p>';
    return;
  }

  devDeleteList.innerHTML = results
    .map((submission) => `
      <article class="dev-delete-row" data-submission-id="${escapeHtml(submission.id)}">
        <div>
          <strong>${escapeHtml(submission.id)}, ${escapeHtml(submission.title || "Untitled submission")}</strong>
          <small>
            ${escapeHtml([
              submission.insured_name,
              submission.industry,
              submission.status,
              submission.broker_name
            ].filter(Boolean).join(" | "))}
          </small>
        </div>
        <button
          class="dev-delete-cross"
          type="button"
          data-delete-submission="${escapeHtml(submission.id)}"
          data-delete-title="${escapeHtml(submission.title || "")}"
          aria-label="Delete ${escapeHtml(submission.id)}"
        >
          &times;
        </button>
      </article>
    `)
    .join("");
}

function renderBrokerTable(brokers) {
  if (!devBrokerTable) {
    return;
  }

  if (devBrokerCount) {
    devBrokerCount.textContent = `${brokers.length} of ${devCatalog.brokers.length} brokers`;
  }

  if (!brokers.length) {
    devBrokerTable.innerHTML = '<p class="empty-state">No matching brokers.</p>';
    return;
  }

  devBrokerTable.innerHTML = `
    <table class="dev-table">
      <thead>
        <tr>
          <th>Broker</th>
          <th>Contacts</th>
          <th>Focus</th>
          <th>Metrics</th>
          <th>Notes</th>
        </tr>
      </thead>
      <tbody>
        ${brokers.map(renderBrokerRow).join("")}
      </tbody>
    </table>
  `;
}

function renderBrokerRow(broker) {
  const contacts = broker.contacts || {};
  const producer = contacts.producer || {};
  const accountManager = contacts.account_manager || {};
  const metrics = broker.relationship_metrics || {};

  return `
    <tr>
      <td>
        <strong>${escapeHtml(broker.firm_name)}</strong>
        <small>${escapeHtml([broker.broker_id, broker.broker_type, broker.branch, broker.service_tier].filter(Boolean).join(" | "))}</small>
      </td>
      <td>
        <small><b>Producer:</b> ${escapeHtml(producer.name || "Not provided")}</small>
        <small><b>Manager:</b> ${escapeHtml(accountManager.name || "Not provided")}</small>
      </td>
      <td>
        <div class="dev-chip-row">${renderChips(broker.market_focus || [])}</div>
      </td>
      <td>
        <small>Quote ${escapeHtml(formatPct(metrics.quote_ratio_12m))} | Bind ${escapeHtml(formatPct(metrics.bind_ratio_12m))}</small>
        <small>${escapeHtml(formatNumber(metrics.avg_response_hours))}h response | ${escapeHtml(formatNumber(metrics.data_quality_score))} data quality</small>
      </td>
      <td>
        <small>${escapeHtml(broker.placement_notes || "No notes.")}</small>
      </td>
    </tr>
  `;
}

function renderClaimInformation(records) {
  renderClaimSummary();

  if (!devClaimList) {
    return;
  }

  if (devClaimCount) {
    devClaimCount.textContent = `${records.length} of ${devCatalog.claims.records.length} accounts`;
  }

  if (!records.length) {
    devClaimList.innerHTML = '<p class="empty-state">No matching claim records.</p>';
    return;
  }

  devClaimList.innerHTML = records.map(renderClaimAccount).join("");
}

function renderClaimSummary() {
  if (!devClaimSummary) {
    return;
  }

  const totals = devCatalog.claims.totals || {};
  const cards = [
    ["Companies With Claims", formatNumber(totals.companies_with_claims)],
    ["Total Claims", formatNumber(totals.total_claims)],
    ["Open Claims", formatNumber(totals.open_claims)],
    ["Total Incurred", formatCurrency(totals.total_incurred)],
  ];

  devClaimSummary.innerHTML = cards
    .map(([label, value]) => `
      <article>
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </article>
    `)
    .join("");
}

function renderClaimAccount(record) {
  const aggregate = record.aggregate || {};
  const claims = Array.isArray(record.claims) ? record.claims : [];
  return `
    <article class="dev-claim-card">
      <header>
        <div>
          <strong>${escapeHtml(record.submission_id)}, ${escapeHtml(record.title || record.insured_name || "Untitled submission")}</strong>
          <small>${escapeHtml([record.industry_bucket || record.industry, record.status, record.broker_name].filter(Boolean).join(" | "))}</small>
        </div>
        <span>${escapeHtml(formatNumber(aggregate.total_claims))} claims | ${escapeHtml(formatCurrency(aggregate.total_incurred))}</span>
      </header>
      <div class="dev-claim-detail-grid">
        <span>Open: ${escapeHtml(formatNumber(aggregate.open_claims))}</span>
        <span>Paid: ${escapeHtml(formatCurrency(aggregate.total_paid))}</span>
        <span>Reserved: ${escapeHtml(formatCurrency(aggregate.total_reserved))}</span>
        <span>Latest: ${escapeHtml(aggregate.latest_loss_date || "None")}</span>
      </div>
      <div class="dev-claim-events">
        ${claims.length ? claims.map(renderClaimEvent).join("") : '<p>No linked claims for this account.</p>'}
      </div>
    </article>
  `;
}

function renderClaimEvent(claim) {
  return `
    <div class="dev-claim-event">
      <strong>${escapeHtml(claim.claim_id)}</strong>
      <span>${escapeHtml([claim.loss_date, titleCase(claim.claim_type), titleCase(claim.status), titleCase(claim.severity)].filter(Boolean).join(" | "))}</span>
      <small>${escapeHtml(formatCurrency((claim.amount_paid || 0) + (claim.amount_reserved || 0)))} incurred - ${escapeHtml(claim.cause || "No cause provided")}</small>
    </div>
  `;
}

function renderWorkflow(query) {
  if (!devWorkflowVisual) {
    return;
  }

  const workflow = devCatalog.workflow || {};
  const skills = devCatalog.agent_skills.skills.filter((skill) => matchesQuery(skill, query));
  if (devSkillCount) {
    devSkillCount.textContent = `${skills.length} of ${devCatalog.agent_skills.skills.length} skills`;
  }

  devWorkflowVisual.innerHTML = `
    <section class="dev-workflow-hero">
      <div>
        <p class="eyebrow">${escapeHtml(workflow.title || "Information Agent")}</p>
        <h3>${escapeHtml(workflow.summary || "Routes prompts to the right underwriting data.")}</h3>
      </div>
      ${renderWorkflowMetrics((workflow.orchestration || {}).metrics || [])}
    </section>
    ${renderOrchestrationBoard(workflow.orchestration || {})}
    <section class="dev-workflow-layout" aria-label="Agent workflow map">
      <div class="dev-workflow-map">
        <div class="dev-workflow-map-heading">
          <span>Runtime Sequence</span>
          <strong>${escapeHtml((workflow.nodes || []).length)} stages</strong>
        </div>
        ${renderWorkflowNodes(workflow.nodes || [], workflow.edges || [])}
      </div>
      <aside class="dev-workflow-side">
        <section class="dev-cycle-panel" aria-label="Cyclic paths">
          <div class="dev-side-heading">
            <span>Feedback Loops</span>
            <strong>${escapeHtml((workflow.cycles || []).length)} cyclic paths</strong>
          </div>
          ${renderWorkflowCycles(workflow.cycles || [])}
        </section>
        <section class="dev-retrieval-band" aria-label="Retrieval skill groups">
          <div class="dev-side-heading">
            <span>Retrieval Groups</span>
            <strong>${escapeHtml((workflow.retrieval_groups || []).length)} groups</strong>
          </div>
          ${(workflow.retrieval_groups || []).map(renderRetrievalGroup).join("")}
        </section>
      </aside>
    </section>
    <section class="dev-skill-grid" aria-label="Agent skills">
      ${skills.length ? skills.map(renderSkillCard).join("") : '<p class="empty-state">No matching agent skills.</p>'}
    </section>
  `;
}

function renderWorkflowMetrics(metrics) {
  if (!Array.isArray(metrics) || !metrics.length) {
    return "";
  }

  return `
    <div class="dev-workflow-metrics" aria-label="Workflow runtime metrics">
      ${metrics.map((metric) => `
        <span>
          <small>${escapeHtml(metric.label || "")}</small>
          <strong>${escapeHtml(metric.value || "")}</strong>
        </span>
      `).join("")}
    </div>
  `;
}

function renderOrchestrationBoard(orchestration) {
  const layers = Array.isArray(orchestration.layers) ? orchestration.layers : [];
  const paths = Array.isArray(orchestration.execution_paths) ? orchestration.execution_paths : [];
  const traceContract = Array.isArray(orchestration.trace_contract) ? orchestration.trace_contract : [];
  if (!layers.length && !paths.length && !traceContract.length) {
    return "";
  }

  return `
    <section class="dev-orchestration-board" aria-label="Agent orchestration overview">
      <div class="dev-orchestration-main">
        <div class="dev-side-heading">
          <span>Orchestration Layer</span>
          <strong>${escapeHtml(layers.length)} runtime controls</strong>
        </div>
        <div class="dev-orchestration-layers">
          ${layers.map(renderOrchestrationLayer).join("")}
        </div>
      </div>
      <aside class="dev-orchestration-aside">
        ${renderExecutionPaths(paths)}
        ${renderTraceContract(traceContract)}
      </aside>
    </section>
  `;
}

function renderOrchestrationLayer(layer, index) {
  return `
    <article class="dev-orchestration-layer ${escapeHtml(layer.key || "")}">
      <div class="dev-layer-index">${escapeHtml(String(index + 1).padStart(2, "0"))}</div>
      <div>
        <span>${escapeHtml(layer.label || layer.key || "Layer")}</span>
        <strong>${escapeHtml(layer.purpose || "")}</strong>
        <div class="dev-layer-io">
          <small>Reads: ${escapeHtml(formatShortList(layer.reads || []))}</small>
          <small>Emits: ${escapeHtml(formatShortList(layer.emits || []))}</small>
        </div>
      </div>
    </article>
  `;
}

function renderExecutionPaths(paths) {
  if (!Array.isArray(paths) || !paths.length) {
    return "";
  }

  return `
    <section class="dev-execution-paths" aria-label="Execution paths">
      <div class="dev-side-heading">
        <span>Execution Paths</span>
        <strong>${escapeHtml(paths.length)} routes</strong>
      </div>
      ${paths.map((path) => `
        <article class="dev-execution-path">
          <strong>${escapeHtml(path.label || "Execution path")}</strong>
          <div>
            ${(Array.isArray(path.steps) ? path.steps : []).map((step) => `<code>${escapeHtml(step)}</code>`).join("<i></i>")}
          </div>
        </article>
      `).join("")}
    </section>
  `;
}

function renderTraceContract(fields) {
  if (!Array.isArray(fields) || !fields.length) {
    return "";
  }

  return `
    <section class="dev-trace-contract" aria-label="Persisted trace contract">
      <div class="dev-side-heading">
        <span>Trace Contract</span>
        <strong>${escapeHtml(fields.length)} fields</strong>
      </div>
      <div class="dev-chip-row">
        ${fields.map((field) => `<span>${escapeHtml(field)}</span>`).join("")}
      </div>
    </section>
  `;
}

function renderWorkflowNodes(nodes, edges) {
  return nodes
    .map((node, index) => {
      const nextNode = nodes[index + 1];
      const edge = nextNode ? findWorkflowEdge(edges, node.id, nextNode.id) : null;
      return `
        <article class="dev-workflow-node phase-${escapeHtml(String(node.phase || "").toLowerCase())}" data-workflow-node="${escapeHtml(node.id)}">
          <div class="dev-workflow-index">${escapeHtml(String(index + 1).padStart(2, "0"))}</div>
          <div>
            <span>${escapeHtml(node.phase || "")}</span>
            <strong>${escapeHtml(node.label || node.id)}</strong>
            <p>${escapeHtml(node.description || "")}</p>
          </div>
        </article>
        ${edge ? renderWorkflowConnector(edge) : ""}
      `;
    })
    .join("");
}

function formatShortList(values) {
  const items = Array.isArray(values) ? values.filter(Boolean) : [];
  if (!items.length) {
    return "None";
  }
  const visible = items.slice(0, 4).join(", ");
  const remaining = items.length - 4;
  return remaining > 0 ? `${visible}, +${remaining}` : visible;
}

function renderWorkflowConnector(edge) {
  return `
    <div class="dev-workflow-connector" aria-label="${escapeHtml(edge.label || "Next workflow step")}">
      <i aria-hidden="true"></i>
      <span>${escapeHtml(edge.label || "")}</span>
    </div>
  `;
}

function renderWorkflowCycles(cycles) {
  if (!cycles.length) {
    return '<p class="empty-state">No cyclic paths are defined.</p>';
  }

  return cycles
    .map((cycle) => `
      <article class="dev-cycle-card">
        <div class="dev-cycle-card-heading">
          <strong>${escapeHtml(cycle.label || "Feedback loop")}</strong>
        </div>
        <div class="dev-cycle-path" aria-label="${escapeHtml((cycle.from || "") + " to " + (cycle.to || ""))}">
          <code>${escapeHtml(formatWorkflowNodeId(cycle.from))}</code>
          <span aria-hidden="true">&#8634;</span>
          <code>${escapeHtml(formatWorkflowNodeId(cycle.to))}</code>
        </div>
        <p>${escapeHtml(cycle.description || "")}</p>
      </article>
    `)
    .join("");
}

function findWorkflowEdge(edges, from, to) {
  return (Array.isArray(edges) ? edges : []).find((edge) => edge.from === from && edge.to === to) || null;
}

function formatWorkflowNodeId(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderRetrievalGroup(group) {
  const skillIds = Array.isArray(group.skill_ids) ? group.skill_ids.filter(Boolean) : [];
  return `
    <article>
      <strong>${escapeHtml(group.label)}</strong>
      <small>${escapeHtml(skillIds.length ? skillIds.join(", ") : "No mapped skills")}</small>
    </article>
  `;
}

function renderSkillCard(skill) {
  const triggerExamples = Array.isArray(skill.trigger_examples) ? skill.trigger_examples.slice(0, 3) : [];
  const dataSources = [
    ...(Array.isArray(skill.data_sources) ? skill.data_sources : []),
    ...(skill.data_source ? [skill.data_source] : [])
  ];
  return `
    <article class="dev-skill-card">
      <header>
        <div>
          <span>${escapeHtml(skill.action_type || "skill")}</span>
          <strong>${escapeHtml(skill.label || skill.skill_id)}</strong>
        </div>
        <code>${escapeHtml(skill.skill_id || "")}</code>
      </header>
      <p>${escapeHtml(skill.output || "No output description.")}</p>
      <div class="dev-chip-row">${renderChips(triggerExamples)}</div>
      ${dataSources.length ? `<small>Sources: ${escapeHtml(dataSources.join(" | "))}</small>` : ""}
    </article>
  `;
}

function renderTraceViewer(query) {
  if (!devTraceViewer) {
    return;
  }

  const traces = devCatalog.agent_traces.filter((trace) => matchesQuery(trace, query));
  if (devTraceCount) {
    devTraceCount.textContent = `${traces.length} of ${devCatalog.agent_traces.length} traces`;
  }

  if (!traces.length) {
    devTraceViewer.innerHTML = '<p class="empty-state">No matching agent traces.</p>';
    return;
  }

  devTraceViewer.innerHTML = `
    <section class="dev-trace-explainer">
      <strong>Trace Viewer</strong>
      <p>Each row is a persisted planner, tool loop, confidence check, retry, and model-response run. Use this to debug why the agent selected documents, analytics, tasks, SOP, or other underwriting data.</p>
    </section>
    <div class="dev-trace-list">
      ${traces.map(renderTraceCard).join("")}
    </div>
  `;
}

function renderTraceCard(trace) {
  const confidence = trace.confidence || {};
  const score = Number(confidence.score || 0);
  const label = confidence.label || "unknown";
  const skills = Array.isArray(trace.selected_skills) ? trace.selected_skills : [];
  return `
    <article class="dev-trace-card">
      <header>
        <div>
          <strong>${escapeHtml(trace.submission_id || "unknown submission")}</strong>
          <small>${escapeHtml(trace.prompt_preview || "No prompt preview.")}</small>
        </div>
        <span class="${escapeHtml(traceStatusClass(label))}">${escapeHtml(formatPct(score))}</span>
      </header>
      <div class="dev-trace-meta">
        <span>${escapeHtml(trace.status || "unknown")}</span>
        <span>${escapeHtml(formatDateTime(trace.updated_at || trace.created_at))}</span>
        <span>${escapeHtml(String(trace.attempt_count || 0))} attempts</span>
        <span>${escapeHtml(String(trace.source_count || 0))} sources</span>
        <span>${escapeHtml(String(trace.step_count || 0))} steps</span>
      </div>
      <div class="dev-chip-row">
        ${skills.length ? renderChips(skills) : "<span>No skills recorded</span>"}
      </div>
      <a class="inline-data-link" href="/api/submissions/${encodeURIComponent(trace.submission_id || "")}/agent-traces/${encodeURIComponent(trace.trace_id || "")}" target="_blank" rel="noreferrer">
        Open trace JSON
      </a>
    </article>
  `;
}

function traceStatusClass(label) {
  const normalized = String(label || "").toLowerCase();
  if (normalized === "high") {
    return "good";
  }
  if (normalized === "medium") {
    return "watch";
  }
  return "alert";
}

async function handleDeleteSubmission(event) {
  const button = event.target.closest("[data-delete-submission]");
  if (!button) {
    return;
  }

  const submissionId = button.dataset.deleteSubmission;
  const title = button.dataset.deleteTitle || submissionId;
  const confirmed = window.confirm(
    `This is going to delete all traces of this submission and its documents.\n\nSubmission: ${submissionId}, ${title}\n\nThis removes the submission folder, documents, chat history, notes, guides, tasks, stages, claims, underwriting data, decision workflow, and search index entry.\n\nAre you sure?`
  );

  if (!confirmed) {
    return;
  }

  button.disabled = true;
  button.textContent = "Deleting";

  try {
    await AUApi.delete(`/api/dev/submissions/${encodeURIComponent(submissionId)}`);
    await loadDevCatalog();
  } catch (error) {
    console.warn(error);
    button.disabled = false;
    button.innerHTML = "&times;";
    window.alert(error.message || "Unable to delete submission.");
  }
}

function filterSubmissions(query) {
  return devCatalog.submissions.filter((submission) => matchesQuery(submission, query));
}

function filterBrokers(query) {
  return devCatalog.brokers.filter((broker) => matchesQuery(broker, query));
}

function filterClaims(query) {
  return devCatalog.claims.records.filter((record) => matchesQuery(record, query));
}

function matchesQuery(value, query) {
  const text = String(query || "").trim().toLowerCase();
  if (!text) {
    return true;
  }
  return collectSearchText(value).toLowerCase().includes(text);
}

function collectSearchText(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (Array.isArray(value)) {
    return value.map(collectSearchText).join(" ");
  }
  if (typeof value === "object") {
    return Object.values(value).map(collectSearchText).join(" ");
  }
  return String(value);
}

function activateDevTab(tabName) {
  const selectedTab = VALID_DEV_TABS.has(tabName) ? tabName : "support";
  activeDevTab = selectedTab;
  devTabs.forEach((tab) => {
    const isActive = tab.dataset.devTab === selectedTab;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
  });
  devPanels.forEach((panel) => {
    const isActive = panel.dataset.devPanel === selectedTab;
    panel.classList.toggle("active", isActive);
    panel.hidden = !isActive;
  });
}

function applyDevUrlState() {
  const query = getDevSearchQueryFromUrl();
  activeDevTab = getDevTabFromUrl();
  if (devDataSearch && devDataSearch.value !== query) {
    devDataSearch.value = query;
  }
  activateDevTab(activeDevTab);
}

function updateDevUrlState({ query, tab }) {
  const url = new URL(window.location.href);
  const text = String(query || "").trim();
  if (text) {
    url.searchParams.set("q", text);
  } else {
    url.searchParams.delete("q");
  }

  const tabName = VALID_DEV_TABS.has(tab) ? tab : "support";
  const hash = tabName === "support" ? "" : `#${tabName}`;
  window.history.replaceState({}, "", `${url.pathname}${url.search}${hash}`);
}

function getDevQuery() {
  return devDataSearch?.value || "";
}

function getDevSearchQueryFromUrl() {
  return new URLSearchParams(window.location.search).get("q") || "";
}

function getDevTabFromUrl() {
  const tab = String(window.location.hash || "").replace("#", "");
  return VALID_DEV_TABS.has(tab) ? tab : "support";
}

function renderChips(values) {
  return values
    .filter(Boolean)
    .map((value) => `<span>${escapeHtml(value)}</span>`)
    .join("");
}

function formatCurrency(value) {
  const number = Number(value || 0);
  return number.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });
}

function formatPct(value) {
  if (value === null || value === undefined || value === "") {
    return "0%";
  }
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function formatDateTime(value) {
  if (!value) {
    return "TBD";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function titleCase(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
