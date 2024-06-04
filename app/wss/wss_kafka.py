# -*- coding: gbk -*-
import asyncio
import json
import logging

import websockets
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer


# �洢�ͻ��˶�����Ϣ
subscriptions = {}
clients = {}
subscriptions_lock = asyncio.Lock()
binance_ws = None


# Kafka Producer����
async def create_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='localhost:9092')
    # �ǵ�����producer
    await producer.start()
    return producer


async def manage_binance_connection(kafka_producer):
    global binance_ws
    while True:
        try:
            # ά�ֵ��Ұ���WebSocket����
            async with websockets.connect("wss://stream.binance.com:443/stream") as ws:
                binance_ws = ws
                while True:
                    message = await ws.recv()
                    # ���ձҰ���Ϣ�����͵�Kafka
                    await kafka_producer.send_and_wait('binance_topic', message.encode('utf-8'))
        except Exception as e:
            print(f"Error with Binance WebSocket: {e}")
            binance_ws = None
            await asyncio.sleep(5)  # ��������ǰ�ȴ�


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
                            # ���Ͷ������󵽱Ұ�
                            if binance_ws:
                                await binance_ws.send(json.dumps({
                                    "method": "SUBSCRIBE",
                                    "params": [params],
                                    "id": client_id
                                }))
                        subscriptions[params].add(websocket)

            # actionΪfalseʱ��������������⣬������ȡ�����Ĵ���
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
    # ����Kafka����������
    consumer = AIOKafkaConsumer(
        'binance_topic',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest'
    )
    # ��ʼ������Ϣ
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode())
            stream = data.get("stream")
            if stream in subscriptions:
                # ����Ϣ���͸����ж����˴�stream�Ŀͻ���
                for client in subscriptions[stream]:
                    if client.open:
                        await client.send(json.dumps(data))
                        print(f'client: {client} received send {data}')
    finally:
        # ��ȷ�ر�������
        await consumer.stop()


async def main():
    kafka_producer = await create_kafka_producer()
    # ����Kafka������
    await kafka_producer.start()
    # ����Kafka����������
    consumer_task = asyncio.create_task(start_kafka_consumer())
    # ά�ֱҰ�WebSocket����
    binance_task = asyncio.create_task(manage_binance_connection(kafka_producer))
    # ����WebSocket������
    start_server = websockets.serve(handle_client, "0.0.0.0", 8888)
    await start_server
    # ����ֱ����ȡ��
    await asyncio.Future()  # Runs forever


if __name__ == "__main__":
    asyncio.run(main())
