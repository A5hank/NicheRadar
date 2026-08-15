"use strict";

/*
 * Page sections
 *
 * NicheRadar has three main views:
 * 1. The landing/search page.
 * 2. The query-review page.
 * 3. The analysis dashboard.
 */
const landingView = document.querySelector("#landing-view");
const reviewView = document.querySelector("#review-view");
const dashboardView = document.querySelector("#dashboard-view");

/*
 * Landing-page elements
 */
const nicheForm = document.querySelector("#niche-form");
const nicheInput = document.querySelector("#niche-input");
const formError = document.querySelector("#form-error");
const startAnalysisButton = document.querySelector(
  "#start-analysis-button",
);
const startAnalysisButtonLabel = document.querySelector(
  "#start-analysis-button-label",
);

/*
 * Query-review elements
 */
const queryReviewForm = document.querySelector("#query-review-form");
const reviewNiche = document.querySelector("#review-niche");
const queryCount = document.querySelector("#query-count");
const reviewQueryList = document.querySelector("#review-query-list");
const newQueryInput = document.querySelector("#new-query-input");
const addQueryButton = document.querySelector("#add-query-button");
const reviewError = document.querySelector("#review-error");
const runAnalysisButton = document.querySelector(
  "#run-analysis-button",
);
const runAnalysisButtonLabel = document.querySelector(
  "#run-analysis-button-label",
);
const reviewBackButton = document.querySelector(
  "#review-back-button",
);

/*
 * Dashboard elements
 */
const dashboardTitle = document.querySelector("#dashboard-title");
const approvedQueryCount = document.querySelector(
  "#approved-query-count",
);
const queryList = document.querySelector("#query-list");
const videosConsideredCount = document.querySelector(
  "#videos-considered-count",
);
const breakoutCount = document.querySelector("#breakout-count");
const exceptionalCount = document.querySelector(
  "#exceptional-count",
);
const resultList = document.querySelector("#result-list");
const newAnalysisButton = document.querySelector(
  "#new-analysis-button",
);
const mobileNewAnalysis = document.querySelector(
  "#mobile-new-analysis",
);

/*
 * Every analysis must contain exactly five unique queries.
 *
 * The backend also validates this rule, but validating in JavaScript means
 * the user receives an immediate message without making an unnecessary
 * network request.
 */
const REQUIRED_QUERY_COUNT = 5;

/*
 * These variables hold the browser's current state.
 */
let activeNiche = "";
let reviewedQueries = [];
let isGeneratingQueries = false;
let isRunningAnalysis = false;

/*
 * Intl.NumberFormat converts large values into compact readable text.
 *
 * Examples:
 * 250000 becomes "250K"
 * 1200000 becomes "1.2M"
 */
const compactNumberFormatter = new Intl.NumberFormat("en", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const wholeNumberFormatter = new Intl.NumberFormat("en");

/*
 * Convert an API number into compact dashboard text.
 */
function formatCompactNumber(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return compactNumberFormatter.format(number);
}

/*
 * Format whole-number statistics such as "videos considered".
 */
function formatWholeNumber(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "0";
  }

  return wholeNumberFormatter.format(number);
}

/*
 * Hidden subscriber counts produce null multipliers.
 *
 * In that case, the dashboard displays an em dash instead of pretending
 * that the multiplier is zero.
 */
