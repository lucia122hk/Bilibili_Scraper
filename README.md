# Bilibili_Scraper
B站科技区内容爬虫工具，可批量获取排行榜视频的BV号、评论、弹幕及视频基本信息，适用于内容分析或数据采集场景。


## 功能说明
1. **BV号爬取**：通过Selenium爬取B站科技数码区排行榜（`https://www.bilibili.com/v/popular/rank/tech`）的视频BV号，支持滚动加载和反爬处理。
2. **评论与回复获取**：基于`bilibili_api`库获取指定BV号视频的评论及嵌套回复，支持批量处理。
3. **弹幕采集**：通过B站XML接口解析弹幕，提取视频实时弹幕内容（依赖`lxml`解析）。
4. **视频信息提取**：获取视频标题、描述、播放量、评论数等基础数据。
5. **数据保存**：支持将结果保存为Excel文件（.xlsx，含评论、弹幕、视频信息等）。


## 使用教程
### 2. 获取视频评论、弹幕及信息
1. **重要**：修改`Bli_CDScraper.py`中的`get_credentials`函数，替换为自己的B站凭证（`SESSDATA`、`bili_jct`、`buvid3`）。  
   - 凭证获取：登录B站后，通过浏览器开发者工具（F12）的`Application > Cookies`获取。  
   - 注意：凭证为个人敏感信息，请勿上传至公开仓库，建议通过环境变量或配置文件加载。

2. 批量处理视频数据（示例代码片段）
   ```python
   from Bli_CDScraper import get_video_comments, get_video_danmaku, get_video_info, save_to_csv
   import json

   # 从内置JSON文件加载BV号列表（all_bvids.json）
   with open("all_bvids.json", "r", encoding="utf-8") as f:
       bvids = json.load(f)

   # 处理单个BV号
   for bvid in bvids[:5]:  # 示例：处理前5个
       comments = get_video_comments(bvid)  # 获取评论
       danmaku = get_video_danmaku(bvid)    # 获取弹幕
       title, desc = get_video_info(bvid)   # 获取标题和描述
       stat = sync(get_video_stats(bvid))   # 获取播放量等统计信息

       # 保存到Excel（实际格式为.xlsx）
       data = {
           "comments": comments,
           "danmaku": danmaku,
           "title": title,
           "description": desc,
           "stat": stat
       }
       save_to_csv(data, bvid)  # 函数名虽为save_to_csv，实际保存为Excel
