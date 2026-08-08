# -*- coding: utf-8 -*-
"""
jcb_notify.py — Line Notify 通知模組
"""

import inspect
import logging
import pprint
import traceback

import requests_async

logger = logging.getLogger(__name__)


class Notifier:
    """Line Notify 通知發送"""

    API_URL = "https://notify-api.line.me/api/notify"

    def __init__(self, token):
        """
        Args:
            token: Line Notify 存取權杖
        """
        self.token = token

    async def send(self, message, pic_path=None):
        """發送 Line Notify 通知

        Args:
            message: 通知文字
            pic_path: 可選的圖片檔案路徑
        Returns:
            HTTP 狀態碼，失敗時回傳 None
        """
        if not self.token:
            logger.info('未設定 Line Token，略過通知')
            return None

        files = {'imageFile': open(pic_path, 'rb')} if pic_path else None

        try:
            r = await requests_async.post(
                self.API_URL,
                headers={"Authorization": "Bearer " + self.token},
                params={'message': message},
                files=files,
                verify=False,
                timeout=5
            )
            return r.status_code
        except Exception as e:
            logger.info(f'{inspect.stack()[0][3]}')
            logger.info(f'{pprint.pformat(e)}')
            logger.info(f'{traceback.format_exc()}')
            return None
