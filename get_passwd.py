"""
本脚本用于生成高强度8位密码
"""

import random
import string


passwds = []
count = input('请确认要生成几条密码： ')
slat = '!@#$%^&*'
while True:
    passwd = set(random.sample(string.ascii_letters + string.digits + slat, 8))
    if passwd.intersection(string.ascii_uppercase) and passwd.intersection(string.ascii_lowercase) and passwd.intersection(string.digits) and passwd.intersection(slat):
        passwds.append(''.join(passwd))
    if len(passwds) == int(count):
        break

for i in passwds:
    print(i)
