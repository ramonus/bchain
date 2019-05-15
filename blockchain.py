import hashlib, json, time, uuid, datetime
from wallet_utils import *

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # Creates the genesis block
        self.new_block(previous_hash=0, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain

        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of the previous block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain)+1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash,
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block
    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go to mined block

        :param sender: <str> Address of the sender
        :param recipient: <str> Address of the recipient
        :param amount: <int> Amount transfered
        :return: <int> The index of the block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index'] + 1
    
    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
            - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
            - p is the previous proof, and p' is the new proof
        
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof,proof) is False:
            proof +=1
        return proof
    
    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if corrext, otherwise False
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
        
    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: <dict> Block
        :return: <str>
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def is_valid_next_block(self, block):
        """
        Checks if a given block is suitable to add to the chain

        :param block: <dict> Block dict to add
        :return: <bool> True if it's valid
        """

        # Check if the given block hash it's equal to computed hash
        scheck = block['hash'] == self.hash_block(block)

        # Check if last_block hash field it's equal to it's computed hash
        lcheck = self.last_block['hash'] == self.hash_block(self.last_block)

        # Check if new block previous_hash it's equal to real last_block hash
        pcheck = block['previous_hash'] == self.last_block['hash']

        # Check if new block index it's equal to last_block's index +1
        ncheck = block['block_n'] == self.last_block['block_n'] + 1

        # Check if proof of work algorithm it's correct
        
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

    @staticmethod
    def is_valid_proof(last_proof, last_hash, proof):
        """
        Checks if the proof of work it's correct.

        :param last_proof: <int> The value of the PoW of the previous block
        :param last_hash: <str> The String representation of the hash of the previous block.
        :return: <bool> True if the proof is valid.
        """
        guess = f'{last_proof}{last_hash}{proof}'.encode()
        guess_hash = sha(guess).hexdigest()
        return guess_hash[:4] = "0"*4
    
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

