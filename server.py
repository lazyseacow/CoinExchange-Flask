from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
import asyncio
import websockets
from websocket import create_connection
import json

from gevent import spawn

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent',)

connected_clients = set()
third_party_url = "wss://stream.binance.com:9443/ws"
third_party_connections = {}

@socketio.on('connect')
def handle_connect(data):
    print('Client connected')
    print(data)
    connected_clients.add(request.sid)

@socketio.on('disconnect')
def handle_disconnect():

    print('Client disconnected')
    connected_clients.remove(request.sid)
    if request.sid in third_party_connections:
        spawn(close_third_party_connection(request.sid))

@socketio.on('subscribe')
def handle_subscribe(data):
    print(data)
    print("subscribe was called")
    spawn(subscribe_to_third_party(third_party_url, request.sid, data))

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    spawn(unsubscribe_from_third_party(request.sid, data))

def subscribe_to_third_party(url, client_sid, data):
    ws = create_connection(url)
    third_party_connections[client_sid] = ws
    try:
        subscribe_message = json.dumps(data.get('params'))
        ws.send(subscribe_message)
        while True:
            message = ws.recv()
            print(message)
            socketio.emit('third_party_data', {'data': message}, to=client_sid)
    finally:
        ws.close()
        if client_sid in third_party_connections:
            del third_party_connections[client_sid]


def unsubscribe_from_third_party(client_sid, data):
    if client_sid in third_party_connections:
        ws = third_party_connections[client_sid]
        ws.send(json.dumps(data))
        ws.close()
        del third_party_connections[client_sid]


def close_third_party_connection(client_sid):
    if client_sid in third_party_connections:
        ws = third_party_connections[client_sid]
        ws.close()
        del third_party_connections[client_sid]

if __name__ == '__main__':
    socketio.run(app, debug=True)
