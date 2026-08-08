# -*- coding: utf-8 -*-
"""單元測試 — jcb_scheduler.py Scheduler 類別"""

import os
import sys
import pytest
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jcb_scheduler import Scheduler


class TestScheduler:
    """Scheduler 類別測試"""

    def test_init(self):
        """測試初始化"""
        ts = 1000.0
        sched = Scheduler(ts)
        assert sched.start_timestamp == ts

    def test_get_staggered_time_default(self):
        """測試預設錯開時間（0.5s）"""
        sched = Scheduler(1000.0)
        assert sched.get_staggered_time(0) == 1000.0
        assert sched.get_staggered_time(1) == 1000.5
        assert sched.get_staggered_time(2) == 1001.0
        assert sched.get_staggered_time(3) == 1001.5

    def test_get_staggered_time_custom(self):
        """測試自定義錯開時間"""
        sched = Scheduler(1000.0)
        assert sched.get_staggered_time(0, stagger_seconds=1.0) == 1000.0
        assert sched.get_staggered_time(1, stagger_seconds=1.0) == 1001.0
        assert sched.get_staggered_time(2, stagger_seconds=2.0) == 1004.0

    @pytest.mark.asyncio
    async def test_sleep_until_already_past(self):
        """測試目標時間已過時應立即返回"""
        start = datetime.datetime.now().timestamp() - 10  # 10 秒前
        await Scheduler.sleep_until(start)
        # 應該立即返回，不阻塞

    @pytest.mark.asyncio
    async def test_sleep_until_future(self):
        """測試未來時間應等待到目標時間"""
        start = datetime.datetime.now().timestamp() + 0.5  # 0.5 秒後
        before = datetime.datetime.now().timestamp()
        await Scheduler.sleep_until(start)
        after = datetime.datetime.now().timestamp()
        assert after - before >= 0.4  # 至少等待 0.4 秒
