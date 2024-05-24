import asyncio
from datetime import datetime, timedelta

import websockets
import json

connected_clients = set()
client_last_active = {}
third_party_url = "wss://stream.binance.com:9443/ws"
third_party_connections = {}


async def handle_client(websocket):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            client_last_active[websocket] = datetime.now()
            data = json.loads(message)
            if 'action' in data:
                if data['action'] == 'subscribe':
                    await handle_subscribe(websocket, data)
                elif data['action'] == 'unsubscribe':
                    await handle_unsubscribe(websocket, data)
            else:
                for client in connected_clients:
                    if client != websocket:
                        await client.send(message)
    except websockets.exceptions.ConnectionClosedError:
        print("WebSocket connection closed with error.")
    finally:
        connected_clients.remove(websocket)
        client_last_active.pop(websocket, None)
        await cleanup(websocket)


async def check_inactive_clients():
    while True:
        now = datetime.now()
        to_close = [ws for ws, last_active in client_last_active.items() if now - last_active > timedelta(minutes=3)]
        for ws in to_close:
            await ws.close(reason='Heartbeat timeout')
            connected_clients.remove(ws)
            client_last_active.pop(ws, None)
        await asyncio.sleep(30)  # 每30秒检查一次


async def handle_subscribe(client_websocket, data):
    # 创建到第三方的连接并保存该连接
    if client_websocket not in third_party_connections:
        third_party_ws = await websockets.connect(third_party_url)
        third_party_connections[client_websocket] = third_party_ws
        asyncio.create_task(forward_third_party_messages(third_party_ws, client_websocket))

    await third_party_connections[client_websocket].send(json.dumps(data['params']))


async def forward_third_party_messages(third_party_ws, client_websocket):
    try:
        while True:
            message = await third_party_ws.recv()
            print(f'Receive from Binance:{message}')
            if client_websocket.open:
                await client_websocket.send(message)
    except websockets.exceptions.ConnectionClosed as e:
        print(e)
        print("Third-party WebSocket connection closed.")


async def handle_unsubscribe(client_websocket, data):
    if client_websocket in third_party_connections:
        await third_party_connections[client_websocket].send(json.dumps(data['params']))
        await third_party_connections[client_websocket].close()
        del third_party_connections[client_websocket]


async def cleanup(websocket):
    if websocket in third_party_connections:
        await third_party_connections[websocket].close()
        del third_party_connections[websocket]


# Start the WebSocket server
# async def main():
#     async with websockets.serve(handle_client, 'localhost', 8888):
#         await asyncio.Future()  # run forever

async def main():
    server = await websockets.serve(handle_client, 'localhost', 8888)  # 正确启动WebSocket服务
    asyncio.create_task(check_inactive_clients())  # 启动心跳检查任务
    await server.wait_closed()  # 保持服务器运行直到被关闭

asyncio.run(main())
