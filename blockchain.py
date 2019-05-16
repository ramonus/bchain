import hashlib, json, time, uuid, datetime, copy
from wallet_utils import *
from ecdsa.keys import BadSignatureError

class Blockchain:
    
    BLOCK_SIZE = 10

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.wallet = get_wallet()
        # Creates the genesis block
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

        # Correct the timestamp
        if isinstance(timestamp, datetime.datetime):
            timestamp = timestamp.isoformat()

        # Create the block dict
        block = {
            'block_n': n,
            'timestamp': timestamp,
            'token_n': len(tokens),
            'tokens': tokens,
            'miner': self.wallet['address'],
            'previous_hash': previous_hash,
            'pow': 9 if previous_pow is None else self.next_pow(previous_pow, previous_hash),
        }

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
        self.chain.append(block)
        return True

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
        return guess_hash[:4] == "0"*4
    
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
            'amount': amount,
            'timestamp': datetime.datetime.now().isoformat(),
            'public_key': public,
        }

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
        required = ['sender', 'recipient', 'amount', 'timestamp', 'public_key', 'signature']
        for r in required:
            if r not in txn:
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

    def mine(self):
        if not self.is_full():
            tr = copy.deepcopy(self.current_transactions)
            self.current_transactions = []
        else:
            tr = copy.deepcopy(self.current_transactions[:self.BLOCK_SIZE])
            self.current_transactions = self.current_transactions[self.BLOCK_SIZE:]
        nb = self.create_next_block(tr)
        if self.is_valid_next_block(self.last_block, nb):
            self.update_chain(nb)
            return nb
        return False
        


