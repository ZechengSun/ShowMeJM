from pkg.platform.types import MessageChain, Image
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
import jmcomic
from jmcomic import JmSearchPage, JmOption
import re
import random
import os
import aiofiles
import asyncio
import json
from datetime import datetime, timedelta

from plugins.ShowMeJM.utils import domain_checker, jm_file_resolver
from plugins.ShowMeJM.utils.jm_options import JmOptions


# 注册插件
@register(name="ShowMeJM", description="jm下载", version="2.1", author="exneverbur")
class MyPlugin(BasePlugin):
    init_options = {
        "platform": 'napcat',
        'http_host': '192.168.5.2',
        'http_port': 13000,
        'token': '',
        'batch_size': 20,
        'pdf_max_pages': 200,
        'group_folder': '/',
        'auto_find_jm': True,
        'prevent_default': True,
        'option': 'plugins/ShowMeJM/config.yml'
    }

    options = JmOptions.from_dict(init_options)

    # 插件加载时触发
    def __init__(self, host: APIHost):
        super().__init__(host)
        self.cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        self.cache_file = os.path.join(self.cache_dir, "jm_max_page.json")  # 使用 JSON 文件
        self.semaphore = asyncio.Semaphore(5)

    # 异步初始化插件时触发
    async def initialize(self):
        await self.save_max_page()

    async def save_max_page(self):
        os.makedirs(self.cache_dir, exist_ok=True)

        # 读取缓存文件中的数据
        cache_data = {}
        if os.path.exists(self.cache_file):
            try:
                async with aiofiles.open(self.cache_file, "r") as f:
                    content = await f.read()
                    if content.strip():
                        cache_data = json.loads(content)
            except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
                print(f"读取缓存文件时出错: {e}")

        # 检查是否已有该 search_query 的最大页数记录
        if "" in cache_data:
            print(f"查询 '' 已缓存，最大页数为: {cache_data['']['max_page']}，时间为: {cache_data['']['timestamp']}")
            return

        try:
            # 获取最大页数
            max_page = await self.run_with_semaphore(
                self.find_max_page,
                query='',
                initial_page=3000,
            )
            # 更新缓存数据
            cache_data[""] = {
                "max_page": max_page,
                "timestamp": datetime.now().isoformat(),
                "reliable": True  # 设置为可靠
            }

            # 保存到 JSON 文件
            async with aiofiles.open(self.cache_file, "w") as f:
                await f.write(json.dumps(cache_data, indent=4))
            print(f"最大页码已保存到 {self.cache_file}，查询 '' 的值为: {max_page}")
        except Exception as e:
            print(f"获取最大页码时发生错误: {e}")

    async def run_with_semaphore(self, func, *args, **kwargs):
        async with self.semaphore:
            return await func(*args, **kwargs)

    async def find_max_page(self, query='', initial_page=3000):
        print(f"正在获取搜索结果为 '{query}' 的分页目录总页数")
        config = jmcomic.create_option_by_file(self.options.option)
        client = config.new_jm_client()
        result = client.search_site(search_query=query, page=initial_page)

        if result:
            last_album_id = list(result.iter_id_title())[-1][0]
            print(f"最后一页的最后一个本子 id 是：{last_album_id}")
        else:
            raise ValueError(f"第 {initial_page} 页无结果，无法确定最大页数范围")

        low, high = 1, initial_page
        while low < high:
            mid = (low + high) // 2
            try:
                result = client.search_site(search_query=query, page=mid)
                current_last_album_id = list(result.iter_id_title())[-1][0]
                print(f"第 {mid} 页的最后一个本子 id 是：{current_last_album_id}")
                if current_last_album_id == last_album_id:
                    high = mid
                else:
                    low = mid + 1
            except Exception:
                high = mid

        max_page = high - 1
        print(f"分页目录总页数为 {max_page}")
        return max_page

    @handler(PersonNormalMessageReceived)
    @handler(GroupNormalMessageReceived)
    async def message_received(self, ctx: EventContext):
        receive_text = ctx.event.text_message
        cleaned_text = re.sub(r'@\S+\s*', '', receive_text).strip()
        prevent_default = self.options.prevent_default
        if cleaned_text.startswith('jm更新域名'):
            await self.do_update_domain(ctx)
        elif cleaned_text.startswith('jm清空域名'):
            await self.do_clear_domain(ctx)
        elif cleaned_text.startswith('随机jm'):
            await self.do_random_download(ctx, cleaned_text)
        elif cleaned_text.startswith('jm'):
            await self.do_download(ctx, cleaned_text)
        elif cleaned_text.startswith('查jm'):
            await self.do_search(ctx, cleaned_text)
        # 匹配消息中包含的 6~7 位数字
        elif self.options.auto_find_jm:
            prevent_default = False
            matched = await self.do_auto_find_jm(ctx, cleaned_text)
            if matched and self.options.prevent_default:
                prevent_default = True
        else:
            # 未匹配上任何指令 说明此次消息与本插件无关
            prevent_default = False
        if prevent_default:
            # 阻止该事件默认行为（向接口获取回复）
            ctx.prevent_default()

    # 插件卸载时触发
    def __del__(self):
        pass

    def parse_command(self, ctx: EventContext, message: str):
        parts = message.split(' ')  # 分割命令和参数
        command = parts[0]
        args = []
        if len(parts) > 1:
            args = parts[1:]
        print("接收指令:", command, "参数：", args)
        return args

    # 更新域名
    async def do_update_domain(self, ctx: EventContext):
        await ctx.reply(MessageChain(["检查中, 请稍后..."]))
        # 自动将可用域名加进配置文件中
        domains = domain_checker.get_usable_domain(self.options.option)
        usable_domains = []
        check_result = "域名连接状态检查完成√\n"
        for domain, status in domains:
            check_result += f"{domain}: {status}\n"
            if status == 'ok':
                usable_domains.append(domain)
        await ctx.reply(MessageChain([check_result]))
        try:
            domain_checker.update_option_domain(self.options.option, usable_domains)
        except Exception as e:
            await ctx.reply(MessageChain(["修改配置文件时发生问题: " + str(e)]))
            return
        await ctx.reply(MessageChain([
                                         "已将可用域名添加到配置文件中~\n PS:如遇网络原因下载失败, 对我说:'jm清空域名'指令可以将配置文件中的域名清除, 此时我将自动寻找可用域名哦"]))

    # 清空域名
    async def do_clear_domain(self, ctx: EventContext):
        domain_checker.clear_domain(self.options.option)
        await ctx.reply(MessageChain([
                                         "已将默认下载域名全部清空, 我将会自行寻找可用域名\n PS:对我说:'jm更新域名'指令可以查看当前可用域名并添加进配置文件中哦"]))

    # 随机下载漫画
    async def do_random_download(self, ctx: EventContext, cleaned_text):
        args = self.parse_command(ctx, cleaned_text)
        client = JmOption.default().new_jm_client()

        if len(args) == 0:
            # 在全部本子中随机
            await ctx.reply(MessageChain(["正在寻找随机本子，请稍候..."]))
            try:
                # 读取缓存文件中的最大页数
                async with aiofiles.open(self.cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.loads(await f.read())
                    max_page = cache_data.get("", {}).get("max_page", 3000)  # 默认最大页数为 3000
            except (FileNotFoundError, ValueError, json.JSONDecodeError):
                max_page = 3000

            if max_page < 1:
                await ctx.reply(MessageChain(["随机本子下载失败：最大页数无效"]))
                return

            random_page = random.randint(1, max_page)
            try:
                result = client.search_site(search_query='', page=random_page)
                album_list = list(result.iter_id_title())
                if not album_list:
                    raise ValueError("未找到任何漫画")

                random_index = random.randint(0, len(album_list) - 1)
                selected_album_id = album_list[random_index][0]
                await ctx.reply(MessageChain([f"找到的随机本子 ID 是：{selected_album_id}，即将开始下载，请稍候..."]))
                await jm_file_resolver.before_download(ctx, self.options, selected_album_id)
            except Exception as e:
                await ctx.reply(MessageChain([f"随机本子下载失败：{e}"]))

        elif len(args) == 1:
            # 在指定 query 的搜索结果中随机
            search_query = args[0]
            tags = re.sub(r'[，,]+', ' ', search_query)  # 替换逗号为空格
            await ctx.reply(MessageChain([f"正在寻找关键词为 '{tags}' 的随机本子，用时较长，请稍候..."]))

            try:
                # 获取指定 query 的最大页数
                async with aiofiles.open(self.cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.loads(await f.read())
                    query_data = cache_data.get(tags, {})
                    reliable = query_data.get("reliable", False)
                    last_timestamp_str = query_data.get("timestamp")
                    last_timestamp_dt = datetime.fromisoformat(last_timestamp_str) if last_timestamp_str else None
                    max_page = query_data.get("max_page", 3000)

                    # 检查可靠性和时间戳
                    if not reliable or (
                            last_timestamp_dt and (datetime.now() - last_timestamp_dt > timedelta(hours=24))):
                        max_page_updated = await self.run_with_semaphore(
                            self.find_max_page,
                            query=tags,
                        )
                        cache_data[tags] = {
                            "max_page": max_page_updated,
                            "timestamp": datetime.now().isoformat(),
                            "reliable": True,
                        }
                        async with aiofiles.open(self.cache_file, "w", encoding="utf-8") as writer_f:
                            await writer_f.write(json.dumps(cache_data, ensure_ascii=False, indent=4))
                        max_page = max_page_updated

                if max_page < 1:
                    await ctx.reply(MessageChain([f"随机本子下载失败：关键词 '{tags}' 的最大页数无效"]))
                    return

                random_page = random.randint(1, max_page)
                result = client.search_site(search_query=tags, page=random_page)
                album_list = list(result.iter_id_title())
                if not album_list:
                    raise ValueError(f"未找到关键词 '{tags}' 的任何漫画")

                random_index = random.randint(0, len(album_list) - 1)
                selected_album_id = album_list[random_index][0]
                await ctx.reply(MessageChain([f"找到的随机本子 ID 是：{selected_album_id}，即将开始下载，请稍候..."]))
                await jm_file_resolver.before_download(ctx, self.options, selected_album_id)
            except Exception as e:
                await ctx.reply(MessageChain([f"随机本子下载失败：{e}"]))

        else:
            # 参数错误处理
            await ctx.reply(MessageChain([f"使用方法不正确，请输入指令 /jm 获取使用说明"]))

    # 下载漫画
    async def do_download(self, ctx: EventContext, cleaned_text: str):
        args = self.parse_command(ctx, cleaned_text)
        if len(args) == 0:
            await ctx.reply(MessageChain([
                                             "你是不是在找: \n""1.搜索功能: \n""格式: 查jm [关键词/标签] [页码(默认第一页)]\n""例: 查jm 鸣潮,+无修正 2\n\n""2.下载指定id的本子:\n""格式:jm [jm号]\n""例: jm 350234\n\n""4.下载随机本子:\n""格式:随机jm\n\n""3.寻找可用下载域名:\n""格式:jm更新域名\n\n""4.清除默认域名:\n""格式:jm清空域名"]))
            if self.options.prevent_default:
                # 阻止该事件默认行为（向接口获取回复）
                ctx.prevent_default()
            return
        await ctx.reply(MessageChain([f"即将开始下载{args[0]}, 请稍候..."]))
        await jm_file_resolver.before_download(ctx, self.options, args[0])

    # 执行JM的搜索
    async def do_search(self, ctx: EventContext, cleaned_text: str):
        args = self.parse_command(ctx, cleaned_text)
        if len(args) == 0:
            # image_path = os.path.join(self.cache_dir, "jmSearch.png")
            # if os.path.exists(image_path):
            #     await ctx.reply(MessageChain([Image(path=image_path)]))
            await ctx.reply(MessageChain(
                [
                    "请指定搜索条件, 格式: 查jm [关键词/标签] [页码(默认第一页)]\n例: 查jm 鸣潮,+无修正 2\n使用提示: 请使用中英文任意逗号隔开每个关键词/标签，切勿使用空格进行分割"]))
            return
        page = int(args[1]) if len(args) > 1 else 1
        config = jmcomic.create_option_by_file(self.options.option)
        client = config.new_jm_client()
        search_query = args[0]
        tags = re.sub(r'[，,]+', ' ', search_query)
        search_page: JmSearchPage = client.search_site(search_query=tags, page=page)
        # search_page默认的迭代方式是page.iter_id_title()，每次迭代返回 albun_id, title
        results = []
        for album_id, title in search_page:
            results.append([album_id, title])
        search_result = f"当前为第{page}页\n\n"
        i = 1
        for itemArr in results:
            search_result += f"{i}. [{itemArr[0]}]: {itemArr[1]}\n"
            i += 1
        search_result += "\n对我说jm jm号进行下载吧~"
        await ctx.reply(MessageChain([search_result]))

    # 匹配逆天文案
    async def do_auto_find_jm(self, ctx: EventContext, cleaned_text: str):
        numbers = re.findall(r'\d+', cleaned_text)
        concatenated_numbers = ''.join(numbers)
        if 6 <= len(concatenated_numbers) <= 7:
            await ctx.reply(MessageChain([f"你提到了{concatenated_numbers}...对吧?"]))
            await jm_file_resolver.before_download(ctx, self.options, concatenated_numbers)
            return True
        return False
