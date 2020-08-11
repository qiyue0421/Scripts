#!/usr/bin/env python
# -*- coding:utf-8 -*-
import datetime
import sys
import io


def dbproxy_errorlog(filename):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    punish_list = ['errorCode=4000', 'errorCode=3013', 'Connection timed out']
    with io.open(filename, encoding='utf-8') as f:
        for line in f.read().split(date):
            if 'ERROR' in line and not any(code in line for code in punish_list):
                print(date + line)


def ctgcache_errorlog(filename):
    date = '[' + datetime.datetime.now().strftime('%y%m%d')
    f = io.open(filename, encoding='utf-8')
    _, line = f.read().split(date, 1)
    f.close()
    line = date + line
    for i in line.split(date):
        if 'WARN' in i or 'ERROR' in i:
            print(date + i)


def ctgmq_errorlog(filename):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    f = io.open(filename, encoding='utf-8')
    _, line = f.read().split(date, 1)
    f.close()
    line = date + line
    for i in line.split(date):
        if 'WARN' in i or 'ERROR' in i:
            print(date + i)


if __name__ == '__main__':
    # python2使用
    # reload(sys)
    # sys.setdefaultencoding("utf8")
    useage = '''
            命令使用示例：   
            ./script '/app/udal/dbproxy_103_8913/logs/dbproxy.log' > dbproxy.log
            ./script '/data/ctgcache/cache_apps/access/access_100000_23_pto_oss_bus_2/logs/error.log' > ctgcache.log
            ./script '/app/ctgmq/running/namesrv/PTO_MQ_001_namesrv/3/logs/rocketmqlogs/namesrv.log' > ctgmq.log
            '''
    try:
        filename = sys.argv[1]
        if 'dbproxy' in filename:
            dbproxy_errorlog(filename)
        elif 'ctgcache' in filename:
            ctgcache_errorlog(filename)
        elif 'ctgmq' in filename:
            ctgmq_errorlog(filename)
        else:
            print(useage)
    except IndexError as e:
        print(useage)
