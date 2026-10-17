import pytest

from football_intelligence.tracking.alignment import (
    atd_to_video_frame,
    timestamp_to_frame,
    validate_atd_frame_sequence,
    video_to_atd_frame,
)


@pytest.mark.parametrize(
    ("atd_id", "video_frame"),
    [
        (1, 0),
        (11186, 11185),
        (199319, 199318),
    ],
)
def test_atd_video_alignment(atd_id, video_frame):
    assert atd_to_video_frame(atd_id) == video_frame
    assert video_to_atd_frame(video_frame) == atd_id


def test_invalid_atd_frame():
    with pytest.raises(ValueError):
        atd_to_video_frame(0)


def test_timestamp_conversion():
    assert timestamp_to_frame(10.0, 25) == 250


def test_valid_frame_sequence():
    validate_atd_frame_sequence(
        [1, 2, 3, 4],
        expected_frames=4,
    )


def test_missing_frame_is_rejected():
    with pytest.raises(ValueError):
        validate_atd_frame_sequence(
            [1, 2, 4, 5],
            expected_frames=4,
        )
