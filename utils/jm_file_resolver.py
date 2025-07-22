"""
对文件的下载与打包
"""
import gc
import glob
import os
import re
import shutil
import time
from typing import List

import yaml

import jmcomic
from PIL import Image
from jmcomic import JmOption, PartialDownloadFailedException

from pkg.platform.types import MessageChain
from pkg.plugin.context import EventContext
from plugins.ShowMeJM.utils.jm_send_http_request import *

import pikepdf


def build_pdf_pattern(base_dir: str, album_name: str) -> str:
    safe_name = glob.escape(album_name)
    return os.path.join(base_dir, f"{safe_name}-*.pdf")


def find_existing_pdfs(base_dir: str, album_name: str) -> list[str]:
    pattern = build_pdf_pattern(base_dir, album_name)
    return glob.glob(pattern)


def load_jm_opt_from_file(yaml_path: str) -> JmOption:
    if not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"JM下载配置文件不存在：{yaml_path}")
    return JmOption.from_file(yaml_path)


def read_base_dir(yaml_path: str) -> str:
    with open(yaml_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return os.path.abspath(cfg["dir_rule"]["base_dir"])


async def before_download(ctx: EventContext, options: JmOptions, album_id: int) -> None:
    try:
        pdf_files = await download_album_and_get_pdfs(options, album_id)
        print(f"成功生成 {len(pdf_files)} 个 PDF")
        await ctx.reply(MessageChain(["本子打包已准备就绪，准备发送…"]))
        single_file_tag = len(pdf_files) == 1
        is_group = ctx.event.launcher_type != "person"
        await send_files_in_order(
            options, ctx, pdf_files, album_id, single_file_tag, is_group
        )
    except Exception as e:
        await ctx.reply(MessageChain([f"打包处理过程中出错: {e}"]))
        print("before_download exception:", e)


async def download_album_and_get_pdfs(options: JmOptions, album_id: int) -> List[str]:
    """
    下载整本并返回 PDF 绝对路径列表。
    """
    # 1. 读配置和基础目录
    jm_option = load_jm_opt_from_file(options.option)
    base_dir = read_base_dir(options.option)
    pdf_name = str(album_id)
    # 2. 如果已有 PDF，直接复用
    if existing := find_existing_pdfs(base_dir, pdf_name):
        print(f"存在现有 PDF，跳过下载：{pdf_name}")
        return existing

    # 3. 执行 JM 下载
    try:
        album, _ = jmcomic.download_album(album_id, jm_option, check_exception=True)
        pdf_name = album.album_id
    except PartialDownloadFailedException as e:
        # 做简单的补下载
        for img, error in e.downloader.download_failed_image:
            e.downloader.download_by_image_detail(img)

    # 4. 下载完再生成pdf
    album_folder = os.path.join(base_dir, pdf_name)
    return all2PDF(options, album_folder, base_dir, pdf_name)


def encrypt_pdf(input_pdf, output_pdf, password):
    """
    使用 pikepdf 为 PDF 添加密码保护
    """
    with pikepdf.open(input_pdf) as pdf:
        pdf.save(output_pdf, encryption=pikepdf.Encryption(owner=password, user=password))


def all2PDF(options, input_folder, pdfpath, pdfname):
    start_time = time.time()
    image_paths = []
    # 遍历主目录（自然排序）
    with os.scandir(input_folder) as entries:
        for entry in sorted(entries, key=lambda e: int(e.name) if e.is_dir() and e.name.isdigit() else float('inf')):
            if entry.is_dir():
                # 处理子目录内容（自然排序）
                subdir = os.path.join(input_folder, entry.name)
                with os.scandir(subdir) as sub_entries:
                    for sub_entry in sorted(sub_entries,
                                            key=lambda e: int(re.search(r'\d+', e.name).group()) if re.search(r'\d+',
                                                                                                              e.name) else float(
                                                'inf')):
                        if sub_entry.is_file():
                            image_paths.append(os.path.join(subdir, sub_entry.name))
    pdf_files = []
    total_pages = len(image_paths)
    pdf_page_size = options.pdf_max_pages if options.pdf_max_pages > 0 else total_pages

    # 分段处理逻辑优化
    for chunk_idx, page_start in enumerate(range(0, total_pages, pdf_page_size), 1):
        chunk = image_paths[page_start:page_start + pdf_page_size]
        temp_pdf = f"plugins/ShowMeJM/temp{pdfname}-{chunk_idx}.pdf"
        final_pdf = os.path.abspath(os.path.join(pdfpath, f"{pdfname}-{chunk_idx}.pdf"))
        try:
            batch_size = options.batch_size
            # 预加载第一部分
            images = []
            for img_path in chunk[:batch_size]:
                with Image.open(img_path) as img:
                    images.append(img.copy())
            if images:
                try:
                    images[0].save(temp_pdf, format='PDF', save_all=True, append_images=images[1:])
                finally:
                    for img in images:
                        if hasattr(img, "fp") and img.fp is not None:
                            img.close()
            # 添加后续图片
            for i in range(batch_size, len(chunk), batch_size):
                batch = chunk[i:i + batch_size]
                batch_images = [Image.open(img) for img in batch]
                try:
                    images[0].save(temp_pdf, format='PDF', save_all=True, append_images=batch_images, append=True)
                finally:
                    for img in batch_images:
                        if hasattr(img, "fp") and img.fp is not None:
                            img.close()

            # 加密 PDF 文件
            if options.pdf_password is not None and options.pdf_password != '':
                encrypt_pdf(temp_pdf, final_pdf, password=options.pdf_password)
                print(f"成功生成并加密第{chunk_idx}个PDF: {final_pdf}")
            else:
                shutil.move(temp_pdf, final_pdf)
            pdf_files.append(final_pdf)

        except (IOError, OSError) as e:
            print(f"图像处理异常: {str(e)}")
            raise Exception(f"PDF生成失败: {e}")
        finally:
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)
            gc.collect()
    end_time = time.time()
    print(f"总运行时间：{end_time - start_time:.2f}秒")
    return pdf_files


