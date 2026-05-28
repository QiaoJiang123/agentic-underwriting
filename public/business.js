const businessSlides = Array.from(document.querySelectorAll(".business-slide-page"));
const businessSlideList = document.querySelector("#businessSlideList");
const businessSlideTitle = document.querySelector("#businessSlideTitle");
const businessSlideCounter = document.querySelector("#businessSlideCounter");
const businessProgressBar = document.querySelector("#businessProgressBar");
const businessPrevSlide = document.querySelector("#businessPrevSlide");
const businessNextSlide = document.querySelector("#businessNextSlide");
const businessPresentButton = document.querySelector("#businessPresentButton");

let activeBusinessSlide = getSlideIndexFromHash();

initBusinessDeck();

function initBusinessDeck() {
  renderBusinessSlideList();
  showBusinessSlide(activeBusinessSlide, { updateHash: false });

  businessPrevSlide?.addEventListener("click", () => showBusinessSlide(activeBusinessSlide - 1));
  businessNextSlide?.addEventListener("click", () => showBusinessSlide(activeBusinessSlide + 1));
  businessPresentButton?.addEventListener("click", enterBusinessPresentationMode);

  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight" || event.key === "PageDown" || event.key === " ") {
      event.preventDefault();
      showBusinessSlide(activeBusinessSlide + 1);
    }
    if (event.key === "ArrowLeft" || event.key === "PageUp") {
      event.preventDefault();
      showBusinessSlide(activeBusinessSlide - 1);
    }
    if (event.key === "Home") {
      event.preventDefault();
      showBusinessSlide(0);
    }
    if (event.key === "End") {
      event.preventDefault();
      showBusinessSlide(businessSlides.length - 1);
    }
  });

  window.addEventListener("hashchange", () => {
    showBusinessSlide(getSlideIndexFromHash(), { updateHash: false });
  });
}

function renderBusinessSlideList() {
  if (!businessSlideList) {
    return;
  }

  businessSlideList.innerHTML = businessSlides
    .map((slide, index) => {
      const title = slide.dataset.slideTitle || `Slide ${index + 1}`;
      return `
        <button class="business-slide-list-button" type="button" data-slide-target="${index}">
          <span>${String(index + 1).padStart(2, "0")}</span>
          <strong>${escapeBusinessHtml(title)}</strong>
        </button>
      `;
    })
    .join("");

  businessSlideList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-slide-target]");
    if (!button) {
      return;
    }
    showBusinessSlide(Number(button.dataset.slideTarget || 0));
  });
}

function showBusinessSlide(index, options = {}) {
  const boundedIndex = Math.min(Math.max(Number(index) || 0, 0), businessSlides.length - 1);
  activeBusinessSlide = boundedIndex;

  businessSlides.forEach((slide, slideIndex) => {
    slide.classList.toggle("active", slideIndex === boundedIndex);
  });

  document.querySelectorAll("[data-slide-target]").forEach((button) => {
    const isActive = Number(button.dataset.slideTarget || 0) === boundedIndex;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-current", isActive ? "step" : "false");
  });

  const currentSlide = businessSlides[boundedIndex];
  const title = currentSlide?.dataset.slideTitle || `Slide ${boundedIndex + 1}`;
  if (businessSlideTitle) {
    businessSlideTitle.textContent = title;
  }
  if (businessSlideCounter) {
    businessSlideCounter.textContent = `${boundedIndex + 1} / ${businessSlides.length}`;
  }
  if (businessProgressBar) {
    businessProgressBar.style.width = `${((boundedIndex + 1) / businessSlides.length) * 100}%`;
  }
  if (businessPrevSlide) {
    businessPrevSlide.disabled = boundedIndex === 0;
  }
  if (businessNextSlide) {
    businessNextSlide.disabled = boundedIndex === businessSlides.length - 1;
    businessNextSlide.textContent = boundedIndex === businessSlides.length - 1 ? "Done" : "Next";
  }

  if (options.updateHash !== false) {
    window.history.replaceState({}, "", `#slide-${boundedIndex + 1}`);
  }
}

function getSlideIndexFromHash() {
  const match = String(window.location.hash || "").match(/slide-(\d+)/i);
  if (!match) {
    return 0;
  }
  return Math.max(Number(match[1]) - 1, 0);
}

async function enterBusinessPresentationMode() {
  try {
    if (!document.fullscreenElement && document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen();
      businessPresentButton.textContent = "Exit";
      return;
    }
    if (document.exitFullscreen) {
      await document.exitFullscreen();
      businessPresentButton.textContent = "Present";
    }
  } catch (error) {
    console.info("Fullscreen presentation mode is unavailable in this browser surface.", error);
    businessPresentButton.textContent = "Present";
  }
}

function escapeBusinessHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
