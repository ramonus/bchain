from pathlib import Path
import json

def load_data(path, default=[]):
    """
    Given a path returns the json content.

    :param path: <str> Path of the file.
    :param default: <any> If the file does not exist, return this.
    """

    p = Path(path)
    
    if p.exists():
        return json.loads(p.read_text())
    else:
        return default

def save_data(data,path):
    """
    Saves the data in path with json format.

    :param data: <any> Json serializable data.
    :param path: <str> Path to save the data.
    :return: <bool> If success saving.
    """

    p = Path(path)
    p.write_text(json.dumps(data, sort_keys=True))
    return True