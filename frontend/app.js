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
 * Global theme control
 *
 * The button exists outside the three application views, so the same
 * control remains available on the landing, review, and dashboard pages.
 */
const themeToggle = document.querySelector("#theme-toggle");

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
 * Query-relevance warning popup elements.
 */
const relevanceDialog = document.querySelector(
  "#relevance-dialog",
);

const relevanceDialogTitle = document.querySelector(
  "#relevance-dialog-title",
);

const relevanceDialogDescription = document.querySelector(
  "#relevance-dialog-description",
);

const relevanceWarningList = document.querySelector(
  "#relevance-warning-list",
);

const editRelevanceQueriesButton = document.querySelector(
  "#edit-relevance-queries-button",
);

const continueDespiteWarningButton = document.querySelector(
  "#continue-despite-warning-button",
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
 * Theme names are kept as constants so the exact strings are defined
 * in one place instead of being repeated throughout the application.
 */
const THEME_STORAGE_KEY = "nicheradar-theme";
const LIGHT_THEME = "light";
const DARK_THEME = "dark";

/*
 * Every analysis can contain upto five unique queries.
 *
 * The backend also validates this rule, but validating in JavaScript means
 * the user receives an immediate message without making an unnecessary
 * network request.
 */
const MIN_QUERY_COUNT = 1;
const MAX_QUERY_COUNT = 5;

/*
 * These variables hold the browser's current state.
 */
let activeNiche = "";
let originalSuggestedQueries = [];
let reviewedQueries = [];
let relevanceWarnings = [];
let isGeneratingQueries = false;
let isCheckingRelevance = false;
let isRunningAnalysis = false;

/*
 * Apply one of NicheRadar's supported themes.
 *
 * The early script in index.html already chooses the initial theme before
 * CSS loads. This function keeps the button's accessibility information
 * synchronized and optionally remembers later user changes.
 */
function applyTheme(theme, { persist = false } = {}) {
  const appliedTheme =
    theme === DARK_THEME ? DARK_THEME : LIGHT_THEME;

  const darkModeIsActive = appliedTheme === DARK_THEME;
  const nextThemeName = darkModeIsActive
    ? LIGHT_THEME
    : DARK_THEME;

  document.documentElement.dataset.theme = appliedTheme;

  themeToggle.setAttribute(
    "aria-pressed",
    String(darkModeIsActive),
  );

  themeToggle.setAttribute(
    "aria-label",
    `Switch to ${nextThemeName} mode`,
  );

  themeToggle.title = `Switch to ${nextThemeName} mode`;

  if (persist) {
    try {
      window.localStorage.setItem(
        THEME_STORAGE_KEY,
        appliedTheme,
      );
    } catch {
      /*
       * A browser may block localStorage in a restricted privacy mode.
       * The visible theme can still change for the current page session.
       */
    }
  }
}

/*
 * Synchronize the button with the theme chosen by the early HTML script.
 */
function initializeTheme() {
  const initialTheme =
    document.documentElement.dataset.theme === DARK_THEME
      ? DARK_THEME
      : LIGHT_THEME;

  applyTheme(initialTheme);
}

initializeTheme();

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
 * Ask FastAPI to assess manually added or edited queries.
 *
 * This endpoint only uses Groq. It does not begin YouTube collection.
 */
async function requestQueryRelevance(niche, queries) {
  const response = await fetch("/api/query-relevance", {
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
        "NicheRadar could not verify query relevance.",
      ),
    );
  }

  const warningsAreValid =
    Array.isArray(payload?.warnings) &&
    payload.warnings.every(
      (warning) =>
        warning &&
        typeof warning === "object" &&
        typeof warning.query === "string" &&
        typeof warning.reason === "string",
    );

  if (
    !payload ||
    typeof payload.niche !== "string" ||
    !warningsAreValid
  ) {
    throw new Error(
      "NicheRadar received an invalid relevance response.",
    );
  }

  return payload;
}

/*
 * Send the approved queries to the complete analysis API.
 *
 * FastAPI will:
 * - search YouTube using every approved query;
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
 * Normalize query text in the same general way as the backend.
 *
 * Leading and trailing whitespace is removed, and consecutive whitespace
 * characters are collapsed into one ordinary space.
 */
function normalizeQueryText(query) {
  return query.trim().replace(/\s+/g, " ");
}

/*
 * Create a case-insensitive comparison value for one query.
 */
function queryComparisonKey(query) {
  return normalizeQueryText(query).toLowerCase();
}

/*
 * Check whether every query is unique after normalization.
 */
