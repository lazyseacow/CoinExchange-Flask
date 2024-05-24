import asyncio
from datetime import datetime, timedelta

import websockets
import json

connected_clients = set()
client_last_active = {}
third_party_url = "wss://stream.binance.com:9443/ws"
third_party_connections = {}


async def handle_client(websocket):
    try:
        # token = await websocket.recv()
        # if not await validate_token(token):
        #     await websocket.close(reason="authentication failed")
        #     return

        connected_clients.add(websocket)

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
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            client_last_active.pop(websocket, None)
            await cleanup(websocket)


async def check_inactive_clients():
    while True:
        now = datetime.now()
        inactive_clients = [ws for ws, last_active in client_last_active.items()
                            if now - last_active > timedelta(seconds=10)]
        for ws in inactive_clients:
            if ws in connected_clients:
                print("Closing inactive connection.")
                await ws.close(reason='Heartbeat timeout')
                connected_clients.remove(ws)
                client_last_active.pop(ws, None)
                await cleanup(ws)
        await asyncio.sleep(5)  # 检查间隔



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


async def validate_token(token):
    # 这里添加您的认证逻辑，例如解码 JWT 或检查数据库
    # 返回 True 如果 token 有效，否则返回 False
    return token == "YOUR_SECRET_TOKEN"


async def main():
    server = await websockets.serve(handle_client, 'localhost', 8888)  # 正确启动WebSocket服务
    asyncio.create_task(check_inactive_clients())  # 启动心跳检查任务
    await server.wait_closed()  # 保持服务器运行直到被关闭

asyncio.run(main())
