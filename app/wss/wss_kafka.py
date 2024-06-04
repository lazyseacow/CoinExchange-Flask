# -*- coding: gbk -*-
import asyncio
import json
import logging

import websockets
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer


# 存储客户端订阅信息
subscriptions = {}
clients = {}
subscriptions_lock = asyncio.Lock()
binance_ws = None


# Kafka Producer配置
async def create_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='localhost:9092')
    # 记得启动producer
    await producer.start()
    return producer


async def manage_binance_connection(kafka_producer):
    global binance_ws
    while True:
        try:
            # 维持到币安的WebSocket连接
            async with websockets.connect("wss://stream.binance.com:443/stream") as ws:
                binance_ws = ws
                while True:
                    message = await ws.recv()
                    # 接收币安消息并推送到Kafka
                    await kafka_producer.send_and_wait('binance_topic', message.encode('utf-8'))
        except Exception as e:
            print(f"Error with Binance WebSocket: {e}")
            binance_ws = None
            await asyncio.sleep(5)  # 重试连接前等待


async def handle_client(websocket, path):
    global clients, binance_ws
    client_id = id(websocket)
    clients[client_id] = websocket
    # client_ip = websocket.remote_address[0]
    # client_port = websocket.remote_address[1]
    try:
        async for message in websocket:
            message = json.loads(message)
            action = message['action']
            params_list = message['params']

            if action == 'true':
                async with subscriptions_lock:
                    for params in params_list:
                        if params not in subscriptions:
                            subscriptions[params] = set()
                            # 发送订阅请求到币安
                            if binance_ws:
                                await binance_ws.send(json.dumps({
                                    "method": "SUBSCRIBE",
                                    "params": [params],
                                    "id": client_id
                                }))
                        subscriptions[params].add(websocket)

            # action为false时，仅用作心跳检测，不进行取消订阅处理
    finally:
        await handle_disconnect(websocket)


async def handle_disconnect(websocket):
    global binance_ws
    client_id = id(websocket)
    subscriptions_to_remove = []
    for params, clients_set in list(subscriptions.items()):
        if websocket in clients_set:
            clients_set.remove(websocket)
            if not clients_set:
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


async def start_kafka_consumer():
    # 创建Kafka消费者配置
    consumer = AIOKafkaConsumer(
        'binance_topic',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest'
    )
    # 开始消费消息
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode())
            stream = data.get("stream")
            if stream in subscriptions:
                # 将消息发送给所有订阅了此stream的客户端
                for client in subscriptions[stream]:
                    if client.open:
                        await client.send(json.dumps(data))
                        print(f'client: {client} received send {data}')
    finally:
        # 正确关闭消费者
        await consumer.stop()


async def main():
    kafka_producer = await create_kafka_producer()
    # 启动Kafka生产者
    await kafka_producer.start()
    # 启动Kafka消费者任务
    consumer_task = asyncio.create_task(start_kafka_consumer())
    # 维持币安WebSocket连接
    binance_task = asyncio.create_task(manage_binance_connection(kafka_producer))
    # 创建WebSocket服务器
    start_server = websockets.serve(handle_client, "0.0.0.0", 8888)
    await start_server
    # 运行直到被取消
    await asyncio.Future()  # Runs forever


if __name__ == "__main__":
    asyncio.run(main())
