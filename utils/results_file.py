from typing import List, Dict, Any
import io
import pickle


"""
Results file format
-------------------

It's a sequence of records, where each record is:
1. Pickled contents of a `Dict[str, Any]`
2. 4 bytes containing the start offset of the pickled contents.

Thus a results file is simply read sequentially from back to front.
"""


def load(filename: str) -> List[Dict[str, Any]]:
    """
    Loads the binary results file.

    Parameters
    ----------
    filename : str
        Path to the binary-format results file.

    Returns
    -------
    List[Dict[str, Any]]
        The results in chronological order (most recent first)
    """
    results: List[Dict[str, Any]] = []
    with open(filename, 'rb') as f:
        f.seek(0, io.SEEK_END)  # go to the end of the file.
        addr = f.tell() - 4  # record the start of #2
        while True:
            f.seek(addr)
            bytes = f.read(4)
            result_pos = int.from_bytes(bytes, 'little', signed=False)
            result_len = addr - result_pos
            f.seek(result_pos)  # go to the start of #1
            blob = f.read(result_len)  # read #1
            results.append(pickle.loads(blob))
            addr = result_pos - 4  # record the start of #2 for the previous record.
            if addr == -4:
                # Very strict condition here so we can "catch" mistakes.
                break
    return results


def append(filename: str, result: Dict[str, Any]) -> None:
    """
    Appends a result to the binary results file.

    Parameters
    ----------
    filename : str
        Path to the binary-format results file.
    result : Dict[str, Any]
        The result to append.
    """
    with open(filename, 'a+b') as f:
        f.seek(0, io.SEEK_END)  # go to the end of the file.
        addr = f.tell()  # record the start of #2
        blob = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
        f.write(blob)  # write #1
        f.write(addr.to_bytes(4, 'little'))
