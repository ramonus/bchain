from pathlib import Path
import json, config

def save_chain(chain):
    """
    Saves a given chain to "config.chain_path".

    :param chain: <list> Chain to save.
    :return: <pathlib.Path> Path where it was saved.
    """

    p = Path(config.chain_path)
    p.write_text(json.dumps(chain, sort_keys=True))
    print("Chain saved to",p)
    return p

def load_chain(path=None):
    """
    Reads a chain in "path" but if the file does not exist return a empty chain

    :param path: <str> (Optional) Path of the file where the chain is saved.
    :return: <list> Chain.
    """

    if path is None:
        p = Path(config.chain_path)
        if not p.exists():
            return []
        else:
            return json.loads(p.read_text())
    else:
        return json.loads(Path(path).read_text())