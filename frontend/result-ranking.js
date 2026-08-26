"use strict";

/*
 * Pure result-list ordering utilities shared by the browser dashboard and
 * the dependency-free Node regression tests.
 */
(function exposeResultRanking(globalScope) {
  const RANKING_MODES = Object.freeze({
    VIEWS_PER_DAY: "views_per_day",
    VIEWS: "views",
    SUBSCRIBER_MULTIPLIER: "subscriber_multiplier",
  });

  const DEFAULT_RANKING_MODE = RANKING_MODES.VIEWS_PER_DAY;
  const rankingModeValues = new Set(Object.values(RANKING_MODES));

  function normalizeRankingMode(value) {
    return rankingModeValues.has(value) ? value : DEFAULT_RANKING_MODE;
  }

  function finiteNumberOrNull(value) {
    if (
      value === null ||
      value === undefined ||
      (typeof value === "string" && value.trim() === "")
    ) {
      return null;
    }

    const number = Number(value);

    return Number.isFinite(number) ? number : null;
  }

  function compareMetricDescending(firstValue, secondValue) {
    const firstNumber = finiteNumberOrNull(firstValue);
    const secondNumber = finiteNumberOrNull(secondValue);

    if (firstNumber === null && secondNumber === null) {
      return 0;
    }

    if (firstNumber === null) {
      return 1;
    }

    if (secondNumber === null) {
      return -1;
    }

    return secondNumber - firstNumber;
  }

  function sortResultVideos(videos, rankingMode = DEFAULT_RANKING_MODE) {
    if (!Array.isArray(videos)) {
      throw new TypeError("videos must be an array");
    }

    const normalizedMode = normalizeRankingMode(rankingMode);

    return videos
      .map((video, originalIndex) => ({
        video,
        originalIndex,
      }))
      .sort((firstEntry, secondEntry) => {
        const metricComparison = compareMetricDescending(
          firstEntry.video[normalizedMode],
          secondEntry.video[normalizedMode],
        );

        if (metricComparison !== 0) {
          return metricComparison;
        }

        return firstEntry.originalIndex - secondEntry.originalIndex;
      })
      .map((entry, index) => ({
        ...entry.video,
        rank: index + 1,
      }));
  }

  const resultRanking = Object.freeze({
    DEFAULT_RANKING_MODE,
    RANKING_MODES,
    normalizeRankingMode,
    sortResultVideos,
  });

  if (typeof module !== "undefined" && module.exports) {
    module.exports = resultRanking;
  }

  if (globalScope) {
    globalScope.NicheRadarResultRanking = resultRanking;
  }
})(typeof globalThis === "undefined" ? undefined : globalThis);
