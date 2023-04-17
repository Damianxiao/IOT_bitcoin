import logging
import os.path
#默认日志目录
from utils import cur_path

LOGDIR = "logs"
#默认日志等级
LOGLEVEL = logging.INFO

#=================================#

import os
import sys

#sys.path.append('/home/findns/Projects/mininet')

import traceback
from cmd import Cmd
from command import xtermCMD
import time

from mininet.net import Mininet
from mininet.link import Link
from mininet.cli import CLI
from mininet.node import ( UserSwitch, OVSSwitch, OVSBridge,
                           IVSSwitch,OVSKernelSwitch,OVSController,Host, CPULimitedHost,Controller,Ryu, NOX, )
from mininet.topo import ( SingleSwitchTopo, LinearTopo,
                           SingleSwitchReversedTopo,MinimalTopo )
from mininet.topolib import TreeTopo, TorusTopo
from myTopo import *
from mininet.nodelib import LinuxBridge
from mininet.util import *
import shutil

from mininet.link import TCLink

IP = "10.0.0.0/8"
PORT = 9000

# 定义字典
SWITCHES = { 'user': UserSwitch,
             'ovs': OVSSwitch,
             'ovsbr' : OVSBridge,
             'ovsk': OVSSwitch,
             'ivs': IVSSwitch,
             'lxbr': LinuxBridge,
             'default': OVSKernelSwitch }
TOPODEF = 'minimal'
TOPOS = { 'minimal': MinimalTopo,
          'linear': LinearTopo,
          'reversed': SingleSwitchReversedTopo,
          'single': SingleSwitchTopo,
          'tree': TreeTopo,
          'torus': TorusTopo }
HOSTDEF = 'proc'
HOSTS = { 'proc': Host,
          'rt': specialClass( CPULimitedHost, defaults=dict( sched='rt' ) ),
          'cfs': specialClass( CPULimitedHost, defaults=dict( sched='cfs' ) ) }

CONTROLLERDEF = 'default'
CONTROLLERS = { 'ref': Controller,
                'ovsc': OVSController,
                'nox': NOX,
                'ryu': Ryu, }

P2PNet=None
MODE = "pow"
# mininet 初始化
net = Mininet(topo=Topo,host=CPULimitedHost, link=TCLink,controller = OVSController)


def setMode(mode):
    global MODE;
    MODE = mode;

def setupP2PNet(arg1=1, arg2=3, netType="net", attack="none",attack_num=1):
    #  通过mininet 设置了一个P2P网络
    global P2PNet;

    # 网络结构 环形 、 net 、 star、tree
    if netType == "circle":
        print("circle");
        topo = circleTopo(arg1,arg2)
        # topo = buildTopo(TOPOS, "torus,3,3")
        switch = customClass(SWITCHES,"ovsbr,stp=1")
        P2PNet = Mininet(topo=topo,switch=switch, ipBase=IP,waitConnected=True);
    elif netType == "net":
        print("net");
        topo = netTopo(arg1)
        switch = customClass(SWITCHES, "ovsbr,stp=1")
        P2PNet = Mininet(topo=topo, switch=switch, ipBase=IP, waitConnected=True);
    else:
        if netType == "star":
            print("star");
            topo = starTopo(arg1)
        elif netType == "tree":
            print("tree");
            topo = treeTopo(arg1,arg2)
        elif netType == "netsimple":
            print("netSimple");
            topo = netsimpleTopo(arg1)
        else:
            print("netType error!");
            sys.exit(0);

        P2PNet = Mininet(topo=topo,link=TCLink,ipBase=IP,controller = OVSController);

    P2PNet.start();
    #限制带宽
    # P2PNet.iperf()

    # 迭代网络中所有主机 并打印
    for i, s in enumerate(P2PNet.switches):
        print(i,s.IP)

    #  如果有攻击模式，启用攻击方式
    for i, host in enumerate(P2PNet.hosts):
        print(i,host.IP)
        if(i>=0):
            print( host.cmd("ping -c1 10.0.0.1"))
        if attack=="BGP" and (i>= arg1-attack_num) :
            cmd = xtermCMD(host.IP(), PORT, P2PNet.hosts[0].IP(), PORT, MODE,nodeType="BGP")
        elif attack=="double" and (i< attack_num) :
            cmd = xtermCMD(host.IP(), PORT, P2PNet.hosts[0].IP(), PORT, str(attack_num),nodeType="double")
        elif attack == "double":
            cmd = xtermCMD(host.IP(), PORT, P2PNet.hosts[0].IP(), PORT, "double", nodeType="normal")
        elif MODE=="PBFT":
            cmd = xtermCMD(host.IP(), PORT, P2PNet.hosts[0].IP(), PORT, MODE, nodeType=str(arg1))
        else:
            cmd= xtermCMD(host.IP(), PORT, P2PNet.hosts[0].IP(), PORT, MODE)
        print(cmd)
        host.cmd(cmd % (i))
        time.sleep(1)

    path = os.path.join(cur_path, 'CMD')
    with open(os.path.join(path,"main"), 'w') as f:
        f.close()

def recordNodesInfo(attack="none",attack_num=0):
    path = os.path.join(cur_path, 'Logs')
    with open(os.path.join(path, "main"), 'w') as f:
        for i, host in enumerate(P2PNet.hosts):
            if attack=="BGP" and i>=len(P2PNet.hosts)-attack_num:
                f.write(str(host.IP()) + " " + host.name +" "+ "BGP\n")
            else:
                f.write(str(host.IP()) +" "+ host.name+"\n")

