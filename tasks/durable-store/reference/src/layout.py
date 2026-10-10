"""How keys map to file names. See docs/design.md."""

import json

PREFIX = "d."
MANIFEST = "MANIFEST"
MANIFEST_TMP = "MANIFEST.tmp"


def data_name(key, generation):
    """The file holding the value `key` was given by commit `generation`.

    Hex, because a key may contain any character and a file name may not
    contain "/". A new name per commit, because overwriting the file an
    older, still-current manifest points at would change the old state too.
    """
    return f"{PREFIX}{key.encode('utf-8').hex()}.{generation}"


def encode_manifest(generation, files):
    return json.dumps({"generation": generation, "files": files}, sort_keys=True).encode("utf-8")


def decode_manifest(data):
    m = json.loads(data.decode("utf-8"))
    return m["generation"], m["files"]
