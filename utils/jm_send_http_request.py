"""
向消息平台发送上传文件的请求
"""

import aiohttp

from plugins.ShowMeJM.utils.jm_options import JmOptions


# 发送私聊文件
async def upload_private_file(options: JmOptions, user_id, file, name):
    url = f"http://{options.http_host}:{options.http_port}/upload_private_file"
    payload = {
        "user_id": user_id,
        "file": file,
        "name": name
    }
    if options.token == "":
        headers = {
            'Content-Type': 'application/json'
        }
    else:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {options.token}'
        }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"上传失败，状态码: {response.status}, 错误信息: {response.text}")
            res = await response.json()
            print("消息平台返回->" + str(res))
            if res["status"] != "ok":
                raise Exception(f"上传失败，状态码: {res['status']}, 描述: {res['message']}\n完整消息: {str(res)}")


# 发送群文件
async def upload_group_file(options: JmOptions, group_id, file, name):
    url = f"http://{options.http_host}:{options.http_port}/upload_group_file"
    payload = {
        "group_id": group_id,
        "file": file,
        "name": name,
        "folder_id": options.group_folder
    }
    if options.token == "":
        headers = {
            'Content-Type': 'application/json'
        }
    else:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {options.token}'
        }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"上传失败，状态码: {response.status}, 错误信息: {response.text}")
            res = await response.json()
            print("消息平台返回->" + str(res))
            if res["status"] != "ok":
                raise Exception(f"上传失败，状态码: {res['status']}, 描述: {res['message']}\n完整消息: {str(res)}")
