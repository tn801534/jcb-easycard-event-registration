# -*- coding: utf-8 -*-
"""
main_android.py — JCB 悠遊卡登錄程式 Android APK 入口
使用 Kivy 提供圖形化介面
"""

import datetime
import logging
import os
import sys
import traceback
import threading
import asyncio

from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout

# Android 路徑處理
if 'ANDROID_ARGUMENT' in os.environ:
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.INTERNET])

    # Android 的設定檔路徑
    app_root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(app_root, 'jcb.ini')
else:
    config_path = 'jcb.ini'

from jcb_config import Config
from jcb_core import JCBAPI
from jcb_scheduler import Scheduler
from jcb_notify import Notifier
from jcb_recaptcha import CaptchaSolver


class JCBLogHandler(logging.Handler):
    """將日誌發送到 Kivy UI 的處理器"""

    def __init__(self, app):
        super().__init__()
        self.app = app

    def emit(self, record):
        msg = self.format(record)
        Clock.schedule_once(lambda dt: self.app.append_log(msg))


class JCBRoot(BoxLayout):
    pass


class JCBApp(App):
    """JCB 悠遊卡登錄程式 Kivy 應用程式"""

    log_text = StringProperty('')
    progress_value = NumericProperty(0)
    status_text = StringProperty('載入設定中...')

    def build(self):
        self.title = 'JCB 悠遊卡登錄'
        self.running = False
        self.loop = None
        self.task = None
        self.root = JCBRoot()
        return self.root

    def on_start(self):
        """App 啟動後載入設定"""
        try:
            self.config = Config(config_path)
            cards = len(self.config.txtCreditCardVal)
            self.root.ids.status_label.text = (
                f'✅ 設定載入成功\n'
                f'📋 卡片數量: {cards} 組\n'
                f'⏰ 開始時間: {datetime.datetime.fromtimestamp(round(self.config.get_start_timestamp(), 3)).strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'🔑 Line Notify: {"已設定" if self.config.linetoken else "未設定"}'
            )
            self.root.ids.start_btn.disabled = False
        except Exception as e:
            self.root.ids.status_label.text = f'❌ 設定載入失敗: {e}'

    def append_log(self, msg):
        """追加日誌到 UI"""
        current = self.root.ids.log_output.text
        lines = current.split('\n')
        # 保留最後 200 行
        if len(lines) > 200:
            current = '\n'.join(lines[-200:])
        self.root.ids.log_output.text = current + msg + '\n'
        # 自動滾動到底部
        self.root.ids.log_output.cursor = (0, len(self.root.ids.log_output.text))

    def start_registration(self):
        """開始登錄流程"""
        if self.running:
            return

        self.running = True
        self.root.ids.start_btn.disabled = True
        self.root.ids.stop_btn.disabled = False
        self.root.ids.progress_bar.value = 0
        self.root.ids.log_output.text = ''

        # 設定日誌
        self._setup_logging()

        # 在背景執行緒中啟動 asyncio 事件迴圈
        threading.Thread(target=self._run_async, daemon=True).start()

    def _setup_logging(self):
        """設定日誌處理器"""
        log_handler = JCBLogHandler(self)
        log_handler.setFormatter(logging.Formatter(
            '%(asctime)s.%(msecs)03d %(levelname)s %(message)s',
            datefmt='%H:%M:%S'
        ))
        logging.getLogger().addHandler(log_handler)

    def _run_async(self):
        """在背景執行緒中執行非同步主流程"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._async_main())
        except Exception as e:
            Logger.error(f'Async error: {e}')
        finally:
            if self.loop:
                self.loop.close()
            Clock.schedule_once(lambda dt: self._on_complete())

    async def _async_main(self):
        """非同步主流程"""
        api = JCBAPI(mode=self.config.mode, testing=self.config.testing)
        scheduler = Scheduler(self.config.get_start_timestamp())
        notifier = Notifier(self.config.linetoken)
        captcha = CaptchaSolver(
            api_key=self.config.api_key,
            max_token=self.config.max_token,
            get_token_semaphore=self.config.get_token_semaphore,
        )

        credit_cards = self.config.txtCreditCardVal
        easy_cards = self.config.txtEasyCardVal
        total = len(credit_cards)

        Logger.info(f'開始登錄，共 {total} 張卡片')

        # 等待開始時間
        await scheduler.sleep_until(self.config.get_start_timestamp())
        Logger.info('開始時間到，啟動登錄')

        captcha.get_captchaKey_flag = True
        shoot_semaphore = asyncio.Semaphore(self.config.shoot_semaphore)
        captcha.shoot_semaphore = shoot_semaphore

        # 啟動 token 收集器
        token_task = asyncio.create_task(
            captcha.token_collector(self.config.get_start_timestamp())
        )

        for i in range(total):
            if not self.running:
                Logger.info('使用者中止登錄')
                break

            credit_card = credit_cards[i]
            easy_card = easy_cards[i]

            if self.config.is_card_recorded(easy_card[3]):
                Logger.info(f'卡片 {easy_card} 已被登錄，跳過')
                continue

            stagger_time = scheduler.get_staggered_time(i)
            await scheduler.sleep_until(stagger_time)

            # 取得 captcha token
            captcha_key = None
            while captcha_key is None and self.running:
                if captcha.token_list:
                    captcha_key = captcha.token_list.pop(0)
                if captcha_key is None:
                    await asyncio.sleep(1)

            if not self.running:
                break

            success, message, is_captcha_error = await api.send_request(
                semaphore=shoot_semaphore,
                count=i, captchaKey=captcha_key,
                txtCreditCardValS=credit_card,
                txtEasyCardValS=easy_card,
                start_timestamp=self.config.get_start_timestamp(),
            )

            if success:
                self.config.record_card(easy_card[3])
                Logger.info(f'✅ 卡片 {i+1}/{total} 登錄成功')
                await notifier.send(f'【JCB 登錄成功】{self.config.myname} - 卡片 {i+1}/{total}')
            elif is_captcha_error:
                Logger.warning(f'⚠️ 卡片 {i+1} 圖形驗證碼錯誤')
            else:
                Logger.error(f'❌ 卡片 {i+1} 登錄失敗: {message}')

            # 更新進度
            progress = int((i + 1) / total * 100)
            Clock.schedule_once(lambda dt, p=progress: setattr(self.root.ids.progress_bar, 'value', p))

        captcha.do_recaptcha = False
        token_task.cancel()
        Logger.info('🎉 登錄作業完成')

    def stop_registration(self):
        """停止登錄流程"""
        self.running = False
        self.root.ids.stop_btn.disabled = True
        Logger.info('正在停止登錄...')

    def _on_complete(self):
        """登錄完成後的 UI 更新"""
        self.root.ids.start_btn.disabled = False
        self.root.ids.stop_btn.disabled = True
        if self.root.ids.progress_bar.value >= 100:
            self.root.ids.status_label.text = '✅ 登錄作業已完成'
        else:
            self.root.ids.status_label.text = '⏹️ 登錄已中止'


if __name__ == '__main__':
    JCBApp().run()
