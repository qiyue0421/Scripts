#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
    1、本脚本用于收集udal服务器的错误sql
    2、以json格式输出
"""

"""
bug修复：
1、2020/09/15 v2.3版本，修复错误语句切割bug
2、2020/09/15 v2.4版本，修复sql语句中出现不属于增删查改等类型
3、2020/09/15 v2.5版本，修复error_type参数的切割语法，保留 'syntax error'字样
4、2020/10/10 v2.6版本，修复日志不存在报错的bug
5、2020/10/12 v2.7版本，修复报错类型关键字parse err不存在时导致索引超出范围异常
6、2020/10/20 v3.0版本，重写过滤规则及信息采集模块，运用正则表达式进行匹配
7、2020/10/27 v3.1版本，服务器pto用户密码修改
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


# 扩展一个JSONEncoder出来用来格式化set类型
class CJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def dbproxy_errorlog(filename):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    filter_list = ['Connection timed out', 'program err', 'INFORMATION_SCHEMA']
    key_list = ['ERROR', 'syntax error', 'Connection=ServerConnection']
    sql_list = ['select', 'update', 'insert', 'delete', 'SELECT', 'UPDATE', 'INSERT', 'DELETE']
    error_dict = {}
    with open(filename, encoding='utf-8') as file:
        for line in file.read().split(date):
            line = date + line
            if not any(code in line for code in filter_list) and all(i in line for i in key_list):
                sql_expr = re.compile(r'sql=(.*)\njava', re.S)
                sql = re.findall(sql_expr, line)[0].replace('\n', '').replace('\t', '')
                sql = re.sub(' +', ' ', sql)

                if any(s in sql for s in sql_list):
                    error_msg_expr = re.compile(r'syntax error, (.*)\n')
                    error_msg = re.findall(error_msg_expr, line)[0]

                    client_expr = re.compile(r"\[(.*?)\]")
                    client_info = re.findall(client_expr, line)[1]
                    client_info_list = client_info.split(',')
                    client_addr = client_info_list[1].split('=')[1].split(':')[0]
                    user = client_info_list[2].split('=')[1]
                    schema = client_info_list[5].split('=')[1]

                    time_expr = re.compile(r'^(.*?)\.')
                    appear_time = re.findall(time_expr, line)[0]

                    x = error_dict.setdefault(error_msg, {})
                    if x:
                        error_dict[error_msg]['count'] += 1
                    else:
                        error_dict[error_msg]['count'] = 1
                        error_dict[error_msg]['sql'] = sql
                        error_dict[error_msg]['user'] = user
                        error_dict[error_msg]['schema'] = schema
                        error_dict[error_msg]['client_addr'] = set()
                    error_dict[error_msg]['last_appear_time'] = appear_time
                    error_dict[error_msg]['client_addr'].add(client_addr)
    return error_dict
    # print(json.dumps(error_dict, indent=4, cls=CJsonEncoder))


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
                if os.path.exists(log_file):
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
        f.write(json.dumps(result, indent=4, ensure_ascii=False, cls=CJsonEncoder))
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
    ip_lists = ['10.25.1.103', '10.25.1.104', '10.25.1.105', '10.25.1.106', '10.25.1.107', '10.25.1.108', '10.25.1.109', '10.25.1.110',
                '10.25.1.111', '10.25.1.112', '10.25.1.113', '10.25.1.114', '10.26.1.103', '10.26.1.104', '10.26.1.105', '10.26.1.106']
    access_dict = {'ssh_port': 2236, 'ssh_user': 'pto', 'ssh_password': 'CO1-db-2020#!'}
    result = {}
    cmd = 'cat %s' % os.path.join(work_dir, 'errorsql.log')
    for ip in ip_lists:
        access_dict['ssh_ip'] = ip
        if ssh_server(access_dict, cmd):
            if '10.26' in ip:
                access_dict['ssh_password'] = 'CO3-db-2020#!'
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
                        result[key][k]['client_addr'] = sql_dict[key][k]['client_addr']
                        result[key][k]['user'] = sql_dict[key][k]['user']
                        result[key][k]['schema'] = sql_dict[key][k]['schema']
                        result[key][k]['last_appear_time'] = sql_dict[key][k]['last_appear_time']
    log_name = os.path.join(work_dir, 'errorsql_all.log')
    with open(log_name, 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, indent=4, ensure_ascii=False, cls=CJsonEncoder))


if __name__ == '__main__':
    work_dir = '/home/pto'
    os.chdir(work_dir)
    if len(sys.argv) != 2:
        print('本脚本用于收集udal服务器的错误sql')
        print('使用方法：errorlog [arg]')
        print('参数说明：self——在本地机器收集错误sql  all——收集所有udal机器上的错误sql并汇总  version——显示当前脚本版本号\n')
        print('添加定时任务如下：')
        print('agent服务器:   00 22  *   *   *  /home/pto/errorsql/errorsql self &')
        print('server服务器:  30 23  *   *   *  /home/pto/errorsql/errorsql all &')
    elif sys.argv[1] == 'self':
        main()
    elif sys.argv[1] == 'all':
        paramiko_ssh(work_dir)
    elif sys.argv[1] == 'version':
        print('当前版本为v3.1 2020/10/27')
