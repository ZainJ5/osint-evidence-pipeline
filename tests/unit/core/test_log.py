import json
import logging

from pipeline.core.log import EmailScrubFilter, JsonFormatter, log_event


def _record(msg, **extra):
    record = logging.LogRecord("pipeline", logging.INFO, __file__, 1, msg, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_email_in_message_is_scrubbed():
    record = _record("contact jane.doe@example.com now")
    EmailScrubFilter().filter(record)
    assert "jane.doe@example.com" not in record.getMessage()
    assert "[email]" in record.getMessage()


def test_email_in_structured_fields_is_scrubbed():
    record = _record("stage", fields={"note": "a@b.io", "nested": {"x": "c@d.org"}})
    EmailScrubFilter().filter(record)
    assert "a@b.io" not in json.dumps(record.fields)
    assert "c@d.org" not in json.dumps(record.fields)


def test_json_formatter_emits_one_json_object_with_fields():
    record = _record("stage_done", fields={"run_id": "r1", "stage": "collect"})
    line = JsonFormatter().format(record)
    data = json.loads(line)
    assert data["event"] == "stage_done"
    assert data["run_id"] == "r1"
    assert data["level"] == "INFO"


def test_log_event_never_outputs_email(caplog):
    logger = logging.getLogger("pipeline.test")
    logger.addFilter(EmailScrubFilter())
    with caplog.at_level(logging.INFO, logger="pipeline.test"):
        log_event(logger, "candidate_registered", candidate_id="c1", email="x@y.com")
    assert "x@y.com" not in caplog.text
