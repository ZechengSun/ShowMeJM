# ShowMeJM

<!--
## 插件开发者详阅

### 开始

此仓库是 LangBot 插件模板，您可以直接在 GitHub 仓库中点击右上角的 "Use this template" 以创建你的插件。  
接下来按照以下步骤修改模板代码：

#### 修改模板代码

- 修改此文档顶部插件名称信息
- 将此文档下方的`<插件发布仓库地址>`改为你的插件在 GitHub· 上的地址
- 补充下方的`使用`章节内容
- 修改`main.py`中的`@register`中的插件 名称、描述、版本、作者 等信息
- 修改`main.py`中的`MyPlugin`类名为你的插件类名
- 将插件所需依赖库写到`requirements.txt`中
- 根据[插件开发教程](https://docs.langbot.app/plugin/dev/tutor.html)编写插件代码
- 删除 README.md 中的注释内容


#### 发布插件

推荐将插件上传到 GitHub 代码仓库，以便用户通过下方方式安装。   
欢迎[提issue](https://github.com/RockChinQ/LangBot/issues/new?assignees=&labels=%E7%8B%AC%E7%AB%8B%E6%8F%92%E4%BB%B6&projects=&template=submit-plugin.yml&title=%5BPlugin%5D%3A+%E8%AF%B7%E6%B1%82%E7%99%BB%E8%AE%B0%E6%96%B0%E6%8F%92%E4%BB%B6)，将您的插件提交到[插件列表](https://github.com/stars/RockChinQ/lists/qchatgpt-%E6%8F%92%E4%BB%B6)

下方是给用户看的内容，按需修改
-->
## 介绍
这是可以帮你下载漫画并发送给群友/个人的插件, 本插件仅包含图片打包和上传功能, 请不要使用此插件向其他人传播不和谐的内容

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

(当前只支持napcat, 其他消息平台可以自行参考平台官方文档修改发送请求部分的代码)

napcat为例:

1.在网络配置中新建, 选择http服务器, 填写你的host和port(注意端口号不要被其他程序占用)

![img.png](img/img.png)

2.在本项目的main.py中修改http_host和http_port两个变量即可

![img_1.png](img/img_1.png)

3.在本项目的main.py中按需调整打包参数

![img_6.png](img/img_6.png)

3.修改有关下载文件的配置(插件文件夹中的config.yml)中的文件保存路径以及其他配置, 参考[此文档](https://github.com/hect0x7/JMComic-Crawler-Python/blob/master/assets/docs/sources/option_file_syntax.md)

![img_3.png](img/img_3.png)

## 效果
单文件打包

![img_4.png](img/img_4.png)

分批打包

![img_5.png](img/img_5.png)

自动匹配逆天文案

![img_7.png](img/img_7.png)
## 计划功能

1.增加搜索

2.可以重复利用已下载的文件, 并删除指定天数前下载的文件以释放硬盘空间

3.增加其他消息平台的适配

## 已知BUG

暂未发现, 欢迎提issue

![img.png](img.png)