"use strict";

/*
 * Pure spelling-suggestion utilities shared by the landing page and the
 * dependency-free Node regression tests.
 */
(function exposeSpellingSuggestion(globalScope) {
  function normalizeNicheText(value) {
    return typeof value === "string" ? value.trim().replace(/\s+/g, " ") : "";
  }

  function comparisonKey(value) {
    return normalizeNicheText(value).toLowerCase();
  }

  /*
   * Return a suggestion only when the API response belongs to this exact
   * submitted niche. Invalid or unavailable spelling checks deliberately
   * become null so the caller can continue with the original input.
   */
  function getUsableSpellingSuggestion(requestedNiche, payload) {
    const normalizedRequestedNiche = normalizeNicheText(requestedNiche);

    if (!normalizedRequestedNiche || !payload || typeof payload !== "object") {
      return null;
    }

    if (typeof payload.niche !== "string") {
      return null;
    }

    if (comparisonKey(payload.niche) !== comparisonKey(normalizedRequestedNiche)) {
      return null;
    }

    if (payload.suggestion === null) {
      return null;
    }

    if (typeof payload.suggestion !== "string") {
      return null;
    }

    const normalizedSuggestion = normalizeNicheText(payload.suggestion);

    if (
      !normalizedSuggestion ||
      comparisonKey(normalizedSuggestion) === comparisonKey(normalizedRequestedNiche)
    ) {
      return null;
    }

    return normalizedSuggestion;
  }

  /*
   * Keep is the default. The suggested spelling is used only after the
   * caller passes the explicit "use" choice from the visible UI.
   */
  function chooseNicheAfterSpellingCheck(originalNiche, suggestion, choice) {
    const normalizedOriginalNiche = normalizeNicheText(originalNiche);
    const normalizedSuggestion = normalizeNicheText(suggestion);

    if (!normalizedOriginalNiche) {
      throw new TypeError("originalNiche must contain text");
    }

    if (
      choice === "use" &&
      normalizedSuggestion &&
      comparisonKey(normalizedSuggestion) !== comparisonKey(normalizedOriginalNiche)
    ) {
      return normalizedSuggestion;
    }

    return normalizedOriginalNiche;
  }

  const spellingSuggestion = Object.freeze({
    chooseNicheAfterSpellingCheck,
    getUsableSpellingSuggestion,
    normalizeNicheText,
  });

  if (typeof module !== "undefined" && module.exports) {
    module.exports = spellingSuggestion;
  }

  if (globalScope) {
    globalScope.NicheRadarSpellingSuggestion = spellingSuggestion;
  }
})(typeof globalThis === "undefined" ? undefined : globalThis);
