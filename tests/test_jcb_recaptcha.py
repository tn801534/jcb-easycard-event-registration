# -*- coding: utf-8 -*-

"""單元測試 — jcb_recaptcha.py CaptchaSolver 類別"""


import os

import sys

import pytest

from unittest.mock import patch, AsyncMock, MagicMock


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jcb_recaptcha import CaptchaSolver


class TestCaptchaSolver:

    """CaptchaSolver 類別測試"""


    def test_init(self):

        """測試初始化"""

        solver = CaptchaSolver(api_key="test_key", max_token=2, get_token_semaphore=5)

        assert solver.api_key == "test_key"

        assert solver.max_token == 2

        assert solver.get_token_semaphore == 5

        assert solver.token_list == []

        assert solver.do_recaptcha is True

        assert solver.get_captchaKey_flag is False

        assert solver.SITE_KEY == "6LdyfSsUAAAAABlOOqXqgQ9qF5UD5_3Wq4EHqC2q"


    def test_init_no_api_key(self):

        """測試無 API Key 初始化"""

        solver = CaptchaSolver(api_key="")

        assert solver.api_key == ""


    def test_token_management(self):

        """測試 token 池管理"""

        solver = CaptchaSolver(api_key="test_key")

        # 初始空池

        assert solver.token_count() == 0

        assert solver.pop_token() is None

        # 加入 token

        solver.token_list.append("token1")

        solver.token_list.append("token2")

        assert solver.token_count() == 2

        # 取出 token（FIFO）

        assert solver.pop_token() == "token1"

        assert solver.token_count() == 1

        assert solver.pop_token() == "token2"

        assert solver.token_count() == 0

        assert solver.pop_token() is None


    def test_set_lock(self):

        """測試注入鎖"""

        solver = CaptchaSolver(api_key="test_key")

        lock = MagicMock()

        solver.set_lock(lock)

        assert solver.lock == lock


    @pytest.mark.asyncio

    async def test_token_collector_no_api_key(self):

        """測試無 API Key 時 token_collector 應立即返回"""

        solver = CaptchaSolver(api_key="")

        await solver.token_collector(1000.0)

        # 應立即返回，不阻塞


    @pytest.mark.asyncio

    async def test_get_recaptcha_v2_proxyless(self):

        """測試 anticaptcha 請求"""

        solver = CaptchaSolver(api_key="test_key", max_token=1)

        semaphore = AsyncMock()

        semaphore.__aenter__ = AsyncMock(return_value=None)

        semaphore.__aexit__ = AsyncMock(return_value=None)


        # Mock the internal import of recaptchav2proxyless
        mock_mod = MagicMock()
        mock_mod.recaptchaV2Proxyless = MagicMock(return_value="captcha_token_123")
        with patch.dict("sys.modules", {"recaptchav2proxyless": mock_mod}):
            await solver.get_recaptcha_v2_proxyless(0, semaphore)
            assert solver.token_list == ["captcha_token_123"]

