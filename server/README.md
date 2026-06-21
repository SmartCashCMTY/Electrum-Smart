# Electrum-SMART Server 3.0.0

Minimal Electrum protocol server for SmartCash 3.0.0. Queries smartcashd via JSON-RPC.

## Requirements
- Python 3.7+
- Access to smartcashd RPC

## Configuration
Edit `RPC_URL`, `RPC_USER`, `RPC_PASS` in `electrum_server.py`.

## Deployment
```bash
cp electrum-server.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now electrum-server
```

## Protocol Support
- server.version, server.banner, server.features
- blockchain.headers.subscribe
- blockchain.block.header
- blockchain.block.headers
- blockchain.transaction.get
- blockchain.address.get_history
- blockchain.address.subscribe
- blockchain.scripthash.get_history, get_balance, subscribe
