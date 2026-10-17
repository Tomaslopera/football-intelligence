"""Frame-number conversion and source alignment."""


def atd_to_video_frame(frame_id: int) -> int:
    """Convert one-based ATD frame ID to zero-based video frame."""
    if frame_id < 1:
        raise ValueError("ATD frame IDs must start at 1")

    return frame_id - 1


def video_to_atd_frame(frame: int) -> int:
    """Convert zero-based video frame to one-based ATD ID."""
    if frame < 0:
        raise ValueError("Video frame cannot be negative")

    return frame + 1


def timestamp_to_frame(seconds: float, fps: float) -> int:
    """Convert elapsed seconds to a video-frame index."""
    if not 0 <= seconds < float("inf"):
        raise ValueError("Timestamp must be finite and non-negative")

    if not 0 < fps < float("inf"):
        raise ValueError("FPS must be finite and positive")

    return round(seconds * fps)


def validate_atd_frame_sequence(
    frame_ids: list[int],
    expected_frames: int,
) -> None:
    """Validate the full ordered ATD frame sequence."""
    if expected_frames <= 0:
        raise ValueError("Expected frame count must be positive")

    if len(frame_ids) != expected_frames:
        raise ValueError(
            f"Expected {expected_frames} frames, received {len(frame_ids)}"
        )

    for expected_id, actual_id in enumerate(frame_ids, start=1):
        if actual_id != expected_id:
            raise ValueError(
                f"Frame alignment error: expected {expected_id}, got {actual_id}"
            )
