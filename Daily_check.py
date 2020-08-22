#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
本脚本用于日常环境巡检，主要有五个模块，分别是高可用数据库、分布式数据库、分布式缓存、分布式消息、lvs负载均衡

软件打包：
在linux环境下，使用pyinstaller工具将本脚本打包成一个二进制文件，注意脚本中引用的相关模块需要提前下载到打包环境当中，参考命令如下
pyinstaller -F Daily_check.py

使用教程：
直接执行打包后的二进制文件即可
"""
import subprocess
import logging
from kazoo.client import KazooClient
import sys
import random


class Check_lvs:
    def __init__(self, info_dict):
        self.lvs_ip = info_dict['lvs_ip']
        self.zk_base_path = info_dict['zk_base_path']
        self.udal_account = info_dict['udal_account']
        self.zk_urls = info_dict['zk_urls']
        self.lvs_access_dict = self.read_zk()

    # 从zookeeper中获取各应用lvs的连接地址，返回一个字典
    def read_zk(self):
        try:
            # 随机取出一个zk进行访问连接
            random.shuffle(self.zk_urls)
            zk_url = self.zk_urls[0]

            # 建立zk连接
            zk = KazooClient(hosts=zk_url)
            zk.start()

            # 获取基本路径下的所有应用节点名
            nodes = zk.get_children(self.zk_base_path)
            lvs_access_dict = {}

            # 遍历所有应用节点对应的子节点，其中保存了连接访问地址
            for node in nodes:
                application_name = str(node).split('|')[1]
                # 注意此处节点构建要加上'/'，否则出现节点获取异常
                link_path = zk.get_children(self.zk_base_path + '/' + node)
                lvs_access_dict[application_name] = link_path
            return lvs_access_dict
        except:
            print(' zk连接异常，程序退出！')
            sys.exit()

    # 进行lvs连通性检查
    def check(self):
        print('lvs巡检开始')
        udal_user, udal_passwd = self.udal_account[0], self.udal_account[1]
        for app_name, links in self.lvs_access_dict.items():
            # 取出各个应用的访问端口
            port = links[0].split(':')[1]
            try:
                cmd = 'mysql -h %s -P %s -u %s -p\'%s\' -e "show databases;" >/dev/null 2>&1' % (self.lvs_ip, port, udal_user, udal_passwd)
                status = subprocess.check_call(cmd, shell=True)
                if status == 0:
                    print('%s:%s 连通正常，应用 %s 检测正常' % (self.lvs_ip, str(port), app_name))
            except:
                print('\033[1;31m%s:%s 连通异常，应用 %s 检测异常\033[0m' % (self.lvs_ip, str(port), app_name))
                continue
        print('lvs巡检完成！')


if __name__ == '__main__':
    # 初始化配置参数（包括lvs ip信息、zk根节点路径、udal访问用户、zk地址列表）
    lvs_ip = '10.26.1.125'
    zk_base_path = '/alogic/global/arm'
    udal_account = ('paas', 'xKt!t1Fy')
    zk_urls = ['10.26.1.120:10050', '10.26.1.121:10050', '10.26.1.122:10050']
    init_dict = {'lvs_ip': lvs_ip, 'zk_base_path': zk_base_path, 'udal_account': udal_account, 'zk_urls': zk_urls}
    check_lvs = Check_lvs(init_dict)
    check_lvs.check()
