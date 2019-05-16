from Hybrid.ECDSA import ECDSA
from base58 import b58encode
import hashlib, json
from pathlib import Path
import config

sha = lambda x: hashlib.sha256(x if isinstance(x,bytes) else x.encode()).digest()

def ripemd160(x,_hex=False):
    """
    Calculates a ripemd160 hash of a given bytes

    :param x: <bytes> bytes to hash
    :param _hex: <bool> If True, the output will be in hex format, default to False
    :return: <bytes>/<str> Hash output
    """

    ri = hashlib.new('ripemd160')
    ri.update(x)
    if _hex:
        return ri.hexdigst()
    else:
        return ri.digest()

def get_wallet(path=None):
    """
    Loads a wallet or creates a new one

    :param path: <str> (Optional) Path of the .dat file, default to 'wallets/wallet.dat'.
    :return: <dict> Wallet dict
    """

    if path is None:
        path = Path(config.wallets_dir)/config.node_wallet
    elif isinstance(path, str):
        if not path.endswith(".dat"):
            path += '.dat'
        if not '/' in path:
            path = Path(config.wallets_dir)/path
        else:
            path = Path(path)
    else:
        path = Path(path)
        
    error = False
    if path.exists():
        try:
            w = json.loads(path.read_text())
        except:
            print("Wallet corrupted")
            error = True
    else:
        error = True
    if error:
        w = create_wallet()
        save_wallet(w)
    return w
            

def calculate_address(public):
    """
    Given a public key, calculates the wallet address
    
    :param public: <str>/<bytes> Wallet's public key
    :return: <str> String representation of the wallet address
    """

    # If public key is a string, convert it to bytes
    if isinstance(public, str):
        public = bytes.fromhex(public)

    # Adds a '\x04' byte padding if it does not exist
    if public[0]!=b'\x04':
        public = b'\x04'+public
    
    # Calculates sha256 hash
    s1 = sha(public)

    # Calculates ripemd160 hash and adds a '\x00' padding
    ri = b'\x00'+ripemd160(s1)
    
    # Calculates double sha256 hash
    s2 = sha(ri)
    s3 = sha(s2)

    # Gets a chunk of the 4 first bytes of the final sha256 hash
    chk = s3[:4]

    # Adds this chunk to the ripemd160 hash
    nri = ri + chk

    # Encodes the output to base 58 following BitCoin standard
    en = b58encode(nri)
    
    return en.decode()

def create_wallet():
    """
    Creates a brand new wallet

    :return: <dict> Wallet
    """

    # Generate keys
    e = ECDSA()
    public = e.publickey.to_string()
    private = e.privatekey.to_string()
    wallet_dir = calculate_address(public)

    # Create the wallet dict
    wallet = {
        'address': wallet_dir,
        'public': public.hex(),
        'private': private.hex(),
    }

    return wallet

def save_wallet(wallet,path=None):
    """
    Saves a wallet to a specified file.

    :param wallet: <dict> Wallet to save.
    :param path: <str> (Optional) Where to save the wallet.
    :return: <bool> True if success, otherwise False
    """

    wp = Path(config.wallets_dir)
    if not wp.exists():
        wp.mkdir()
    
    if path is None:
        p = wp/config.node_wallet
        if p.exists():
            n = 1
            while (wp/config.wallet_namef.format(n)).exists():
                n+=1
            p = wp/config.wallet_namef.format(n)
    else:
        p = Path(path)
    
    try:
        p.write_text(json.dumps(wallet, sort_keys=True))
        print("Wallet saved to:",p)
    except Exception as e:
        print("Error saving wallet:",str(e))
        return False
    return True

if __name__=="__main__":
    w = create_wallet()
    print(w)
    print("Address:",calculate_address(w['public']))