from pathlib import Path
import json, config

def save_transactions(transactions):
    """
    Saves a given transaction list to config.transactions_path.

    :param transactions: <list> List of transactions.
    :return: <pathlib.Path> Path of the file saved.
    """

    p = Path(config.transactions_path)
    p.write_text(json.dumps(transactions, sort_keys=True))
    return p

def load_transactions():
    """
    Loads a transaction list if the default file exists, otherwise returns a empty list.

    :return: <list> List of transactions.
    """
    
    p = Path(config.transactions_path)
    if p.exists():
        return json.loads(p.read_text())
    else:
        return []