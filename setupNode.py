
import asyncio # 异步操作库
import sys
import signal

from myAttackNode import AttackNode
from myNode import Node
from myPBFTNode import PBFTNode

# 这是一个python函数，用于设置和启动一个节点。
# 该节点可以连接到一个或多个对等节点，并使用Proof of Work（PoW）或Proof of Stake（PoS）算法运行。
def setupNode(local_addr, peer_addr, mode):
    # local_addr: 节点的本地IP地址和端口号。
    # peer_addr: 与之连接的对等节点的IP地址和端口号。
    # mode: 节点的模式选择，可以是“double”，“pow”或“pos”中的一个，
    # 分别表示同时使用PoW和PoS，仅使用PoW或仅使用PoS。
    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, loop.stop) # 新建循环对象，在接受到sigint再结束

    #将节点node与IP,port 绑定在一起
    f = loop.create_datagram_endpoint(Node, local_addr=local_addr)
    _, node = loop.run_until_complete(f)


    node.setLocalAddr(local_addr)

    # print("MyId: ", node.ID)

    if mode == "double":
        loop.run_until_complete(node.join(peer_addr,getMoney=False))
        loop.create_task(node.startPOW())
    else:
        loop.run_until_complete(node.join(peer_addr, getMoney=True))

    # create_task() 是 asyncio 库中的一个函数，用于在事件循环中创建一个协程任务（coroutine task）。
    # 它会将给定的协程对象封装成一个任务对象，然后自动将任务提交到事件循环中运行。
    # 当协程执行完毕或遇到阻塞时，事件循环会暂停该任务，切换到其他可运行的任务，直至该任务再次被唤醒。
    # create_task() 函数返回所创建的任务对象，可以用于取消该任务或获取其执行结果等操作。
    if mode == "pow":
        loop.create_task(node.startPOW())
    elif mode == "pos":
        loop.create_task(node.startPOS())

    loop.create_task(node.nodeCommand())

    loop.create_task(node.fileCommand())

    loop.run_forever()


def setupBGPNode(local_addr, peer_addr, mode):

    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, loop.stop)

    #将节点node与IP,port 绑定在一起
    f = loop.create_datagram_endpoint(Node, local_addr=local_addr)
    _, node = loop.run_until_complete(f)


    node.setLocalAddr(local_addr)


    loop.run_until_complete(node.BGPjoin())

    #
    # if mode == "pow":
    #     loop.create_task(node.startPOW())
    # elif mode == "pos":
    #     loop.create_task(node.startPOS())

    loop.create_task(node.nodeCommand())

    loop.create_task(node.fileCommand())

    loop.run_forever()


def setupDoubleAttackNode(local_addr, peer_addr, attack_num):

    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, loop.stop)

    #将节点node与IP,port 绑定在一起
    f = loop.create_datagram_endpoint(AttackNode, local_addr=local_addr)
    _, node = loop.run_until_complete(f)


    node.setLocalAddr(local_addr)
    node.sethackers(attack_num)


    loop.run_until_complete(node.join(peer_addr))


    loop.create_task(node.startPOW())


    loop.create_task(node.nodeCommand())

    loop.create_task(node.fileCommand())

    loop.run_forever()


def setupPBFTNode(local_addr, peer_addr, peer_num):

    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, loop.stop)

    #将节点node与IP,port 绑定在一起
    f = loop.create_datagram_endpoint(PBFTNode, local_addr=local_addr)
    _, node = loop.run_until_complete(f)


    node.setLocalAddr(local_addr)
    node.setPeer_num(peer_num)

    loop.run_until_complete(node.join(peer_addr,getMoney=True))


    loop.create_task(node.nodeCommand())

    loop.create_task(node.fileCommand())

    loop.run_forever()

if __name__ == '__main__':

    if sys.argv[6] == "BGP" :
        setupBGPNode(
            local_addr=(sys.argv[1], int(sys.argv[2])),
            peer_addr=(sys.argv[3], int(sys.argv[4])),
            mode=(sys.argv[5])
        )
    elif sys.argv[6] == "double" :
        setupDoubleAttackNode(
            local_addr=(sys.argv[1], int(sys.argv[2])),
            peer_addr=(sys.argv[3], int(sys.argv[4])),
            attack_num=int(sys.argv[5])
        )
    elif sys.argv[5] == "PBFT" :
        setupPBFTNode(
            local_addr=(sys.argv[1], int(sys.argv[2])),
            peer_addr=(sys.argv[3], int(sys.argv[4])),
            peer_num=int(sys.argv[6])
        )
    else:
        setupNode(
            local_addr=(sys.argv[1], int(sys.argv[2])),
            peer_addr=(sys.argv[3], int(sys.argv[4])),
            mode  = (sys.argv[5])
        )