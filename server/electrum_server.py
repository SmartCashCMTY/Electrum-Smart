#!/usr/bin/env python3
"""Minimal Electrum Server for SmartCash 3.0.0 using JSON-RPC to daemon."""

import asyncio, json, struct, time, hashlib, ssl, logging
import urllib.request, base64
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('electrum-server')

RPC_URL = "http://151.252.59.32:29679/"
RPC_USER = "smartcashrpc"
RPC_PASS = "a551f91d9199429fa89e7b39cbdce00412221b56de0384211e16a9da614354ab"
TCP_PORT = 50001
SSL_PORT = 50002
CERTFILE = "/etc/electrumx/server.crt"
KEYFILE = "/etc/electrumx/server.key"

subscriptions = defaultdict(set)
current_height = 0
current_tip = b""

def rpc(method, params=[]):
    data = json.dumps({"method": method, "params": params})
    auth = base64.b64encode(f"{RPC_USER}:{RPC_PASS}".encode()).decode()
    req = urllib.request.Request(RPC_URL, data=data.encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        if result.get("error"):
            raise Exception(result["error"])
        return result["result"]

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    log.info(f"Connect {addr}")
    session = {"id": str(addr), "subs": set()}
    try:
        while True:
            raw = await reader.read(4)
            if not raw: break
            magic, size = struct.unpack('<HH', raw)
            data = await reader.readexactly(size)
            request = json.loads(data)
            result = await process_request(session, request)
            if result is not None:
                resp = json.dumps(result).encode()
                writer.write(struct.pack('<HH', 0, len(resp)) + resp)
                await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    finally:
        for sub in session.get("subs", set()):
            subscriptions[sub].discard(session["id"])
        writer.close()

async def process_request(session, req):
    method = req.get("method", ""); params = req.get("params", []); mid = req.get("id")
    try:
        if method == "server.version":
            result = ["Electrum-SMART 3.0.0", "1.4"]
        elif method == "server.banner":
            result = "SmartCash 3.0.0 Electrum Server"
        elif method == "server.features":
            result = {"genesis_hash": "000007acc6970b812948d14ea5a0a13db0fdd07d5047c7e69101fa8b361e05a4",
                      "hosts": {"151.252.59.31": {"tcp_port": 50001, "ssl_port": 50002}},
                      "protocol_max": "1.4.2", "protocol_min": "1.4",
                      "pruning": None, "server_version": "Electrum-SMART 3.0.0"}
        elif method == "blockchain.headers.subscribe":
            global current_height, current_tip
            bh = rpc("getbestblockhash")
            hh = rpc("getblockheader", [bh, False])
            current_tip = bytes.fromhex(hh); current_height = rpc("getblockcount")
            subscriptions["headers"].add(session["id"])
            session.setdefault("subs", set()).add("headers")
            result = {"hex": hh, "height": current_height}
        elif method == "blockchain.block.header":
            bh = rpc("getblockhash", [params[0]])
            result = bytes.fromhex(rpc("getblockheader", [bh, False]))
        elif method == "blockchain.block.headers":
            sh, cnt = params[0], params[1]
            end = min(cnt, current_height + 1 - sh); r = b""
            for h in range(sh, sh + end):
                bh = rpc("getblockhash", [h])
                r += bytes.fromhex(rpc("getblockheader", [bh, False]))
            result = {"count": end, "hex": r.hex(), "max": 2016}
        elif method == "blockchain.transaction.get":
            raw = rpc("getrawtransaction", [params[0] if isinstance(params[0], str) else params[0]])
            result = bytes.fromhex(raw)
        elif method in ("blockchain.estimatefee", "mempool.get_fee_histogram"):
            result = 0.00001
        elif method == "blockchain.relayfee":
            result = 0.00001
        elif method.startswith("blockchain.scripthash."):
            result = await handle_scripthash(method, params, session)
        elif method.startswith("blockchain.address."):
            result = await handle_address(method, params, session)
        else:
            log.warning(f"Unknown method: {method}")
    except Exception as e:
        log.error(f"Error {method}: {e}")
        result = None
    if result is not None and mid is not None:
        return {"jsonrpc": "2.0", "id": mid, "result": result}

async def handle_scripthash(method, params, session):
    if method == "blockchain.scripthash.get_history":
        return []
    elif method == "blockchain.scripthash.subscribe":
        subscriptions[params[0]].add(session["id"])
        return None  # no response for subscribe
    elif method == "blockchain.scripthash.get_balance":
        return {"confirmed": 0, "unconfirmed": 0}

async def handle_address(method, params, session):
    if method == "blockchain.address.get_history":
        try:
            txs = rpc("getaddresstxids", [params[0]])
            history = []
            for txid in txs[:100]:
                history.append({"tx_hash": txid, "height": 0, "fee": 0})
            return history
        except:
            return []
    elif method == "blockchain.address.subscribe":
        subscriptions[params[0]].add(session["id"])
        return None
    elif method == "blockchain.address.get_balance":
        return {"confirmed": 0, "unconfirmed": 0}

async def main():
    global current_height, current_tip
    try:
        current_height = rpc("getblockcount")
        bh = rpc("getblockhash", [current_height])
        current_tip = bytes.fromhex(rpc("getblockheader", [bh, False]))
        log.info(f"Daemon height: {current_height}")
    except Exception as e:
        log.error(f"Daemon connect failed: {e}")
    
    ssl_ctx = None
    try:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(CERTFILE, KEYFILE)
    except: pass
    
    tcp = await asyncio.start_server(handle_client, '0.0.0.0', TCP_PORT)
    ssl_srv = await asyncio.start_server(handle_client, '0.0.0.0', SSL_PORT, ssl=ssl_ctx) if ssl_ctx else None
    log.info(f"Listening TCP:{TCP_PORT} SSL:{SSL_PORT}")
    async with tcp:
        await tcp.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
