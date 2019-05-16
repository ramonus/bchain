import hashlib, json, time, uuid
from flask import Flask, jsonify, request
from blockchain import Blockchain

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
            blockchain.current_transactions.append(t)
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
    GET request to view all transactions.
    """

    # Create response
    response = {
        'length': len(blockchain.current_transactions),
        'transactions': blockchain.current_transactions,
    }

    return jsonify(response), 200

@app.route("/chain",methods=['GET'])
def full_chain():
    """
    GET request to view full length chain.
    """

    # Create response
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }

    return jsonify(response), 200

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

if __name__=="__main__":
    app.run(host='0.0.0.0',port=5000)
