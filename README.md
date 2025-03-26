# ShowMeJM

## 介绍
这是可以帮你下载漫画并发送给QQ的插件, 本插件仅包含图片打包和上传功能, 请不要使用此插件向其他人传播不和谐的内容

图片转pdf的部分参考了此项目的代码: [image2pdf](https://github.com/salikx/image2pdf)

支持分批次处理图片, 分批打包
## 安装

配置完成 [LangBot](https://github.com/RockChinQ/LangBot) 主程序后使用管理员账号向机器人发送命令即可安装：

```
!plugin get https://github.com/exneverbur/ShowMeJM
```
或查看详细的[插件安装说明](https://docs.langbot.app/plugin/plugin-intro.html#%E6%8F%92%E4%BB%B6%E7%94%A8%E6%B3%95)

## 使用

<!-- 插件开发者自行填写插件使用说明 -->
首先要在消息平台配置http客户端

(当前在napcat, llonebot测试过功能正常, 其他消息平台可以自行参考平台官方文档修改发送请求部分的代码)

napcat为例:

1.在网络配置中新建, 选择http服务器, 填写你的host和port(注意端口号不要被其他程序占用) 如果langbot和napcat在同一网络环境下host直接填写127.0.0.1或localhost, 配置完可以在浏览器访问一下, 比如127.0.0.1:2333, 如果返回信息里有'NapCat4 Is Running'字样说明运行正常。只要你在napcat配置的url+端口号在langbot所在的网络环境下能正常访问到就ok

![img.png](img/1.png)

2.在本项目的main.py中修改http_host和http_port两个变量即可

若你在消息平台配置了token, 则也需要将同样的token添加在此处的token属性中

![img.png](img/img8.png)

3.在本项目的main.py中按需调整打包参数

![img_6.png](img/3.png)

4.修改有关下载文件的配置(插件文件夹中的config.yml)中的文件保存路径以及其他配置, 图中框选出来的值要改成你自己本地的存储路径, 下载的图片和解析后的pdf都会存在这里 其他配置不要修改, 一定要修改请参考[此文档](https://github.com/hect0x7/JMComic-Crawler-Python/blob/master/assets/docs/sources/option_file_syntax.md)

![img_3.png](img/2.png)

## 指令

| 指令                       |      含义       |      示例       |
|:-------------------------|:-------------:|:-------------:|
| jm                       |    获取指令帮助     |      jm       |
| jm [jm号]                 | 获取并上传指定jm号的漫画 |   jm 350234   |
| 查jm [关键词/标签] [页码(默认第一页)] |      搜索       | 查jm 鸣潮,+无修正 2 |

## 效果
单文件打包

![单文件上传.png](img/6.png)

分批打包

![img_3.png](img/4.png)

自动匹配逆天文案

![img_2.png](img/5.png)

搜索

![img_1.png](img/7.png)
## 计划功能

1.可以重复利用已下载的文件, 并删除指定天数前下载的文件以释放硬盘空间

2.增加其他消息平台的适配

## 已知BUG

暂未发现, 欢迎提issue

![img.png](img/img.png)
