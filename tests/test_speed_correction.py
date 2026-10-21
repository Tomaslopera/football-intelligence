"""Evidence-based unit overrides and reproducible derived-data correction."""

import json

import pytest
from epts_fixture import write_epts_pair

from football_intelligence.features.storage import read_feature_parquet
from football_intelligence.tracking.audit import audit_metrica
from football_intelligence.tracking.correction import rebuild_speed_units
from football_intelligence.tracking.lineage import file_sha256
from football_intelligence.tracking.metrica import (
    load_metrica_epts,
    read_metrica_metadata,
)
from football_intelligence.tracking.models import RecordingSource

EVIDENCE = "Synthetic provider documentation: this fixture's speed numbers are m/s"


def test_bar_ath_tactical_source_contract_is_applied_by_audit(tmp_path):
    xml, txt = write_epts_pair(tmp_path, speed_unit="kph", speeds=(10, 20))
    result = audit_metrica(
        xml,
        txt,
        tmp_path / "known",
        match_id="BAR-ATH",
        source=RecordingSource.TACTICAL,
        limit=None,
    )
    assert result["lineage"]["speed_units"]["source"] == "kph"
    assert result["lineage"]["speed_units"]["effective_source"] == "m/s"
    assert "DATA.md" in result["lineage"]["speed_units"]["override_evidence"]
    assert result["feature_summary"]["home_mean_speed_mps"]["max"] == 20
    generic = audit_metrica(
        xml,
        txt,
        tmp_path / "generic",
        match_id="OTHER",
        source=RecordingSource.TACTICAL,
        limit=None,
    )
    assert generic["feature_summary"]["home_mean_speed_mps"]["max"] == pytest.approx(
        20 / 3.6
    )


def test_documented_override_is_explicit_and_does_not_change_generic_kph(tmp_path):
    xml, txt = write_epts_pair(tmp_path, speed_unit="kph", speeds=(36, 72))
    original = (xml.read_bytes(), txt.read_bytes())
    assert load_metrica_epts(xml, txt)["1_s"].iloc[0] == pytest.approx(10)
    overridden = load_metrica_epts(
        xml, txt, speed_unit_override="m/s", speed_unit_evidence=EVIDENCE
    )
    assert overridden["1_s"].iloc[0] == 36
    metadata = read_metrica_metadata(
        xml,
        match_id="TEST",
        total_frames=3,
        speed_unit_override="m/s",
        speed_unit_evidence=EVIDENCE,
    )
    assert metadata.source_speed_unit == "kph"
    assert metadata.effective_speed_unit == "m/s"
    assert metadata.speed_unit_evidence == EVIDENCE
    assert (xml.read_bytes(), txt.read_bytes()) == original


@pytest.mark.parametrize(
    ("override", "evidence"),
    [("m/s", None), ("m/s", " "), ("mph", EVIDENCE), (None, EVIDENCE)],
)
def test_invalid_overrides_rejected(tmp_path, override, evidence):
    xml, txt = write_epts_pair(tmp_path)
    with pytest.raises(ValueError, match="override"):
        load_metrica_epts(
            xml, txt, speed_unit_override=override, speed_unit_evidence=evidence
        )


def test_rebuild_equivalent_to_corrected_source_adapter(tmp_path):
    xml, txt = write_epts_pair(tmp_path, speed_unit="kph", speeds=(10, 20))
    prior, corrected, direct = (
        tmp_path / name for name in ("prior", "corrected", "direct")
    )
    audit_metrica(
        xml,
        txt,
        prior,
        match_id="SYNTHETIC",
        source=RecordingSource.TACTICAL,
        limit=None,
    )
    prior_hash = file_sha256(prior / "audit.json")
    result = rebuild_speed_units(
        prior, corrected, effective_unit="m/s", evidence=EVIDENCE
    )
    audit_metrica(
        xml,
        txt,
        direct,
        match_id="SYNTHETIC",
        source=RecordingSource.TACTICAL,
        limit=None,
        speed_unit_override="m/s",
        speed_unit_evidence=EVIDENCE,
    )
    rows = read_feature_parquet(corrected / "features/features-v1.0.parquet")
    assert rows == read_feature_parquet(direct / "features/features-v1.0.parquet")
    assert rows[0].home_mean_speed_mps == 20
    assert rows[0].away_mean_speed_mps == 10
    assert result["lineage"]["correction_factor"] == 3.6
    assert result["lineage"]["speed_units"]["source"] == "kph"
    assert result["lineage"]["speed_units"]["effective_source"] == "m/s"
    assert result["lineage"]["upstream_audit_sha256"] == prior_hash
    assert file_sha256(prior / "audit.json") == prior_hash
    assert json.loads((corrected / "quality-review.json").read_text())[
        "feature_consistency_passed"
    ]
    with pytest.raises(ValueError, match="already effective"):
        rebuild_speed_units(
            corrected, tmp_path / "twice", effective_unit="m/s", evidence=EVIDENCE
        )
    with pytest.raises(FileExistsError):
        rebuild_speed_units(prior, corrected, effective_unit="m/s", evidence=EVIDENCE)
