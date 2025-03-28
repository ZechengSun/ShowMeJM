from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
import jmcomic
from jmcomic import JmSearchPage
import re

from plugins.ShowMeJM.utils import domain_checker, jm_file_resolver
from plugins.ShowMeJM.utils.jm_options import JmOptions


# 注册插件
@register(name="ShowMeJM", description="jm下载", version="1.8", author="exneverbur")
class MyPlugin(BasePlugin):
    init_options = {
        # 消息平台的域名,端口号和token
        # 使用时需在napcat内配置http服务器 host和port对应好
        'http_host': 'localhost',
        'http_port': 2333,
        # 若消息平台未配置token则留空 否则填写配置的token
        'token': '',
        # 打包成pdf时每批处理的图片数量 每批越小内存占用越小, 但速度也会越慢
        'batch_size': 100,
        # 每个pdf中最多有多少个图片 超过此数量时将会创建新的pdf文件 设置为0则不限制, 所有图片都在一个pdf文件中
        'pdf_max_pages': 200,
        # 上传到群文件的哪个目录?默认"/"是传到根目录 如果指定目录要提前在群文件里建好文件夹
        'group_folder': '/',
        # 是否开启自动匹配消息中的jm号功能(消息中的所有数字加起来是6~7位数字就触发下载本子) 此功能可能会下载很多不需要的本子占据硬盘, 请谨慎开启
        'auto_find_jm': True,
        # 如果成功找到本子是否停止触发其他插件(Ture:若找到本子则后续其他插件不会触发)
        'prevent_default': True,
        # 配置文件所在位置
        'option': 'plugins/ShowMeJM/config.yml'
    }

    options = JmOptions.from_dict(init_options)

    # 插件加载时触发
    def __init__(self, host: APIHost):
        super().__init__(host)

    # 异步初始化
    async def initialize(self):
        pass

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
        elif cleaned_text.startswith('jm'):
            await self.do_download(ctx, cleaned_text)
        elif cleaned_text.startswith('查jm'):
            await self.do_search(ctx, cleaned_text)
        # 匹配消息中包含的 6~7 位数字
        elif self.options.auto_find_jm:
            await self.do_auto_find_jm(ctx, cleaned_text)
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

    # 执行JM的搜索
    async def do_search(self, ctx: EventContext, cleaned_text: str):
        args = self.parse_command(ctx, cleaned_text)
        if len(args) == 0:
            await ctx.reply("请指定搜索条件, 格式: 查jm [关键词/标签] [页码(默认第一页)]\n例: 查jm 鸣潮,+无修正 2")
            return
        page = int(args[1]) if len(args) > 1 else 1
        config = jmcomic.create_option_by_file(self.options.option)
        client = config.new_jm_client()
        search_query = args[0]
        tags = search_query.replace(',', ' ').replace('，', ' ')
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
        await ctx.reply(search_result)

    # 更新域名
    async def do_update_domain(self, ctx: EventContext):
        await ctx.reply("检查中, 请稍后...")
        # 自动将可用域名加进配置文件中
        domains = domain_checker.get_usable_domain(self.options.option)
        usable_domains = []
        check_result = "域名连接状态检查完成√\n"
        for domain, status in domains:
            check_result += f"{domain}: {status}\n"
            if status == 'ok':
                usable_domains.append(domain)
        await ctx.reply(check_result)
        try:
            domain_checker.update_option_domain(self.options.option, usable_domains)
        except Exception as e:
            await ctx.reply("修改配置文件时发生问题: " + str(e))
            return
        await ctx.reply(
            "已将可用域名添加到配置文件中~\n PS:如遇网络原因下载失败, 对我说:'jm清空域名'指令可以将配置文件中的域名清除, 此时我将自动寻找可用域名哦")

    # 清空域名
    async def do_clear_domain(self, ctx: EventContext):
        domain_checker.clear_domain(self.options.option)
        await ctx.reply(
            "已将默认下载域名全部清空, 我将会自行寻找可用域名\n PS:对我说:'jm更新域名'指令可以查看当前可用域名并添加进配置文件中哦")

    # 下载漫画
    async def do_download(self, ctx: EventContext, cleaned_text: str):
        args = self.parse_command(ctx, cleaned_text)
        if len(args) == 0:
            await ctx.reply(
                "你是不是在找: \n"
                "1.搜索功能: \n"
                "格式: 查jm [关键词/标签] [页码(默认第一页)]\n"
                "例: 查jm 鸣潮,+无修正 2\n\n"
                "2.下载功能:\n"
                "格式:jm [jm号]\n"
                "例: jm 350234\n\n"
                "3.寻找可用下载域名:\n"
                "格式:jm更新域名\n\n"
                "4.清除默认域名:\n"
                "格式:jm清空域名"
            )
            if self.options.prevent_default:
                # 阻止该事件默认行为（向接口获取回复）
                ctx.prevent_default()
            return
        await ctx.reply(f"即将开始下载{args[0]}, 请稍后...")
        await jm_file_resolver.before_download(ctx, self.options, args[0])

    # 匹配逆天文案
    async def do_auto_find_jm(self, ctx: EventContext, cleaned_text: str):
        numbers = re.findall(r'\d+', cleaned_text)
        concatenated_numbers = ''.join(numbers)
        if 6 <= len(concatenated_numbers) <= 7:
            await ctx.reply(f"你提到了{concatenated_numbers}...对吧?")
            await jm_file_resolver.before_download(ctx, self.options, concatenated_numbers)
