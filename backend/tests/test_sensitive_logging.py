"""Real link and exception paths must not emit sensitive payload markers."""

import json
import logging
from urllib.parse import quote

import pytest

from app.utils.hyperlinks import unwrap_tracking_url
from app.utils.logging import JsonFormatter


@pytest.mark.parametrize('wrapper', ['proofpoint', 'microsoft', 'barracuda'])
def test_link_unwrap_does_not_log_urls(wrapper, caplog):
    destination = 'https://example.test/private/person@example.test?token=secret-marker#private'
    urls = {
        'proofpoint': f'https://urldefense.com/v3/__{destination}__',
        'microsoft': 'https://safelinks.protection.outlook.com/?url=' + quote(destination, safe=''),
        'barracuda': 'https://linkprotect.cudasvc.com/?a=' + quote(destination, safe=''),
    }
    with caplog.at_level(logging.INFO, logger='app.utils.hyperlinks'):
        assert unwrap_tracking_url(urls[wrapper]) == destination
    assert caplog.records
    assert 'secret-marker' not in caplog.text
    assert 'person@example.test' not in caplog.text
    assert 'https://' not in caplog.text


def test_formatter_drops_exception_message_and_traceback():
    try:
        raise RuntimeError('private@example.test token=secret-marker')
    except RuntimeError:
        import sys
        record = logging.LogRecord('app', logging.ERROR, __file__, 1, 'Operation failed', (), sys.exc_info())
    output = JsonFormatter().format(record)
    assert json.loads(output)['error_type'] == 'RuntimeError'
    assert 'private@example.test' not in output
    assert 'secret-marker' not in output
