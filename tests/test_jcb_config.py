# -*- coding: utf-8 -*-
"""單元測試 — jcb_config.py Config 類別"""

import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jcb_config import Config


class TestConfig:
    """Config 類別測試"""

    def test_parse_basic_config(self, sample_config_file):
        """測試基本設定檔解析"""
        config = Config(sample_config_file)
        assert config.mode == 0
        assert config.testing is False
        assert config.linetoken == 'test_token_123'
        assert config.api_key == 'test_api_key'
        assert config.myname == 'test_user'
        assert config.max_token == 1
        assert config.get_token_semaphore == 30
        assert config.shoot_semaphore == 7

    def test_parse_card_values(self, sample_config_file):
        """測試信用卡與悠遊卡值解析"""
        config = Config(sample_config_file)
        assert len(config.txtCreditCardVal) == 2
        assert len(config.txtEasyCardVal) == 2
        # 第一組信用卡
        assert config.txtCreditCardVal[0] == ["123456", "78", "9012"]
        # 第一組悠遊卡
        assert config.txtEasyCardVal[0] == ["1111", "2222", "3333", "4444"]

    def test_parse_start_time(self, sample_config_file):
        """測試開始時間解析"""
        config = Config(sample_config_file)
        assert config.start_hour == 9
        assert config.start_min == 0
        assert config.start_sec == 1

    def test_card_recorded_management(self, sample_config_file):
        """測試已登錄卡號管理"""
        config = Config(sample_config_file)
        # 初始無記錄
        assert config.is_card_recorded("4444") is False
        # 記錄卡號
        config.record_card("4444")
        assert config.is_card_recorded("4444") is True
        # 重複記錄不應新增
        config.record_card("4444")
        assert len(config.cardRecorded) == 1

    def test_mismatched_card_count(self, mismatched_config_file):
        """測試卡片數量不一致時應退出"""
        with pytest.raises(SystemExit):
            Config(mismatched_config_file)

    def test_get_start_timestamp(self, sample_config_file):
        """測試開始時間戳記計算"""
        import datetime
        config = Config(sample_config_file)
        ts = config.get_start_timestamp()
        dt = datetime.datetime.fromtimestamp(ts)
        assert dt.hour == 9
        assert dt.minute == 0
        assert dt.second == 1

    def test_empty_config(self):
        """測試空白設定檔（使用預設值）"""
        content = """mode = 0
testing = False
linetoken =
api_key =
myname =
txtCreditCardVal = "['000000','00','0000']"
txtEasyCardVal = "['0000','0000','0000','0000']"
"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.ini', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            path = f.name
        try:
            config = Config(path)
            assert config.mode == 0
            assert config.max_token == 1  # 預設值
            assert config.linetoken == ''
        finally:
            os.unlink(path)

    def test_exclude_card(self, sample_config_file):
        """測試排除卡號功能"""
        config = Config(sample_config_file)
        assert config.excludeCard == [] or config.excludeCard is None
