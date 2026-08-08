# -*- coding: utf-8 -*-
"""單元測試 — jcb_notify.py Notifier 類別"""

import os
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jcb_notify import Notifier


class TestNotifier:
    """Notifier 類別測試"""

    @pytest.mark.asyncio
    async def test_send_with_token(self):
        """測試有 token 時發送通知"""
        notifier = Notifier("test_token_123")
        with patch("jcb_notify.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = await notifier.send("測試訊息")
            assert result == 200
            mock_post.assert_called_once()
            # 驗證 header 有帶 token
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test_token_123"
            assert call_kwargs["params"]["message"] == "測試訊息"

    @pytest.mark.asyncio
    async def test_send_without_token(self):
        """測試無 token 時不發送"""
        notifier = Notifier("")
        result = await notifier.send("測試訊息")
        assert result is None

    @pytest.mark.asyncio
    async def test_send_network_error(self):
        """測試網路異常時不拋出例外"""
        notifier = Notifier("test_token")
        with patch("jcb_notify.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Timeout")
            result = await notifier.send("測試訊息")
            assert result is None
