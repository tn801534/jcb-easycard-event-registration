# -*- coding: utf-8 -*-
"""
jcb_core.py — 核心 API 層
封裝 ezweb.easycard.com.tw 的 POST 請求與回應解析
"""

import datetime
import inspect
import logging
import pprint
import traceback

import requests_async
import lxml.html

logger = logging.getLogger(__name__)


class JCBAPI:
    """封裝悠遊卡活動登錄/查詢 API"""

    # API 端點
    SERVLET_MAP = {
        0: 'JCBLoginServlet',       # 登錄
        1: 'JCBLoginRecordServlet',  # 查詢
    }
    METHOD_MAP = {
        0: 'loginAccept',
        1: 'queryLoginDate',
    }

    def __init__(self, mode=0, testing=False):
        """
        Args:
            mode: 0=登錄, 1=查詢
            testing: 測試模式（使用查詢端點）
        """
        self.mode = mode
        self.testing = testing

    def _get_servlet_info(self):
        """根據模式決定 API 端點與方法"""
        if not self.testing and not self.mode:
            return 'JCBLoginServlet', 'loginAccept'
        else:
            return 'JCBLoginRecordServlet', 'queryLoginDate'

    def build_payload(self, txtCreditCardValS, txtEasyCardValS, captchaKey):
        """建立 POST 請求 payload

        Args:
            txtCreditCardValS: [txtCreditCard1, txtCreditCard2, txtCreditCard4]
            txtEasyCardValS: [txtEasyCard1, txtEasyCard2, txtEasyCard3, txtEasyCard4]
            captchaKey: reCAPTCHA 回應 token
        Returns:
            (url, data, headers) 元組
        """
        url_str, method_str = self._get_servlet_info()
        request_url = f'https://ezweb.easycard.com.tw/Event01/{url_str}'

        data = (
            f'txtCreditCard1={txtCreditCardValS[0]}'
            f'&txtCreditCard2={txtCreditCardValS[1]}'
            f'&txtCreditCard4={txtCreditCardValS[2]}'
            f'&txtEasyCard1={txtEasyCardValS[0]}'
            f'&txtEasyCard2={txtEasyCardValS[1]}'
            f'&txtEasyCard3={txtEasyCardValS[2]}'
            f'&txtEasyCard4={txtEasyCardValS[3]}'
            f'&g-recaptcha-response={captchaKey}'
            f'&method={method_str}'
        )

        headers = {
            'Host': 'ezweb.easycard.com.tw',
            'Origin': 'https://ezweb.easycard.com.tw',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': request_url,
        }

        return request_url, data, headers

    async def send_request(self, semaphore, count, captchaKey,
                           txtCreditCardValS, txtEasyCardValS,
                           start_timestamp):
        """執行 API 請求

        Args:
            semaphore: asyncio.Semaphore
            count: 卡片序號（用於錯開時間）
            captchaKey: reCAPTCHA token
            txtCreditCardValS: 信用卡值列表
            txtEasyCardValS: 悠遊卡值列表
            start_timestamp: 開始時間戳
        Returns:
            (success, response_text, parsed_result) 或 (False, error_msg, None)
        """
        url, data, headers = self.build_payload(
            txtCreditCardValS, txtEasyCardValS, captchaKey
        )
        card_info = str(txtEasyCardValS)

        async with semaphore:
            try:
                send_time = datetime.datetime.now().strftime('%S.%f')[:-3]
                response = await requests_async.post(
                    url, headers=headers, data=data, verify=False, timeout=60
                )
                resp_time = datetime.datetime.now().strftime('%S.%f')[:-3]
                now_str = datetime.datetime.now().strftime('%H:%M:%S')
                logger.info(
                    f'發送請求 {now_str} count:{count} '
                    f'send_time:{send_time} resp_time:{resp_time}'
                )

                response_text = response.text
                return self._parse_response(response_text, card_info)

            except Exception as e:
                logger.info(f'請求異常 {inspect.stack()[0][3]}')
                logger.info(f'{pprint.pformat(e)}')
                logger.info(f'{traceback.format_exc()}')
                return False, f'請求異常: {e}', None

    def _parse_response(self, response_text, card_info):
        """解析 API 回應

        Returns:
            (success, message, is_captcha_error)
            success: bool — 是否成功
            message: str — 描述訊息
            is_captcha_error: bool — 是否為圖形驗證碼錯誤
        """
        if '圖形驗證碼錯誤, 請重新輸入' in response_text:
            logger.info(f'圖形驗證碼錯誤 {card_info}')
            return False, '圖形驗證碼錯誤', True

        if '登錄結果' in response_text:
            try:
                root = lxml.html.etree.HTML(response_text)
                # 嘗試多種 XPath 定位結果
                result_xpaths = [
                    '/html/body/div/div/section/div/div/div/div/div/div/div/div/div/div/div/div',
                    '/html/body/div/div/section/div/div/div/div/div/div/div/div/div/div/div/div/div/div',
                    '/html/body/div/div/section/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div',
                    '/html/body/div/div/section/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div/div',
                ]
                for xp in result_xpaths:
                    elements = root.xpath(xp)
                    if elements:
                        text = elements[0].text
                        if text:
                            text_stripped = text.strip()
                            logger.info(f'登錄結果: {text_stripped}')
                            return True, text_stripped, False

                logger.info(f'登錄結果 (未找到元素): {card_info}')
                return True, '登錄結果 (未找到明確定義)', False

            except Exception as e:
                logger.info(f'解析回應失敗: {e}')
                return True, f'解析回應失敗: {e}', False

        # 一般回應（查詢模式等）
        logger.info(f'API 回應: {card_info}')
        logger.info(f'回應內容: {response_text[:200]}')
        return True, f'API 回應: {response_text[:100]}', False
