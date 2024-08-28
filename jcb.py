import datetime
import inspect
import json
import logging
import pprint
import os
import sys
import requests_async
import traceback
import ast
import asyncio
import lxml.html
import threading
from asyncio_read_write_lock import FifoLock, Read, Write
from chrome_helper import chrome_helper
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException,InvalidArgumentException
from selenium.webdriver.common.action_chains import ActionChains
from multiprocessing import cpu_count
import http3.exceptions
from urllib3.exceptions import InsecureRequestWarning, MaxRetryError
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()
from recaptchav2proxyless import recaptchaV2Proxyless
# from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask
from configobj import ConfigObj
from recaptchav2proxyless import recaptchaV2Proxyless
# chdir working directory to the script's own directory
if os.path.isabs(sys.argv[0]):
    os.chdir(os.path.dirname(sys.argv[0]))
format_str = '%(asctime)s.%(msecs)03d %(levelname)s %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'
loggingFormatter = logging.Formatter(format_str, date_format)
logging.basicConfig(level=logging.INFO,
                    format=format_str,
                    datefmt=date_format,
                    handlers=[logging.FileHandler(os.path.splitext(os.path.basename(__file__))[0]+'.log', 'a', 'utf-8'), ])
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
logger = logging.getLogger( __name__ )

async def lineNotifyMessage(token, msg, pic=None):
    if pic:
        files = {'imageFile': open(pic, 'rb')}
    else:
        files = None
    try:
        r = await requests_async.post("https://notify-api.line.me/api/notify", headers={"Authorization": "Bearer " + token}, params={'message': msg}, files=files, verify=False, timeout=5)
    except Exception as e:
        logger.info(f'{inspect.stack()[0][3]}')
        logger.info(f'{pprint.pformat(e)}')
        logger.info(f'{traceback.format_exc()}')
    return r.status_code

def waitForElementPresent(driver, selector, timeout=30):
    return WebDriverWait(driver, timeout, 0.1).until(EC.presence_of_element_located(selector))

