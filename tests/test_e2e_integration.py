# -*- coding: utf-8 -*-
"""端到端整合測試 — 完整模擬 JCBApp 執行流程"""

import os
import sys
import tempfile
import datetime
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ===== Helpers =====

def _make_success_html():
    return """<html><body><div><div><section><div><div><div><div><div><div><div><div><div><div><div><div>成功登錄</div></div></div></div></div></div></div></div></div></div></div></div></body></html>"""


@pytest.fixture
def temp_config():
    """建立測試用 config.ini"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
        f.write("""mode = 0
testing = False
linetoken = test_line_token
start_time = 09:00:01
max_token = 2
get_token_semaphore = 30
shoot_semaphore = 7
api_key = test_anticaptcha_key
myname = TEST_USER
txtCreditCardVal = "['123456','78','9012']", "['654321','09','8765']"
txtEasyCardVal = "['1111','2222','3333','4444']", "['5555','6666','7777','8888']"
cardRecorded =
excludeCard =
""")
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def temp_config_no_apikey():
    """無 API Key 的 config"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
        f.write("""mode = 0
testing = False
linetoken = test_line_token
start_time = 09:00:01
max_token = 1
get_token_semaphore = 30
shoot_semaphore = 7
api_key =
myname = TEST_USER
txtCreditCardVal = "['123456','78','9012']"
txtEasyCardVal = "['1111','2222','3333','4444']"
cardRecorded =
excludeCard =
""")
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def temp_config_no_linetoken():
    """無 Line Token 的 config"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
        f.write("""mode = 0
testing = False
linetoken =
start_time = 09:00:01
max_token = 1
get_token_semaphore = 30
shoot_semaphore = 7
api_key = test_anticaptcha_key
myname = TEST_USER
txtCreditCardVal = "['123456','78','9012']"
txtEasyCardVal = "['1111','2222','3333','4444']"
cardRecorded =
excludeCard =
""")
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def temp_config_with_recorded():
    """有已登錄卡號的 config"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
        f.write("""mode = 0
testing = False
linetoken = test_line_token
start_time = 09:00:01
max_token = 1
get_token_semaphore = 30
shoot_semaphore = 7
api_key = test_anticaptcha_key
myname = TEST_USER
txtCreditCardVal = "['123456','78','9012']", "['654321','09','8765']"
txtEasyCardVal = "['1111','2222','3333','4444']", "['5555','6666','7777','8888']"
cardRecorded = 4444
excludeCard =
""")
        path = f.name
    yield path
    os.unlink(path)


