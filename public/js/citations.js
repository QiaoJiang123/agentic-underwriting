(function () {
  function render(sources) {
    const normalized = normalizeSources(sources);
    if (!normalized.length) {
      return "";
    }

    return `
      <section class="source-citations" aria-label="Answer sources">
        <div class="source-citations-heading">Sources used</div>
        <div class="source-citation-list">
          ${normalized.map(renderCitation).join("")}
        </div>
      </section>
    `;
  }

  function normalizeSources(sources) {
    const seen = new Set();
    return (Array.isArray(sources) ? sources : [])
      .filter((source) => source && source.source)
      .map((source) => ({
        skill: String(source.skill || "data"),
        source: String(source.source || "")
      }))
      .filter((source) => {
        const key = `${source.skill}:${source.source}`;
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      })
      .slice(0, 8);
  }

  function renderCitation(source) {
    const label = formatSourceLabel(source.source);
    return `
      <span class="source-citation" title="${escapeHtml(source.source)}">
        <strong>${escapeHtml(formatLabel(source.skill))}</strong>
        <span>${escapeHtml(label)}</span>
      </span>
    `;
  }

  function formatSourceLabel(source) {
    if (source.startsWith("/api/")) {
      return source;
    }
    const parts = source.split("#");
    const filePart = parts[0].split("/").pop() || source;
    return parts[1] ? `${filePart} #${parts[1]}` : filePart;
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

  window.AUCitations = { render };
})();
