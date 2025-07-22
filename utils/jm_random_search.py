'''
随机漫画功能
贡献者 @drdon1234
'''
import os
import json
import asyncio
import aiofiles
from datetime import datetime, timedelta


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

    async def get_max_page(self, query='', initial_page=6000):
        """
        获取搜索的分页目录总页数，并缓存结果
        """
        await self._cache_loaded.wait()  # 保证缓存已加载
        async with self._max_page_lock:
            print(f"正在获取搜索 '{query}' 的分页目录总页数")
            cached_max_page = initial_page
            now = datetime.now()
            cache_entry = self.cache_data.get(query)
            # 检查缓存是否存在
            if cache_entry:
                max_page = cache_entry.get("max_page", initial_page)
                last_update = datetime.fromisoformat(cache_entry.get("timestamp", "1970-01-01T00:00:00"))
                if now - last_update <= timedelta(hours=24):
                    print(f"缓存有效，最大页数为: {max_page}")
                    return max_page
                else:
                    print(f"缓存过期，重新校验最大页数 {max_page}")
                    cached_max_page = max_page

            # 检查最大页
            valid_max_page = await self._validate_max_page(query, cached_max_page)
            # 写回缓存
            self.cache_data[query] = {
                "max_page": valid_max_page,
                "timestamp": now.isoformat()
            }
            await self._save_cache()
            print(f"最大页码更新为: {valid_max_page}")
            return valid_max_page

    async def _validate_max_page(self, query: str, max_page: int) -> int:
        """
        从上次的最大页数开始，验证是否仍是最大页。
        如果不是，向后或向前查找直到找到新的最大页。
        """
        if not await self._is_valid_page(query, max_page):
            # 最大页缩小，右边界左移
            low = 1
            high = max_page - 1
            # 左边界不存在
            if not await self._is_valid_page(query, low):
                return 0

        else:
            # 最大页变大，左右边界右移
            low = max_page + 1
            high = max_page << 1
            # max_page仍是最大页
            if not await self._is_valid_page(query, low):
                return max_page
            while await self._is_valid_page(query, high):
                low = high
                high <<= 1

        return await self._binary_search_max_page(query, low, high)

    async def _binary_search_max_page(self, query: str, low: int, high: int) -> int:
        """
        确保左边界存在，向右边界二分查最大页
        """
        while low <= high:
            mid = (low + high) // 2
            if await self._is_valid_page(query, mid):
                low = mid + 1
            else:
                high = mid - 1
        return high

    async def _is_valid_page(self, query: str, page: int) -> bool:
        """
        包一层异步调用客户端，便于兼容同步/异步接口
        """
        try:
            res = await asyncio.to_thread(self.client.search_site, search_query=query, page=page)
            return bool(res)
        except Exception as e:
            print(f"[JmRandomSearch] 查询第 {page} 页出错: {e}")
            return False

