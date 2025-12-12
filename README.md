# Bilibili_Scraper
B站科技区内容爬虫工具集，支持爬取排行榜视频BV号、批量获取视频评论/弹幕、多维度提取视频基础信息（适配Shadow DOM解析），适用于B站内容分析、数据采集等学习研究场景。

Bilibili_Scraper/
├── Bli_CDScraper.py                # 视频评论、弹幕批量获取工具（基于B站API）
├── BvidScraper.py                  # B站科技区排行榜BV号爬取工具（Selenium模拟浏览器）
├── BilibiliVideoInfoCrawler.py     # 视频基础信息爬虫（适配Shadow DOM，提取播放/评论/点赞等数据）
├── README.md                       # 项目总说明文档（安装、使用、注意事项等）
├── all_bvids.json                  # 历史爬取的BV号列表（批量处理数据源）
├── requirements.txt                # 项目依赖库清单（含版本约束）
└── data/                           # 数据输出目录（运行爬虫后自动创建）
    ├── BVID_<视频ID>.xlsx          # 单视频评论/弹幕数据（Excel格式，来自Bli_CDScraper）
    └── bilibili_videos_batch.json  # 批量视频基础信息


### 文件功能说明
1. **Bli_CDScraper.py**  
   核心功能：通过B站API获取指定BV号视频的评论（含嵌套回复）、弹幕、标题、描述及播放量等统计信息，并将数据保存为Excel文件至`data`目录。  
   依赖：`bilibili_api`库、`pandas`、`lxml`等。

2. **BvidScraper.py**  
   核心功能：使用Selenium模拟浏览器操作，爬取B站科技区排行榜（`https://www.bilibili.com/v/popular/rank/tech`）的视频BV号，支持滚动加载和反爬处理（随机User-Agent、隐藏webdriver特征），结果保存至文本文件。

3. **BilibiliVideoInfoCrawler.py**  
   核心功能：专为解析B站Shadow DOM结构设计的视频信息爬虫，支持：
   - 提取视频标题、UP主、发布时间、描述等基础信息；
   - 解析播放量、弹幕数、评论数（Shadow DOM内）、点赞/投币/收藏/分享数等统计数据；
   - 支持单视频爬取、批量爬取，结果可保存为JSON文件；
   - 内置调试模式，可排查Shadow DOM解析问题。  
   依赖：`selenium`、`beautifulsoup4`、`re`等。

4. **all_bvids.json**  
   存储历史爬取的BV号列表（JSON格式），用于批量获取多个视频的数据。

5. **data/**  
   自动生成的输出目录，用于存储：
   - `Bli_CDScraper.py`生成的Excel格式评论/弹幕数据；

## 功能说明
1. **BV号爬取**：通过Selenium爬取B站科技数码区排行榜的视频BV号，支持滚动加载和反爬处理（如随机User-Agent、隐藏自动化特征）。
2. **评论与回复获取**：基于`bilibili_api`库获取指定BV号视频的评论及嵌套回复，支持批量处理和重试机制。
3. **弹幕采集**：通过B站XML接口解析弹幕，提取视频实时弹幕内容（依赖`lxml`解析）。
4. **视频信息深度提取**：适配B站Shadow DOM结构，精准提取播放量、评论数、点赞/投币/收藏/分享数、UP主信息、发布时间等核心数据。
5. **批量爬取与保存**：支持单/批量视频爬取，结果可保存为Excel/JSON格式，自动创建`data`目录存储输出文件。

## 使用教程
### 获取视频评论、弹幕及信息
   **重要**：修改`Bli_CDScraper.py`中的`get_credentials`函数，替换为自己的B站凭证（`SESSDATA`、`bili_jct`、`buvid3`）。  
   - 凭证获取：登录B站后，通过浏览器开发者工具（F12）的`Application > Cookies`获取。  
   - 注意：凭证为个人敏感信息，请勿上传至公开仓库，建议通过环境变量或配置文件加载。