function queriesAreUnique(queries) {
  const comparisonKeys = queries.map(
    queryComparisonKey,
  );

  return (
    new Set(comparisonKeys).size ===
    comparisonKeys.length
  );
}

/*
 * Return only queries that were added or changed by the user.
 *
 * The locked original niche at index zero is deliberately excluded.
 */
function getQueriesNeedingRelevanceCheck() {
  const originalSuggestionKeys = new Set(
    originalSuggestedQueries.map(
      queryComparisonKey,
    ),
  );

  return reviewedQueries
    .slice(1)
    .map(normalizeQueryText)
    .filter(
      (query) =>
        !originalSuggestionKeys.has(
          queryComparisonKey(query),
        ),
    );
}

/*
 * Close the popup if it is currently visible.
 */
function closeRelevanceDialog() {
  if (relevanceDialog.open) {
    relevanceDialog.close();
  }
}


/*
 * Remove all old warning state.
 *
 * This is used whenever the user changes the reviewed queries so an old
 * warning can never be applied to a newer query list.
 */
function resetRelevanceWarnings() {
  relevanceWarnings = [];
  relevanceWarningList.replaceChildren();
  closeRelevanceDialog();
}


/*
 * Rebuild the list of unrelated queries shown inside the popup.
 */
function renderRelevanceWarnings() {
  relevanceWarningList.replaceChildren();

  relevanceWarnings.forEach((warning) => {
    const item = document.createElement("div");
    item.className = "relevance-warning-item";

    const copy = document.createElement("div");
    copy.className = "relevance-warning-copy";

    const queryName = document.createElement("strong");
    queryName.className = "relevance-warning-query";
    queryName.textContent = warning.query;

    const reason = document.createElement("p");
    reason.className = "relevance-warning-reason";
    reason.textContent =
      warning.reason ||
      `This query does not appear related to ${activeNiche}.`;

    const removeButton = document.createElement("button");
    removeButton.type = "button";

    /*
     * Reusing remove-query-button gives this button the same appearance
     * and hover behaviour as the existing query removal controls.
     */
    removeButton.className =
      "remove-query-button relevance-warning-remove-button";

    removeButton.textContent = "Remove";
    removeButton.setAttribute(
      "aria-label",
      `Remove unrelated query ${warning.query}`,
    );

    removeButton.addEventListener("click", () => {
      const warningKey = queryComparisonKey(
        warning.query,
      );

      const queryIndex = reviewedQueries.findIndex(
        (query, index) =>
          index > 0 &&
          queryComparisonKey(query) === warningKey,
      );

      if (queryIndex !== -1) {
        reviewedQueries.splice(queryIndex, 1);
      }

      relevanceWarnings = relevanceWarnings.filter(
        (existingWarning) =>
          queryComparisonKey(existingWarning.query) !==
          warningKey,
      );

      renderQueryReview();

      reviewError.textContent =
        reviewValidationMessage();

      if (relevanceWarnings.length === 0) {
        resetRelevanceWarnings();
        runAnalysisButton.focus();
        return;
      }

      renderRelevanceWarnings();
    });

    copy.append(queryName, reason);
    item.append(copy, removeButton);
    relevanceWarningList.append(item);
  });
}


/*
 * Display the popup for the warnings returned by the backend.
 */
function showRelevanceWarnings(warnings) {
  relevanceWarnings = [...warnings];

  const warningCount = relevanceWarnings.length;
  const multipleWarnings = warningCount !== 1;

  relevanceDialogTitle.textContent = multipleWarnings
    ? "Some queries have no clear relation"
    : "No clear relation found";

  relevanceDialogDescription.textContent =
    multipleWarnings
      ? (
          `${warningCount} searches do not appear clearly related ` +
          `to “${activeNiche}”.`
        )
      : (
          `This search does not appear clearly related ` +
          `to “${activeNiche}”.`
        );

  renderRelevanceWarnings();

  if (!relevanceDialog.open) {
    relevanceDialog.showModal();
  }
}


/*
 * Close the popup and focus the first query that received a warning.
 */
function returnToWarnedQuery() {
  const firstWarning = relevanceWarnings[0];

  const warningIndex = firstWarning
    ? reviewedQueries.findIndex(
        (query) =>
          queryComparisonKey(query) ===
          queryComparisonKey(firstWarning.query),
      )
    : -1;

  resetRelevanceWarnings();

  window.requestAnimationFrame(() => {
    const queryInputs =
      reviewQueryList.querySelectorAll("input");

    if (warningIndex > 0 && queryInputs[warningIndex]) {
      queryInputs[warningIndex].focus();
      queryInputs[warningIndex].select();
      return;
    }

    newQueryInput.focus();
  });
}

