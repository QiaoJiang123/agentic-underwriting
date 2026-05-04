const searchInput = document.querySelector("#submissionSearch");
const searchResults = document.querySelector("#searchResults");
const exampleResults = document.querySelector("#exampleResults");

let submissions = [];

initSearch();

async function initSearch() {
  try {
    const response = await fetch("/api/search-metadata");
    const data = await response.json();
    submissions = Array.isArray(data.submissions) ? data.submissions : [];
    renderMatches([]);
    renderExamples(submissions.slice(0, 3));
    searchInput.focus();
  } catch (error) {
    searchResults.innerHTML = '<p class="empty-state">Unable to load submission index.</p>';
  }
}

searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim().toLowerCase();

  if (!query) {
    renderMatches([]);
    return;
  }

  const filtered = submissions.filter((submission) => {
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

    return haystack.includes(query);
  });

  renderMatches(filtered);
});

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

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