async def queryJCB(semaphore, count, captchaKey, txtCreditCardValS, txtEasyCardValS):
    global max_captchaKey, do_recaptcha
    await sleep_by_timestamp(start_timestamp + count * 0.5)
    if not testing and not mode:
        urlStr = 'JCBLoginServlet'  # 登錄
        methodStr = 'loginAccept'  # 登錄
    else:
        urlStr = 'JCBLoginRecordServlet'  # 查詢
        methodStr = 'queryLoginDate'  # 查詢
    txtCreditCard1 = txtCreditCardValS[0]
    txtCreditCard2 = txtCreditCardValS[1]
    txtCreditCard4 = txtCreditCardValS[2]
    txtEasyCard1 = txtEasyCardValS[0]
    txtEasyCard2 = txtEasyCardValS[1]
    txtEasyCard3 = txtEasyCardValS[2]
    txtEasyCard4 = txtEasyCardValS[3]
    configread = ConfigObj('jcb.ini', encoding='UTF8')
    cardRecorded = configread.as_list("cardRecorded")
    if txtEasyCard4 in cardRecorded:
        logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} {inspect.stack()[0][3]} txtEasyCardValS:{str(txtEasyCardValS)} 已登錄成功略過')
        return
    # 登錄
    request_url = f'https://ezweb.easycard.com.tw/Event01/{urlStr}'
    data = 'txtCreditCard1=' + txtCreditCard1 + '&txtCreditCard2=' + txtCreditCard2 + '&txtCreditCard4=' + txtCreditCard4 \
           + '&txtEasyCard1=' + txtEasyCard1 + '&txtEasyCard2=' + txtEasyCard2 + '&txtEasyCard3=' + txtEasyCard3 + '&txtEasyCard4=' + txtEasyCard4 \
           + '&g-recaptcha-response=' + captchaKey + '&method=' + methodStr
    # logger.info(f'{inspect.stack()[0][3]} data:{str(data)}')
    # 登錄
    headers = {}
    headers['Host'] = 'ezweb.easycard.com.tw'
    headers['Origin'] = 'https://ezweb.easycard.com.tw'
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    headers['Referer'] = request_url
    async with semaphore:
        try:
            # logger.info(inspect.stack()[0][3] + ' txtEasyCardVal:' + str( txtEasyCardVal) + ' send requests begin')
            # responsejson = response.json()
            send_time = datetime.datetime.now().strftime('%S.%f')[:-3]
            response = await requests_async.post(request_url, headers=headers, data=data, verify=False, timeout=60)
            resp_time = datetime.datetime.now().strftime('%S.%f')[:-3]
            logger.info(f'送單回傳 {datetime.datetime.now().strftime("%H:%M:%S")} count:{count} send_time:{str(send_time)} resp_time:{str(resp_time)}')
            responsetext = response.text
            if "圖形驗證碼錯誤, 請重新輸入" in responsetext:
                logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} ERROR:{inspect.stack()[0][3]} txtEasyCardValS:{str(txtEasyCardValS)} 圖形驗證碼錯誤, 請重新輸入')
                return
            if "登錄結果" in responsetext:
                root = lxml.html.etree.HTML(responsetext)
                items = root.xpath('//*[@id="search_tb"]//tr/td[1]/text()')
                if len(items) == 0:
                    logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} ERROR:{inspect.stack()[0][3]} responsetext:{str(responsetext)}')
                logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} txtEasyCardValS:{str(txtEasyCardValS)} 登錄結果月份:' + ','.join([x.strip() for x in items]))
                # if testing:
                #     await lineNotifyMessage(linetoken, f"{str(txtEasyCardValS)} 登錄成功")
                #     async with lock(Write):
                #         configwrite = ConfigObj('jcb.ini', encoding='UTF8')
                #         cardRecorded = configwrite.as_list("cardRecorded")
                #         if txtEasyCard4 not in cardRecorded:
                #             cardRecorded.append(txtEasyCard4)
                #             configwrite['cardRecorded'] = cardRecorded
                #             configwrite.write()
                return
            if "開放" in responsetext:
                logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} ERROR:{inspect.stack()[0][3]} txtEasyCardValS:{str(txtEasyCardValS)} 還沒開放')
                return
            if "登錄名額已滿" in responsetext:
                logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} ERROR:{inspect.stack()[0][3]} txtEasyCardValS:{str(txtEasyCardValS)} 登錄名額已滿')
                do_recaptcha = False
                # 測試
                # if max_captchaKey < 2:
                #     max_captchaKey = max_captchaKey + 1
                return
            if "成功" in responsetext:
                logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} {inspect.stack()[0][3]} txtEasyCardValS:{str(txtEasyCardValS)} 登錄成功')
                async with lock(Write):
                    configwrite = ConfigObj('jcb.ini', encoding='UTF8')
                    cardRecorded = configwrite.as_list("cardRecorded")
                    if txtEasyCard4 not in cardRecorded:
                        cardRecorded.append(txtEasyCard4)
                        configwrite['cardRecorded'] = cardRecorded
                        configwrite.write()
                if max_captchaKey < 2:
                    max_captchaKey = max_captchaKey+1
                await lineNotifyMessage(linetoken, f"{str(txtEasyCardValS)} 登錄成功")
                return
            if "已登錄過" in responsetext:
                logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} {inspect.stack()[0][3]} txtEasyCardValS:{str(txtEasyCardValS)} 登錄重複')
                async with lock(Write):
                    configwrite = ConfigObj('jcb.ini', encoding='UTF8')
                    cardRecorded = configwrite.as_list("cardRecorded")
                    if txtEasyCard4 not in cardRecorded:
                        cardRecorded.append(txtEasyCard4)
                        configwrite['cardRecorded'] = cardRecorded
                        configwrite.write()
                await lineNotifyMessage(linetoken, f"{str(txtEasyCardValS)} 登錄成功(重複)")
                return
            logger.info(f'ERROR:{inspect.stack()[0][3]} responsetext:{str(responsetext)}')
        except(MaxRetryError, asyncio.TimeoutError, requests.exceptions.ReadTimeout, http3.exceptions.ReadTimeout, http3.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
            # logger.info(inspect.stack()[0][3] + ' except:' + str(e))
            errMsg = f'{inspect.stack()[0][3]} {str(pprint.pformat(e))}'
            logger.info(f'ERROR:{inspect.stack()[0][3]} errMsg:{str(errMsg)}')
        except Exception as e:
            # logger.info(inspect.stack()[0][3] + ' traceback:' + str(traceback.format_exc()))
            errMsg = f'{inspect.stack()[0][3]} {str(pprint.pformat(e))} {str(traceback.format_exc())}'
            logger.info(f'ERROR:{inspect.stack()[0][3]} errMsg:{str(errMsg)}')
        else:
            logger.info(f'ERROR:{inspect.stack()[0][3]} responsetext:{str(responsetext)}')

async def drawPrize():
    global accounts, do_drawprize, do_recaptcha, captchaKeyList, stop_time, max_captchaKey, get_captchaKey_flag
    if start_timestamp > datetime.datetime.now().timestamp():
        logger.info(f'發射官等待中 預計送單時間{datetime.datetime.fromtimestamp(round(start_timestamp, 3)).strftime("%H:%M:%S.%f")[:-3]}')
        await sleep_by_timestamp(start_timestamp)
    count = 0
    semaphore = asyncio.Semaphore(shoot_semaphore)
    while do_recaptcha:
        configread = ConfigObj('jcb.ini', encoding='UTF8')
        cardRecorded = configread.as_list("cardRecorded")
        excludeCard = configread.as_list("excludeCard")
        deltxtCreditCardVals = []
        for key, txtEasyCardValRow in enumerate(txtEasyCardVal[:]):
            txtEasyCardValS = ast.literal_eval(txtEasyCardValRow)
            txtEasyCard4 = txtEasyCardValS[3]
            if txtEasyCard4 in cardRecorded or txtEasyCard4 in excludeCard:
                txtEasyCardVal.remove(txtEasyCardValRow)
                deltxtCreditCardVals.append(txtCreditCardVal[key])
        for deltxtCreditCardVal in deltxtCreditCardVals:
            txtCreditCardVal.remove(deltxtCreditCardVal)
        # logger.info(f'txtEasyCardVal len:{len(txtEasyCardVal)} {txtEasyCardVal} ')
        # logger.info(f'txtCreditCardVal len:{len(txtCreditCardVal)} {txtCreditCardVal}')
        # logger.info(f'max_captchaKey {max_captchaKey}')
        if(len(txtCreditCardVal)==0):
            logger.info(f'送單組 {datetime.datetime.now().strftime("%H:%M:%S")} 所有卡片都已登錄過')
            get_captchaKey_flag = False
            do_recaptcha = False
            break

        for counter in range(max_captchaKey):
            get_captchaKey_flag = True
            while len(captchaKeyList) == 0:
                await asyncio.sleep(1)
            if len(captchaKeyList) > 0:
                captchaKey = captchaKeyList.pop(0)
                row = count % len(txtCreditCardVal)
                logger.info(f'送單組 {datetime.datetime.now().strftime("%H:%M:%S")} count:{count} row:{row} {ast.literal_eval(txtEasyCardVal[row])} 準備開始送單captchaKey:{captchaKey}')
                # not block here
                asyncio.create_task(queryJCB(semaphore, count, captchaKey, ast.literal_eval(txtCreditCardVal[row]),ast.literal_eval(txtEasyCardVal[row])))
                count += 1
                # threading.Thread(target=queryJCB, args=(semaphore, count, captchaKey, ast.literal_eval(txtCreditCardVal[row]),ast.literal_eval(txtEasyCardVal[row]))).start()
                # await queryJCB()
        get_captchaKey_flag = False
        await asyncio.sleep(1)
    logger.info(f'送單組 {datetime.datetime.now().strftime("%H:%M:%S")} 關閉送單')

# 取得token
async def getRecaptchaV2Proxyless(count, semaphore):
    global solver, do_recaptcha, captchaKeyList
    site_key = '6LfhNyoUAAAAACy6h4y3FRqxuMYhS6RXPcVlGenJ'  # grab from site
    request_url = 'https://ezweb.easycard.com.tw/Event01/JCBLoginRecordServlet'
    solver = recaptchaV2Proxyless()
    solver.set_verbose(0)
    solver.set_key(api_key)
    solver.set_website_url(request_url)
    solver.set_website_key(site_key)
    async with semaphore:
        nowtime = datetime.datetime.now().timestamp()
        # and nowtime < (start_timestamp - 3)
        if do_recaptcha:
            #下二行是看帳號是否死掉用的 假token
            #import string, random
            #captchaKeyList.append(f'03AGdBq25801eS2vxC{"".join(random.choice(string.ascii_letters) for x in range(25))}-p5RBQA9mpBw2XHzPGb-aLwys-WLVD54poL950EJmKDZwFby1Yl6Ygq7s8YyOYmrPgVy9IZ-DB6nojEYrNEOxTYfJrLz8qfYrLGIytdZ6HANdIX-PrHwKYQo9tzEYYWSj-37RaNJ2sOo6J_yyipBfhSnezx9mwHRJLz7y-P9VBy4gwiM-HJm3VwQm02pzUDs7WbMQNsYDudTIh9UIdsbNIdesZX5bFv8zl4DDzKhmzuzDv47WafyusIoXufT855HZfrciZCH6mEuR_MGeY2ckSL0XjrvW7gim7aJdyd7v7LF6TJW7QcqDnAXBesRKiYjAmK5JAZeumMe76YRktxakaOfPkT2GvFA65djSApBFvlibihkIJ4n6DRjbJHexYph5QMYLh4nCujJJ6nGGmga9')
            #logger.info(f'{inspect.stack()[0][3]} count:{count} 取得token captchaKey:{captchaKeyList[-1][0:30]}...')
            try:
                logger.info(f'自動組子彈兵 count:{count} 準備取得token start_time:{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}')
                captchaKey = await solver.solve_and_return_solution()
                if captchaKey != 0:
                    logger.info(f'自動組子彈兵 count:{count} end_time:{datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]} 拿到子彈captchaKey:{captchaKey[0:30]}... ')
                    captchaKeyList.append(captchaKey)
                else:
                    logger.info(f'自動組子彈兵 count:{count} error:{solver.error_code} {solver.err_string}')
            except Exception as e:
                logger.info('except')
                logger.info(pprint.pformat(e))
                logger.info(str(traceback.format_exc()))
        else:
            logger.info(f'自動組子彈兵 count:{count} 停止取得token')
# 非同步睡眠
async def sleep_by_timestamp(wakeuptimestamp):
    while True:
        nowtimestamp = datetime.datetime.now().timestamp()
        diff_time = wakeuptimestamp - nowtimestamp
        if diff_time > 0.015:
            await asyncio.sleep(diff_time - 0.015)
        elif diff_time > 0.01:
            await asyncio.sleep(0.001)
        else:
            break

async def get_restdo_captchakey():
    global captchaKeyList
    restdo_captchaKeyList = []
    CHROME_DRIVER_FOLDER = r"C:\Users\tn-pc\OneDrive\Python"
    CHROME_DRIVER_EXE = f"{CHROME_DRIVER_FOLDER}\chromedriver.exe"
    # chrome_helper.check_browser_driver_available(CHROME_DRIVER_FOLDER)
    # logger.info( f'手動組子彈兵等待中 預計開始領時間{datetime.datetime.fromtimestamp(round(start_timestamp - 110, 3)).strftime("%H:%M:%S.%f")[:-3]}')
    # while datetime.datetime.now().timestamp() < start_timestamp-2:
    #     if((len(captchaKeyList)>=max_captchaKey and do_faster)):
    #         break
    #     await asyncio.sleep(1)
    # try:
    #     logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} 手動組Server版開始領子彈')
    #     jsondata = {"send_timestamp": datetime.datetime.now().timestamp(), "subtract_min": 2, "myname": f'{myname}'}
    #     response = await requests_async.post(f'https://jjhung.asuscomm.com:7000/gettoken', json=jsondata, timeout=5)
    #     restdo_captchaKeyList = [x["token"] for x in json.loads(response.text) if "token" in x]
    #     captchaKeyList += restdo_captchaKeyList
    #     # logger.info(f'手動組:共取得{len(restdo_captchaKeyList)}發子彈')
    # except Exception as e:
    #     logger.info(f'手動組:出事了...{str(pprint.pformat(e))}')
        # logger.info(str(traceback.format_exc()))
    # logger.info(f'{datetime.datetime.now().strftime("%H:%M:%S")} 手動組共取得{len(restdo_captchaKeyList)}發子彈')

async def get_captchaKey():
    global do_recaptcha, get_captchaKey_flag
    # 有贊助失學少女的api_key才往下跑
    if api_key:
        # 睡到開跑前110秒醒來打工拿token
        logger.info(f'自動組子彈兵等待中 預計開始領時間{datetime.datetime.fromtimestamp(round(start_timestamp - 10, 3)).strftime("%H:%M:%S.%f")[:-3]}')
        await sleep_by_timestamp(start_timestamp-10)
        semaphore = asyncio.Semaphore(get_token_semaphore)
        # tasks = []
        count = 0
        while do_recaptcha:
            if get_captchaKey_flag:
                logger.info(f'自動組子彈兵開始領子彈 {datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]}')
                for counter in range(max_captchaKey):
                    asyncio.create_task(getRecaptchaV2Proxyless(count,semaphore))
                    count = count+1
                await asyncio.sleep(15)
            else:
                # logger.info(f'自動組子彈兵開始領子彈 {datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]} 不需領子彈')
                pass
            await asyncio.sleep(1)
        logger.info(f'自動組 {datetime.datetime.now().strftime("%H:%M:%S")} 子彈兵關閉領子彈 ')
        # await asyncio.gather(*tasks)
    # get_captchaKey_done = True

async def create_task():
    await asyncio.gather(*[get_captchaKey(), drawPrize(), get_restdo_captchakey()])

config = ConfigObj('jcb.ini', encoding='UTF8')
txtCreditCardVal = config.as_list('txtCreditCardVal')
txtEasyCardVal = config.as_list('txtEasyCardVal')
mode = int(config.get("mode", 100))
testing = config.as_bool('testing')
linetoken = config.get('linetoken')
api_key = config.get('api_key')
myname = config.get('myname')
max_captchaKey = int(config.get("max_token", 100))
shoot_semaphore = int(config.get("shoot_semaphore", 30))
get_token_semaphore = int(config.get("get_token_semaphore", 30))
captchaKeyList = []
lock = FifoLock()
do_recaptcha = True
do_faster = False
get_captchaKey_flag = False
# 設定時間
start_time = None if config.get('start_time') == "None" or config.get('start_time') == "" else str(config.get('start_time')).split(':')
start_hour, start_min, start_sec = None, None, None
if start_time:
    start_time_len = len(start_time)
    start_hour = int(start_time[0]) if start_time_len > 0 and start_time[0] else None
    start_min = int(start_time[1]) if start_time_len > 1 and start_time[1] else 0
    start_sec = int(start_time[2]) if start_time_len > 2 and start_time[2] else 0

# 檢查參數
if len(txtCreditCardVal) != len(txtEasyCardVal):
    logger.info(f'ERROR:{str(inspect.stack()[0][3])} txtCreditCardVal len:{str(len(txtCreditCardVal))} txtEasyCardVal len:{str(len(txtEasyCardVal))} 參數數量不符請檢查ini')
    sys.exit(1)


# 設定喚醒時間 wakeuptimestamp
nowDate = datetime.datetime.now()
start_timestamp = (nowDate.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)).timestamp()
if start_hour is not None:  # 依指定開始時間起跑
    runDate = nowDate.replace(hour=start_hour % 24, minute=start_min, second=start_sec, microsecond=0)
    # 不需要加一天
    # runDate = runDate if runDate > nowDate else runDate + datetime.timedelta(days=1)
    start_timestamp = runDate.timestamp()
# if start_timestamp < datetime.datetime.now().timestamp():
#     start_timestamp = datetime.datetime.now().timestamp() + 115
#     do_faster = True
logger.info(f'開跑時間為 {datetime.datetime.fromtimestamp(round(start_timestamp, 3)).strftime("%H:%M:%S.%f")[:-3]}')

try:
    asyncio.get_event_loop().run_until_complete(create_task())
except KeyboardInterrupt:
    logger.info('鍵盤中斷')
    raise
except Exception as e:
    logger.info(f'程式出錯了!!! 請回報錯誤原因:{e}')
    logger.info(f'\n{traceback.format_exc()}')
    os.system("pause")