/*
 * Return an empty string when the reviewed queries are valid.
 *
 * Otherwise, return the message that should be shown to the user.
 */
function reviewValidationMessage() {
  const count = reviewedQueries.length;

  if (count < MIN_QUERY_COUNT) {
    return "Keep the original niche before continuing.";
  }

  if (count > MAX_QUERY_COUNT) {
    return `Use no more than ${MAX_QUERY_COUNT} queries.`;
  }

  if (reviewedQueries.some((query) => !query.trim())) {
    return "Every query needs some text.";
  }

  const originalQuery = queryComparisonKey(
    reviewedQueries[0],
  );

  const normalizedNiche = queryComparisonKey(
    activeNiche,
  );

  if (originalQuery !== normalizedNiche) {
    return "The original niche must remain as query one.";
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
/*
 * Keep the query-review controls synchronized with the current state.
 *
 * The controls are locked during both relevance checking and YouTube
 * analysis so the submitted query list cannot change midway through a
 * request.
 */
function updateReviewControls() {
  const count = reviewedQueries.length;
  const validationMessage =
    reviewValidationMessage();

  const queryLabel =
    count === 1 ? "query" : "queries";

  const reviewIsBusy =
    isCheckingRelevance || isRunningAnalysis;

  queryCount.textContent =
    `${count} ${queryLabel} ready · maximum ${MAX_QUERY_COUNT}`;

  addQueryButton.disabled =
    reviewIsBusy || count >= MAX_QUERY_COUNT;

  newQueryInput.disabled =
    reviewIsBusy || count >= MAX_QUERY_COUNT;

  runAnalysisButton.disabled =
    reviewIsBusy || Boolean(validationMessage);

  reviewBackButton.disabled = reviewIsBusy;

  if (isCheckingRelevance) {
    runAnalysisButtonLabel.textContent =
      "Checking queries...";
  } else if (isRunningAnalysis) {
    runAnalysisButtonLabel.textContent =
      "Analysing videos...";
  } else {
    runAnalysisButtonLabel.textContent =
      "Use these queries";
  }

  runAnalysisButton.setAttribute(
    "aria-busy",
    String(reviewIsBusy),
  );

  for (
    const control of reviewQueryList.querySelectorAll(
      "input, button",
    )
  ) {
    control.disabled = reviewIsBusy;
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

    const isOriginalQuery = index === 0;

    if (isOriginalQuery) {
      input.readOnly = true;
      input.classList.add("locked-query-input");
      input.setAttribute(
        "aria-label",
        "Original niche query, locked",
      );

      const lockedBadge = document.createElement("span");
      lockedBadge.className = "locked-query-badge";
      lockedBadge.textContent = "Required";

      item.append(number, input, lockedBadge);
    } else {
      input.setAttribute(
        "aria-label",
        `Search query ${index + 1}`,
      );

      input.addEventListener("input", () => {
        resetRelevanceWarnings();

        reviewedQueries[index] = input.value;

        reviewError.textContent =
          reviewValidationMessage();

        updateReviewControls();
      });

      const removeButton =
        document.createElement("button");

      removeButton.className =
        "remove-query-button";

      removeButton.type = "button";
      removeButton.textContent = "Remove";

      removeButton.setAttribute(
        "aria-label",
        `Remove query ${index + 1}`,
      );

      removeButton.addEventListener("click", () => {
        resetRelevanceWarnings();

        reviewedQueries.splice(index, 1);
        renderQueryReview();

        reviewError.textContent =
          reviewValidationMessage();

        if (!newQueryInput.disabled) {
          newQueryInput.focus();
        }
      });

      item.append(number, input, removeButton);
    }

    reviewQueryList.append(item);
  });

  updateReviewControls();
}

/*
 * Add the text from the "Add another query" field.
 */
function addReviewedQuery() {
  const query = normalizeQueryText(
    newQueryInput.value,
  );

  if (reviewedQueries.length >= MAX_QUERY_COUNT) {
    reviewError.textContent =
      `You already have the maximum of ${MAX_QUERY_COUNT} queries.`;
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
      queryComparisonKey(item) ===
      queryComparisonKey(query),
  );

  if (queryAlreadyExists) {
    reviewError.textContent =
      "That query is already in the list.";
    newQueryInput.focus();
    return;
  }

  resetRelevanceWarnings();
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

  const hasThumbnail =
    typeof videoData.thumbnail_url === "string" &&
    videoData.thumbnail_url.trim() !== "";

  if (hasThumbnail) {
    const thumbnailImage = document.createElement("img");

    thumbnailImage.src = videoData.thumbnail_url;
    thumbnailImage.alt = "";
    thumbnailImage.loading = "lazy";
    thumbnailImage.decoding = "async";

    thumbnailImage.addEventListener("error", () => {
      thumbnail.classList.add("thumbnail-fallback");
      thumbnail.replaceChildren(
        document.createElement("i"),
      );
    });

    thumbnail.append(thumbnailImage);
  } else {
    thumbnail.classList.add("thumbnail-fallback");
    thumbnail.append(document.createElement("i"));
  }

  const videoText = document.createElement("div");
  const heading = document.createElement("h3");
  const channel = document.createElement("p");

  heading.textContent = videoData.title;
  channel.textContent = videoData.channel_name;

  videoText.append(heading, channel);
  video.append(thumbnail, videoText);

  const subscriberText =
    videoData.subscribers === null
      ? "Hidden"
      : formatCompactNumber(videoData.subscribers);

  const cardLink = document.createElement("a");

  cardLink.className = "result-row-link";
  cardLink.href = videoData.url;
  cardLink.target = "_blank";
  cardLink.rel = "noopener noreferrer";
  cardLink.setAttribute(
    "aria-label",
    `Open ${videoData.title} on YouTube`,
  );

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
    cardLink,
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

  originalSuggestedQueries = queries.map(
    normalizeQueryText,
  );

  reviewedQueries = [
    ...originalSuggestedQueries,
  ];

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
 * Run the real YouTube analysis after the queries have either:
 *
 * 1. Passed the relevance check, or
 * 2. Been explicitly approved with "Continue anyway".
 */
async function runApprovedAnalysis() {
  if (isRunningAnalysis) {
    return;
  }

  resetRelevanceWarnings();
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
}

/*
 * Query-review submission:
 *
 * 1. Normalize and validate the approved queries.
 * 2. Find queries that were added or edited by the user.
 * 3. Ask the backend to check only those changed queries.
 * 4. Show a popup when any changed query appears unrelated.
 * 5. Otherwise begin the real YouTube analysis.
 */
queryReviewForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    if (isCheckingRelevance || isRunningAnalysis) {
      return;
    }

    reviewedQueries = reviewedQueries.map(
      normalizeQueryText,
    );

    renderQueryReview();

    const validationMessage =
      reviewValidationMessage();

    if (validationMessage) {
      reviewError.textContent = validationMessage;
      return;
    }

    reviewError.textContent = "";
    resetRelevanceWarnings();

    const queriesToCheck =
      getQueriesNeedingRelevanceCheck();

    /*
     * Unchanged Groq suggestions are already related by design.
     * If nothing was manually added or edited, skip another Groq request.
     */
    if (queriesToCheck.length === 0) {
      await runApprovedAnalysis();
      return;
    }

    let relevanceReview;

    isCheckingRelevance = true;
    updateReviewControls();

    try {
      relevanceReview =
        await requestQueryRelevance(
          activeNiche,
          queriesToCheck,
        );
    } catch (error) {
      reviewError.textContent =
        error instanceof Error
          ? error.message
          : "NicheRadar could not check these queries.";

      return;
    } finally {
      isCheckingRelevance = false;
      updateReviewControls();
    }

    if (relevanceReview.warnings.length > 0) {
      showRelevanceWarnings(
        relevanceReview.warnings,
      );

      return;
    }

    await runApprovedAnalysis();
  },
);

/*
 * Return to editing without starting the YouTube analysis.
 */
editRelevanceQueriesButton.addEventListener(
  "click",
  returnToWarnedQuery,
);


/*
 * The warning is advisory, so the user may deliberately include the query.
 */
continueDespiteWarningButton.addEventListener(
  "click",
  async () => {
    await runApprovedAnalysis();
  },
);


/*
 * Pressing Escape behaves like "Back to queries".
 */
relevanceDialog.addEventListener(
  "cancel",
  (event) => {
    event.preventDefault();
    returnToWarnedQuery();
  },
);

/*
 * Switch to the opposite theme and remember the user's selection.
 */
themeToggle.addEventListener("click", () => {
  const currentTheme =
    document.documentElement.dataset.theme === DARK_THEME
      ? DARK_THEME
      : LIGHT_THEME;

  const nextTheme =
    currentTheme === DARK_THEME
      ? LIGHT_THEME
      : DARK_THEME;

  applyTheme(nextTheme, {
    persist: true,
  });
});

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
