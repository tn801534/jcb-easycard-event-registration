# -*- coding: utf-8 -*-
"""
jcb_recaptcha.py — reCAPTCHA 處理模組
支援 Anticaptcha 自動模式與手動模式
"""

import datetime
import logging
import pprint
import traceback

import asyncio
import requests_async

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """reCAPTCHA 解決器

    管理 captcha token 池，自動從 Anticaptcha 取得 token
    """

    # reCAPTCHA 網站金鑰（固定值）
    SITE_KEY = '6LdyfSsUAAAAABlOOqXqgQ9qF5UD5_3Wq4EHqC2q'
    PAGE_URL = 'https://ezweb.easycard.com.tw/Event01/JCBMainServlet'

    def __init__(self, api_key, max_token=1, get_token_semaphore=30):
        """
        Args:
            api_key: Anticaptcha API Key（空字串表示不使用自動模式）
            max_token: 最大 token 數量
            get_token_semaphore: 同時取得 token 的並發數
        """
        self.api_key = api_key
        self.max_token = max_token
        self.get_token_semaphore = get_token_semaphore

        # Token 池（執行緒安全）
        self.token_list = []
        self.lock = None  # 由外部注入 FifoLock

        # 控制旗標
        self.do_recaptcha = True
        self.get_captchaKey_flag = False

    def set_lock(self, lock):
        """設定執行緒安全鎖（由外部注入）"""
        self.lock = lock

    async def get_recaptcha_v2_proxyless(self, count, semaphore):
        """從 Anticaptcha 取得一個 reCAPTCHA token

        Args:
            count: 請求序號
            semaphore: asyncio.Semaphore
        """
        async with semaphore:
            try:
                from recaptchav2proxyless import recaptchaV2Proxyless
                result = recaptchaV2Proxyless(
                    self.api_key,
                    self.PAGE_URL,
                    self.SITE_KEY,
                    # action: 'verify'  # v3 專用，v2 不需要
                )
                logger.info(
                    f'Anticaptcha 結果 count:{count} '
                    f'time:{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}'
                )

                if self.lock:
                    # 使用 FifoLock 確保執行緒安全
                    from asyncio_read_write_lock import Write
                    async with Write(self.lock):
                        self.token_list.append(result)
                else:
                    self.token_list.append(result)

            except Exception as e:
                logger.info(f'Anticaptcha 錯誤 count:{count}')
                logger.info(f'{pprint.pformat(e)}')
                logger.info(f'{traceback.format_exc()}')

    async def token_collector(self, start_timestamp):
        """背景收集 reCAPTCHA token

        在開始時間前 10 秒啟動，持續收集 token 直到 do_recaptcha=False

        Args:
            start_timestamp: 開始時間戳記
        """
        if not self.api_key:
            logger.info('未設定 Anticaptcha API Key，略過自動 token 收集')
            return

        # 等待到開始時間前 10 秒
        logger.info(
            f'等待 token 收集開始時間: '
            f'{datetime.datetime.fromtimestamp(round(start_timestamp - 10, 3)).strftime("%H:%M:%S.%f")[:-3]}'
        )
        await self._sleep_until(start_timestamp - 10)

        semaphore = asyncio.Semaphore(self.get_token_semaphore)
        count = 0

        while self.do_recaptcha:
            if self.get_captchaKey_flag:
                now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                logger.info(f'開始收集 token {now_str}')
                for _ in range(self.max_token):
                    asyncio.create_task(
                        self.get_recaptcha_v2_proxyless(count, semaphore)
                    )
                    count += 1
                await asyncio.sleep(15)
            else:
                pass  # 等待 flag 被開啟
            await asyncio.sleep(1)

        logger.info(f'Token 收集結束 {datetime.datetime.now().strftime("%H:%M:%S")}')

    def pop_token(self):
        """從 token 池取出一個 token（非同步安全）

        Returns:
            token 字串，若無可用 token 則回傳 None
        """
        if self.token_list:
            return self.token_list.pop(0)
        return None

    def token_count(self):
        """回傳目前 token 池中的數量"""
        return len(self.token_list)

    @staticmethod
    async def _sleep_until(target_timestamp):
        """精確睡眠到指定時間戳"""
        import time
        while True:
            now = datetime.datetime.now().timestamp()
            diff = target_timestamp - now
            if diff <= 0:
                break
            if diff > 1:
                await asyncio.sleep(diff * 0.5)
            else:
                time.sleep(0.001)
