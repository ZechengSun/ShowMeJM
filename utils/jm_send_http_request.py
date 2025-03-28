"""
向消息平台发送上传文件的请求
"""

import aiohttp

from plugins.ShowMeJM.utils.jm_options import JmOptions
from plugins.ShowMeJM.utils.jm_platform_http_adapter import *

# 发送私聊文件
async def upload_private_file(options: JmOptions, user_id, file, name):
    url, payload, headers = get_upload_private_file_request_body(options, user_id, file, name)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"上传失败，状态码: {response.status}, 错误信息: {response.text}")
            res = await response.json()
            print("消息平台返回->" + str(res))
            if res["status"] != "ok":
                raise Exception(f"上传失败，状态码: {res['status']}\n完整消息: {str(res)}")


# 发送群文件
async def upload_group_file(options: JmOptions, group_id, file, name):
    url, payload, headers = get_upload_group_file_request_body(options, group_id, file, name)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"上传失败，状态码: {response.status}, 错误信息: {response.text}")
            res = await response.json()
            print("消息平台返回->" + str(res))
            if res["status"] != "ok":
                raise Exception(f"上传失败，状态码: {res['status']}\n完整消息: {str(res)}")
