#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install ecdsa pyaes qrcode pbkdf2 jsonrpclib pysocks pycryptodomex PyQt5
else
    source venv/bin/activate
fi
python3 electrum-smart
