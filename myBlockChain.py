# -*- coding: utf-8 -*-
import asyncio
import hashlib
import json
from time import time
from utils import *
from collections import defaultdict


class BlockChain(object):
    def __init__(self,ID):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.set_node_id(ID)
        self.stop = False;
        # self.logger = None

    def set_node_id(self, node_id):
        self.node_id = node_id

    # def set_logger(self, logger):
    #     self.logger = logger

    def create_genesis_block(self):
        # Create the genesis block
        self.new_block(previous_hash=1, proof=100)

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        # parsed_url = urlparse(address)
        self.nodes.add(address)

    # 参数中 previous hash是一个可选的，可以不传
    def new_block(self, proof, previous_hash=None):
        """
        生成新块
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """
        
        #如果当前区块链中没有任何区块，则创建一个创世区块并添加到区块链中。

        if len(self.chain) == 0:
            id = random_id()

            self.current_transactions.append({
                'id': id,
                'sender': 0,
                'recipient': self.node_id,
                'amount': 999,
            })

        valid_transactions, invalid_transactions = self.check_transactions()

        # self.logger.info('valid_transactions')
        # self.logger.info(valid_transactions)
        # self.logger.info('invalid_transactions')
        # self.logger.info(invalid_transactions)

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': valid_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'minerID': self.node_id,
            'minerAmount': self.current_transactions[-1]['amount'],
        }

        # Reset the current list of transactions

        self.current_transactions = [tx for tx in invalid_transactions]

        self.chain.append(block)
        return block

    def new_hackblock(self, proof, node_id, amount, previous_hash=None):
        """
        生成双花新块
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        valid_transactions, invalid_transactions = self.check_transactions()

        id = random_id()
        valid_transactions.append({
            'id': id,
            'sender': node_id,
            'recipient': -1,
            'amount': amount,
        })

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': valid_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'minerID': self.node_id,
            'minerAmount': self.current_transactions[-1]['amount'],
        }

        print(node_id, " withdraw ", amount, " money from bank!")


        return block


    def new_transaction(self, sender, recipient, amount):
        """
        生成新交易信息，信息将加入到下一个待挖的区块中
        :param sender: <int> Address of the Sender
        :param recipient: <int> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """

        id = random_id()

        self.current_transactions.append({
            'id' : id,
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        # Hashes a Block
        """
        生成块的 SHA-256 hash值
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # Returns the last Block in the chain
        return self.chain[-1]

    # 调用来自 myNode.mine()
    @asyncio.coroutine
    def proof_of_work(self, last_proof):
        """
        简单的工作量证明:
         - 查找一个 p' 使得 hash(pp') 以6个0开头
         - p 是上一个块的证明,  p' 是当前的证明
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        count= 0
        shares=[]
        while self.valid_proof(last_proof, proof) is False:
            tmp = random.randint(1,3)
            ### print(proof)
            ### 加入之前判断此share是否存在
            ###  sharesList集需要足够多的元素,这里先定为15个
            if (len(shares) >= 15):
                return shares
            if(proof[:4] == "0000"):
                if(proof in share is False):
                    share+=1
                    shares.append(proof)
            proof += tmp
            count+=1
            # proof 相当于nonce 用hash方法得到一个hash值
            if count==5:
                yield from asyncio.sleep(1)
                count=0
            if self.stop == True:
                break;

        return proof

    def pos(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    # from proof_of_work
    @staticmethod
    def valid_proof(last_proof, proof):
        """
        验证证明: 是否hash(last_proof, proof)以6个0开头?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess_str = '%s%s' % (last_proof, proof)
        guess = guess_str.encode()

        # guess = f'{last_proof}{proof}'.encode()

        guess_hash = hashlib.sha256(guess).hexdigest()
        # 设置一个相对简单的hash难度，只要满足这个难度的都视为一个share
        # 挖出了足够的share将被打包成一个batch
        # if(guess_hash[:6] == "000000"):
        #     return "proof"
        # elif(guess_hash[:4] == "0000"): # 这里的share先定为4
        #     return "share"
        return guess_hash[:2] == "000000" # 这里是两个0

    # check if chain has fork
    def check_chain(self, chain):
        """
                    Determine if a given blockchain is valid
                    :param chain: <list> A blockchain
                    :return: <bool> True if valid, False if not
                    """
        # self.logger.info('in check_chain')

        last_block = chain[0]
        current_index = 1
        UTXO = defaultdict(int)
        tx_id_set = set()

        for tx in last_block['transactions']:
            UTXO[str(tx['sender'])] -= int(tx['amount'])
            UTXO[str(tx['recipient'])] += int(tx['amount'])

            if str(tx['id']) not in tx_id_set:
                tx_id_set.add(str(tx['id']))
            else:
                return False

        while current_index < len(chain):
            block = chain[current_index]
            # print(last_block)
            # print(block)
            # print("\n-----------\n")
            # Check that the hash of the block is correct
            # check fork

            if block['previous_hash'] != self.hash(last_block):
                print("return false !!!!!")
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            for tx in block['transactions']:
                UTXO[str(tx['sender'])] -= int(tx['amount'])
                UTXO[str(tx['recipient'])] += int(tx['amount'])

                if str(tx['id']) not in tx_id_set:
                    tx_id_set.add(str(tx['id']))
                else:
                    return False

            last_block = block
            current_index += 1

        for id in UTXO:
            if id == '0':
                continue
            elif UTXO[id] < 0:
                return False

        return True



    def removeSomeTX(self,IDlist):
        print("before remove: ",len(self.current_transactions))
        tmp_TXs = []
        for tx in self.current_transactions:
            if tx['id'] not in IDlist:
                tmp_TXs.append(tx)
        self.current_transactions = tmp_TXs
        print("after remove: ", len(self.current_transactions))


    def getAllTX(self):
        txIds=[]
        for block in self.chain:
            for tx in block['transactions']:
                txIds.append(tx['id'])
        return txIds


    def get_all_tx(self):
        txs=[]
        for block in self.chain:
            for tx in block['transactions']:
                txs.append(tx)

        return txs

    # 检测交易是否有效
    def check_transactions(self):
        # self.logger.info('in check_transactions')
        valid_transactions = []
        invalid_transactions = []

        current_index = 0
        UTXO = defaultdict(int)

        while current_index < len(self.chain):
            block = self.chain[current_index]

            for tx in block['transactions']:
                UTXO[str(tx['sender'])] -= int(tx['amount'])
                UTXO[str(tx['recipient'])] += int(tx['amount'])

            current_index += 1

        # for id in UTXO:
        #     print(id,UTXO[id])

        for tx in self.current_transactions:
            # print('sender = ',str(tx['sender']))
            # print('amount = ',str(tx['amount']))
            if UTXO[str(tx['sender'])] - int(tx['amount']) < 0 and str(tx['sender']) != "0":
                invalid_transactions.append(tx)
            else:
                UTXO[str(tx['sender'])] -= int(tx['amount'])
                UTXO[str(tx['recipient'])] += int(tx['amount'])
                valid_transactions.append(tx)

        # valid_transactions=self.current_transactions
        # invalid_transactions=[]

        return valid_transactions, invalid_transactions