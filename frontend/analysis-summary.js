"use strict";

/*
 * Pure analysis-summary utilities shared by the browser dashboard and the
 * dependency-free Node regression tests. The browser sends only completed,
 * deterministic analysis facts to the summary endpoint; it never sends raw
 * video titles or treats an AI response as a source of scoring facts.
 */
(function exposeAnalysisSummary(globalScope) {
  const NEW_CREATOR_SIGNAL_LABELS = Object.freeze({
    favourable: "Favourable",
    mixed: "Mixed",
    limited: "Limited",
    insufficient_evidence: "Insufficient evidence",
  });

  function normalizeText(value) {
    return typeof value === "string" ? value.trim().replace(/\s+/g, " ") : "";
  }

  function comparisonKey(value) {
    return normalizeText(value).toLowerCase();
  }

  function asNonNegativeNumber(value) {
    const number = Number(value);

    return Number.isFinite(number) && number >= 0 ? number : null;
  }

  function asNonNegativeInteger(value) {
    const number = asNonNegativeNumber(value);

    return number !== null && Number.isInteger(number) ? number : null;
  }

  function asRecord(value) {
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : null;
  }

  /*
   * Older analysis responses do not contain server-built summary_context.
   * This fallback preserves a graceful UI failure path during a staggered
   * frontend/backend rollout. New responses always use the server context,
   * which includes precise channel and subscriber-coverage facts.
   */
  function buildFallbackSummaryContext(analysis) {
    const source = asRecord(analysis);
    const virality = asRecord(source?.virality_score);
    const confidence = asRecord(source?.confidence_score);
    const breakdown = asRecord(virality?.breakdown);
    const videos = Array.isArray(source?.videos) ? source.videos : [];

    const queryCount = Array.isArray(source?.queries) ? source.queries.length : null;
    const videosConsidered = asNonNegativeInteger(source?.videos_considered);
    const videosReturned = asNonNegativeInteger(source?.videos_returned);
    const breakoutCount = asNonNegativeInteger(source?.breakout_count);
    const exceptionalCount = asNonNegativeInteger(
      source?.exceptional_performance_count,
    );
    const uniqueChannelCount = asNonNegativeInteger(
      breakdown?.unique_channel_count,
    );
    const medianViewsPerDay = asNonNegativeNumber(
      breakdown?.median_views_per_day,
    );
    const viralityScore = asNonNegativeNumber(virality?.score);
    const confidenceScore = asNonNegativeNumber(confidence?.score);

    if (
      queryCount === null ||
      videosConsidered === null ||
      videosReturned === null ||
      breakoutCount === null ||
      exceptionalCount === null ||
      uniqueChannelCount === null ||
      medianViewsPerDay === null ||
      viralityScore === null ||
      confidenceScore === null
    ) {
      return null;
    }

    const returnedVideos = videos.slice(0, videosReturned);
    const videosWithSubscriberData = returnedVideos.filter(
      (video) => video && video.subscribers !== null && video.subscribers !== undefined,
    ).length;
    const breakoutChannels = new Set(
      returnedVideos
        .filter((video) => video?.performance === "breakout")
        .map((video) => normalizeText(video.channel_name))
        .filter(Boolean),
    );

    return {
      query_count: queryCount,
      videos_considered: videosConsidered,
      videos_returned: videosReturned,
      videos_with_subscriber_data: videosWithSubscriberData,
      breakout_count: breakoutCount,
      breakout_channel_count: breakoutChannels.size,
      exceptional_count: exceptionalCount,
      unique_channel_count: uniqueChannelCount,
      virality_score: viralityScore,
      confidence_score: confidenceScore,
      median_views_per_day: medianViewsPerDay,
    };
  }

  function buildAnalysisSummaryRequest(analysis) {
    const source = asRecord(analysis);
    const niche = normalizeText(source?.niche);

    if (!niche) {
      return null;
    }

    const summaryContext =
      asRecord(source?.summary_context) || buildFallbackSummaryContext(source);

    if (!summaryContext) {
      return null;
    }

    return {
      niche,
      summary_context: summaryContext,
    };
  }

  function normalizeSignalLabel(value) {
    const key = normalizeText(value).toLowerCase().replace(/[\s-]+/g, "_");

    return Object.prototype.hasOwnProperty.call(NEW_CREATOR_SIGNAL_LABELS, key)
      ? key
      : null;
  }

  function normalizeObservations(value) {
    if (!Array.isArray(value)) {
      return null;
    }

    const observations = value
      .map(normalizeText)
      .filter((observation) => observation.length > 0 && observation.length <= 420);

    return observations.length >= 3 && observations.length <= 5 ? observations : null;
  }

  /*
   * Parse only a response tied to the active niche. A malformed or stale
   * response becomes null, allowing the dashboard to keep its safe fallback.
   */
  function getUsableAnalysisSummary(requestedNiche, payload) {
    const requestedKey = comparisonKey(requestedNiche);
    const source = asRecord(payload);

    if (!requestedKey || !source || comparisonKey(source.niche) !== requestedKey) {
      return null;
    }

    const signal = asRecord(source.new_creator_signal);
    const signalLabel = normalizeSignalLabel(signal?.label);
    const signalRationale = normalizeText(signal?.rationale);

    if (!signalLabel || !signalRationale || signalRationale.length > 420) {
      return null;
    }

    return {
      observations: source.observations === null ? null : normalizeObservations(source.observations),
      newCreatorSignal: {
        label: signalLabel,
        labelText: NEW_CREATOR_SIGNAL_LABELS[signalLabel],
        rationale: signalRationale,
      },
    };
  }

  const analysisSummary = Object.freeze({
    NEW_CREATOR_SIGNAL_LABELS,
    buildAnalysisSummaryRequest,
    buildFallbackSummaryContext,
    getUsableAnalysisSummary,
    normalizeText,
  });

  if (typeof module !== "undefined" && module.exports) {
    module.exports = analysisSummary;
  }

  if (globalScope) {
    globalScope.NicheRadarAnalysisSummary = analysisSummary;
  }
})(typeof globalThis === "undefined" ? undefined : globalThis);
