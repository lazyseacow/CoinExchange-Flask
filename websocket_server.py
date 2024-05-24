import asyncio
from datetime import datetime, timedelta
import websockets
import json

# Global sets and dictionaries to manage connected clients and their activities
connected_clients = set()
client_last_active = {}
third_party_url = "wss://stream.binance.com:9443/ws"
third_party_connections = {}


# A class to manage third party connections
class ThirdPartyConnectionManager:
    def __init__(self, url):
        self.url = url
        self.connection = None
        self.subscriptions = set()

    async def connect(self):
        if not self.connection or self.connection.closed:
            self.connection = await websockets.connect(self.url)
        return self.connection

    async def subscribe(self, client_websocket, data):
        self.subscriptions.add(client_websocket)
        if len(self.subscriptions) == 1:  # First subscriber triggers the connection
            await self.connect()
            await self.connection.send(json.dumps(data['params']))
            asyncio.create_task(self.receive_messages())

    async def close(self, client_websocket):
        if client_websocket in self.subscriptions:
            # if data and 'params' in data:
            #     await self.connection.send(json.dumps(data['params']))
            self.subscriptions.remove(client_websocket)
            if not self.subscriptions:
                await self.connection.close()

    async def receive_messages(self):
        try:
            while True:
                message = await self.connection.recv()
                print(f'Received from third party: {message}')
                await self.broadcast(message)
        except websockets.exceptions.ConnectionClosed:
            print("Third-party WebSocket connection closed.")
            self.connection = None  # Reset connection on close

    async def broadcast(self, message):
        for client in self.subscriptions.copy():  # Use a copy to avoid modification during iteration
            if client.open:
                await client.send(message)
            else:
                self.subscriptions.discard(client)  # Remove closed connections


# Initialize the third party connection manager
third_party_manager = ThirdPartyConnectionManager(third_party_url)


async def handle_client(websocket):
    try:
        connected_clients.add(websocket)
        async for message in websocket:
            client_last_active[websocket] = datetime.now()
            data = json.loads(message)
            if 'action' in data:
                if data['action'] == 'subscribe':
                    if validate_subscription_data(data):
                        await third_party_manager.subscribe(websocket, data)
                    else:
                        await websocket.send("Invalid subscription data.")
                elif data['action'] == 'unsubscribe':
                    await third_party_manager.close(websocket)
            else:
                # 检查是否是有效的普通消息
                if validate_message(data):
                    for client in connected_clients:
                        if client != websocket:
                            await client.send(message)
                else:
                    await websocket.send("Invalid message format.")
    except websockets.exceptions.ConnectionClosedError:
        print("WebSocket connection closed with error.")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            client_last_active.pop(websocket, None)
            await cleanup(websocket)


async def cleanup(websocket):
    await third_party_manager.close(websocket)
    if websocket in third_party_connections:
        await third_party_connections[websocket].close()
        del third_party_connections[websocket]


def validate_subscription_data(data):
    # 添加对订阅数据的验证逻辑
    return "params" in data


def validate_message(data):
    # 添加对消息数据的验证逻辑
    return isinstance(data, dict)  # 简单示例


async def check_inactive_clients():
    while True:
        if connected_clients:
            print(connected_clients)
            now = datetime.now()
            inactive_clients = [ws for ws, last_active in client_last_active.items()
                                if now - last_active > timedelta(seconds=20)]
            for ws in inactive_clients:
                if ws in connected_clients:
                    print("Closing inactive connection.")
                    await ws.close(reason='Heartbeat timeout')
                    connected_clients.remove(ws)
                    client_last_active.pop(ws, None)
                    await third_party_manager.close(ws)
        await asyncio.sleep(10)  # Check every 5 seconds


async def main():
    server = await websockets.serve(handle_client, 'localhost', 8888)
    asyncio.create_task(check_inactive_clients())
    await server.wait_closed()

asyncio.run(main())
