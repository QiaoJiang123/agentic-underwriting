(function () {
  function render(workflow) {
    const gates = workflow && Array.isArray(workflow.gates) ? workflow.gates : [];
    if (!gates.length) {
      return `
        <section class="uw-panel decision-workflow-panel">
          <div class="card-heading">
            <h4>Underwriting Decision Workflow</h4>
            <span class="claim-system-tag">No gates</span>
          </div>
          <p class="uw-section-note">Decision workflow data is not available.</p>
        </section>
      `;
    }

    return `
      <section class="uw-panel decision-workflow-panel" data-agent-surface="decision-workflow">
        <div class="card-heading">
          <h4>Underwriting Decision Workflow</h4>
          <span class="claim-system-tag">${escapeHtml((workflow.decision_policy || {}).version || "demo")}</span>
        </div>
        <div class="decision-gate-grid">
          ${gates.map(renderGate).join("")}
        </div>
      </section>
    `;
  }

  function renderGate(gate) {
    const tone = statusTone(gate.status);
    const blockers = Array.isArray(gate.blockers) ? gate.blockers : [];
    const actions = Array.isArray(gate.required_actions) ? gate.required_actions : [];
    const decision = gate.decision || {};
    const score = Math.round(Number(gate.score || 0) * 100);

    return `
      <article class="decision-gate-card ${tone}">
        <div class="decision-gate-top">
          <div>
            <span>${escapeHtml(formatLabel(gate.status || "pending"))}</span>
            <strong>${escapeHtml(gate.label || gate.key || "Decision Gate")}</strong>
          </div>
          <div class="decision-gate-score">${score}%</div>
        </div>
        <p>${escapeHtml(gate.rationale || "")}</p>
        ${blockers.length ? `
          <div class="decision-gate-section">
            <small>Blockers</small>
            <ul>${blockers.slice(0, 4).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          </div>
        ` : '<div class="decision-gate-section"><small>Blockers</small><p>None</p></div>'}
        <div class="decision-gate-section">
          <small>Required Actions</small>
          <ul>${actions.slice(0, 3).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
        ${decision.status ? `
          <div class="decision-record">
            <span>${escapeHtml(formatLabel(decision.status))}</span>
            <small>${escapeHtml([decision.decided_by, decision.decided_at].filter(Boolean).join(" · "))}</small>
            ${decision.note ? `<p>${escapeHtml(decision.note)}</p>` : ""}
          </div>
        ` : ""}
      </article>
    `;
  }

  function statusTone(status) {
    const value = String(status || "").toLowerCase();
    if (/ready|approved|not_required/.test(value)) {
      return "good";
    }
    if (/required|held|declined|needs_work|not_ready/.test(value)) {
      return "alert";
    }
    return "watch";
  }

  function formatLabel(value) {
    return String(value || "")
      .replace(/[_-]+/g, " ")
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

  window.AUDecisionWorkflow = { render };
})();
