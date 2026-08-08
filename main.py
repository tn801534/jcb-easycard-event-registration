# -*- coding: utf-8 -*-
"""
main.py — JCB 悠遊卡登錄程式入口
PC Python 版本，支援多卡批次登錄與 Line Notify 通知
"""

import datetime
import logging
import os
import sys
import traceback

import asyncio
from asyncio_read_write_lock import FifoLock, Write

from jcb_config import Config
from jcb_core import JCBAPI
from jcb_scheduler import Scheduler
from jcb_notify import Notifier
from jcb_recaptcha import CaptchaSolver

# ===== 日誌設定 =====
format_str = '%(asctime)s.%(msecs)03d %(levelname)s %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'
log_file = os.path.splitext(os.path.basename(__file__))[0] + '.log'

logging.basicConfig(
    level=logging.INFO,
    format=format_str,
    datefmt=date_format,
    handlers=[
        logging.FileHandler(log_file, 'a', 'utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


class JCBApp:
    """JCB 悠遊卡登錄應用程式主類別"""

    def __init__(self, config_path='jcb.ini'):
        self.config = Config(config_path)

        # 初始化各模組
        self.api = JCBAPI(mode=self.config.mode, testing=self.config.testing)
        self.scheduler = Scheduler(self.config.get_start_timestamp())
        self.notifier = Notifier(self.config.linetoken)
        self.captcha = CaptchaSolver(
            api_key=self.config.api_key,
            max_token=self.config.max_token,
            get_token_semaphore=self.config.get_token_semaphore,
        )

        # 執行緒安全鎖
        self.lock = FifoLock()
        self.captcha.set_lock(self.lock)

        # 卡片列表
        self.credit_cards = self.config.txtCreditCardVal
        self.easy_cards = self.config.txtEasyCardVal

        # 開始時間
        self.start_timestamp = self.config.get_start_timestamp()

        logger.info(
            f'開始時間: {datetime.datetime.fromtimestamp(round(self.start_timestamp, 3)).strftime("%H:%M:%S.%f")[:-3]}'
        )
        logger.info(f'卡片數量: {len(self.credit_cards)}')

    async def _main_loop(self, shoot_semaphore):
        """主執行迴圈 — 對應原 drawPrize() 邏輯

        1. 等待開始時間
        2. 通知 captcha 收集器開始收集
        3. 逐卡處理（錯開 0.5s）
        """
        # 等待開始時間
        await self.scheduler.sleep_until(self.start_timestamp)
        logger.info(f'開始時間到 {datetime.datetime.now().strftime("%H:%M:%S")}')

        # 通知 captcha 收集器開始收集 token
        self.captcha.get_captchaKey_flag = True

        # 逐張卡片處理
        for i in range(len(self.credit_cards)):
            credit_card = self.credit_cards[i]
            easy_card = self.easy_cards[i]

            # 檢查是否已登錄
            if self.config.is_card_recorded(easy_card[3]):
                logger.info(
                    f'{datetime.datetime.now().strftime("%H:%M:%S")} '
                    f'卡片 {easy_card} 已被登錄，跳過'
                )
                continue

            # 等待錯開時間
            stagger_time = self.scheduler.get_staggered_time(i)
            await self.scheduler.sleep_until(stagger_time)

            # 等待可用 captcha token
            captcha_key = None
            while captcha_key is None:
                # 從 token 池取出
                if self.captcha.token_list:
                    async with Write(self.lock):
                        if self.captcha.token_list:
                            captcha_key = self.captcha.token_list.pop(0)
                if captcha_key is None:
                    await asyncio.sleep(1)

            # 發送 API 請求
            success, message, is_captcha_error = await self.api.send_request(
                semaphore=shoot_semaphore,
                count=i,
                captchaKey=captcha_key,
                txtCreditCardValS=credit_card,
                txtEasyCardValS=easy_card,
                start_timestamp=self.start_timestamp,
            )

            if success:
                # 記錄已登錄
                self.config.record_card(easy_card[3])
                logger.info(f'卡片 {easy_card} 登錄成功: {message}')

                # 發送 Line Notify 通知
                await self.notifier.send(
                    f'【JCB 登錄成功】{self.config.myname}\n'
                    f'信用卡: {credit_card[0]}...{credit_card[2]}\n'
                    f'悠遊卡: {easy_card[0]}...{easy_card[3]}\n'
                    f'結果: {message}'
                )
            elif is_captcha_error:
                logger.warning(f'卡片 {easy_card} 圖形驗證碼錯誤')
            else:
                logger.error(f'卡片 {easy_card} 登錄失敗: {message}')

    async def run(self):
        """主執行流程 — 對應原 create_task() 邏輯

        並行執行:
        1. token_collector: 背景收集 captcha token
        2. main_loop: 主登錄迴圈
        """
        logger.info('JCB 悠遊卡登錄程式啟動')

        # 建立並發控制 semaphore
        shoot_semaphore = asyncio.Semaphore(self.config.shoot_semaphore)
        self.captcha.shoot_semaphore = shoot_semaphore

        # 並行執行 token 收集 + 主登錄迴圈
        await asyncio.gather(
            self.captcha.token_collector(self.start_timestamp),
            self._main_loop(shoot_semaphore),
        )

        # 停止 token 收集
        self.captcha.do_recaptcha = False
        logger.info('JCB 悠遊卡登錄程式執行完畢')


def main():
    """程式入口"""
    try:
        app = JCBApp()
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info('使用者中斷程式')
    except Exception as e:
        logger.error(f'程式執行錯誤: {e}')
        logger.error(traceback.format_exc())
        os.system("pause")


if __name__ == '__main__':
    main()
