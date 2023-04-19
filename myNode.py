from aioconsole import ainput

from myBlockChain import BlockChain
from myRPC import *;
from myRoutingTable import KadTable;

import logging  # 引入logging模块
import os.path
#from watchdog.events import *
import time
from batch import *

from myleger import Leger;

class Node(myRPCProtocol):

    def __init__(self, ID=None):

        super(Node, self).__init__()

        if ID is None: # 若没有ID 随机赋给一个
            ID = random_id()

        self.ID = ID #节点ID
        self.routingTable = KadTable(self.ID) # 路由表
        self.recallFunctions = self.recordFunctions()

        self.BroadCasts = []
        # self.leger = Leger(self.ID);

        self.blockchain = None
        self.local_addr = None
        self.wallet = 0
        self.heap=[]

        self.pos = 0


    def setLocalAddr(self,local_addr):
        self.local_addr = local_addr;
        self.initFileCMD()
        self.logger = self.init_logger()
        self.recordbaseInfo()


    def recordFunctions(self):
        funcs = []
        funcs.extend(myRPCProtocol.__dict__.values())
        funcs.extend(Node.__dict__.values())


        return {
            func.funcName: func.recall_function
            for func in funcs if hasattr(func, 'funcName')
        }


    @convert2RPC
    def ping(self,peer,peerID):
        print(self.ID, "handling ping", peer, peerID)
        return (self.ID, peerID)


    @convert2RPC
    def findNodes(self, peer, peerID):
        self.routingTable.add(peerID,peer);
        return self.routingTable.getKpeers(peerID);

    @convert2RPC
    def testBoradCast(self, peer, peerId, args):
        print("Recived boardCast message!!!!", peer, peerId, args)

    @convert2RPC
    def recordTX(self, peer, peerId, transaction):
        print("Recived new transaction!!!!", peer, peerId, transaction)
        if transaction['id'] not in [x['id'] for x in self.blockchain.current_transactions]:
            logging.info("Recived new transaction")
            self.blockchain.current_transactions.append(transaction);
            logging.info(self.blockchain.current_transactions)
            self.recordTXInfo()


    @convert2RPC
    def recordNewBlock(self, peer, peerId, newBlock):
        print("Recived new Block!!!!", peer, peerId, newBlock)
        logging.info("Recived new Block")
        self.blockchain.stop = True;
        self.pos = 0

        #TODO 判断新块是否有冲突, 有冲突从其他人拉去区块,否则直接更新
        tmp_chain = [x for x in self.blockchain.chain]
        tmp_chain.append(newBlock)
        if self.blockchain.check_chain(tmp_chain):
            self.blockchain.chain.append(newBlock);
        else:
            print("run resolve_conflicts()!!!")
            # loop = asyncio.get_event_loop();
            # loop.run_until_complete(self.resolve_conflicts())
            asyncio.ensure_future(self.resolve_conflicts())
            # self.resolve_conflicts()

        IDlist = self.blockchain.getAllTX()
        self.blockchain.removeSomeTX(IDlist)

        logging.info(self.blockchain.chain)
        self.recordBlockInfo()
        self.recordTXInfo()




    @convert2RPC
    def download_peer_blockchain(self, peer, peerID):
        # print(self.ID, "downloading blockchain from", peer, peerID)
        return self.blockchain

    @convert2RPC
    def getpos(self, peer, peerID):
        # print(self.ID, "downloading blockchain from", peer, peerID)
        return self.pos

    @convert2RPC
    def getwallet(self, peer, peerID):
        # print(self.ID, "downloading blockchain from", peer, peerID)
        return self.wallet


    @asyncio.coroutine
    def updateRoutingTable(self, peer):
        # self.routingTable.add(self.ID,self)
        peers = yield from self.findNodes(peer, self.ID)
        for peerID in peers.keys():
            self.routingTable.add(peerID, peers[peerID])

        # self.routingTable.printTable();

    @asyncio.coroutine
    def BGPjoin(self):

        # print(self.ID, "Pinging ", peer)
        print("myIP: ", self.local_addr, " myID: ", self.ID)
        try:
            yield from self.download_blockchain_all();
        except socket.timeout:
            print("Could not download blockchain", "BGPNode")
            return

        try:
            tx_id = self.create_transaction(self.blockchain, self.ID, self.ID,
                                            0)
            self.logger.info('init get transactinon from miner = ')
            self.logger.info(self.blockchain.current_transactions)
            self.recordTXInfo()
            yield from self.postBoardcast(random_id(), 'recordTX', self.ID,
                                          self.blockchain.current_transactions[-1]);
        except socket.timeout:
            print("Could not get money from node0", "BGPNode")
            return





    @asyncio.coroutine
    def join(self, peer, getMoney=True):

        # print(self.ID, "Pinging ", peer)
        print("myIP: ",self.local_addr," myID: ",self.ID)

        try:
            yield from self.ping(peer, self.ID)
        except socket.timeout:
            print("Could not ping %r", peer)
            return

        try:
            yield from self.updateRoutingTable(peer);
            # print("======================print my routing table============================")
            # self.routingTable.printTable();
        except socket.timeout:
            print("Could not updateRoutingTable", peer)
            return


        try:
            yield from self.download_blockchain_all();
        except socket.timeout:
            print("Could not download blockchain", peer)
            return

        #默认启动后找第一个人要钱
        if getMoney==True:
            try:
                tx_id = self.create_transaction(self.blockchain, self.routingTable.getPeerIDByIP(peer[0]), self.ID, random.randint(1,10))
                self.logger.info('init get transactinon from miner = ')
                self.logger.info(self.blockchain.current_transactions)
                self.recordTXInfo()
                yield from self.postBoardcast(random_id(), 'recordTX', self.ID, self.blockchain.current_transactions[-1]);
            except socket.timeout:
                print("Could not get money from node0", peer)
                return

    @asyncio.coroutine
    def getAllPOS(self):
        peers = self.routingTable.getNeighborhoods()

        all_pos = []

        for peerID, peer in peers.items():
            try:
                pos = yield from self.getpos(peers[peerID], self.ID)
                if pos != None:
                    all_pos.append(pos)
            except socket.timeout:
                print("Could not download_peer_blockchain", peers[peerID])

        return all_pos


    @asyncio.coroutine
    def download_blockchain_all(self):
        peers = self.routingTable.getNeighborhoods()

        if len(peers) == 0:
            # genesis block
            self.blockchain = BlockChain(self.ID)
            # self.blockchain.set_logger(self.logger)
            self.blockchain.create_genesis_block()
        else:
            for peerID, peer in peers.items():
                try:
                    receive_blockchain = yield from self.download_peer_blockchain(peers[peerID], self.ID)
                    self.logger.info('receive blockchain.chain = ')
                    self.logger.info(receive_blockchain.chain)
                    if self.blockchain == None:
                        self.blockchain = receive_blockchain
                        self.blockchain.set_node_id(self.ID)
                        # self.blockchain.set_logger(self.logger)
                    elif len(receive_blockchain.chain) > len(self.blockchain.chain):
                        self.blockchain = receive_blockchain
                        self.blockchain.set_node_id(self.ID)
                        # self.blockchain.set_logger(self.logger)

                except socket.timeout:
                    print("Could not download_peer_blockchain", peers[peerID])


        print('current blockchain = ', self.blockchain.chain)
        self.logger.info('blockchain.node_id = ' + str(self.blockchain.node_id))
        self.logger.info(self.blockchain.chain)
        self.recordBlockInfo()


    @asyncio.coroutine
    def resolve_conflicts(self):

        logging.info("In resolve conflicts!")
        print("In resolve conflicts!")

        peers = self.routingTable.getNeighborhoods()
        new_chain = None

        # We're only looking for chains longer than ours
        self_length = len(self.blockchain.chain)

        # Grab and verify the chains from all the nodes in our network
        for peerID, peer in peers.items():
            try:
                receive_blockchain = yield from self.download_peer_blockchain(peers[peerID], self.ID)
                chain = receive_blockchain.chain
                length = len(chain)

                # Check if the length is longer and the chain is valid
                # if the blockchain length is 2 block head current blockchain
                # TODO test receive blockchain length
                print(length," ",self_length,"  ",self.blockchain.check_chain(chain))
                if length - 1 > self_length and self.blockchain.check_chain(chain):
                    logging.info("block chain has been covered, len: "+ str(length)+ ". Probability: "+ str(1 / length))
                    print("block chain has been covered, len: ", length, ". Probability: ", str(1/length))
                    self_length = length
                    new_chain = chain
            except socket.timeout:
                print("Could not download_peer_blockchain in resolve_conflicts", peers[peerID])

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.blockchain.chain = new_chain
            self.blockchain.set_node_id(self.ID)
            self.logger.info('blockchain.node_id = ' + str(self.blockchain.node_id))
            self.logger.info(self.blockchain.chain)
            self.recordBlockInfo()

            IDlist = self.blockchain.getAllTX()
            self.blockchain.removeSomeTX(IDlist)
            self.recordTXInfo()
            return True

        return False

    # 调用from startPOW
    @asyncio.coroutine
    def mine(self):
        # We run the proof of work algorithm to get the next proof...
        last_block = self.blockchain.last_block
        last_proof = last_block['proof']
        # use proof of work

        res = yield from self.blockchain.proof_of_work(last_proof)
        ## 判断pow返回的类型，是list还是一个proof，即是shares还是挖出区块
        ## 判断batch合法性
        if len(res)>1:
            tree = build_complete_binary_tree_ex(res) # 生成batch
            ## 对batch进行验证 首先检查根，如果合格再进入路径检查
            root = tree[0]
            if(root[:4] == "0000"):
                treeNode = build_tree(tree)  # 转为树结构节点
                dfs(treeNode)  # 取路径摘要
                path = find_path(treeNode)  # 获得路径
                for i,item in enumerate(path): # 评估摘要路径的合法性
                    if i == len(path)-1:
                        if item[0][:4] == "0000":
                            continue;
                        else:
                            return "denied" # share被拒绝
                    if(item[0][:4] == "0000" and item[1]!=0):
                        continue;
                    else:
                        return "denied" # share被拒绝
                # 此处代表评估已通过，通过share的有效数量来给予激励
                if self.blockchain.stop == True:
                    return None;
                # 给工作量证明的节点提供奖励.
                # 发送者为 "0" 表明是新挖出的币
                # 这里的出块奖励是随机1~10
                self.blockchain.new_transaction(
                    sender="0",
                    recipient=self.ID,
                    amount=len(path)/10, #暂定为路径长度的10分之一
                )
                # 仅赋奖励 不出块
                # 这个response？
                response ={
                    'message': "Shares batch validation pass",
                    'transactions': block['transactions'],
                }
                return "receive" # share评估通过
            else:
                return "denied" # share被拒绝
        else:
            proof = res
            if self.blockchain.stop == True:
                return None;
            # 给工作量证明的节点提供奖励.
            # 发送者为 "0" 表明是新挖出的币
            # 这里的出块奖励是随机1~10
            self.blockchain.new_transaction(
                sender="0",
                recipient=self.ID,
                amount=random.randint(1, 10),
            )

            # from myBlockchain - new_block
            # Forge the new Block by adding it to the chain
            block = self.blockchain.new_block(proof)

            response = {
                'message': "New Block Forged",
                'index': block['index'],
                'transactions': block['transactions'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
            }
            return response




    @asyncio.coroutine
    def startPOW(self):
        while True:
            response = yield from self.mine() #一般在方法中嵌套使用，这个声明就相当于在第一层调用mine()一样
            if response!=None:
                if len(response)== 5 :
                    print(self.ID, ' has mined new block ')
                    self.logger.info('after mining, blockchain = ')
                    self.logger.info(self.blockchain.chain)
                    # broadcast new Blcokchain
                    self.recordBlockInfo()
                    self.recordTXInfo()
                    yield from self.postBoardcast(random_id(), 'recordNewBlock', self.ID, self.blockchain.chain[-1]);
                elif len(response)== 2 :
                    print(self.ID, ' submit a shares batch ')
                    self.logger.info(self.blockchain.chain)
            else:
                print('This new block has been mined by others')
                self.logger.info('This blockchain has been mined by others')
            #每当挖完矿或者别人挖到矿时,等待一段时间,等所有消息处理完毕 ?
            # yield from asyncio.sleep(30)
            yield from asyncio.sleep(5)
            self.blockchain.stop=False;


    def mine_quick(self):
        last_block = self.blockchain.last_block
        last_proof = last_block['proof']
        # use pos (very quick)
        proof = self.blockchain.pos(last_proof)

        # 给pos的节点提供奖励.
        # 发送者为 "0" 表明是新挖出的币
        self.blockchain.new_transaction(
            sender="0",
            recipient=self.ID,
            amount=random.randint(1, 10),
        )

        # Forge the new Block by adding it to the chain
        self.blockchain.new_block(proof)


    @asyncio.coroutine
    def startPOS(self):
        print("POS start !!!")
        while True:
            #没两分钟进行一次pos协议
            period = 120
            yield from asyncio.sleep(period)

            # TODO 暂时简化
            self.pos = random.randint(0,self.wallet)

            # 等待其他人计算pos值
            yield from asyncio.sleep(30)

            all_pos = yield from self.getAllPOS()
            leader = True
            for pos in all_pos:
                print(pos,"  ",self.pos)
                if pos>=self.pos:
                    leader=False

            if leader == True:
                print(self.ID, ' has mined new block ')

                self.mine_quick()

                self.logger.info('after mining, blockchain = ')
                self.logger.info(self.blockchain.chain)
                # broadcast new Blcokchain
                self.recordBlockInfo()
                self.recordTXInfo()
                yield from self.postBoardcast(random_id(), 'recordNewBlock', self.ID, self.blockchain.chain[-1]);
            else:
                print('This new block has been mined by others')
                self.logger.info('This blockchain has been mined by others')
            #每当挖完矿或者别人挖到矿时,等待一段时间,等所有消息处理完毕
            yield from asyncio.sleep(30)





    def create_transaction(self, blockchain, sender, recipient, amount):
        # Create a new Transaction
        # tx_index = blockchain.new_transaction(sender, recipient, amount)
        # return tx_index

        if sender != self.ID:
            tx_index = blockchain.new_transaction(sender, recipient, amount)
            return tx_index
        elif sender == self.ID and self.wallet - amount >= 0:
            tx_index = blockchain.new_transaction(sender, recipient, amount)
            return tx_index
        else:
            return -1


    def init_logger(self):
        # 第一步，创建一个logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)  # Log等级总开关
        # 第二步，创建一个handler，用于写入日志文件
        rq = time.strftime('%Y%m%d%H%M', time.localtime(time.time()))
        log_path = os.path.join(cur_path,'Logs',str(self.local_addr[0]))

        if not os.path.exists(log_path):
            os.mkdir(log_path)

        log_name = os.path.join(log_path, str(self.ID) + ".log")

        logfile = log_name
        fh = logging.FileHandler(logfile, mode='w')
        fh.setLevel(logging.DEBUG)  # 输出到file的log等级的开关
        # 第三步，定义handler的输出格式
        formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
        fh.setFormatter(formatter)
        # 第四步，将logger添加到handler里面
        logger.addHandler(fh)
        return logger

    def recordbaseInfo(self):
        log_path = os.path.join(cur_path, 'Logs', str(self.local_addr[0]))

        if not os.path.exists(log_path):
            os.mkdir(log_path)

        baseInfo = os.path.join(log_path, "baseInfo")
        with open(baseInfo,'w') as f:
            f.write(str(self.ID)+"\n")
            f.write(str(self.local_addr)+"\n")

    def recordTXInfo(self):
        log_path = os.path.join(cur_path, 'Logs', str(self.local_addr[0]))

        if not os.path.exists(log_path):
            os.mkdir(log_path)

        TXInfo = os.path.join(log_path, "TXInfo")
        save_data(self.blockchain.current_transactions,TXInfo)

    def update_wallet(self):
        # update wallet value
        txs = self.blockchain.get_all_tx()

        # self.logger.info('txs = ')
        # self.logger.info(txs)

        self.wallet = 0

        for tx in txs:
            if tx['sender'] ==self.ID:
                self.wallet -= tx['amount']
            if tx['recipient'] == self.ID:
                self.wallet += tx['amount']

    # serialize block and wallet
    def recordBlockInfo(self):
        log_path = os.path.join(cur_path, 'Logs', str(self.local_addr[0]))

        if not os.path.exists(log_path):
            os.mkdir(log_path)

        BlockInfo = os.path.join(log_path, "BlockInfo")
        save_data(self.blockchain.chain,BlockInfo)

        self.update_wallet()

        wallet_info = os.path.join(log_path, "wallet")
        save_data(self.wallet,wallet_info)



    def initFileCMD(self):
        path = os.path.join(cur_path,'CMD')

        with open(os.path.join(path,str(self.local_addr[0])), 'w') as f:
            f.close();




    @asyncio.coroutine
    def pingAll(self, peer, peerID):
        peers = self.routingTable.getNeighborhoods();
        for peerID, peer in peers.keys():
            try:
                yield from self.ping(peers[peerID], self.ID);
            except socket.timeout:
                print("pingAll timeout %r", peer)


    @asyncio.coroutine
    def postBoardcast(self, messageID, funcName, *args):
        if messageID not in self.BroadCasts:
            self.BroadCasts.append(messageID);

            obj = ('broadcast', messageID, funcName, *args)
            message = pickle.dumps(obj, protocol=0)

            peers = self.routingTable.getNeighborhoods();

            for peer in peers.values():
                try:
                    self.transport.sendto(message, peer)
                except socket.timeout:
                    print("transport sendto timeout %r", peer)




#收到的所有请求,更新路由表
    # 处理请求
    def handleRequest(self, peer, messageID, funcName, args, kwargs):
        peerID = args[0];
        self.routingTable.add(peerID,peer);
        super(Node, self).handleRequest(peer, messageID, funcName, args, kwargs);




    # 处理回复
    def handleReply(self, peer, messageID, response):
        peerID, response = response;
        self.routingTable.add(peerID,peer);
        super(Node, self).handleReply(peer, messageID, response);



    # 处理广播
    def handleBroadcast(self, peer, messageID, funcName, *args):
        peerID = args[0];
        self.routingTable.add(peerID, peer);

        if messageID not in self.BroadCasts:
            self.BroadCasts.append(messageID);
            self.postBoardcast(messageID, funcName, args);
            super(Node,self).handleBroadcast(peer, messageID, funcName, *args);

    # 处理超时
    def handletimeout(self, messageID, peer, args, kwargs):
        if messageID in self.requests:
            reply = self.requests.pop(messageID);
            reply.set_exception(socket.timeout);
            peerID = self.routingTable.getPeerIDByIP(peer[0]);
            print('remove peerID ',peerID)

            self.routingTable.remove(peerID);
            # super(Node, self).handletimeout( messageID,peer, args, kwargs);




#=================监听命令行=====================#
    async def nodeCommand(self):

        while True:
            line = await ainput(">>> ")
            line = line.strip()

            if not line:
                continue;


            await self.dealCMD(line)

# =================监听文件命令行=====================#

    async def fileCommand(self):
        while True:
            line = self.readFromFile()
            if line != None:
                line = line.strip()
                if len(line) > 0:
                    await self.dealCMD(line)
                    self.clearFileCMD()

            await asyncio.sleep(2)




    def printHelpList(self):
        print("==========this is a help list!==========")


    def printLog(self):
        path = os.path.join(cur_path,'Logs')
        with open(os.path.join(path, str(self.ID)+".log"), 'r') as f:
            lines = f.readlines()
            for line in lines:
                print(line)


    def clearFileCMD(self):
        path = os.path.join(cur_path,'CMD')
        with open(os.path.join(path, str(self.local_addr[0])), 'w') as f:
            f.close()

    def readFromFile(self):
        path = os.path.join(cur_path,'CMD')
        with open(os.path.join(path,str(self.local_addr[0])),'r') as f:
            lines = f.readlines();
            if len(lines)>0:
                return lines[0].strip();
            else:
                return None;

    async def dealCMD(self,line):
        line = line.split();

        cmd = line[0];
        args = line[1:];

        if cmd in ["?", "help"]:
            self.printHelpList();

        elif cmd in ["id"]:
            print("NodeId : ", self.ID);

        elif cmd in ["ip"]:
            print("<ip,port> ",self.local_addr)

        elif cmd in ["showHashTable"]:
            self.routingTable.printTable();

        elif cmd in ["showlog"]:
            self.printLog();

        elif cmd in ["ping"]:
            IP = args[0];
            peer = self.routingTable.getPeerByIP(IP)
            if peer != None:
                try:
                    await self.ping(peer, self.ID);
                except socket.timeout:
                    print("Could not ping %r", peer)
                    return
            else:
                print("peerIP : ", IP, " not exist!");

        elif cmd in ["testBoardCast"]:
            try:
                await self.postBoardcast(random_id(), 'testBoradCast', self.ID, "Testargs");
            except socket.timeout:
                print(self.ID, ": could not postBoardcast")
                return
        elif cmd in ["join"]:
            try:
                await self.join(("10.0.0.1",9000),getMoney=False)
                self.mine_quick()
                self.logger.info('after mining, blockchain = ')
                self.logger.info(self.blockchain.chain)
                self.recordBlockInfo()
                self.recordTXInfo()
                await self.postBoardcast(random_id(), 'recordNewBlock', self.ID, self.blockchain.chain[-1]);

            except socket.timeout:
                print(self.ID, ": could not join 10.0.0.1")
                return
        elif cmd in ["mine"]:
            self.mine_quick()
            # IDlist = [x.id for x in self.blockchain.chain[-1]['transactions']]
            # self.blockchain.removeSomeTX(IDlist)
            self.logger.info('after mining, blockchain = ')
            self.logger.info(self.blockchain.chain)
            # broadcast new Blcokchain
            self.recordBlockInfo()
            self.recordTXInfo()
            await self.postBoardcast(random_id(), 'recordNewBlock', self.ID, self.blockchain.chain[-1]);


        elif cmd in ["createTx"]:
            IP = args[0];
            amount = int(args[1])
            peerID = self.routingTable.getPeerIDByIP(IP)
            if peerID != None:
            # check for enough money
                tx_id = self.create_transaction(self.blockchain, self.ID, peerID, amount)
                if tx_id != -1:
                    self.logger.info('current transactinon = ')
                    self.logger.info(self.blockchain.current_transactions)
                    self.recordTXInfo()
                    await self.postBoardcast(random_id(), 'recordTX', self.ID, self.blockchain.current_transactions[-1]);
                else:
                    self.logger.info('could not create transaction, wallet < amount')
                    log_str=str(self.wallet)+' < '+str(amount)
                    self.logger.info(log_str)
            else:
                print("no such reciever! peerIP: ", IP)