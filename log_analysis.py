#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
    1、本脚本用于

"""
import datetime
import os
import paramiko
import json


def dbproxy_errorlog(filename):
    # date = datetime.datetime.now().strftime('%Y-%m-%d')
    date = '2020-08-28'
    filter_list = ['errorCode=4000', 'errorCode=3013', 'Connection timed out', 'program err']
    error_dict = {}
    # 判断日志是否当天有更新
    # mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filename)).strftime('%Y-%m-%d')
    mtime = '2020-08-28'
    if mtime == date:
        with open(filename, encoding='utf-8') as f:
            for line in f.read().split(date):
                if 'ERROR' in line and not any(code in line for code in filter_list):
                    error = line.split('\n')[1]
                    if ':' in error:
                        # 获取报错类型
                        error_type = error.split(':')[0]
                        # 如果字典中不存在该报错类型，就首先将它的值设置为一个空字典
                        x = error_dict.setdefault(error_type, {})
                        if x:
                            error_dict[error_type]["count"] += 1
                        else:
                            error_dict[error_type]["count"] = 1
                            error_dict[error_type]["example"] = date + line

    return error_dict


def ctgcache_errorlog(filename):
    date = '[' + datetime.datetime.now().strftime('%y%m%d')
    f = open(filename, encoding='utf-8')
    _, line = f.read().split(date, 1)
    f.close()
    line = date + line
    for i in line.split(date):
        if 'WARN' in i or 'ERROR' in i:
            print(date + i)


def ctgmq_errorlog(filename):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    f = open(filename, encoding='utf-8')
    _, line = f.read().split(date, 1)
    f.close()
    line = date + line
    for i in line.split(date):
        if 'WARN' in i or 'ERROR' in i:
            print(date + i)


def udal(base_dir):
    udal_dict = {}
    for dir in os.listdir(base_dir):
        if dir.startswith('dbproxy') and os.path.isdir(os.path.join(base_dir, dir)):
            log_file = os.path.join(base_dir, dir, 'logs/dbproxy.log')
            error_dict = dbproxy_errorlog(log_file)
            udal_dict[dir] = error_dict
    return udal_dict


def paramiko_ssh(ip_lists):
    result = {}
    for ip in ip_lists:
        # 实例化SSHClient
        client = paramiko.SSHClient()

        # 自动添加策略，保存服务器的主机名和密钥信息，如果不添加，那么不再本地know_hosts文件中记录的主机将无法连接
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # 连接SSH服务端，以用户名和密码进行认证
        client.connect(hostname=ip, port=22, username='root', password='123456')

        result[ip] = udal('/app/udal')

        # 关闭SSHClient
        client.close()
    print(json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == '__main__':
    # python2使用
    # reload(sys)
    # sys.setdefaultencoding("utf8")
    work_dir = '/home/pto'
    os.chdir(work_dir)
    paramiko_ssh(['192.168.15.150', '192.168.15.151'])
