# -*- coding: utf-8 -*-
"""pytest 共用 fixtures"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_config_content():
    return """mode = 0
testing = False
linetoken = test_token_123
start_time = 09:00:01
max_token = 1
get_token_semaphore = 30
shoot_semaphore = 7
api_key = test_api_key
myname = test_user
txtCreditCardVal = "['123456','78','9012']", "['654321','09','8765']"
txtEasyCardVal = "['1111','2222','3333','4444']", "['5555','6666','7777','8888']"
cardRecorded =
excludeCard =
"""


@pytest.fixture
def sample_config_file(sample_config_content):
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.ini', delete=False, encoding='utf-8'
    ) as f:
        f.write(sample_config_content)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def mismatched_config_file():
    content = """mode = 0
testing = False
linetoken =
start_time = 09:00:01
max_token = 1
get_token_semaphore = 30
shoot_semaphore = 7
api_key =
myname = test_user
txtCreditCardVal = "['123456','78','9012']"
txtEasyCardVal = "['1111','2222','3333','4444']", "['5555','6666','7777','8888']"
cardRecorded =
excludeCard =
"""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.ini', delete=False, encoding='utf-8'
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)
