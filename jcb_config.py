# -*- coding: utf-8 -*-
"""
jcb_config.py — 設定檔讀取模組
支援多組信用卡 + 悠遊卡設定，以及已登錄卡號管理
"""

import os
import sys
import datetime
from configobj import ConfigObj


class Config:
    """封裝 jcb.ini 設定檔存取"""

    def __init__(self, config_path='jcb.ini'):
        # 切換工作目錄到腳本所在目錄
        if os.path.isabs(sys.argv[0]):
            os.chdir(os.path.dirname(sys.argv[0]))

        self.config = ConfigObj(config_path, encoding='UTF8')
        self._parse()

    def _parse(self):
        """解析所有設定值"""
        cfg = self.config

        # 模式: 0=登錄, 1=查詢
        self.mode = int(cfg.get("mode", 0))
        self.testing = cfg.as_bool('testing')

        # Line Notify 通知
        self.linetoken = cfg.get('linetoken', '')

        # Anticaptcha API Key
        self.api_key = cfg.get('api_key', '')

        # 使用者名稱
        self.myname = cfg.get('myname', '')

        # Token 管理
        self.max_token = int(cfg.get("max_token", 1))
        self.get_token_semaphore = int(cfg.get("get_token_semaphore", 30))
        self.shoot_semaphore = int(cfg.get("shoot_semaphore", 7))

        # 多組卡片設定
        self.txtCreditCardVal = cfg.as_list('txtCreditCardVal')
        self.txtEasyCardVal = cfg.as_list('txtEasyCardVal')

        # 已登錄 / 排除卡號
        self.cardRecorded = cfg.as_list("cardRecorded") or []
        self.excludeCard = cfg.as_list("excludeCard") or []

        # 開始時間
        self._parse_start_time(cfg)

        # 驗證卡片數量一致
        self._validate()

    def _parse_start_time(self, cfg):
        """解析開始時間"""
        raw = cfg.get('start_time', '')
        self.start_hour = None
        self.start_min = 0
        self.start_sec = 0

        if raw and raw != "None" and raw != "":
            parts = str(raw).split(':')
            if len(parts) > 0 and parts[0]:
                self.start_hour = int(parts[0])
            if len(parts) > 1 and parts[1]:
                self.start_min = int(parts[1])
            if len(parts) > 2 and parts[2]:
                self.start_sec = int(parts[2])

    def _validate(self):
        """驗證信用卡與悠遊卡數量一致"""
        if len(self.txtCreditCardVal) != len(self.txtEasyCardVal):
            import logging
            logging.getLogger(__name__).error(
                f'信用卡數量({len(self.txtCreditCardVal)}) '
                f'與悠遊卡數量({len(self.txtEasyCardVal)})不一致，請檢查 jcb.ini'
            )
            sys.exit(1)

    def is_card_recorded(self, easycard_last):
        """檢查悠遊卡末碼是否已登錄"""
        return easycard_last in self.cardRecorded

    def record_card(self, easycard_last):
        """記錄已登錄的悠遊卡末碼"""
        if easycard_last not in self.cardRecorded:
            self.cardRecorded.append(easycard_last)
            self.config['cardRecorded'] = self.cardRecorded
            self.config.write()

    def get_start_timestamp(self):
        """計算開始時間戳記"""
        now = datetime.datetime.now()
        if self.start_hour is not None:
            run_date = now.replace(
                hour=self.start_hour % 24,
                minute=self.start_min,
                second=self.start_sec,
                microsecond=0
            )
            return run_date.timestamp()
        else:
            # 預設為下一個整點
            return (now.replace(minute=0, second=0, microsecond=0)
                    + datetime.timedelta(hours=1)).timestamp()
