#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
    1、本脚本用于收集所有udal服务器的错误sql
    2、多线程实现
    3、json格式输出
"""
import datetime
import os
import paramiko
import json
import threading


def dbproxy_errorlog(filename):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    # date = '2020-08-28'
    filter_list = ['errorCode=4000', 'errorCode=3013', 'Connection timed out', 'program err']
    key_list = ['ERROR', 'syntax error']
    error_dict = {}
    # 判断日志是否当天有更新
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filename)).strftime('%Y-%m-%d')
    # mtime = '2020-08-28'
    if mtime == date:
        with open(filename, encoding='utf-8') as f:
            for line in f.read().split(date):
                if all(i in line for i in key_list) and not any(code in line for code in filter_list):
                    content = line.split('at com')[0].split(')', 1)[1].strip()
                    sql = content.split('\n')[0]
                    error_type = content.split('\n')[1]
                    x = error_dict.setdefault(error_type, {})
                    if x:
                        error_dict[error_type]['count'] += 1
                    else:
                        error_dict[error_type]['count'] = 1
                        error_dict[error_type]['sql'] = sql
    return error_dict


def udal(base_dir, CO3_flag):
    if CO3_flag:
        dbproxy_map = {'8901': 'MSS-OA', '8904': 'MSS-F&T'}
    else:
        dbproxy_map = {
            '8901': 'OSSNET',
            '8903': 'OSS',
            '8905': 'AIOPS',
            '8907': 'PAAS',
            '8909': 'DCOOS',
            '8911': 'BSS-PUBLIC',
            '8913': 'BSS-COC',
            '8915': 'BSS-CRM',
            '8917': 'BSS-MCCM',
            '8919': 'BSS-BILLING',
            '8921': 'BSS-RBC',
            '8923': 'BSS-SETT',
            '8925': 'BSS-DIGCHANNEL',
            '8927': 'UCC'
        }
    udal_dict = {}
    for dir_name in os.listdir(base_dir):
        if dir_name.startswith('dbproxy') and os.path.isdir(os.path.join(base_dir, dir_name)):
            port = dir_name.split('_')[2]
            # 通过端口号查看是否是实例
            if port in dbproxy_map.keys():
                log_file = os.path.join(base_dir, dir_name, 'logs/dbproxy.log')
                udal_dict[dbproxy_map[port]] = dbproxy_errorlog(log_file)
    # 如果实例中心没有错误语句，则删除
    for k in udal_dict.keys():
        if udal_dict[k] == {}:
            del udal_dict[k]
    return udal_dict


def paramiko_ssh(ip):
    # 实例化SSHClient
    client = paramiko.SSHClient()

    # 自动添加策略，保存服务器的主机名和密钥信息，如果不添加，那么不再本地know_hosts文件中记录的主机将无法连接
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # 连接SSH服务端，以用户名和密码进行认证
    client.connect(hostname=ip, port=2236, username='pto', password='pto-2020#')

    udal_dir = '/app/udal'

    if ip.startswith('10.25'):
        result[ip] = udal(udal_dir, CO3_flag=False)
    else:
        result[ip] = udal(udal_dir, CO3_flag=True)
    # 关闭SSHClient
    client.close()


if __name__ == '__main__':
    work_dir = '/home/pto'
    os.chdir(work_dir)
    ip_lists = ['10.25.1.103', '10.25.1.104', '10.25.1.105', '10.25.1.106', '10.25.1.107', '10.25.1.108', '10.25.1.109', '10.25.1.110',
                '10.25.1.111', '10.25.1.112', '10.25.1.113', '10.25.1.114', '10.26.1.103', '10.26.1.104', '10.26.1.105', '10.26.1.106']
    # ip_lists = ['10.25.1.103', '10.26.1.103']
    thread_list = []
    # 限制最大线程数为
    threading_max = threading.BoundedSemaphore(8)
    result = {}
    for ip in ip_lists:
        threading_max.acquire()
        t = threading.Thread(target=paramiko_ssh, args=[ip])
        thread_list.append(t)

    for t in thread_list:
        t.setDaemon(True)
        t.start()
        print('%s 开启线程%s' % (datetime.datetime.now(), t.name))

    for t in thread_list:
        t.join()
    log_name = os.path.join(work_dir, 'errorsql.log')
    with open(log_name, encoding='utf-8') as f:
        f.write(json.dumps(result, indent=4, ensure_ascii=False))
    print('错误日志巡查完成，输出日志 %s' % log_name)