function formatMultiplier(value) {
  if (value === null || value === undefined) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(2)}x`;
}

/*
 * FastAPI normally returns errors in a property named "detail".
 *
 * Validation errors may return an array of objects instead of one string,
 * so this function understands both forms.
 */
function extractApiError(payload, fallbackMessage) {
  if (!payload || typeof payload !== "object") {
    return fallbackMessage;
  }

  if (typeof payload.detail === "string") {
    return payload.detail;
  }

  if (Array.isArray(payload.detail)) {
    const firstError = payload.detail.find(
      (item) =>
        item &&
        typeof item === "object" &&
        typeof item.msg === "string",
    );

    if (firstError) {
      return firstError.msg;
    }
  }

  return fallbackMessage;
}

/*
 * Fetch the body of an HTTP response.
 *
 * Returning null when JSON parsing fails lets the calling function show
 * a useful message instead of throwing a confusing JSON syntax error.
 */
async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

/*
 * Ask the FastAPI backend to generate query suggestions using Groq.
 *
 * The API key stays inside Python and is never exposed to the browser.
 */
async function requestQuerySuggestions(niche) {
  const response = await fetch("/api/queries", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      niche,
    }),
  });

  const payload = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      extractApiError(
        payload,
        "NicheRadar could not generate search queries.",
      ),
    );
  }

  if (
    !payload ||
    typeof payload.niche !== "string" ||
    !Array.isArray(payload.queries) ||
    payload.queries.some((query) => typeof query !== "string")
  ) {
    throw new Error(
      "NicheRadar received an invalid query response.",
    );
  }

  return payload;
}

/*
 * Send the approved five queries to the complete analysis API.
 *
 * FastAPI will:
 * - search YouTube using all five queries;
 * - combine and deduplicate the videos;
 * - select the top videos by total views;
 * - rank the selected videos by views per day;
 * - calculate breakout and exceptional-performance labels.
 */
async function requestAnalysis(niche, queries) {
  const response = await fetch("/api/analyses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      niche,
      queries,
    }),
  });

  const payload = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      extractApiError(
        payload,
        "NicheRadar could not complete the analysis.",
      ),
    );
  }

  if (
    !payload ||
    typeof payload !== "object" ||
    !Array.isArray(payload.queries) ||
    !Array.isArray(payload.videos)
  ) {
    throw new Error(
      "NicheRadar received an invalid analysis response.",
    );
  }

  return payload;
}

/*
 * Display the approved query chips above the statistics.
 */
function renderQueries(queries) {
  queryList.replaceChildren();

  for (const query of queries) {
    const chip = document.createElement("span");
    chip.textContent = query;
    queryList.append(chip);
  }
}

/*
 * Compare queries without being affected by capitalisation.
 *
 * Therefore "Marvel News" and "marvel news" are treated as duplicates.
 */
function queriesAreUnique(queries) {
  const normalizedQueries = queries.map((query) =>
    query.trim().toLowerCase(),
  );

  return new Set(normalizedQueries).size === normalizedQueries.length;
}

/*
 * Return an empty string when the reviewed queries are valid.
 *
 * Otherwise, return the message that should be shown to the user.
 */
function reviewValidationMessage() {
  if (reviewedQueries.length !== REQUIRED_QUERY_COUNT) {
    return `Choose exactly ${REQUIRED_QUERY_COUNT} queries before continuing.`;
  }

  if (reviewedQueries.some((query) => !query.trim())) {
    return "Every query needs some text.";
  }

  if (!queriesAreUnique(reviewedQueries)) {
    return "Each query must be different.";
  }

  return "";
}

/*
 * Keep the query-review controls in sync with the current state.
 *
 * During analysis, the inputs and buttons are disabled so the user cannot
 * change the queries after the request has already been sent.
 */
function updateReviewControls() {
  const count = reviewedQueries.length;
  const validationMessage = reviewValidationMessage();

  queryCount.textContent =
    `${count} of ${REQUIRED_QUERY_COUNT} queries ready`;

  addQueryButton.disabled =
    isRunningAnalysis || count >= REQUIRED_QUERY_COUNT;

  newQueryInput.disabled =
    isRunningAnalysis || count >= REQUIRED_QUERY_COUNT;

  runAnalysisButton.disabled =
    isRunningAnalysis || Boolean(validationMessage);

  reviewBackButton.disabled = isRunningAnalysis;

  runAnalysisButtonLabel.textContent = isRunningAnalysis
    ? "Analysing videos..."
    : "Use these queries";

  runAnalysisButton.setAttribute(
    "aria-busy",
    String(isRunningAnalysis),
  );

  for (const control of reviewQueryList.querySelectorAll(
    "input, button",
  )) {
    control.disabled = isRunningAnalysis;
  }
}

/*
 * Rebuild the editable query list.
 *
 * Each input directly updates the matching value in reviewedQueries.
 */
function renderQueryReview() {
  reviewQueryList.replaceChildren();

  reviewedQueries.forEach((query, index) => {
    const item = document.createElement("div");
    item.className = "review-query-item";

    const number = document.createElement("span");
    number.className = "query-number";
    number.textContent = index + 1;

    const input = document.createElement("input");
    input.type = "text";
    input.value = query;
    input.setAttribute(
      "aria-label",
      `Search query ${index + 1}`,
    );

    input.addEventListener("input", () => {
      reviewedQueries[index] = input.value;
      reviewError.textContent = reviewValidationMessage();
      updateReviewControls();
    });

    const removeButton = document.createElement("button");
    removeButton.className = "remove-query-button";
    removeButton.type = "button";
    removeButton.textContent = "Remove";
    removeButton.setAttribute(
      "aria-label",
      `Remove query ${index + 1}`,
    );

    removeButton.addEventListener("click", () => {
      reviewedQueries.splice(index, 1);
      renderQueryReview();
      reviewError.textContent = reviewValidationMessage();

      if (!newQueryInput.disabled) {
        newQueryInput.focus();
      }
    });

    item.append(number, input, removeButton);
    reviewQueryList.append(item);
  });

  updateReviewControls();
}

/*
 * Add the text from the "Add another query" field.
 */
function addReviewedQuery() {
  const query = newQueryInput.value.trim();

  if (reviewedQueries.length >= REQUIRED_QUERY_COUNT) {
    reviewError.textContent =
      `You already have ${REQUIRED_QUERY_COUNT} queries.`;
    return;
  }

  if (!query) {
    reviewError.textContent =
      "Type a query before adding it.";
    newQueryInput.focus();
    return;
  }

  const queryAlreadyExists = reviewedQueries.some(
    (item) =>
      item.trim().toLowerCase() === query.toLowerCase(),
  );

  if (queryAlreadyExists) {
    reviewError.textContent =
      "That query is already in the list.";
    newQueryInput.focus();
    return;
  }

  reviewedQueries.push(query);
  newQueryInput.value = "";
  renderQueryReview();
  reviewError.textContent = reviewValidationMessage();
}

/*
 * Create one basic table cell.
 *
 * The data-label value is used by the responsive mobile layout.
 */
function createTextCell(label, value, emphasis = false) {
  const elementName = emphasis ? "strong" : "span";
  const cell = document.createElement(elementName);

  cell.dataset.label = label;
  cell.textContent = value;

  return cell;
}

/*
 * Convert the API performance value into the corresponding CSS class.
 */
function performanceClass(performance) {
  if (performance === "breakout") {
    return "breakout-row";
  }

  if (performance === "exceptional_performance") {
    return "exceptional-row";
  }

  return "regular-row";
}

/*
 * Build one result row using a real video returned by FastAPI.
 *
 * No innerHTML is used for API data. Assigning values through textContent
 * prevents titles or channel names from being interpreted as HTML.
 */
function createResultRow(videoData) {
  const row = document.createElement("article");

  row.className =
    `result-row ${performanceClass(videoData.performance)}`;

  row.setAttribute("role", "row");

  const rank = document.createElement("strong");
  rank.className = "result-rank";
  rank.textContent = videoData.rank;

  const video = document.createElement("div");
  video.className = "result-video";

  const thumbnail = document.createElement("span");
  thumbnail.className = "thumbnail";
  thumbnail.setAttribute("aria-hidden", "true");
  thumbnail.append(document.createElement("i"));

  const videoText = document.createElement("div");
  const heading = document.createElement("h3");
  const channel = document.createElement("p");

  heading.textContent = videoData.title;
  channel.textContent = videoData.channel_name;

  videoText.append(heading, channel);
  video.append(thumbnail, videoText);

  const link = document.createElement("a");
  link.href = videoData.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "Open ↗";
  link.setAttribute(
    "aria-label",
    `Open ${videoData.title} on YouTube`,
  );

  const subscriberText =
    videoData.subscribers === null
      ? "Hidden"
      : formatCompactNumber(videoData.subscribers);

  row.append(
    rank,
    video,
    createTextCell(
      "Views",
      formatCompactNumber(videoData.views),
    ),
    createTextCell(
      "Views/day",
      formatCompactNumber(videoData.views_per_day),
    ),
    createTextCell(
      "Subscribers",
      subscriberText,
    ),
    createTextCell(
      "Multiplier",
      formatMultiplier(videoData.subscriber_multiplier),
      true,
    ),
    link,
  );

  return row;
}

/*
 * Render every ranked video.
 *
 * The backend already sends them in views-per-day order, so JavaScript
 * preserves that order rather than sorting them again.
 */
function renderResults(videos) {
  resultList.replaceChildren();

  if (videos.length === 0) {
    const emptyMessage = document.createElement("p");
    emptyMessage.className = "empty-results";
    emptyMessage.textContent =
      "No matching Shorts were returned for these queries.";
    resultList.append(emptyMessage);
    return;
  }

  for (const video of videos) {
    resultList.append(createResultRow(video));
  }
}

/*
 * Change the landing button while Groq generates suggestions.
 */
function setLandingBusy(isBusy) {
  nicheInput.disabled = isBusy;
  startAnalysisButton.disabled = isBusy;
  startAnalysisButtonLabel.textContent = isBusy
    ? "Building queries..."
    : "Analyse";

  startAnalysisButton.setAttribute(
    "aria-busy",
    String(isBusy),
  );
}

/*
 * Open the query-review screen with Groq's real suggestions.
 */
function showReview(niche, queries) {
  activeNiche = niche;
  reviewedQueries = [...queries];

  reviewNiche.textContent = niche;
  reviewError.textContent = "";
  newQueryInput.value = "";

  renderQueryReview();
  reviewError.textContent = reviewValidationMessage();

  landingView.hidden = true;
  dashboardView.hidden = true;
  reviewView.hidden = false;

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

/*
 * Populate and display the dashboard from the analysis API response.
 */
function showDashboard(analysis) {
  dashboardTitle.textContent = analysis.niche;

  approvedQueryCount.textContent =
    `${analysis.queries.length} approved`;

  videosConsideredCount.textContent =
    formatWholeNumber(analysis.videos_considered);

  breakoutCount.textContent =
    formatWholeNumber(analysis.breakout_count);

  exceptionalCount.textContent =
    formatWholeNumber(
      analysis.exceptional_performance_count,
    );

  renderQueries(analysis.queries);
  renderResults(analysis.videos);

  landingView.hidden = true;
  reviewView.hidden = true;
  dashboardView.hidden = false;

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

/*
 * Return to the landing page.
 */
function showLanding({ clearInput = true } = {}) {
  dashboardView.hidden = true;
  reviewView.hidden = true;
  landingView.hidden = false;

  if (clearInput) {
    nicheInput.value = "";
  }

  formError.textContent = "";
  setLandingBusy(false);

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });

  nicheInput.focus();
}

/*
 * Landing-page submission:
 * 1. Validate the niche.
 * 2. Request Groq suggestions.
 * 3. Open the review screen.
 *
 * Because this listens to the form's submit event, both clicking the
 * button and pressing Enter in the search field work.
 */
nicheForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (isGeneratingQueries) {
    return;
  }

  const niche = nicheInput.value.trim();

  if (!niche) {
    formError.textContent =
      "Enter a niche to begin your analysis.";
    nicheInput.focus();
    return;
  }

  formError.textContent = "";
  isGeneratingQueries = true;
  setLandingBusy(true);

  try {
    const expansion =
      await requestQuerySuggestions(niche);

    showReview(
      expansion.niche,
      expansion.queries,
    );
  } catch (error) {
    formError.textContent =
      error instanceof Error
        ? error.message
        : "NicheRadar could not generate search queries.";
  } finally {
    isGeneratingQueries = false;
    setLandingBusy(false);
  }
});

/*
 * Add-query controls.
 */
addQueryButton.addEventListener(
  "click",
  addReviewedQuery,
);

newQueryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    addReviewedQuery();
  }
});

/*
 * Query-review submission:
 * 1. Clean the five queries.
 * 2. Validate them.
 * 3. Send them to /api/analyses.
 * 4. Display the real dashboard.
 */
queryReviewForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    if (isRunningAnalysis) {
      return;
    }

    reviewedQueries = reviewedQueries.map(
      (query) => query.trim(),
    );

    const validationMessage =
      reviewValidationMessage();

    if (validationMessage) {
      reviewError.textContent = validationMessage;
      renderQueryReview();
      return;
    }

    reviewError.textContent = "";
    isRunningAnalysis = true;
    updateReviewControls();

    try {
      const analysis = await requestAnalysis(
        activeNiche,
        reviewedQueries,
      );

      showDashboard(analysis);
    } catch (error) {
      reviewError.textContent =
        error instanceof Error
          ? error.message
          : "NicheRadar could not complete the analysis.";
    } finally {
      isRunningAnalysis = false;
      updateReviewControls();
    }
  },
);

/*
 * Navigation controls.
 */
reviewBackButton.addEventListener("click", () => {
  showLanding({
    clearInput: false,
  });
});

newAnalysisButton.addEventListener(
  "click",
  () => showLanding(),
);

mobileNewAnalysis.addEventListener(
  "click",
  () => showLanding(),
);

for (const homeLink of document.querySelectorAll(".brand")) {
  homeLink.addEventListener("click", (event) => {
    event.preventDefault();

    if (!isRunningAnalysis) {
      showLanding();
    }
  });
}
