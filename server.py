import hashlib, json, time, uuid
from flask import Flask, jsonify, request, render_template
from blockchain import Blockchain
from wallet_utils import create_wallet, save_wallet

# Instantiate our node
app = Flask(__name__)

# Generate globally unique address for this node
node_identifier = str(uuid.uuid4()).replace("-","")

# Instantiate Blockchain
blockchain = Blockchain()


@app.route("/mine",methods=['GET'])
def mine():
    """
    GET request to try to mine a block.
    """

    # Call function to mine a block
    mined_block = blockchain.mine()

    # Check if it worked
    if mined_block is not False:
        # If it's not False
        msg = "New block mined"
        error = []
        data = mined_block
        s = 201
    else:
        # If it's False
        msg = "Error mining block"
        error = ["Unknown error"]
        data = None
        s = 401

    # Create response
    response = {
        'message': msg,
        'error': error,
        'data': data,
    }
    
    return jsonify(response), s

@app.route("/transactions/new",methods=['POST'])
def new_transaction():
    """
    This method will listen for a POST request to /transactions/new and expect data ['wallet', 'recipient', 'amount']
    """

    # Read json string
    values = json.loads(request.get_data().decode())

    print("Values:",values)

    # Setup error and message lists
    error = []
    msg = []

    # Check that the required fields are in POST'ed data
    required = ['wallet', 'recipient', 'amount']

    # Get values
    try:
        wallet = values['wallet']
        recipient = values['recipient']
        amount = values['amount']

        # Create transaction
        t = blockchain.create_transaction(wallet, recipient, amount)
        
        # Compute state
        state = blockchain.is_valid_chain()
        state = blockchain.update_state(state, blockchain.current_transactions)
        # Check transaction validity
        if blockchain.is_valid_transaction(state, t):
            blockchain.update_transactions(t)
            msg = "Done"
        else:
            msg = "Not enough funds, maybe some are reserved"
            error.append("Not enough funds")
    except KeyError as e:
        error.append("Invalid input")

    # Create response
    response = {
        'message': msg,
        'error': error,
    }

    return jsonify(response), 201

@app.route("/transactions",methods=['GET'])
def transactions():
    """
    GET request to view all pending transactions.
    """

    return jsonify(blockchain.current_transactions), 200

@app.route("/transactions/hash",methods=['GET'])
def get_transaction_hash():
    """
    GET request to view all pending transactions hash in a list.
    """
    # Get state
    state = blockchain.is_valid_chain()
    # Get all transactions hash
    hashes = [t['hash'] for t in blockchain.current_transactions if blockchain.is_valid_transaction(state, t)]

    return jsonify(hashes), 200

@app.route("/transactions/length",methods=['GET'])
def transactions_length():
    """
    GET request to view pending transactions length.
    """

    # Create response
    resp = {
        "length": len(blockchain.current_transactions),
    }
    return jsonify(resp), 200

@app.route("/transaction/<hash>")
def get_transaction(hash):
    """
    GET request to retrive a single transaction given a hash.
    """

    tra = [i for i in blockchain.current_transactions if i['hash']==hash]
    if len(tra)==1:
        return jsonify(tra[0]), 200
    elif len(tra)==0:
        
        # Create response
        resp = {
            "error":"No transaction found with hash: "+hash
        }
        
        return jsonify(resp), 200
    else:
        
        # Create response
        resp = {
            "error":"Error, multiple transactions found!",
        }

        return jsonify(resp), 200

@app.route("/nodes",methods=["GET"])
def get_nodes():
    """
    GET request to view all current nodes.
    """

    return jsonify(blockchain.nodes), 200

@app.route("/chain",methods=['GET'])
def full_chain():
    """
    GET request to view full chain.
    """

    return jsonify(blockchain.chain), 200

@app.route("/chain/length",methods=['GET'])
def chain_length():
    """
    GET request to view full chain's length.
    """

    # Create response
    resp = {
        "length": len(blockchain.chain)
    }
    return jsonify(resp), 200

@app.route("/chain/last",methods=['GET'])
def last_block():
    """
    GET request to view the last block on node's chain.
    """

    return jsonify(blockchain.last_block), 200

@app.route("/state",methods=['GET'])
def state():
    """
    GET request to view the current state in main chain.
    """
    
    # Get state
    state = blockchain.is_valid_chain()
    
    return jsonify(state), 200

@app.route("/state/all",methods=['GET'])
def state_all():
    """
    GET request to view the current state adding the pending transactions.
    """

    # Get state
    state = blockchain.is_valid_chain()
    
    # Update with pending transactions
    state = blockchain.update_state(state, blockchain.current_transactions)
    
    return jsonify(state), 200


"""
This section will be a test gui to simplify debugging
"""

@app.route("/")
def root():
    return render_template('index.html')

@app.route("/new_transaction")
def ntransaction():
    return render_template('newt_gui.html')

@app.route("/get_wallets")
def get_wallets():
    from pathlib import Path
    p = Path("wallets")
    wallets = []
    for pa in p.iterdir():
        w = {"name":pa.stem, "wallet": json.loads(pa.read_text())}
        wallets.append(w)
    return jsonify(wallets), 200

@app.route("/new_wallet")
def new_wallet():
    w = create_wallet()
    n = save_wallet(w)
    resp = {
        "name":n,
        "wallet": w,
    }

    return jsonify(resp), 201

if __name__=="__main__":
    app.run(host='0.0.0.0',port=5000)
