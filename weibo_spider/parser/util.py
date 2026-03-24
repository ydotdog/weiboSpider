import hashlib
import json
import logging
import sys

import requests
from lxml import etree

# Set GENERATE_TEST_DATA to True when generating test data.
GENERATE_TEST_DATA = False
TEST_DATA_DIR = 'tests/testdata'
URL_MAP_FILE = 'url_map.json'
logger = logging.getLogger('spider.util')

# 全局代理配置，由 spider.py 初始化
_proxies = None


def set_proxies(proxy_url):
    """设置全局代理"""
    global _proxies
    if proxy_url:
        _proxies = {'http': proxy_url, 'https': proxy_url}
        logger.info(u'已启用代理: %s', proxy_url)


def get_proxies():
    return _proxies


def hash_url(url):
    return hashlib.sha224(url.encode('utf8')).hexdigest()


DEFAULT_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/133.0.0.0 Safari/537.36')


def handle_html(cookie, url):
    """处理html"""
    from time import sleep
    headers = {'User-Agent': DEFAULT_UA, 'Cookie': cookie}
    for attempt in range(5):
        try:
            resp = requests.get(url, headers=headers, timeout=10,
                                proxies=_proxies)
            if resp.status_code == 200 and len(resp.content) > 0:
                selector = etree.HTML(resp.content)
                return selector
            elif resp.status_code == 403:
                wait = 300 * (attempt + 1)
                logger.warning(u'403 IP被限制，等待%d秒后重试(第%d次)',
                               wait, attempt + 1)
                sleep(wait)
            elif resp.status_code == 432:
                logger.error(u'432 User-Agent被拒绝，请更新UA')
                return None
            else:
                wait = 60 * (attempt + 1)
                logger.warning(u'请求返回状态码%d，等待%d秒后重试(第%d次)',
                               resp.status_code, wait, attempt + 1)
                sleep(wait)
        except Exception as e:
            wait = 60 * (attempt + 1)
            logger.warning(u'请求异常，等待%d秒后重试(第%d次): %s',
                           wait, attempt + 1, str(e))
            sleep(wait)
    logger.error(u'请求%s失败，已重试5次', url)
    return None


def handle_garbled(info):
    """处理乱码"""
    try:
        if hasattr(info, 'xpath'): # 检查 info 是否具有 xpath 方法
            info_str = info.xpath('string(.)')  # 提取字符串内容
        else:
            info_str = str(info) # 若不支持 xpath，将其转换为字符串

        info = info_str.replace(u'\u200b', '').encode(
            sys.stdout.encoding, 'ignore').decode(sys.stdout.encoding)
        return info
    except Exception as e:
        logger.exception(e)
        return u'无'


def bid2mid(bid):
    """convert string bid to string mid"""
    alphabet = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    base = len(alphabet)
    bidlen = len(bid)
    head = bidlen % 4
    digit = int((bidlen - head) / 4)
    dlist = [bid[0:head]]
    for d in range(1, digit + 1):
        dlist.append(bid[head:head + d * 4])
        head += 4
    mid = ''
    for d in dlist:
        num = 0
        idx = 0
        strlen = len(d)
        for char in d:
            power = (strlen - (idx + 1))
            num += alphabet.index(char) * (base**power)
            idx += 1
            strnum = str(num)
            while (len(d) == 4 and len(strnum) < 7):
                strnum = '0' + strnum
        mid += strnum
    return mid


def to_video_download_url(cookie, video_page_url):
    if video_page_url == '':
        return ''

    video_object_url = video_page_url.replace('m.weibo.cn/s/video/show',
                                              'm.weibo.cn/s/video/object')
    try:
        headers = {'User-Agent': DEFAULT_UA, 'Cookie': cookie}
        wb_info = requests.get(video_object_url, headers=headers,
                               proxies=_proxies).json()
        video_url = wb_info['data']['object']['stream'].get('hd_url')
        if not video_url:
            video_url = wb_info['data']['object']['stream']['url']
            if not video_url:  # 说明该视频为直播
                video_url = ''
    except json.decoder.JSONDecodeError:
        logger.warning(u'当前账号没有浏览该视频的权限')

    return video_url


def string_to_int(string):
    """字符串转换为整数"""
    if len(string) == 0:
        logger.warning("string to int, the input string is empty!")
        return 0
    if isinstance(string, int):
        return string
    elif string.endswith(u'万+'):
        string = string[:-2] + '0000'
    elif string.endswith(u'万'):
        string = float(string[:-1]) * 10000
    elif string.endswith(u'亿'):
        string = float(string[:-1]) * 100000000
    return int(string)
