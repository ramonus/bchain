import hashlib, json, time, uuid, datetime, copy, requests, random
from wallet_utils import *
from chain_utils import *
from transaction_utils import *
from utils import *
from ecdsa.keys import BadSignatureError
import threading, requests
from urllib.parse import urlparse

"""
Decorators
"""

def save_time(t):
    with open("mine_times.log","a") as f:
        f.write(str(t)+"\n")

def _mcontroller(func):
    def mine_controller(self):
        print("STARTING MINE")
        st = time.time()
        self.mining = True
        nb = func(self)
        self.mining = False
        et = time.time()-st
        print("ENDING MINE - {:.2f}s".format(et))
        save_time(et)
        return nb
    return mine_controller

class Blockchain:
    
    BLOCK_SIZE = 10

    def __init__(self, uid, port=5000):
        self.port = port
        self.node_uid = uid
        self.chain = load_chain()
        self.current_transactions = load_transactions()
        self.wallet = get_wallet()
        self.nodes = load_data("nodes.json")
        self.chain_transaction_hashes = set()
        self.resolving_chains = False
        self.resolving_transactions = False
        self.mining = False
        # Creates the genesis block
        if len(self.chain)==0:
            self.update_chain(self.create_genesis_block())

    def new_block(self, n, timestamp, tokens, previous_hash, previous_pow=None):
        """
        Create a new Block in the Blockchain

        :param n: <int> Number of block
        :param timestamp: <float> Timestamp of the block creation
        :param tokens: <list> Tokens
        :param previous_hash: <str> String representation of the hash of the previous block
        :param previous_pow: <int> Power of Work of the previous block
        :return: <dict> New Block
        """

        # Create the reward transaction for the miner
        t = self.create_reward_transaction(self.wallet)

        # Create a copy of the tokens and append the reward transaction
        tokens = tokens.copy()
        tokens.append(t)

        # Check the tokens/transactions
        state = self.is_valid_chain()
        for t in tokens:
            if self.is_valid_transaction(state,t):
                state = self.update_state(state, t)
            else:
                raise Exception("Error creating block, invalid transactions found")
        # Correct the timestamp
        if isinstance(timestamp, datetime.datetime):
            timestamp = timestamp.isoformat()

        # Create the block dict
        print("Calculing pow")
        block = {
            'block_n': n,
            'timestamp': timestamp,
            'token_n': len(tokens),
            'tokens': tokens,
            'miner': self.wallet['address'],
            'previous_hash': previous_hash,
            'pow': 9 if previous_pow is None else self.next_pow(previous_pow, previous_hash),
        }
        print("pow calculed")

        # Add the hash to the block
        block['hash'] = self.hash_block(block)

        return block

    def create_genesis_block(self):
        """
        Creates a genesis block for starting a chain
        """
        return self.new_block(0, datetime.datetime.now(), [], "0")

    def create_next_block(self, tokens):
        """
        Create the next block taking the current chain and a given token list

        :param tokens: <list> List of tokens
        """

        # Get the last block, it's hash and block_n
        last_block = self.last_block
        last_block_hash = self.hash_block(last_block)
        n = last_block['block_n']

        return self.new_block(n+1, datetime.datetime.now(), tokens, last_block_hash, last_block['pow'])

    def update_chain(self, block):
        """
        Adds a new block to the chain

        :param block: <dict> Block to add.
        """
        if (len(self.chain)==0 and self.is_genesis_block(block)) or self.is_valid_next_block(self.last_block, block):
            self.chain.append(block)
            save_chain(self.chain)
            self.clean_transactions()
            threading.Thread(target=self.spread_block,args=(self.nodes, block, self.port)).start()

            return True
        else:
            return False
    
    def update_transactions(self,transactions):
        r = []
        for t in transactions:
            r.append(self.update_transaction(t))
        return r

    def update_transaction(self, transaction):
        """
        Adds a new transaction to the transaction pool.

        :param transaction: <dict> Transaction to add.
        :return: <bool> True if the transaction was successfully added.
        """
        hashes = [t['hash'] for t in self.current_transactions]
        if transaction['hash'] not in hashes and transaction['hash'] not in self.get_transaction_hashes():
            self.current_transactions.append(transaction)
            save_transactions(self.current_transactions)
            threading.Thread(target=self.spread_transaction,args=(self.nodes,transaction,)).start()
            return True
        else:
            return False
    @staticmethod
    def is_genesis_block(block):
        return block['block_n']==0 and len(block['tokens'])==1 and block['previous_hash'] == "0" and block['pow'] == 9
    @staticmethod
    def spread_transaction(nodes, transaction):
        print("="*50)
        print("Starting transaction: {} spread.".format(transaction['hash']))
        for node in nodes:
            print("Sending transaction to:",node)
            data = json.dumps(transaction, sort_keys=True)
            r = requests.post(node+"/transactions/add", data=data)
            print("status:",r.status_code)
        print("End transaction spread")
        print("="*50)
    
    @staticmethod
    def spread_block(nodes,block,port=5000):
        print("="*50)
        print("Starting block {} spreading.".format(block['block_n']))
        for node in nodes:
            print("Sending block to",node)
            data = json.dumps(block, sort_keys=True)
            headers = {"port":str(port)}
            r = requests.post(node+"/chain/add",headers=headers,data=data)
            print("status:",r.status_code)
        print("End block spread.")
        print("="*50)

    # Deprecated function!!!
    # def new_transaction(self, sender, recipient, amount):
    #     """
    #     Creates a new transaction to go to mined block

    #     :param sender: <str> Address of the sender
    #     :param recipient: <str> Address of the recipient
    #     :param amount: <int> Amount transfered
    #     :return: <int> The index of the block that will hold this transaction
    #     """
    #     self.current_transactions.append({
    #         'sender': sender,
    #         'recipient': recipient,
    #         'amount': amount,
    #     })
    #     return self.last_block['index'] + 1
    
    def next_pow(self, last_proof, last_hash):
        """
        Given the last_block proof and hash it creates the proof of work for the next block

        :param last_proof: <int> PoW of the last block
        :param last_hash: <str> String representation of the hash of the last block
        :return: <int> Next valid PoW
        """

        # Set initial value to 0
        proof = 0
        
        # Iterate to get the correct proof
        while not self.is_valid_proof(last_proof, last_hash, proof):
            proof += 1
        return proof

    # Deprecated function!!!
    # @staticmethod
    # def valid_proof(last_proof, proof):
    #     """
    #     Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?

    #     :param last_proof: <int> Previous Proof
    #     :param proof: <int> Current Proof
    #     :return: <bool> True if corrext, otherwise False
    #     """

    #     guess = f'{last_proof}{proof}'.encode()
    #     guess_hash = hashlib.sha256(guess).hexdigest()
    #     return guess_hash[:4] == "0000"
        
    # Deprecated function!!!
    # @staticmethod
    # def hash(block):
    #     """
    #     Creates a SHA-256 hash of a Block

    #     :param block: <dict> Block
    #     :return: <str>
    #     """
    #     block_string = json.dumps(block, sort_keys=True).encode()
    #     return hashlib.sha256(block_string).hexdigest()
    
    def is_valid_next_block(self, last_block, block):
        """
        Checks if a given block is valid considering it's parent.

        :param last_block: <dict> Previous block dict.
        :param block: <dict> Block dict to add.
        :return: <bool> True if it's valid.
        """

        # Check if the given block hash it's equal to computed hash
        scheck = block['hash'] == self.hash_block(block)

        # Check if last_block hash field it's equal to it's computed hash
        lcheck = last_block['hash'] == self.hash_block(last_block)

        # Check if new block previous_hash it's equal to real last_block hash
        pcheck = block['previous_hash'] == last_block['hash']

        # Check if new block index it's equal to last_block's index + 1
        ncheck = block['block_n'] == last_block['block_n'] + 1

        # Check if proof of work algorithm it's correct
        powcheck = self.is_valid_proof(last_block['pow'], last_block['hash'], block['pow'])

        print("Check of block:",block['block_n'],"and last_block:",last_block['block_n'],":",scheck,lcheck,pcheck,ncheck,powcheck)

        return scheck and lcheck and pcheck and ncheck and powcheck

    @staticmethod
    def is_valid_proof(last_proof, last_hash, proof):
        """
        Checks if the proof of work it's correct.

        :param last_proof: <int> The value of the PoW of the previous block
        :param last_hash: <str> The String representation of the hash of the previous block.
        :return: <bool> True if the proof is valid.
        """
        guess = f'{last_proof}{last_hash}{proof}'.encode()
        guess_hash = sha(guess).hex()
        return guess_hash[:7] == "0"*7
    
    @property
    def last_block(self):
        # Returns the last block in the chain
        return self.chain[-1]

    @staticmethod
    def hash_block(block):
        """
        Creates a hash of the block excluding the 'hash' field if it exists (it should be the same as computed here)

        :param block: <dict> Block dict
        :return: <str> String representation of sha-256 hash of the block
        """

        # Create a copy of the block
        block = block.copy()

        # Delete the field "hash" to avoid wrong output
        if "hash" in block:
            del block["hash"]

        # return hexdigest
        return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
    @staticmethod
    def hash_transaction(txn):
        """
        Creates a hash of a transaction dict excluding the signature and hash fields.

        :param txn: <dict> Transaction to hash.
        :return: <str> String representation of the transaction hash.
        """

        # Create a copy of the transaction
        tx = copy.deepcopy(txn)

        # Exclude hash and signature
        to_exclude = ["hash","signature"]
        for d in to_exclude:
            if d in tx:
                del tx[d]
        
        # Return hexdigest
        return hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def create_transaction(wallet, recipient, amount):
        """
        Creates a transaction and signs it

        :param wallet: <dict> Sender's wallet dict.
        :param recipient: <str> String representation of recipient address
        :param amount: <float> Amount to transfer
        :return: <dict> New transaction
        """

        # Get the public and private keys
        public = wallet['public']
        private = wallet['private']

        # Calculate the address
        address = calculate_address(public)

        # Create the transaction dict
        t = {
            'sender': address,
            'recipient': recipient,
            'amount': abs(float(amount))*1.0,
            'timestamp': datetime.datetime.now().isoformat(),
            'public_key': public,
        }

        # Create and add a hash of the transaction
        t['hash'] = Blockchain.hash_transaction(t)

        # Sign the transaction with the private key of the sender
        e = ECDSA(privatekey=bytes.fromhex(private))
        t['signature'] = e.sign(t).hex()

        return t

    @staticmethod
    def create_reward_transaction(wallet):
        """
        Create the reward transaction for the miner.

        :param wallet: <dict> Wallet of the miner.
        :return: <dict> Reward transaction or <bool> False if error occurred
        """

        # Check if wallet address equals our computation
        if wallet['address']!=calculate_address(wallet['public']):
            return False

        # Create reward transaction
        t = {
            'sender': '0',
            'recipient': wallet['address'],
            'amount': 1.0,
            'timestamp': datetime.datetime.now().isoformat(),
            'public_key': wallet['public'],
        }

        # Create and add hash to the transaction
        t['hash'] = Blockchain.hash_transaction(t)

        # Get bytes representation of private and public keys
        public = bytes.fromhex(wallet['public'])
        private = bytes.fromhex(wallet['private'])
        
        # Create the ECDSA object
        e = ECDSA(privatekey=private, publickey=public)
        
        # Sign the transaction
        t['signature'] = e.sign(t).hex()

        return t


    @staticmethod
    def is_valid_transaction(state, txn):
        """
        Checks if a desired transaction is valid

        :param state: <dict> Current statte of the network at the moment of last block
        :param txn: <dict> Transaction to check
        :return: <bool> True if the transaction is valid.
        """
        
        # Check required transaction fields
        required = ['sender', 'recipient', 'amount', 'timestamp', 'public_key', 'signature', 'hash']
        for r in required:
            if r not in txn:
                print("Missing keys")
                return False

        # First check if the hash is correct
        if txn['hash']!=Blockchain.hash_transaction(txn):
            print("incorrect hash")
            return False

        if txn['sender']=='0':
            return True

        # First get the public key
        public = txn['public_key']

        # Calculate the address of the sender
        sender = calculate_address(public)

        # Create a ECDSA object with the current public key
        e = ECDSA(publickey=bytes.fromhex(public))

        # Get the amount to transfer
        amount = txn['amount']

        # Get the signature and the recipient address
        s = txn['signature']
        recipient = txn['recipient']

        # Make a copy and delete the signature to verify
        v = txn.copy()
        del v['signature']

        # It's valid if it's a reward transaction (sender='0') or if it's a normal transaction (sender=<current wallet address> and the signature verifies the content)
        try:
            e.verify(s, v)
            verified = True
        except BadSignatureError:
            print("Signatre error")
            verified = False

        return verified and state.get(sender,0)>=amount

    def is_valid_chain(self, chain=None):
        """
        Iterates all over a chain and checks that all hashes and signatures are correct

        :param chain: <dict> (Optional) Set a chain diferent to self to check.
        :return: <dict> State of the blockchain if the chain is valid, otherwise <bool> False.
        """

        # Create a copy of the chain
        if chain is None:
            chain = copy.deepcopy(self.chain)
        else:
            chain = copy.deepcopy(chain)
        
        # If chain it's empty, nobody owns nothing
        if len(chain)==0:
            return {}

        # Exclude the genesis block
        gb = chain.pop(0)

        # Define a empty state
        state = {}

        # Check if the genesis block is correct
        if gb['hash'] != self.hash_block(gb) or gb['block_n']!=0:
            return False

        # Update state
        state = self.update_state(state, gb['tokens'])
        last_block = gb

        # Iterate over all other blocks
        for i in range(len(chain)):
            # Get the following block and check if it's valid
            block = chain[i]
            if self.is_valid_next_block(last_block, block):
                # If valid, update state
                tokens = block['tokens']
                state = self.update_state(state, tokens)
            else:
                # If invalid, return False
                print("Error on block:",i)
                return False
            last_block = block
        return state
    
    def is_valid_node(self, node):
        """
        Checks if the node is a valid node.

        :param node: <str> Url/ip of the node to validate.
        :return: <bool> True if it's valid.
        """

        try:
            lb = self.last_block
            data = json.dumps(lb)
            headers = {"port":str(self.port)}
            r = requests.post(node+"/chain/add",headers=headers, data=data)
            return True
        except Exception as e:
            print("Error validating node {}".format(node))
            return False
    
    @staticmethod
    def retrive_uid(node):
        url = node+"/uid"
        r = requests.get(url)
        if r.status_code==200:
            return r.text
        else:
            return False

    def discover_nodes(self):
        print("="*50)
        print("Node discovery started.")
        picked_nodes = []
        added = 0
        while len(self.nodes)<config.max_nodes and sorted(picked_nodes)!=sorted(self.nodes):
            cnode = self.nodes[random.randint(0,len(self.nodes)-1)]
            while cnode in picked_nodes and len(picked_nodes)!=self.nodes:
                cnode = self.nodes[random.randint(0,len(self.nodes)-1)]
            picked_nodes.append(cnode)
            print("Picked:",cnode)
            if self.is_valid_node(cnode):
                print("Node valid.")
                try:
                    rnodes = self.retrive_nodes(cnode)
                    print("Got:",rnodes)
                    for node in rnodes:
                        if node not in self.nodes:
                            if self.add_node(node):
                                added += 1
                                print("New node added:",node)
                            else:
                                print("Invalid node:",node)
                        else:
                            print("Node {} already exists.".format(node))
                except Exception as e:
                    print("Error getting nodes from {}: {}".format(cnode,str(e)))
            else:
                print("Invalid node")
        print("Finished node discovery. Added {} new nodes.".format(added))
        print("="*50)

    def add_node(self, node):
        """
        Adds a node to the nodes list.

        :param node: <str> Node to add.
        """

        if self.is_valid_node(node) and node not in self.nodes:
            try:
                uid = self.retrive_uid(node)
                if uid!=self.node_uid:
                    self.nodes.append(node)
                    save_data(self.nodes, "nodes.json")
                    return True
            except Exception as e:
                print("Couldn't retrive {} uid".format(node))
            
        return False

    @staticmethod
    def update_state(state,txn):
        """
        Updates a given state with a transaction list, making sure that all transactions are valid.

        :param state: <dict> State dict.
        :param txn: <list> List of transactions.
        :return: <dict> Updated state.
        """

        # Make a copy of the state
        state = state.copy()
        
        # If it's only one transaction
        if isinstance(txn, dict):
            txn = [txn]
            
        # Iterate over all transactions
        for i,tx in enumerate(txn):
            
            # Check if it's a valid transaction
            if Blockchain.is_valid_transaction(state, tx):
                
                # Update the state
                sender = tx['sender']
                recipient = tx['recipient']
                amount = tx['amount']

                # If it's a reward transaction, don't subtract from nobody
                if sender != '0':
                    state[sender] -= amount

                # Add amount to the recipient
                state[recipient] = state.get(recipient, 0) + amount
        return state
    
    def is_full(self):
        """
        Checks if the current transaction list has more or equal items as BLOCK_SIZE
        """
        return len(self.current_transactions)>=self.BLOCK_SIZE

    @_mcontroller
    def mine(self):
        """
        Tries to mine a new block.
        
        :return: <dict> Block dict if it was successful, else False
        """
        if not self.is_full():
            tr = copy.deepcopy(self.current_transactions)
            self.current_transactions = []
        else:
            tr = copy.deepcopy(self.current_transactions[:self.BLOCK_SIZE])
            self.current_transactions = self.current_transactions[self.BLOCK_SIZE:]
        nb = self.create_next_block(tr)
        if self.is_valid_next_block(self.last_block, nb):
            self.update_chain(nb)
            save_transactions(self.current_transactions)
            return nb
        else:
            self.current_transactions = tr+self.current_transactions
        return False
        
    @staticmethod
    def retrive_last_block(node):
        url = node+"/chain/last"
        r = requests.get(url)
        nlb = json.loads(r.text)
        return nlb

    @staticmethod
    def retrive_nodes(node):
        url = node+"/nodes"
        r = requests.get(url)
        return json.loads(r.text)

    def clean_transactions(self):
        state = self.is_valid_chain()
        hashes = self.get_transaction_hashes()
        for t in self.current_transactions:
            if t['hash'] in hashes:
                self.current_transactions.remove(t)
            elif self.is_valid_transaction(state,t):
                state = self.update_state(state,t)
            else:
                self.current_transactions.remove(t)
        save_transactions(self.current_transactions)

    @staticmethod
    def retrive_chain(node):
        url = node+"/chain"
        r = requests.get(url)
        chain = json.loads(r.text)
        return chain
    
    def get_transaction_hashes(self, chain=None):
        if chain is None:
            chain = self.chain
        hashes = set()
        for block in chain:
            for transaction in block['tokens']:
                hashes.add(transaction['hash'])
        return hashes

    def resolve_chains(self):
        self.resolving_chains = True
        for node in self.nodes:
            self.resolve_chain(node)
        self.resolving_chains = False

    def resolve_chain(self, node):
        state = self.is_valid_chain()
        
        if state is False:
            print("INVALID CURRENT CHAIN!")

        try:
            node_last_block = self.retrive_last_block(node)
        except Exception as e:
            print("Error getting {} last_block: {}".format(node, str(e)))
            return False
        last_block = self.last_block
        
        # Check if hashes are correct
        if node_last_block['hash']!=self.hash_block(node_last_block):
            print("Error on node last block")
            return False
        if last_block['hash']!=self.hash_block(last_block):
            print("Error on current chain!")
            return False
        
        print("Last block comparison for chain equality test.")
        # Check if blocks are equal
        if node_last_block['hash']!=last_block['hash'] or state is False:
            print("Last block comparision differs!!!")
            # If are not equal, we need to check which chain is longer
            if node_last_block['block_n']>last_block['block_n'] or state is False:
                print("Chain on {} is longer than ours or we have incorrect one, trying to fetch the full chain.".format(node))
                # If the node's chain is longer than ours
                try:
                    node_chain = self.retrive_chain(node)
                    print("Chain recived!")
                except Exception as e:
                    print("Error getting {} chain: {}".format(node, str(e)))
                    return False
                # If the node's chain is correct
                if self.is_valid_chain(node_chain):
                    print("The chain is valid.")
                    # Then we update our chain
                    self.chain = node_chain
                    save_chain(self.chain)
                    self.clean_transactions()
                    return True
                else:
                    # The node chain is invalid
                    print("Invalid chain!")
                    return False
            else:
                # If our chain is longer
                print("Our chain is equal or longer.")
                return False
        else:
            # If chain last blocks are equal
            print("Chains are equal")
            return False

    @staticmethod
    def get_node_transaction_hashes(node):
        url = node+"/transactions/hash"
        r = requests.get(url)
        hashes = json.loads(r.text)
        return hashes

    @staticmethod
    def get_node_transaction(node,hash):
        url = node+"/transaction/"+hash
        r = requests.get(url)
        t = json.loads(r.text)
        return t
    
    def resolve_transactions_all(self):
        self.resolving_transactions = True
        for node in self.nodes:
            self.resolve_transactions(node)
        self.resolving_transactions = False

    def resolve_transactions(self, node):
        print("="*50)
        print("Starting resolve transactions from",node)
        try:
            # Get node transaction hashes
            print("Getting transaction hashes")
            hashes = self.get_node_transaction_hashes(node)
            print("Got:",hashes)
            local_hashes = [t['hash'] for t in self.current_transactions]
            tdiff = [h for h in hashes if h not in local_hashes]
            print("Pulling {} transactions".format(len(tdiff)))
            for h in tdiff:
                print("Requesting:",h)
                try:
                    print("Transaction recived!")
                    tr = self.get_node_transaction(node,h)
                    self.update_transaction(tr)
                except Exception as e:
                    print("Error requesting transaction:",h)
        except Exception as e:
            print("Error resolving:",node)
        print("Ended resolve transactions.")
        print("="*50)