import logging
import sys

from ..user import User
from .parser import Parser
from .util import handle_html

logger = logging.getLogger('spider.info_parser')


class InfoParser(Parser):
    def __init__(self, cookie, user_id):
        self.cookie = cookie
        self.url = 'https://weibo.cn/%s/info' % (user_id)
        self.selector = handle_html(self.cookie, self.url)

    def extract_user_info(self):
        """提取用户信息"""
        try:
            user = User()
            nickname = self.selector.xpath('//title/text()')[0]
            nickname = nickname[:-3]
            if nickname == u'登录 - 新' or nickname == u'新浪':
                logger.warning(u'cookie错误或已过期,请按照README中方法重新获取')
                sys.exit()
            user.nickname = nickname

            zh_list = [u'性别', u'地区', u'生日', u'简介', u'认证', u'达人']
            en_list = [
                'gender', 'location', 'birthday', 'description',
                'verified_reason', 'talent'
            ]

            # 先尝试标准格式（查看他人资料页）
            basic_info = self.selector.xpath("//div[@class='c'][3]/text()")
            has_info = any(
                ':' in str(i) and str(i).split(':', 1)[0] in zh_list
                for i in basic_info)

            if not has_info:
                # 自己查看自己的资料页：标签在<a>标签内，值在<a>的tail文本中
                basic_info = []
                for c_div in self.selector.xpath("//div[@class='c']"):
                    a_texts = c_div.xpath('a/text()')
                    if u'性别' in a_texts or u'昵称' in a_texts:
                        for a in c_div.xpath('a'):
                            label = (a.text or '').strip()
                            tail = (a.tail or '').strip()
                            if label in zh_list and tail.startswith(':'):
                                basic_info.append(label + tail)
                        break

            for i in basic_info:
                if ':' in str(i) and str(i).split(':', 1)[0] in zh_list:
                    setattr(user, en_list[zh_list.index(str(i).split(':', 1)[0])],
                            str(i).split(':', 1)[1].replace('\u3000', ''))

            # 提取学习经历和工作经历，使用following-sibling定位，兼容自己和他人页面
            tip_divs = self.selector.xpath("//div[@class='tip']")
            for tip in tip_divs:
                tip_text = tip.xpath('string(.)').strip()
                if tip_text == u'学习经历':
                    edu_div = tip.xpath(
                        'following-sibling::div[@class="c"][1]')
                    if edu_div:
                        # 优先用text()（他人页面），fallback用string(.)（自己页面）
                        edu_text = edu_div[0].xpath('text()')
                        if edu_text and len(edu_text[0].strip()) > 1:
                            user.education = edu_text[0][1:].replace(
                                u'\xa0', u' ')
                        else:
                            user.education = ' '.join(
                                edu_div[0].xpath('string(.)').split())
                elif tip_text == u'工作经历':
                    work_div = tip.xpath(
                        'following-sibling::div[@class="c"][1]')
                    if work_div:
                        work_text = work_div[0].xpath('text()')
                        if work_text and len(work_text[0].strip()) > 1:
                            user.work = work_text[0][1:].replace(
                                u'\xa0', u' ')
                        else:
                            user.work = ' '.join(
                                work_div[0].xpath('string(.)').split())

            return user
        except Exception as e:
            logger.exception(e)
