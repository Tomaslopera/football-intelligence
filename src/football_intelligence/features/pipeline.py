"""Build reproducible feature datasets from canonical tracking frames."""

from collections.abc import Iterable
from pathlib import Path

from football_intelligence.features.storage import (
    write_feature_parquet,
)
from football_intelligence.features.temporal import (
    extract_temporal_features,
)
from football_intelligence.tracking.models import (
    MatchMetadata,
    RecordingSource,
    TrackingFrame,
)


def build_feature_dataset(
    frames: Iterable[TrackingFrame],
    metadata: MatchMetadata,
    source: RecordingSource,
    output_path: Path,
) -> Path:
    """Extract and persist causal features for one match and source.

    This operation is intended for batch processing, not API requests.
    """

    def validated_frames() -> Iterable[TrackingFrame]:
        for frame in frames:
            if frame.source != source:
                raise ValueError(
                    "Tracking frame source does not match "
                    "the requested feature dataset source"
                )

            yield frame

    features = extract_temporal_features(
        validated_frames(),
        metadata,
    )

    return write_feature_parquet(
        features,
        source,
        output_path,
    )
