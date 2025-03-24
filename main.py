from pkg.platform.types import File
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
import re
import jmcomic, os, time, yaml
from PIL import Image
import http.client
import json
import time
# 注册插件
@register(name="ShowMeJM", description="jm下载", version="0.1", author="exneverbur")
class MyPlugin(BasePlugin):

    # napcat的域名和端口号
    # 使用时需在napcat内配置http服务器 host和port对应好
    http_host = "localhost"
    http_port = 2333

    # 插件加载时触发
    def __init__(self, host: APIHost):
        super().__init__(host)

    # 异步初始化
    async def initialize(self):
        pass

    @handler(PersonNormalMessageReceived)
    @handler(GroupNormalMessageReceived)
    async def message_received(self, ctx: EventContext):
        print("收到消息:" + ctx.event.text_message)
        receive_text = ctx.event.text_message
        cleaned_text = re.sub(r'@\S+\s*', '', receive_text).strip()
        if cleaned_text.startswith('jm'):  # 检查是否为命令
            parts = cleaned_text.split(' ', 1)  # 分割命令和参数
            command = parts[0]
            if len(parts) > 1:
                args = parts[1]
            else:
                return ctx.add_return("reply", ["请指定jm号"])
            print("接收指令:",command, "参数：", args)
            pdf_path = ''
            try:
                pdf_path = self.download_and_get_pdf(args)
            except Exception as e:
                ctx.add_return("reply", ["下载时出现问题:" + str(e)])
            print("文件路径:" + pdf_path)
            if pdf_path and os.path.exists(pdf_path):
                try:
                    if ctx.event.launcher_type == "person":
                        self.upload_private_file(ctx.event.sender_id, pdf_path, 'jm' + args + '-' + str(time.time()) + '.pdf')
                    else:
                        self.upload_group_file(ctx.event.launcher_id, pdf_path, 'jm' + args + '-' + str(time.time()) + '.pdf')
                    ctx.add_return("reply", ["你的本子即将送达~"])
                    # 阻止该事件默认行为（向接口获取回复）
                    ctx.prevent_default()
                except Exception as e:
                    ctx.add_return("reply", ["发送文件时出错:" + str(e)])
            else:
                ctx.add_return("reply", ["没有找到对应文件" + pdf_path])




    # 插件卸载时触发
    def __del__(self):
        pass

    # 下载图片
    def download_and_get_pdf(self, arg):
        # 自定义设置：
        config = "plugins/ShowMeJM/config.yml"
        loadConfig = jmcomic.JmOption.from_file(config)
        ids = [arg]
        downloadedFileName = ''
        for manhua in ids:
            album, dler = jmcomic.download_album(manhua,loadConfig)
            downloadedFileName = album.name

        with open(config, "r", encoding="utf8") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            path = data["dir_rule"]["base_dir"]

        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_dir():
                    if os.path.exists(os.path.join(path + '/' + entry.name + ".pdf")):
                        if downloadedFileName == entry.name:
                            return os.path.join(path + '/' + entry.name + ".pdf")
                        print("文件：《%s》 已存在，跳过" % entry.name)
                    else:
                        print("开始转换：%s " % entry.name)
                        return self.all2PDF(path + "/" + entry.name, path, entry.name)

    def all2PDF(self, input_folder, pdfpath, pdfname):
        start_time = time.time()
        paht = input_folder
        zimulu = []  # 子目录（里面为image）
        image = []  # 子目录图集
        sources = []  # pdf格式的图

        with os.scandir(paht) as entries:
            for entry in entries:
                if entry.is_dir():
                    zimulu.append(int(entry.name))
        # 对数字进行排序
        zimulu.sort()

        for i in zimulu:
            with os.scandir(paht + "/" + str(i)) as entries:
                for entry in entries:
                    if entry.is_dir():
                        print("这一级不应该有子目录")
                    if entry.is_file():
                        image.append(paht + "/" + str(i) + "/" + entry.name)

        if "jpg" in image[0]:
            output = Image.open(image[0])
            image.pop(0)

        for file in image:
            if "jpg" in file:
                img_file = Image.open(file)
                if img_file.mode == "RGB":
                    img_file = img_file.convert("RGB")
                sources.append(img_file)

        pdf_file_path = pdfpath + "/" + pdfname
        if pdf_file_path.endswith(".pdf") == False:
            pdf_file_path = pdf_file_path + ".pdf"
        output.save(pdf_file_path, "pdf", save_all=True, append_images=sources)
        end_time = time.time()
        run_time = end_time - start_time
        print("运行时间：%3.2f 秒" % run_time)
        return pdf_file_path

    def upload_private_file(self, user_id, file, name):
        conn = http.client.HTTPConnection(self.http_host, self.http_port)
        payload = json.dumps({
            "user_id": user_id,
            "file": file,
            "name": name
        })
        headers = {
            'Content-Type': 'application/json'
        }
        conn.request("POST", "/upload_private_file", payload, headers)

    def upload_group_file(self, group_id, file, name):
        conn = http.client.HTTPConnection(self.http_host, self.http_port)
        payload = json.dumps({
            "group_id": group_id,
            "file": file,
            "name": name,
            "folder_id": "/"
        })
        headers = {
            'Content-Type': 'application/json'
        }
        conn.request("POST", "/upload_group_file", payload, headers)