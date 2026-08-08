# -*- coding: utf-8 -*-
"""整合測試 — 完整登錄流程模擬"""

import os
import sys
import pytest
import datetime
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegration:
    """整合測試：模擬完整登錄流程"""

    @pytest.mark.asyncio
    async def test_full_login_flow_single_card(self):
        """測試單卡完整登錄流程"""
        from jcb_core import JCBAPI
        from jcb_scheduler import Scheduler
        from jcb_recaptcha import CaptchaSolver

        api = JCBAPI()
        semaphore = AsyncMock()
        semaphore.__aenter__ = AsyncMock(return_value=None)
        semaphore.__aexit__ = AsyncMock(return_value=None)

        success_html = """<html><body><div><div><section><div><div><div><div><div><div><div><div><div><div><div><div>成功登錄</div></div></div></div></div></div></div></div></div></div></div></div></body></html>"""

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.text = success_html
            mock_post.return_value = mock_response

            success, message, is_captcha = await api.send_request(
                semaphore=semaphore,
                count=0,
                captchaKey="test_captcha",
                txtCreditCardValS=["123456", "78", "9012"],
                txtEasyCardValS=["1111", "2222", "3333", "4444"],
                start_timestamp=datetime.datetime.now().timestamp(),
            )

            assert success is True
            assert is_captcha is False
            assert "成功" in str(message)

    @pytest.mark.asyncio
    async def test_captcha_error_flow(self):
        """測試圖形驗證碼錯誤流程"""
        from jcb_core import JCBAPI

        api = JCBAPI()
        semaphore = AsyncMock()
        semaphore.__aenter__ = AsyncMock(return_value=None)
        semaphore.__aexit__ = AsyncMock(return_value=None)

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.text = "圖形驗證碼錯誤, 請重新輸入"
            mock_post.return_value = mock_response

            success, message, is_captcha = await api.send_request(
                semaphore=semaphore,
                count=0,
                captchaKey="bad_captcha",
                txtCreditCardValS=["123456", "78", "9012"],
                txtEasyCardValS=["1111", "2222", "3333", "4444"],
                start_timestamp=datetime.datetime.now().timestamp(),
            )

            assert success is False
            assert is_captcha is True

    @pytest.mark.asyncio
    async def test_network_error_flow(self):
        """測試網路異常流程"""
        from jcb_core import JCBAPI

        api = JCBAPI()
        semaphore = AsyncMock()
        semaphore.__aenter__ = AsyncMock(return_value=None)
        semaphore.__aexit__ = AsyncMock(return_value=None)

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection timeout")

            success, message, is_captcha = await api.send_request(
                semaphore=semaphore,
                count=0,
                captchaKey="test_captcha",
                txtCreditCardValS=["123456", "78", "9012"],
                txtEasyCardValS=["1111", "2222", "3333", "4444"],
                start_timestamp=datetime.datetime.now().timestamp(),
            )

            assert success is False
            assert is_captcha is False
            assert "Connection timeout" in str(message)

    @pytest.mark.asyncio
    async def test_multi_card_flow(self):
        """測試多卡批次登錄流程"""
        from jcb_core import JCBAPI

        api = JCBAPI()
        cards = [
            (["123456", "78", "9012"], ["1111", "2222", "3333", "4444"]),
            (["654321", "09", "8765"], ["5555", "6666", "7777", "8888"]),
        ]

        semaphore = AsyncMock()
        semaphore.__aenter__ = AsyncMock(return_value=None)
        semaphore.__aexit__ = AsyncMock(return_value=None)

        success_html = """<html><body><div><div><section><div><div><div><div><div><div><div><div><div><div><div><div>成功</div></div></div></div></div></div></div></div></div></div></div></div></body></html>"""

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.text = success_html
            mock_post.return_value = mock_response

            for i, (credit, easy) in enumerate(cards):
                success, message, is_captcha = await api.send_request(
                    semaphore=semaphore,
                    count=i,
                    captchaKey=f"captcha_{i}",
                    txtCreditCardValS=credit,
                    txtEasyCardValS=easy,
                    start_timestamp=datetime.datetime.now().timestamp() + i * 0.5,
                )
                assert success is True
                assert is_captcha is False

            assert mock_post.call_count == 2
