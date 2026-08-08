# -*- coding: utf-8 -*-
"""單元測試 — jcb_core.py JCBAPI 類別"""

import os
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jcb_core import JCBAPI


class TestJCBAPI:
    """JCBAPI 類別測試"""

    def test_init_default_mode(self):
        """測試預設初始化（登錄模式）"""
        api = JCBAPI()
        assert api.mode == 0
        assert api.testing is False

    def test_init_query_mode(self):
        """測試查詢模式初始化"""
        api = JCBAPI(mode=1)
        assert api.mode == 1
        assert api.testing is False

    def test_init_testing_mode(self):
        """測試測試模式初始化"""
        api = JCBAPI(testing=True)
        assert api.testing is True
        assert api.mode == 0

    def test_build_payload_login_mode(self):
        """測試登錄模式 payload 建立"""
        api = JCBAPI(mode=0)
        credit_card = ["123456", "78", "9012"]
        easy_card = ["1111", "2222", "3333", "4444"]
        captcha_key = "test_captcha_token"

        url, data, headers = api.build_payload(credit_card, easy_card, captcha_key)

        assert "JCBLoginServlet" in url
        assert "method=loginAccept" in data
        assert "txtCreditCard1=123456" in data
        assert "txtEasyCard1=1111" in data
        assert "txtEasyCard4=4444" in data
        assert "g-recaptcha-response=test_captcha_token" in data
        assert headers["Host"] == "ezweb.easycard.com.tw"
        assert headers["Content-Type"] == "application/x-www-form-urlencoded"

    def test_build_payload_testing_mode(self):
        """測試模式 payload 應使用查詢端點"""
        api = JCBAPI(testing=True)
        credit_card = ["123456", "78", "9012"]
        easy_card = ["1111", "2222", "3333", "4444"]

        url, data, _ = api.build_payload(credit_card, easy_card, "captcha")
        assert "JCBLoginRecordServlet" in url
        assert "method=queryLoginDate" in data

    @pytest.mark.asyncio
    async def test_parse_response_success(self):
        """測試成功回應解析"""
        api = JCBAPI()
        success_html = """<html><body><div><div><section><div><div><div><div><div><div><div><div><div><div><div><div>登錄結果: 成功</div></div></div></div></div></div></div></div></div></div></div></div></body></html>"""
        success, message, is_captcha = api._parse_response(success_html, "card_info")
        assert success is True
        assert "成功" in str(message)
        assert is_captcha is False

    @pytest.mark.asyncio
    async def test_parse_response_captcha_error(self):
        """測試圖形驗證碼錯誤回應"""
        api = JCBAPI()
        resp = "圖形驗證碼錯誤, 請重新輸入"
        success, message, is_captcha = api._parse_response(resp, "card_info")
        assert success is False
        assert is_captcha is True

    @pytest.mark.asyncio
    async def test_parse_response_generic(self):
        """測試一般回應"""
        api = JCBAPI()
        resp = "Generic response text"
        success, message, is_captcha = api._parse_response(resp, "card_info")
        assert success is True
        assert is_captcha is False

    @pytest.mark.asyncio
    async def test_send_request_success(self):
        """測試發送請求成功流程"""
        api = JCBAPI()
        semaphore = AsyncMock()
        semaphore.__aenter__ = AsyncMock(return_value=None)
        semaphore.__aexit__ = AsyncMock(return_value=None)

        success_html = """<html><body><div><div><section><div><div><div><div><div><div><div><div><div><div><div><div>成功</div></div></div></div></div></div></div></div></div></div></div></div></body></html>"""

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.text = success_html
            mock_post.return_value = mock_response

            success, message, is_captcha = await api.send_request(
                semaphore=semaphore,
                count=0,
                captchaKey="test_token",
                txtCreditCardValS=["123456", "78", "9012"],
                txtEasyCardValS=["1111", "2222", "3333", "4444"],
                start_timestamp=1000.0,
            )

            assert success is True
            assert is_captcha is False
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_request_network_error(self):
        """測試網路異常處理"""
        api = JCBAPI()
        semaphore = AsyncMock()
        semaphore.__aenter__ = AsyncMock(return_value=None)
        semaphore.__aexit__ = AsyncMock(return_value=None)

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection refused")

            success, message, is_captcha = await api.send_request(
                semaphore=semaphore,
                count=0,
                captchaKey="test_token",
                txtCreditCardValS=["123456", "78", "9012"],
                txtEasyCardValS=["1111", "2222", "3333", "4444"],
                start_timestamp=1000.0,
            )

            assert success is False
            assert "Connection refused" in str(message)
