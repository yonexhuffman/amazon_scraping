#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime, timedelta
from twisted.web._newclient import ResponseNeverReceived
from twisted.internet.error import TimeoutError, ConnectionRefusedError, ConnectError
from isbn import fetch_free_proxies
from random import randint

logger = logging.getLogger(__name__)

class HttpProxyMiddleware(object):
    # 遇到这些类型的错误直接当做代理不可用处理掉, 不再传给retrymiddleware
    DONT_RETRY_ERRORS = (TimeoutError, ConnectionRefusedError, ResponseNeverReceived, ConnectError, ValueError)

    def __init__(self, use_https):
        # 保存上次不用代理直接连接的时间点
        self.last_no_proxy_time = datetime.now()
        # 一定分钟数后切换回不用代理, 因为用代理影响到速度
        self.recover_interval = 20
        # 一个proxy如果没用到这个数字就被发现老是超时, 则永久移除该proxy. 设为0则不会修改代理文件.
        self.dump_count_threshold = 20
        # 存放代理列表的文件, 每行一个代理, 格式为proto://ip:port, 这个文件会被修改, 注意备份
        self.proxy_file = "proxies.dat"
        # 是否在超时的情况下禁用代理
        self.invalid_proxy_flag = True
        # 当有效代理小于这个数时(包括直连), 从网上抓取新的代理, 可以将这个数设为为了满足每个ip被要求输入验证码后得到足够休息时间所需要的代理数
        # 例如爬虫在十个可用代理之间切换时, 每个ip经过数分钟才再一次轮到自己, 这样就能get一些请求而不用输入验证码.
        # 如果这个数过小, 例如两个, 爬虫用A ip爬了没几个就被ban, 换了一个又爬了没几次就被ban, 这样整个爬虫就会处于一种忙等待的状态, 影响效率
        self.extend_proxy_threshold = 10
        # 初始化代理列表
        self.proxies = [{"proxy": None, "valid": True, "count": 0}]
        # 初始时使用0号代理(即无代理)
        self.proxy_index = 0
        # 表示可信代理的数量(如自己搭建的HTTP代理)+1(不用代理直接连接)
        self.fixed_proxy = len(self.proxies)
        # 上一次抓新代理的时间
        self.last_fetch_proxy_time = datetime.now()
        # 每隔固定时间强制抓取新代理(min)
        self.fetch_proxy_interval = 120
        # 一个将被设为invalid的代理如果已经成功爬取大于这个参数的页面， 将不会被invalid
        self.invalid_proxy_threshold = 200
        # 使用http代理还是https代理
        self.use_https = use_https

        # self.fetch_new_proxies()
        # 从文件读取初始代理
        if os.path.exists(self.proxy_file):
            with open(self.proxy_file, "r") as fd:
                lines = fd.readlines()            
                for line in lines:
                    line = line.strip()
                    if not line or self.url_in_proxies(line):
                        continue
                    self.proxies.append({"proxy": line,
                                        "valid": True,
                                        "count": 0})

    @classmethod
    def from_crawler(cls, crawler):
        use_https = crawler.settings.getbool('HTTPS_PROXY')
        return cls(use_https)

    def url_in_proxies(self, url):
        """
        返回一个代理url是否在代理列表中
        """
        for p in self.proxies:
            if url == p["proxy"]:
                return True
        return False

    def reset_proxies(self):
        """
        将所有count>=指定阈值的代理重置为valid,
        """
        logger.info("reset proxies to valid")
        for p in self.proxies:
            if p["count"] >= self.dump_count_threshold:
                p["valid"] = True

    def fetch_new_proxies(self):
        """
        从网上抓取新的代理添加到代理列表中
        """
        logger.info("extending proxies using fetch_free_proxies.py")
        new_proxies = fetch_free_proxies.fetch_all(https=self.use_https)
        logger.info("new proxies: %s" % new_proxies)
        self.last_fetch_proxy_time = datetime.now()

        for np in new_proxies:
            if self.url_in_proxies(np):
                continue
            else:
                self.proxies.append({"proxy": np,
                                     "valid": True,
                                     "count": 0})
        if self.len_valid_proxy() < self.extend_proxy_threshold: # 如果发现抓不到什么新的代理了, 缩小threshold以避免白费功夫
            self.extend_proxy_threshold -= 1

    def len_valid_proxy(self):
        """
        返回proxy列表中有效的代理数量
        """
        count = 0
        for p in self.proxies:
            if p["valid"]:
                count += 1
        return count

    def inc_proxy_index(self, current=-1):
        """
        将代理列表的索引移到下一个有效代理的位置
        如果发现代理列表只有fixed_proxy项有效, 重置代理列表
        如果还发现已经距离上次抓代理过了指定时间, 则抓取新的代理
        """
        assert self.proxies[0]["valid"]
        if current != -1 and self.proxy_index != current: 
            return
        while True:
            #self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
            #self.proxy_index = 0
            # if randint(0, 30) >= 29:
            self.proxy_index = randint(0, len(self.proxies) - 1)
            if self.proxies[self.proxy_index]["valid"]:
                break

        # 两轮proxy_index==0的时间间隔过短， 说明出现了验证码抖动，扩展代理列表
        if self.proxy_index == 0 and datetime.now() > self.last_fetch_proxy_time + timedelta(minutes=10):
            logger.info("captcha thrashing")
            self.fetch_new_proxies()

        if self.len_valid_proxy() <= self.fixed_proxy or self.len_valid_proxy() < self.extend_proxy_threshold: # 如果代理列表中有效的代理不足的话重置为valid
            self.reset_proxies()

        if self.len_valid_proxy() < self.extend_proxy_threshold: # 代理数量仍然不足, 抓取新的代理
            logger.info("valid proxy < threshold: %d/%d" % (self.len_valid_proxy(), self.extend_proxy_threshold))
            self.fetch_new_proxies()

        logger.info("now using new proxy: %s" % self.proxies[self.proxy_index]["proxy"])

        # 一定时间没更新后可能出现了在目前的代理不断循环不断验证码错误的情况, 强制抓取新代理
        #if datetime.now() > self.last_fetch_proxy_time + timedelta(minutes=self.fetch_proxy_interval):
        #    logger.info("%d munites since last fetch" % self.fetch_proxy_interval)
        #    self.fetch_new_proxies()

    def set_proxy(self, request):
        """
        将request设置使用为当前的或下一个有效代理
        """
        # proxy = self.proxies[self.proxy_index]
        
        # if not proxy["valid"]:
        #     self.inc_proxy_index()
        #     proxy = self.proxies[self.proxy_index]

        if "no_proxy" in request.meta.keys():
            # del request.meta["proxy"]
            request.meta["proxy_index"] = self.proxy_index
            return

        self.inc_proxy_index()
        proxy = self.proxies[self.proxy_index]

        if self.proxy_index == 0: # 每次不用代理直接下载时更新self.last_no_proxy_time
            self.last_no_proxy_time = datetime.now()

        if proxy["proxy"]:
            request.meta["proxy"] = "http://" + proxy["proxy"]
        elif "proxy" in request.meta.keys():
            del request.meta["proxy"]
        request.meta["proxy_index"] = self.proxy_index
        proxy["count"] += 1

    def invalid_proxy(self, index):
        """
        将index指向的proxy设置为invalid,
        并调整当前proxy_index到下一个有效代理的位置
        """
        if index < self.fixed_proxy: # 可信代理永远不会设为invalid
            logger.info("fixed proxy will not be invalid: %s" % self.proxies[index])
            self.inc_proxy_index(index)
            return

        if self.proxies[index]["valid"]:
            logger.info("invalidate %s" % self.proxies[index])
            self.proxies[index]["valid"] = False
            if index == self.proxy_index:
                self.inc_proxy_index()

            if self.proxies[index]["count"] < self.dump_count_threshold:
                self.dump_valid_proxy()

    def dump_valid_proxy(self):
        """
        保存代理列表中有效的代理到文件
        """
        if self.dump_count_threshold <= 0:
            return
        logger.info("dumping proxies to file")
        with open(self.proxy_file, "w") as fd:
            for i in range(self.fixed_proxy, len(self.proxies)):
                p = self.proxies[i]
                if p["valid"] or p["count"] >= self.dump_count_threshold:
                    fd.write(p["proxy"]+"\n") # 只保存有效的代理

    def process_request(self, request, spider):
        """
        将request设置为使用代理
        """
        if self.proxy_index > 0  and datetime.now() > (self.last_no_proxy_time + timedelta(minutes=self.recover_interval)):
            logger.info("After %d minutes later, recover from using proxy" % self.recover_interval)
            self.last_no_proxy_time = datetime.now()
            self.proxy_index = 0
        request.meta["dont_redirect"] = True  # 有些代理会把请求重定向到一个莫名其妙的地址

        # spider发现parse error, 要求更换代理
        if "change_proxy" in request.meta.keys() and request.meta["change_proxy"]:
            logger.info("change proxy request get by spider: %s" % request)
            self.invalid_proxy(request.meta["proxy_index"])
            request.meta["change_proxy"] = False

        self.set_proxy(request)

    def process_response(self, request, response, spider):
        """
        检查response.status, 根据status是否在允许的状态码中决定是否切换到下一个proxy, 或者禁用proxy
        """
        if "proxy" in request.meta.keys():
            logger.debug("%s %s %s" % (request.meta["proxy"], response.status, request.url))
        else:
            logger.debug("None %s %s" % (response.status, request.url))

        # status不是正常的200而且不在spider声明的正常爬取过程中可能出现的
        # status列表中, 则认为代理无效, 切换代理
        if response.status != 200 \
                and (not hasattr(spider, "website_possible_httpstatus_list") \
                             or response.status not in spider.website_possible_httpstatus_list):
            logger.info("response status[%d] not in spider.website_possible_httpstatus_list" % response.status)
            self.invalid_proxy(request.meta["proxy_index"])
            new_request = request.copy()
            new_request.dont_filter = True
            return new_request
        else:
            return response

    def process_exception(self, request, exception, spider):
        """
        处理由于使用代理导致的连接异常
        """
        logger.debug("%s exception: %s" % (self.proxies[request.meta["proxy_index"]]["proxy"], exception))
        request_proxy_index = request.meta["proxy_index"]

        # 只有当proxy_index>fixed_proxy-1时才进行比较, 这样能保证至少本地直连是存在的.
        if isinstance(exception, self.DONT_RETRY_ERRORS):
            if request_proxy_index > self.fixed_proxy - 1 and self.invalid_proxy_flag: # WARNING 直连时超时的话换个代理还是重试? 这是策略问题
                if self.proxies[request_proxy_index]["count"] < self.invalid_proxy_threshold:
                    self.invalid_proxy(request_proxy_index)
                elif request_proxy_index == self.proxy_index:  # 虽然超时，但是如果之前一直很好用，也不设为invalid
                    self.inc_proxy_index()
            else:               # 简单的切换而不禁用
                if request.meta["proxy_index"] == self.proxy_index:
                    self.inc_proxy_index()
            new_request = request.copy()
            new_request.dont_filter = True
            return new_request