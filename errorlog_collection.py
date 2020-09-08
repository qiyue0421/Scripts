#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
    1、本脚本用于收集udal服务器的错误sql
    2、以json格式输出
"""
import datetime
import time
import os
import sys
import json
import re
import socket
import paramiko
from paramiko.ssh_exception import NoValidConnectionsError
import encodings.idna


def dbproxy_errorlog(filename):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    filter_list = ['errorCode=4000', 'errorCode=3013', 'Connection timed out', 'program err']
    key_list = ['ERROR', 'syntax error']
    error_dict = {}
    with open(filename, encoding='utf-8') as file:
        for line in file.read().split(date):
            if all(i in line for i in key_list) and not any(code in line for code in filter_list):
                # 切割出具体内容，去除换行符
                content = line.split('at com', 1)[0].split(')', 1)[1].strip().replace('\n', '')
                # 将多余的空格替换为一个空格
                content = re.sub(" +", ' ', content)
                error_type = content.split(':', 1)[1]
                sql = content.split(':', 1)[0]
                x = error_dict.setdefault(error_type, {})
                if x:
                    error_dict[error_type]['count'] += 1
                else:
                    error_dict[error_type]['count'] = 1
                    error_dict[error_type]['sql'] = sql
    return error_dict


def udal(base_dir):
    myip = get_host_ip()
    if str(myip).startswith('10.25'):
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
    else:
        dbproxy_map = {'8901': 'MSS-OA', '8904': 'MSS-F&T'}
    udal_dict = {}
    for dir_name in os.listdir(base_dir):
        if dir_name.startswith('dbproxy') and os.path.isdir(os.path.join(base_dir, dir_name)):
            port = dir_name.split('_')[2]
            # 通过端口号查看是否是实例
            if port in dbproxy_map.keys():
                log_file = os.path.join(base_dir, dir_name, 'logs/dbproxy.log')
                # 日志更新时间是否为当天
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(log_file)).strftime('%Y-%m-%d')
                if mtime == datetime.datetime.now().strftime('%Y-%m-%d'):
                    udal_dict[dbproxy_map[port]] = dbproxy_errorlog(log_file)
    return udal_dict


def get_host_ip():
    global s
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def main():
    start = time.time()
    result = udal('/app/udal')
    log_name = os.path.join(work_dir, 'errorsql.log')
    with open(log_name, 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, indent=4, ensure_ascii=False))
    end = time.time()
    print('错误日志巡查完成，执行时间为 %s，输出日志 %s' % (round(end - start, 2), log_name))


def ssh_server(access, cmd):
    global client
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=access['ssh_ip'], port=access['ssh_port'], username=access['ssh_user'], password=access['ssh_password'])
        stdin, stdout, stderr = client.exec_command(cmd)
        if stdout.channel.recv_exit_status() == 0:
            result = stdout.read()
            return json.loads(result)
    except NoValidConnectionsError as e:
        print(e)
    finally:
        client.close()


def paramiko_ssh(work_dir):
    ip_lists = []
    access_dict = {}
    result = {}
    cmd = 'cat %s' % os.path.join(work_dir, 'errorsql.log')
    for ip in ip_lists:
        access_dict['ssh_ip'] = ip
        if ssh_server(access_dict, cmd):
            sql_dict = ssh_server(access_dict, cmd)
            for key in sql_dict.keys():
                i = result.setdefault(key, {})
                if not i:
                    result[key] = {}
                for k in sql_dict[key].keys():
                    j = result[key].setdefault(k, {})
                    if j:
                        result[key][k]['count'] += sql_dict[key][k]['count']
                    else:
                        result[key][k]['count'] = sql_dict[key][k]['count']
                        result[key][k]['sql'] = sql_dict[key][k]['sql']
    log_name = os.path.join(work_dir, 'errorsql_all.log')
    with open(log_name, 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == '__main__':
    work_dir = '/home/pto'
    os.chdir(work_dir)
    try:
        if sys.argv[1] == 'self':
            main()
        elif sys.argv[1] == 'all':
            paramiko_ssh(work_dir)
        elif sys.argv[1] == 'version':
            print('当前版本为v2.1 2020/09/08')
    except IndexError as e:
        print('本脚本用于收集udal服务器的错误sql, 参数self:在本机收集udal, 参数all:收集所有udal机器上的错误日志并汇总, 参数version:显示当前脚本版本号')
        print('添加定时任务如下：')
        print('agent服务器:   00 22  *   *   *  /home/pto/errorsql/errorsql self &')
        print('server服务器:  30 23  *   *   *  /home/pto/errorsql/errorsql all &')