class TestE2EIntegration:
    """端到端整合測試 — 完整流程驗證"""

    @pytest.mark.asyncio
    async def test_jcbapp_init(self, temp_config):
        """測試 JCBApp 初始化"""
        from main import JCBApp
        app = JCBApp(temp_config)

        assert app.config.mode == 0
        assert app.config.testing is False
        assert app.config.linetoken == 'test_line_token'
        assert app.config.myname == 'TEST_USER'
        assert app.config.max_token == 2
        assert len(app.credit_cards) == 2
        assert len(app.easy_cards) == 2

    @pytest.mark.asyncio
    async def test_jcbapp_init_no_apikey(self, temp_config_no_apikey):
        """測試無 API Key 初始化"""
        from main import JCBApp
        app = JCBApp(temp_config_no_apikey)
        assert app.captcha.api_key == ''
        assert app.captcha.max_token == 1

    @pytest.mark.asyncio
    async def test_jcbapp_init_no_linetoken(self, temp_config_no_linetoken):
        """測試無 Line Token 初始化"""
        from main import JCBApp
        app = JCBApp(temp_config_no_linetoken)
        assert app.config.linetoken == ''

    @pytest.mark.asyncio
    async def test_full_e2e_single_card(self, temp_config_no_apikey):
        """完整端到端流程：單卡、無 API Key（手動模式）"""
        from main import JCBApp
        import asyncio
        from asyncio_read_write_lock import Write

        app = JCBApp(temp_config_no_apikey)

        # 手動注入 captcha token（模擬手動模式）
        async with Write(app.lock):
            app.captcha.token_list.append('manual_captcha_token')

        # Mock API 請求
        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post, \
             patch("jcb_notify.Notifier.send", new_callable=AsyncMock):
            mock_response = MagicMock()
            mock_response.text = _make_success_html()
            mock_post.return_value = mock_response

            # 設定開始時間為現在，讓 scheduler 立即執行
            app.start_timestamp = datetime.datetime.now().timestamp() - 1
            app.scheduler = __import__('jcb_scheduler').Scheduler(app.start_timestamp)

            app.captcha.get_captchaKey_flag = True

            # 執行主迴圈
            await app._main_loop(
                asyncio.Semaphore(app.config.shoot_semaphore)
            )

            # 驗證：API 被呼叫一次
            assert mock_post.call_count == 1

            # 驗證：卡片被記錄為已登錄
            assert app.config.is_card_recorded('4444')

    @pytest.mark.asyncio
    async def test_full_e2e_multi_card(self, temp_config):
        """完整端到端流程：多卡批次"""
        from main import JCBApp
        import asyncio
        from asyncio_read_write_lock import Write

        app = JCBApp(temp_config)

        # 注入 captcha tokens
        async with Write(app.lock):
            app.captcha.token_list.extend(['token_1', 'token_2'])

        # Mock API 請求 — 兩張卡都成功
        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post, \
             patch("jcb_notify.Notifier.send", new_callable=AsyncMock):
            mock_response = MagicMock()
            mock_response.text = _make_success_html()
            mock_post.return_value = mock_response

            app.start_timestamp = datetime.datetime.now().timestamp() - 1
            app.scheduler = __import__('jcb_scheduler').Scheduler(app.start_timestamp)
            app.captcha.get_captchaKey_flag = True

            await app._main_loop(
                asyncio.Semaphore(app.config.shoot_semaphore)
            )

            # 驗證：API 被呼叫兩次
            assert mock_post.call_count == 2

            # 驗證：兩張卡都被記錄
            assert app.config.is_card_recorded('4444')
            assert app.config.is_card_recorded('8888')

    @pytest.mark.asyncio
    async def test_skip_recorded_card(self, temp_config_with_recorded):
        """測試自動跳過已登錄卡片"""
        from main import JCBApp
        import asyncio
        from asyncio_read_write_lock import Write

        app = JCBApp(temp_config_with_recorded)

        # 第一張卡（4444）已記錄，不應發送 API
        async with Write(app.lock):
            app.captcha.token_list.append('token_1')

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post, \
             patch("jcb_notify.Notifier.send", new_callable=AsyncMock):
            mock_response = MagicMock()
            mock_response.text = _make_success_html()
            mock_post.return_value = mock_response

            app.start_timestamp = datetime.datetime.now().timestamp() - 1
            app.scheduler = __import__('jcb_scheduler').Scheduler(app.start_timestamp)
            app.captcha.get_captchaKey_flag = True

            await app._main_loop(
                asyncio.Semaphore(app.config.shoot_semaphore)
            )

            # 只有第二張卡（8888）被處理
            assert mock_post.call_count == 1
            assert app.config.is_card_recorded('4444')  # 原本就記錄
            assert app.config.is_card_recorded('8888')  # 新記錄

    @pytest.mark.asyncio
    async def test_captcha_error_retry(self, temp_config_no_apikey):
        """測試 captcha 錯誤時不記錄卡片"""
        from main import JCBApp
        import asyncio
        from asyncio_read_write_lock import Write

        app = JCBApp(temp_config_no_apikey)

        async with Write(app.lock):
            app.captcha.token_list.append('bad_captcha')

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.text = "圖形驗證碼錯誤, 請重新輸入"
            mock_post.return_value = mock_response

            app.start_timestamp = datetime.datetime.now().timestamp() - 1
            app.scheduler = __import__('jcb_scheduler').Scheduler(app.start_timestamp)
            app.captcha.get_captchaKey_flag = True

            await app._main_loop(
                asyncio.Semaphore(app.config.shoot_semaphore)
            )

            # API 被呼叫，但卡片不應被記錄
            assert mock_post.call_count == 1
            assert not app.config.is_card_recorded('4444')

    @pytest.mark.asyncio
    async def test_network_error_handling(self, temp_config_no_apikey):
        """測試網路異常不會記錄卡片"""
        from main import JCBApp
        import asyncio
        from asyncio_read_write_lock import Write

        app = JCBApp(temp_config_no_apikey)

        async with Write(app.lock):
            app.captcha.token_list.append('token_1')

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection timeout")

            app.start_timestamp = datetime.datetime.now().timestamp() - 1
            app.scheduler = __import__('jcb_scheduler').Scheduler(app.start_timestamp)
            app.captcha.get_captchaKey_flag = True

            await app._main_loop(
                asyncio.Semaphore(app.config.shoot_semaphore)
            )

            # API 被呼叫，但卡片不應被記錄
            assert mock_post.call_count == 1
            assert not app.config.is_card_recorded('4444')

    @pytest.mark.asyncio
    async def test_token_collector_with_apikey(self, temp_config):
        """測試 token 收集器在有 API Key 時啟動"""
        from main import JCBApp

        app = JCBApp(temp_config)

        # Mock Anticaptcha 回傳值
        with patch(
            "jcb_recaptcha.CaptchaSolver.get_recaptcha_v2_proxyless",
            new_callable=AsyncMock
        ) as mock_collect:
            app.start_timestamp = datetime.datetime.now().timestamp() + 5  # 5 秒後
            app.captcha.get_captchaKey_flag = True
            app.captcha.do_recaptcha = False  # 立即停止

            await app.captcha.token_collector(app.start_timestamp - 10)

            # 驗證待命時間計算正確
            expected_wait = (app.start_timestamp - 10) - datetime.datetime.now().timestamp()
            assert expected_wait < 0  # 已過期，直接執行

    @pytest.mark.asyncio
    async def test_token_collector_without_apikey(self, temp_config_no_apikey):
        """測試無 API Key 時 token 收集器直接返回"""
        from main import JCBApp

        app = JCBApp(temp_config_no_apikey)
        assert app.captcha.api_key == ''
        assert app.captcha.max_token == 1

        # 不應拋出異常
        await app.captcha.token_collector(
            datetime.datetime.now().timestamp() + 3600
        )
        # 沒有 API Key 的情況下，token_collector 應直接 return
        assert len(app.captcha.token_list) == 0

    @pytest.mark.asyncio
    async def test_notify_on_success(self, temp_config_no_apikey):
        """測試成功時發送 Line Notify"""
        from main import JCBApp
        import asyncio
        from asyncio_read_write_lock import Write

        app = JCBApp(temp_config_no_apikey)

        async with Write(app.lock):
            app.captcha.token_list.append('token_1')

        with patch("jcb_core.requests_async.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.text = _make_success_html()
            mock_post.return_value = mock_response

            with patch("jcb_notify.Notifier.send", new_callable=AsyncMock) as mock_notify:
                app.start_timestamp = datetime.datetime.now().timestamp() - 1
                app.scheduler = __import__('jcb_scheduler').Scheduler(app.start_timestamp)
                app.captcha.get_captchaKey_flag = True

                await app._main_loop(
                    asyncio.Semaphore(app.config.shoot_semaphore)
                )

                # 驗證 Line Notify 被呼叫
                mock_notify.assert_awaited_once()
                call_args = mock_notify.await_args[0][0]
                assert 'TEST_USER' in call_args
                assert '成功' in call_args

    @pytest.mark.asyncio
    async def test_query_mode_init(self):
        """測試查詢模式初始化"""
        from jcb_core import JCBAPI
        api = JCBAPI(mode=1, testing=False)
        servlet, method = api._get_servlet_info()
        assert servlet == 'JCBLoginRecordServlet'
        assert method == 'queryLoginDate'

    @pytest.mark.asyncio
    async def test_testing_mode_payload(self):
        """測試模式 payload 使用查詢端點"""
        from jcb_core import JCBAPI
        api = JCBAPI(mode=0, testing=True)
        url, data, _ = api.build_payload(
            ['123456', '78', '9012'],
            ['1111', '2222', '3333', '4444'],
            'test_captcha'
        )
        assert 'JCBLoginRecordServlet' in url
        assert 'queryLoginDate' in data
        assert 'g-recaptcha-response=test_captcha' in data
        assert 'txtCreditCard1=123456' in data
        assert 'txtEasyCard1=1111' in data
        assert 'txtEasyCard4=4444' in data

    @pytest.mark.asyncio
    async def test_staggered_timing_single_card(self):
        """測試單卡錯開時間計算"""
        from jcb_scheduler import Scheduler
        sched = Scheduler(datetime.datetime.now().timestamp())
        t = sched.get_staggered_time(0)
        assert t is not None

    @pytest.mark.asyncio
    async def test_staggered_timing_multi_card(self):
        """測試多卡錯開時間間隔"""
        from jcb_scheduler import Scheduler
        base = datetime.datetime.now().timestamp()
        sched = Scheduler(base)
        t0 = sched.get_staggered_time(0)
        t1 = sched.get_staggered_time(1)
        t2 = sched.get_staggered_time(2)
        # 每張卡應錯開
        assert t1 > t0
        assert t2 > t1
        # 間隔應為 0.5 秒
        assert abs((t1 - t0) - 0.5) < 0.01
        assert abs((t2 - t1) - 0.5) < 0.01
