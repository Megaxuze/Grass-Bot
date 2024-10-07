import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets import connect  # WebSocket tanpa proxy
from websockets_proxy import Proxy, proxy_connect  # WebSocket dengan proxy
from fake_useragent import UserAgent

user_agent = UserAgent()
random_user_agent = user_agent.random


async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy or user_id))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"

            if socks5_proxy:
                proxy = Proxy.from_url(socks5_proxy)
                websocket_conn = proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                               extra_headers=custom_headers)
            else:
                websocket_conn = connect(uri, ssl=ssl_context, extra_headers=custom_headers)

            async with websocket_conn as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "3.3.2"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))

        except Exception as e:
            logger.error(e)
            if socks5_proxy:
                logger.error(socks5_proxy)


async def main():
    # find user_id on the site in console: localStorage.getItem('userId')
    _user_id = input('Please Enter your user ID: ')

    try:
        with open('proxy_list.txt', 'r') as file:
            socks5_proxy_list = file.read().splitlines()
    except FileNotFoundError:
        socks5_proxy_list = []  # Jika file tidak ditemukan, tidak ada proxy yang digunakan

    # Jika tidak ada proxy, jalankan satu koneksi tanpa proxy
    if not socks5_proxy_list:
        await connect_to_wss(None, _user_id)
    else:
        tasks = [asyncio.ensure_future(connect_to_wss(i, _user_id)) for i in socks5_proxy_list]
        await asyncio.gather(*tasks)


if __name__ == '__main__':
    # Run the main function
    asyncio.run(main())
