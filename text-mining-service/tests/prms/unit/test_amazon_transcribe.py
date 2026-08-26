import json
import pytest
from unittest.mock import MagicMock, patch
from app.text_mining.prms_mining.audio_transcriber import AmazonTranscribeTranscriber, UnavailableAudioTranscriber, get_audio_transcriber
from app.text_mining.prms_mining.models import AudioTranscriptionUnavailableError, SourceExtractionError, SourceLimitExceededError


def test_get_audio_transcriber_unset():
    with patch("app.text_mining.prms_mining.audio_transcriber.PRMS_AUDIO_TRANSCRIBER", ""):
        assert isinstance(get_audio_transcriber(), UnavailableAudioTranscriber)


def test_get_audio_transcriber_amazon():
    with patch(
        "app.text_mining.prms_mining.audio_transcriber.PRMS_AUDIO_TRANSCRIBER",
        "amazon_transcribe",
    ):
        with patch("app.text_mining.prms_mining.audio_transcriber.get_transcribe_client") as mock_factory:
            mock_factory.return_value = MagicMock()
            transcriber = get_audio_transcriber()
    assert isinstance(transcriber, AmazonTranscribeTranscriber)


def test_amazon_transcribe_success():
    client = MagicMock()
    client.start_transcription_job.return_value = {}
    client.get_transcription_job.return_value = {
        "TranscriptionJob": {
            "TranscriptionJobStatus": "COMPLETED",
            "Transcript": {"TranscriptFileUri": "https://example.com/transcript.json"},
        }
    }
    payload = {
        "results": {
            "transcripts": [{"transcript": "Farmers adopted the innovation."}],
            "items": [{"end_time": "12.5"}],
        }
    }

    transcriber = AmazonTranscribeTranscriber(transcribe_client=client)
    with (
        patch(
            "app.text_mining.prms_mining.audio_transcriber.urlopen"
        ) as mock_urlopen,
        patch("app.text_mining.prms_mining.audio_transcriber.PRMS_MAX_AUDIO_SECONDS", 600),
        patch("app.text_mining.prms_mining.audio_transcriber.PRMS_TRANSCRIBE_LANGUAGE_CODE", ""),
    ):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        text = transcriber.transcribe(
            None,
            file_name="note.m4a",
            bucket_name="prms-bucket",
            object_key="prms/text-mining/audio/note.m4a",
        )

    assert text == "Farmers adopted the innovation."
    client.start_transcription_job.assert_called_once()
    start_kwargs = client.start_transcription_job.call_args.kwargs
    assert start_kwargs["MediaFormat"] == "m4a"
    assert start_kwargs["IdentifyLanguage"] is True
    assert start_kwargs["Media"]["MediaFileUri"].endswith("note.m4a")
    client.delete_transcription_job.assert_called_once()


def test_amazon_transcribe_requires_s3_location():
    transcriber = AmazonTranscribeTranscriber(transcribe_client=MagicMock())
    with pytest.raises(SourceExtractionError):
        transcriber.transcribe(b"bytes-only", file_name="a.mp3")


def test_amazon_transcribe_job_failed():
    client = MagicMock()
    client.get_transcription_job.return_value = {
        "TranscriptionJob": {
            "TranscriptionJobStatus": "FAILED",
            "FailureReason": "Unsupported media format",
        }
    }
    transcriber = AmazonTranscribeTranscriber(transcribe_client=client)
    with pytest.raises(SourceExtractionError, match="failed"):
        transcriber.transcribe(
            None,
            file_name="clip.mp3",
            bucket_name="b",
            object_key="clip.mp3",
        )


def test_amazon_transcribe_duration_limit():
    client = MagicMock()
    client.get_transcription_job.return_value = {
        "TranscriptionJob": {
            "TranscriptionJobStatus": "COMPLETED",
            "Transcript": {"TranscriptFileUri": "https://example.com/t.json"},
        }
    }
    payload = {
        "results": {
            "transcripts": [{"transcript": "long audio"}],
            "items": [{"end_time": "999.0"}],
        }
    }
    transcriber = AmazonTranscribeTranscriber(transcribe_client=client)
    with (
        patch("app.text_mining.prms_mining.audio_transcriber.urlopen") as mock_urlopen,
        patch("app.text_mining.prms_mining.audio_transcriber.PRMS_MAX_AUDIO_SECONDS", 60),
    ):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with pytest.raises(SourceLimitExceededError):
            transcriber.transcribe(
                None,
                file_name="long.wav",
                bucket_name="b",
                object_key="long.wav",
            )


def test_unavailable_still_fail_closed():
    with pytest.raises(AudioTranscriptionUnavailableError):
        UnavailableAudioTranscriber().transcribe(
            None,
            file_name="a.m4a",
            bucket_name="b",
            object_key="a.m4a",
        )
