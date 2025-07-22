'''
随机漫画功能
贡献者 @drdon1234
'''
import asyncio
import json
import os
from datetime import datetime, timedelta

import aiofiles


class JmRandomSearch:
    def __init__(self, client):
        self.client = client
        self.cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        self.cache_file = os.path.join(self.cache_dir, "jm_max_page.json")
        self.cache_data = {}
        self._max_page_lock = asyncio.Lock()  # 异步锁，防止并发冲突
        self._cache_loaded = asyncio.Event()  # 标记缓存是否读取过
        # 启动时异步初始化
        asyncio.create_task(self._init_cache())

    async def _init_cache(self):
        """
        读取缓存文件，初始化缓存数据
        """
        if os.path.exists(self.cache_file):
            try:
                async with aiofiles.open(self.cache_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                    if content.strip():
                        self.cache_data = json.loads(content)
            except Exception as e:
                print(f"[JmRandomSearch] 缓存加载失败: {e}")
        self._cache_loaded.set()

    async def _save_cache(self):
        """
        保存缓存数据到文件
        """
        os.makedirs(self.cache_dir, exist_ok=True)  # 确保缓存目录存在
        try:
            async with aiofiles.open(self.cache_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.cache_data, ensure_ascii=False, indent=4))
        except Exception as e:
            print(f"[JmRandomSearch] 持久化失败: {e}")

    async def get_max_page(self, query=''):
        """
        获取搜索的分页目录总页数，并缓存结果
        """
        await self._cache_loaded.wait()  # 保证缓存已加载
        async with self._max_page_lock:
            print(f"正在获取搜索 '{query}' 的分页目录总页数")
            now = datetime.now()
            cache_entry = self.cache_data.get(query)
            # 检查缓存是否存在
            if cache_entry:
                max_page = cache_entry.get("max_page")
                last_update = datetime.fromisoformat(cache_entry.get("timestamp", "1970-01-01T00:00:00"))
                if now - last_update <= timedelta(hours=24):
                    print(f"缓存有效，最大页数为: {max_page}")
                    return max_page
                else:
                    print(f"缓存过期，重新校验最大页数 {max_page}")
                    valid_max_page = await self._validate_and_extend_cached_max_page(query, max_page)
            else:
                valid_max_page = self.find_max_page(query)
            # 写回缓存
            self.cache_data[query] = {
                "max_page": valid_max_page,
                "timestamp": now.isoformat()
            }
            await self._save_cache()
            print(f"最大页码更新为: {valid_max_page}")
            return valid_max_page

    def get_content_id(self, query: str, page: int) -> int:
        result = self.client.search_site(search_query=query, page=page)
        if not result:
            print(f"未搜索到相关本子（query={query}, page={page}）")
            return -1
        return list(result.iter_id_title())[-1][0]

    def find_max_page(self, query: str) -> int:
        # Step 1: 指数探测找到上界
        page = 2048
        content_id_l = self.get_content_id(query, page)
        page *= 2
        if content_id_l == -1:
            return 0

        while True:
            content_id_r = self.get_content_id(query, page)
            print(f"探测页 {page}, 返回 id={content_id_r}")
            if content_id_r == content_id_l:
                break
            else:
                content_id_l = content_id_r
                page *= 2

        # 此时 page/2 是第一个超出最大页数的位置
        left = page // 4
        right = page // 2

        # Step 2: 二分查找确定最大页
        while left <= right:
            mid = (left + right) // 2
            content_id_mid = self.get_content_id(query, mid)
            print(f"二分页 {mid}, 返回 id={content_id_mid}")
            if content_id_mid == content_id_l:
                # 返回的 id 和 content_id_l 相同，说明超出最大页数
                right = mid - 1
            else:
                # 返回的 id 和之前不同，说明 mid 还在有效范围内
                left = mid + 1

        return left

    async def _validate_and_extend_cached_max_page(self, query, cached_max):
        """
        验证 cached_max 是否依旧有效，如果有效就尝试向后探测几页
        """
        id_at_cached = self.get_content_id(query, cached_max)
        if id_at_cached == -1:
            print(f"[验证失败] 原 cached_max={cached_max} 无效，重新搜索")
            return 0

        # cached_max 仍然有效，尝试向后探测
        probe_limit = 2  # 最多向后探测多少页
        for i in range(probe_limit):
            probe_page = cached_max + 1
            probe_id = self.get_content_id(query, probe_page)
            if probe_id == id_at_cached:
                print(f"[验证成功] 最大页数更新为: {cached_max}")
                return cached_max
            print(f"[向后探测] page={probe_page}, id={probe_id}")
            cached_max = probe_page
            id_at_cached = probe_id
        return self.find_max_page(query)
