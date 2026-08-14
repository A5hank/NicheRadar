"""Build the final combined NicheRadar result set."""

from dataclasses import dataclass

from nicheradar.analytics import PerformanceLabel
from nicheradar.ranking import (
    ScoredVideo,
    rank_scored_videos,
)

DEFAULT_RESULT_LIMIT = 50


@dataclass(frozen=True, slots=True)
class NicheResults:
    """Final selected and ranked NicheRadar videos."""

    considered_count: int
    videos: tuple[ScoredVideo, ...]

    @property
    def all_videos(self) -> tuple[ScoredVideo, ...]:
        """Return the final selected videos."""

        return self.videos

    @property
    def total_count(self) -> int:
        """Return the number of selected videos."""

        return len(self.videos)

    @property
    def breakout_count(self) -> int:
        """Return the number of selected breakout videos."""

        return sum(
            video.metrics.performance_label is PerformanceLabel.BREAKOUT for video in self.videos
        )

    @property
    def exceptional_performance_count(self) -> int:
        """Return selected exceptional performances."""

        return sum(
            video.metrics.performance_label is PerformanceLabel.EXCEPTIONAL_PERFORMANCE
            for video in self.videos
        )


def video_selection_sort_key(
    video: ScoredVideo,
) -> tuple[int, float, str]:
    """Build the key used to select videos by total views."""

    return (
        -video.views,
        -video.metrics.views_per_day,
        video.video_id,
    )


def deduplicate_scored_videos(
    videos: list[ScoredVideo],
) -> list[ScoredVideo]:
    """Remove duplicate video IDs, keeping the highest-view copy."""

    videos_by_views = sorted(
        videos,
        key=video_selection_sort_key,
    )

    unique_videos: list[ScoredVideo] = []
    seen_video_ids: set[str] = set()

    for video in videos_by_views:
        if video.video_id in seen_video_ids:
            continue

        unique_videos.append(video)
        seen_video_ids.add(video.video_id)

    return unique_videos


def build_niche_results(
    videos: list[ScoredVideo],
    *,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> NicheResults:
    """Select by total views, then rank by views per day."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    unique_videos = deduplicate_scored_videos(videos)

    selected_by_views = sorted(
        unique_videos,
        key=video_selection_sort_key,
    )[:limit]

    ranked_for_display = rank_scored_videos(selected_by_views)

    return NicheResults(
        considered_count=len(unique_videos),
        videos=tuple(ranked_for_display),
    )
