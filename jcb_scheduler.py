# -*- coding: utf-8 -*-
"""
jcb_scheduler.py — 排程與重試邏輯
精確時間睡眠、錯開請求時間、重試機制
"""

import datetime
import logging
import time

logger = logging.getLogger(__name__)


class Scheduler:
    """排程器：管理開始時間與錯開請求間隔"""

    def __init__(self, start_timestamp):
        """
        Args:
            start_timestamp: 開始時間戳記（秒）
        """
        self.start_timestamp = start_timestamp

    def get_staggered_time(self, card_index, stagger_seconds=0.5):
        """計算第 card_index 張卡片的實際執行時間

        Args:
            card_index: 卡片序號（從 0 開始）
            stagger_seconds: 每張卡片的錯開秒數（預設 0.5）
        Returns:
            時間戳記（秒）
        """
        return self.start_timestamp + card_index * stagger_seconds

    @staticmethod
    async def sleep_until(target_timestamp):
        """精確睡眠到指定時間戳

        Args:
            target_timestamp: 目標時間戳（秒）
        """
        while True:
            now = datetime.datetime.now().timestamp()
            diff = target_timestamp - now
            if diff <= 0:
                break
            if diff > 1:
                await asyncio.sleep(diff * 0.5)
            else:
                time.sleep(0.001)

    @staticmethod
    def get_next_hour_timestamp():
        """取得下一個整點的時間戳記"""
        now = datetime.datetime.now()
        return (now.replace(minute=0, second=0, microsecond=0)
                + datetime.timedelta(hours=1)).timestamp()

    @staticmethod
    def now_str():
        """回傳目前時間字串 HH:MM:SS"""
        return datetime.datetime.now().strftime('%H:%M:%S')


# 需要在 module 層級 import asyncio
import asyncio