# 按顺序一个一个上传文件 方便阅读
async def send_files_in_order(options: JmOptions, ctx: EventContext, pdf_files, manga_id, single_file_flag, is_group):
    i = 0
    for pdf_path in pdf_files:
        if os.path.exists(pdf_path):
            i += 1
            suffix = '' if single_file_flag else f'-{i}'
            file_name = f"{manga_id}{suffix}.pdf"
            try:
                if is_group:
                    folder_id = await get_group_folder_id(options, ctx, ctx.event.launcher_id, options.group_folder)
                    await upload_group_file(options, ctx.event.launcher_id, folder_id, pdf_path, file_name)
                else:
                    await upload_private_file(options, ctx.event.sender_id, pdf_path, file_name)
                print(f"文件 {file_name} 已成功发送")
            except Exception as e:
                await ctx.reply(MessageChain([f"发送文件 {file_name} 时出错: {str(e)}"]))
                print(f"发送文件 {file_name} 时出错: {str(e)}")


# 获取群文件目录是否存在 并返回目录id
async def get_group_folder_id(options: JmOptions, ctx: EventContext, group_id, folder_name):
    if folder_name == '/':
        return '/'
    data = await get_group_root_files(options, group_id)
    for folder in data.get('folders', []):
        if folder.get('folder_name') == folder_name:
            return folder.get('folder_id')
    # 未找到该文件夹时创建文件夹
    folder_id = await create_group_file_folder(options, group_id, folder_name)
    if folder_id is None:
        data = await get_group_root_files(options, group_id)
        for folder in data.get('folders', []):
            if folder.get('folder_name') == folder_name:
                return folder.get('folder_id')
        return "/"
    return folder_id
