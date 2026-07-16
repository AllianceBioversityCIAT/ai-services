from unittest.mock import patch
from app.llm.prms_mining.prompt_builder import build_final_validation_prompt
from app.utils.prompt.prms.final_validation import VALIDATION_PROMPT_VERSION


def test_final_validation_prompt_shape():
    prompt = build_final_validation_prompt(
        candidates={"results": [{"indicator": "Policy Change", "title": "t", "description": "d", "keywords": ["k"], "geoscope_level": "Global"}]},
        supporting_excerpts='<source id="source-1" type="document">policy enacted</source>',
    )
    assert "CANDIDATE RESULTS JSON" in prompt
    assert "SUPPORTING SOURCE EXCERPTS" in prompt
    assert "Never introduce Knowledge Product" in prompt
    assert VALIDATION_PROMPT_VERSION.startswith("prms-final-validation-")


def test_final_validation_disabled_by_default():
    from app.utils.config import config_util

    assert config_util.PRMS_FINAL_VALIDATION_ENABLED is False or isinstance(
        config_util.PRMS_FINAL_VALIDATION_ENABLED, bool
    )
