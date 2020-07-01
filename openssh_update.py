#!/usr/bin/env python3
# coding=utf-8
import os
import subprocess

'''
1、确保有python3
2、执行机器上需要上传升级安装包和升级脚本
'''


# 检查版本
def check_version():
    version = subprocess.getoutput('ssh -V')
    if '8.2' in version:
        print('当前Openssl版本已经是最新了，无需升级！\n')
        exit(0)
    print('当前Openssl、Openssh软件版本为:\n' + subprocess.getoutput('ssh -V') + '\n')


# 日志实时输出
def log_output(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    while process.poll() is None:
        out = process.stdout.readline().strip()
        if out:
            print(out)


# 安装依赖包
def install_libs():
    print('开始安装相关依赖包...\n')
    cmd = 'yum install -y gcc pam.x86_64 pam-devel.x86_64 krb5-devel.x86_64 pam_krb5.x86_64 krb5-server.x86_64 ' \
          'krb5-libs.x86_64 perl.x86_64 systemd-devel'
    try:
        log_output(cmd)
        print('\n相关依赖包安装完成！\n')
    except subprocess.CalledProcessError as e:
        print('安装出错:\n' + e.stderr)


# 备份旧文件
def backup_old_documents():
    print('开始备份旧文件...\n')
    if os.path.exists('/root/update_ssh/bak'):
        print('已存在备份文件\n')
        return
    cmds = ['mkdir -p /root/update_ssh/bak', 'cp -rp /etc/ssh /root/update_ssh/bak/etc_ssh',
            'cp -rp /etc/ssl /root/update_ssh/bak/etc_ssl', 'cp -rp /etc/pki /root/update_ssh/bak/etc_pki',
            'cp -rp /usr/bin/ssh /root/update_ssh/bak/usr_ssh ', 'cp -rp /etc/pam.d /root/update_ssh/bak/etc_pam.d']
    try:
        for i in cmds:
            subprocess.run(i, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           check=True)
        print('备份完成，备份目录为 /root/update_ssh/bak\n')
    except subprocess.CalledProcessError as e:
        print('错误:\n' + e.stderr)


# 解压安装包
def decompression(dir_name):
    lists = os.listdir(dir_name)
    package_name = 'openssh_update8.2.tar'
    if package_name not in lists:
        print('安装包 %s 未上传，请将安装包上传到 /root 目录下再执行安装脚本\n' % package_name)
        exit(0)
    cmd = 'tar -xvf ' + package_name
    print('解压安装包 %s \n' % package_name)
    subprocess.getoutput(cmd)
    print('解压成功！\n')


# 安装dropbear
def install_dropbear(install_dir, dropbear_name):
    os.chdir(install_dir)
    retcode, output = subprocess.getstatusoutput('netstat -wnlpt | grep :5333')
    print('检查5333端口是否占用...\n')
    if retcode == 0:
        print('端口5333已被占用:\n')
        print(output)
        return
    print('5333端口未被占用\n')
    print('开始解压dropbear安装包...\n')
    cmd1 = 'tar -xvf %s -C /usr/local' % dropbear_name
    cmd2 = '/usr/local/dropbear/dropbear_server.sh start'
    print('开始安装dropbear\n')
    subprocess.getoutput(cmd1)
    subprocess.getoutput(cmd2)
    pid = subprocess.getoutput("ps aux | grep dropbear | grep -v grep | awk '{print$2}'")
    print('dropbear安装完成！服务已启动， pid为%s\n' % pid)


# 安装zlib
def install_zlib(install_dir, zlib_name):
    os.chdir(install_dir)
    print('开始解压zlib安装包...\n')
    subprocess.getoutput('tar -xvf %s' % zlib_name)
    os.chdir(os.path.join(install_dir, 'zlib-1.2.11'))
    print('开始安装zlib...\n')
    cmds = ['./configure --prefix=/usr && make -j20 && make install', 'ldconfig -v']
    for cmd in cmds:
        log_output(cmd)
    print('\nzlib安装完成!\n')


# 安装openssl
def install_openssl(install_dir, openssl_name):
    os.chdir(install_dir)
    print('开始解压openssl安装包...\n')
    subprocess.getoutput('tar -xvf %s' % openssl_name)
    os.chdir(os.path.join(install_dir, 'openssl-1.0.2u'))
    cmds = ["./config --prefix=/usr --openssldir=/etc/pki/tls shared zlib",
            "make -j20 && make MANDIR=/usr/share/man install",
            "ldconfig -v"]
    for cmd in cmds:
        log_output(cmd)
    print('\nopenssl安装完成!\n')
    print('openssl版本:\n' + subprocess.getoutput('openssl version -a') + '\n')


# 安装openssh
def install_openssh(install_dir, openssh_name):
    os.chdir(install_dir)
    print('开始解压openssh安装包...\n')
    subprocess.getoutput('tar -xvf %s' % openssh_name)
    os.chdir(os.path.join(install_dir, 'openssh-8.2p1'))
    cmds = ["LIBS='-lsystemd' ./configure --prefix=/usr --sysconfdir=/etc/ssh --with-ssl-dir=/etc/pki/tls "
            "--mandir=/usr/share/man --with-zlib --with-pam --with-md5-passwords --with-kerberos5",
            "chmod 600 /etc/ssh/ssh_host_rsa_key",
            "chmod 600 /etc/ssh/ssh_host_ecdsa_key",
            "chmod 600 /etc/ssh/ssh_host_ed25519_key",
            "make -j20 && make install"]
    log_output(cmds[0])
    subprocess.getoutput(cmds[1])
    subprocess.getoutput(cmds[2])
    subprocess.getoutput(cmds[3])
    log_output(cmds[4])
    print('\nopenssh安装完成!\n')
    subprocess.getoutput('/usr/local/dropbear/dropbear_server.sh stop')


# 修改sshd_config文件
def sshd_config():
    text = '\nKexAlgorithms curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,' \
           'diffie-hellman-group14-sha1\n'
    file = '/etc/ssh/sshd_config'
    with open(file, 'a') as f:
        f.write(text)


# 重启sshd服务并验证
def restart_sshd():
    subprocess.getoutput('systemctl restart sshd')


# 安装程序包
def install(base_dir):
    check_version()
    install_libs()
    backup_old_documents()
    decompression(base_dir)
    install_dir = base_dir + 'openssh_update8.2/'
    dirlist = []
    for dir_name in os.listdir(install_dir):
        if dir_name.endswith('.tar'):
            dirlist.append(dir_name)
    dropbear_name, openssh_name, openssl_name, zlib_name = dirlist
    install_dropbear(install_dir, dropbear_name)
    install_zlib(install_dir, zlib_name)
    install_openssl(install_dir, openssl_name)
    install_openssh(install_dir, openssh_name)
    sshd_config()
    restart_sshd()
    print('openssh服务升级完成！！')


# 主程序
def main():
    basedir = '/root/'
    install(basedir)


if __name__ == '__main__':
    main()