def readCommnadFromFile():
    path = os.path.join(cur_path, 'CMD')
    with open(os.path.join(path, "main"), 'r') as f:
        lines = f.readlines();
        if len(lines) > 0:
            return lines[0].strip();
        else:
            return None;

def clearFileCMD():
    path = os.path.join(cur_path,'CMD')
    with open(os.path.join(path, "main"), 'w') as f:
        f.close()

def fileCommand():
    while True:
        line = readCommnadFromFile()
        if line != None:
            line = line.strip()
            if len(line) > 0:
                line = line.split();
                cmd = line[0];
                args = line[1:];

                if cmd in ["recordNodesInfo"]:
                    recordNodesInfo()
                elif cmd in ["delNode"]:
                    hostName = args[0].strip()
                    node = None;
                    for host in P2PNet.hosts:
                        if host.name == hostName:
                            node = host;
                            break;
                    P2PNet.delNode(node);
                    recordNodesInfo()

                elif cmd in ["addNode"]:
                    id = len(P2PNet.hosts)

                    newHost = P2PNet.addHost("h%ds%d" % (id, id))

                    switch = P2PNet.switches[0];

                    P2PNet.addLink(switch, newHost);

                    slink = Link(switch, newHost)
                    switch.attach(slink);
                    switch.start(P2PNet.controllers);

                    newHost.configDefault(defaultRoute=newHost.defaultIntf())

                    print(P2PNet.hosts[0].cmd("ping -c1 %s" % newHost.IP()))  # important!!!

                    print(newHost.cmd("ping -c1 10.0.0.1"))

                    cmd = xtermCMD(newHost.IP(), PORT, P2PNet.hosts[0].IP(), PORT, MODE)

                    print(cmd)

                    newHost.cmd(cmd % (id))

                    print("Started new node: %s" % newHost)

                    recordNodesInfo()

                clearFileCMD()

        sleep(2)

#
#
class myCommand(Cmd):
    intro = "Control the bitcoin simulation network. Type help or ? to list commands.\n"
    prompt = ">>> "

    def do_EXIT(self):
        os.system("killall -SIGKILL xterm")
        os.system("mn --clean > /dev/null 2>&1")

    def do_ShowNodes(self, line):
        for i, host in enumerate(P2PNet.hosts):
            print(i, host.IP, host.name)

    # do_AddNode()方法用于向P2P网络中添加新的节点。
    # 它首先为新节点创建一个唯一的ID，然后使用addHost()方法将其添加到网络中。
    # 接下来，它使用addLink()方法将新节点连接到交换机，并使用attach()和start()方法启动交换机。
    # 最后，它使用configDefault()方法配置新节点的默认路由，并使用cmd()方法运行一个xterm命令，用于启动新节点。
    def do_AddNode(self, line):

        # len取主机数量长度
        id = len(P2PNet.hosts)
        # 新建一个主机，分配ID
        newHost = P2PNet.addHost("h%ds%d" % (id, id))
        # 交换机 switches是提前编辑的字典
        switch = P2PNet.switches[0]
        # 使节点连接到交换机
        P2PNet.addLink(switch, newHost)

        slink = Link(switch, newHost)
        switch.attach(slink)
        switch.start(P2PNet.controllers)

        newHost.configDefault(defaultRoute=newHost.defaultIntf())

        print(P2PNet.hosts[0].cmd("ping -c1 %s" % newHost.IP() ))       #important!!!

        print(newHost.cmd("ping -c1 10.0.0.1"))
        # 这个CMD用于启用新节点
        cmd = xtermCMD(newHost.IP(),PORT,P2PNet.hosts[0].IP(),PORT, MODE)

        print(cmd)

        newHost.cmd(cmd % (id))

        print("Started new node: %s" % newHost)

    def do_DelNode(self, line):
        args = line.split()
        if (len(args) != 1):
            print("Expected 1 argument, %d given" % len(args))
        else:
            hostName = args[0].strip()
            node = None;
            for host in P2PNet.hosts:
                if host.name == hostName:
                    node = host;
                    break;
            P2PNet.delNode(node);

    def do_Execute(self,line):
        args = line.split()
        if (len(args) <= 1):
            print("Expected two or more argument, %d given" % len(args))
        else:
            hostName = args[0].strip()
            node = None;
            for host in P2PNet.hosts:
                if host.name == hostName:
                    node = host;
                    break;
            if node !=None:
                path = os.path.join(cur_path,'CMD')
                with open(os.path.join(path, str(node.IP())), 'w') as f:
                    f.write(' '.join(args[2:]));
            else:
                print("no such host : ",hostName)

    def do_CLI(self,Line):
        CLI(P2PNet)


def delete_log():
    log_path = os.path.join(cur_path,'Logs')
    shutil.rmtree(log_path)
    if not os.path.exists(log_path):
        os.mkdir(log_path)

def deleteCMD():

    CMDpath = os.path.join(cur_path,'CMD')
    shutil.rmtree(CMDpath)
    if not os.path.exists(CMDpath):
        os.mkdir(CMDpath)


if __name__ == '__main__':

    try:
        # 每次启动都删除日志和CMD文件
        delete_log()
        deleteCMD()
        # setupP2PNet(5,1,netType='star',attack="double", attack_num=1);
        setMode(MODE)
        # 初始化P2P网络
        setupP2PNet(5,1,netType='star')
        myCommand().cmdloop()
    except SystemExit:
        pass
    except:
        traceback.print_exc()
        traceback.print_stack()

        os.system("killall -SIGKILL xterm")
        os.system("mn --clean > /dev/null 2>&1")

