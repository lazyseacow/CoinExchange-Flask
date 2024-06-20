import asyncio
import json
import logging
import re
import websockets
import redis.asyncio as aioredis
from config import subscribe_trade
from log_util import setupLogging

# 存储客户端订阅信息
subscriptions = {}
clients = {}
subscriptions_lock = asyncio.Lock()
binance_ws = None
logger = setupLogging(logging.DEBUG, 'wss')


# 创建 Redis 连接
async def create_redis_connection():
    redis = aioredis.from_url('redis://localhost/1')
    return redis


async def manage_binance_connection(redis):
    global binance_ws
    while True:
        try:
            # 维持到币安的WebSocket连接
            async with websockets.connect("wss://stream.binance.com:443/stream") as ws:
                binance_ws = ws
                await ws.send(json.dumps(subscribe_trade))
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    stream = data.get('stream')
                    if stream:
                        # 将最新的stream数据存储到Redis哈希表中
                        await redis.hset('binance_data', stream, json.dumps(data))
                    await handle_binance_message(data)
        except Exception as e:
            logger.error(f"Error with Binance WebSocket: {e}")
            binance_ws = None
            await asyncio.sleep(3)  # 重试连接前等待


async def handle_binance_message(data):
    stream = data.get("stream")
    if stream in subscriptions:
        # 将消息发送给所有订阅了此stream的客户端
        for client in subscriptions[stream]:
            if client.open:
                await client.send(json.dumps(data))
                logger.info(f'client: {client} received send {data}')
                # print(f'client: {client} received send {data}')


async def handle_client(websocket, path):
    global clients, binance_ws
    client_id = id(websocket)
    clients[client_id] = websocket
    redis = await create_redis_connection()
    try:
        async for message in websocket:
            message = json.loads(message)
            logger.info(f'Received message from client {client_id}: {message}')
            # print(f'Received message from client {client_id}: {message}')
            action = message['action']
            params_list = message['params']

            if action == 'true':
                async with subscriptions_lock:
                    for param in params_list:
                        if param not in subscriptions:
                            subscriptions[param] = set()

                        subscriptions[param].add(websocket)
                        if not re.match(r".*@ticker$", param):
                            if binance_ws:
                                await binance_ws.send(json.dumps({
                                    "method": "SUBSCRIBE",
                                    "params": [param],
                                    "id": client_id
                                }))
            elif action == 'fetch':
                stream = params_list[0]
                # 从Redis哈希表中获取最新的数据并发送给客户端
                data = await redis.hget('binance_data', stream)
                if data:
                    await websocket.send(data.decode('utf-8'))
    except Exception as e:
        logger.error(f"Error with client {client_id}: {e}")
    finally:
        await handle_disconnect(websocket)


async def handle_disconnect(websocket):
    global binance_ws
    client_id = id(websocket)
    subscriptions_to_remove = []
    for params, clients_set in list(subscriptions.items()):
        if websocket in clients_set:
            clients_set.remove(websocket)
            if not clients_set and not re.match(r".*@ticker$", params):
                subscriptions_to_remove.append(params)
    for params in subscriptions_to_remove:
        if binance_ws:
            await binance_ws.send(json.dumps({
                "method": "UNSUBSCRIBE",
                "params": [params],
                "id": client_id
            }))
            subscriptions.pop(params, None)
    clients.pop(client_id, None)


async def main():
    redis = await create_redis_connection()
    # 维持币安 WebSocket 连接
    binance_task = asyncio.create_task(manage_binance_connection(redis))
    # 创建 WebSocket 服务器
    start_server = websockets.serve(handle_client, "0.0.0.0", 8889)
    await start_server
    # 运行直到被取消
    await asyncio.Future()  # Runs forever


if __name__ == "__main__":
    asyncio.run(main())
