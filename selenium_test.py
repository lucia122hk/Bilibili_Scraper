import time
import json
import re
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


class BilibiliVideoCrawler:
    def __init__(self, headless=True, driver_path=None):
        """
        初始化爬虫
        :param headless: 是否使用无头模式（不显示浏览器界面）
        :param driver_path: ChromeDriver路径，如果为None则使用系统PATH中的驱动
        """
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument('--headless')

        # 添加必要的参数
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')

        # 禁用自动化控制标志
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)

        # 添加User-Agent
        self.chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # 启用DevTools协议，用于执行JavaScript
        self.chrome_options.add_experimental_option('w3c', True)

        self.driver = None
        self.driver_path = driver_path

    def setup_driver(self):
        """设置WebDriver"""
        if self.driver_path:
            self.driver = webdriver.Chrome(executable_path=self.driver_path, options=self.chrome_options)
        else:
            self.driver = webdriver.Chrome(options=self.chrome_options)

        # 隐藏WebDriver特征
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = window.chrome || {};
                window.chrome.runtime = window.chrome.runtime || {};
            '''
        })

    @staticmethod
    def bvid_to_url(bvid):
        """
        将BVID转换为B站视频URL
        :param bvid: B站视频ID，如 BV1xx411c7mD
        :return: 完整的视频URL
        """
        return f"https://www.bilibili.com/video/{bvid}"

    def get_video_info_by_bvid(self, bvid):
        """
        通过BVID获取视频信息
        :param bvid: B站视频ID
        :return: 包含视频信息的字典
        """
        url = self.bvid_to_url(bvid)
        return self.get_video_info(url)

    def get_video_info(self, video_url):
        """
        获取B站视频信息
        :param video_url: 视频链接
        :return: 包含视频信息的字典
        """
        if not self.driver:
            self.setup_driver()

        try:
            print(f"正在访问视频页面: {video_url}")
            self.driver.get(video_url)

            # 等待页面加载完成
            wait = WebDriverWait(self.driver, 20)

            # 等待页面基本加载
            try:
                # 等待标题加载
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#viewbox_report > div.video-info-title > div > h1")))
                print("✓ 标题元素已加载")
            except:
                print("⚠ 标题元素加载超时，继续执行...")

            # 额外等待确保动态内容加载完成
            time.sleep(3)

            # 获取页面源代码
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # 提取数据
            video_info = self._extract_video_data(soup, video_url)

            print("✓ 视频信息获取成功!")
            return video_info

        except Exception as e:
            print(f"✗ 获取视频信息时出错: {str(e)}")
            traceback.print_exc()
            # 尝试截图以便调试
            try:
                timestamp = int(time.time())
                self.driver.save_screenshot(f"error_{timestamp}.png")
                print(f"已保存错误截图: error_{timestamp}.png")
            except:
                pass
            return None

    def _extract_video_data(self, soup, video_url):
        """提取视频数据"""
        # 初始化视频信息字典
        video_info = {
            'bvid': self._extract_bvid_from_url(video_url),
            'url': video_url,
            'title': '',
            'description': '',
            'play_count': 0,
            'danmaku_count': 0,
            'comment_count': 0,
            'favorite_count': 0,
            'coin_count': 0,
            'share_count': 0,
            'like_count': 0,
            'pub_date': '',
            'owner_name': '',
            'owner_mid': 0
        }

        print("\n" + "=" * 60)
        print("开始提取视频数据")
        print("=" * 60)

        # 方法1: 从脚本数据中提取（最准确）
        print("\n[步骤1] 从脚本数据中提取...")
        script_data = self._extract_from_scripts(soup)

        # 方法2: 从页面元素提取（使用你提供的所有选择器）
        print("\n[步骤2] 从页面元素提取...")
        element_data = self._extract_from_elements(soup)

        # 方法3: 使用JavaScript提取（专门处理Shadow DOM中的评论数）
        print("\n[步骤3] 使用JavaScript提取Shadow DOM中的数据...")
        js_data = self._extract_with_javascript()

        # 合并数据
        print("\n[步骤4] 合并数据...")
        for key in video_info.keys():
            # 评论数优先使用JavaScript提取的数据
            if key == 'comment_count':
                if js_data.get('comment_count') not in (None, 0):
                    video_info[key] = js_data['comment_count']
                    print(f"  评论数: 使用JavaScript数据 → {video_info[key]}")
                elif script_data.get(key) not in (None, 0):
                    video_info[key] = script_data[key]
                    print(f"  评论数: 使用脚本数据 → {video_info[key]}")
                elif element_data.get(key) not in (None, 0):
                    video_info[key] = element_data[key]
                    print(f"  评论数: 使用元素数据 → {video_info[key]}")
            # 其他数据优先使用脚本数据
            else:
                if key in script_data and script_data[key] not in (None, '', 0):
                    video_info[key] = script_data[key]
                elif key in element_data and element_data[key] not in (None, '', 0):
                    video_info[key] = element_data[key]

        print("\n" + "=" * 60)
        print("数据提取完成")
        print("=" * 60)

        return video_info

    def _extract_bvid_from_url(self, url):
        """从URL中提取BVID"""
        match = re.search(r'BV[0-9A-Za-z]{10}', url)
        if match:
            return match.group(0)
        return ''

    def _extract_from_scripts(self, soup):
        """从脚本数据中提取视频信息（最准确）"""
        script_data = {}

        try:
            # 查找包含视频信息的script标签
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    script_text = script.string

                    # 查找 window.__INITIAL_STATE__
                    if 'window.__INITIAL_STATE__' in script_text:
                        try:
                            # 提取JSON数据
                            json_str = script_text.split('window.__INITIAL_STATE__=')[1]
                            # 找到第一个分号或函数开始
                            json_str = json_str.split(';')[0] if ';' in json_str else json_str
                            json_str = json_str.split('(function')[0] if '(function' in json_str else json_str

                            data = json.loads(json_str)

                            # 提取视频信息
                            if 'videoData' in data:
                                video_data = data['videoData']

                                # 基本信息
                                script_data['title'] = video_data.get('title', '')
                                script_data['description'] = video_data.get('desc', '')
                                script_data['pub_date'] = self._format_timestamp(video_data.get('pubdate', 0))

                                # UP主信息
                                if 'owner' in video_data:
                                    script_data['owner_name'] = video_data['owner'].get('name', '')
                                    script_data['owner_mid'] = video_data['owner'].get('mid', 0)

                                # 统计信息
                                stat = video_data.get('stat', {})
                                script_data['play_count'] = stat.get('view', 0)
                                script_data['danmaku_count'] = stat.get('danmaku', 0)
                                script_data['comment_count'] = stat.get('reply', 0)
                                script_data['favorite_count'] = stat.get('favorite', 0)
                                script_data['coin_count'] = stat.get('coin', 0)
                                script_data['share_count'] = stat.get('share', 0)
                                script_data['like_count'] = stat.get('like', 0)

                            print("✓ 从window.__INITIAL_STATE__提取到数据")
                            break
                        except Exception as e:
                            print(f"✗ 解析window.__INITIAL_STATE__时出错: {str(e)}")
                            continue

                    # 查找 __NEXT_DATA__ (B站有时使用)
                    elif '__NEXT_DATA__' in script_text:
                        try:
                            json_str = script_text.split('__NEXT_DATA__ = ')[1].split(';')[0]
                            data = json.loads(json_str)

                            # 尝试提取视频信息
                            if 'props' in data and 'pageProps' in data['props']:
                                video_data = data['props']['pageProps'].get('videoData', {})

                                if video_data:
                                    script_data['title'] = video_data.get('title', '')
                                    script_data['description'] = video_data.get('desc', '')

                                    # 统计信息
                                    stat = video_data.get('stat', {})
                                    script_data['play_count'] = stat.get('view', 0)
                                    script_data['danmaku_count'] = stat.get('danmaku', 0)
                                    script_data['comment_count'] = stat.get('reply', 0)
                                    script_data['favorite_count'] = stat.get('favorite', 0)
                                    script_data['coin_count'] = stat.get('coin', 0)
                                    script_data['share_count'] = stat.get('share', 0)
                                    script_data['like_count'] = stat.get('like', 0)

                            print("✓ 从__NEXT_DATA__提取到数据")
                            break
                        except Exception as e:
                            print(f"✗ 解析__NEXT_DATA__时出错: {str(e)}")
                            continue

        except Exception as e:
            print(f"✗ 从脚本提取数据时出错: {str(e)}")

        return script_data

    def _extract_from_elements(self, soup):
        """
        从页面元素提取视频信息
        使用你提供的所有选择器，除了评论数
        """
        element_data = {}

        try:
            print("\n[元素提取] 开始使用你提供的选择器...")

            # 1. 标题 - 使用你提供的选择器
            title_elem = soup.select_one("#viewbox_report > div.video-info-title > div > h1")
            if title_elem:
                element_data['title'] = title_elem.get_text(strip=True)
                print(f"  ✓ 标题: {element_data['title']}")
            else:
                print("  ✗ 未找到标题元素")

            # 2. 描述 - 使用你提供的选择器
            desc_elem = soup.select_one("#v_desc > div.basic-desc-info")
            if desc_elem:
                desc_text = desc_elem.get_text(separator='\n', strip=True)
                if desc_text:
                    element_data['description'] = desc_text
                    print(f"  ✓ 描述: {desc_text[:50]}...")
            else:
                print("  ✗ 未找到描述元素")

            # 3. 播放量
            play_elem = soup.select_one("#viewbox_report > div.video-info-meta > div > div.view.item > div")
            if play_elem:
                play_text = play_elem.get_text(strip=True)
                element_data['play_count'] = self._parse_count(play_text)
                print(f"  ✓ 播放量: {play_text} → {element_data['play_count']:,}")
            else:
                print("  ✗ 未找到播放量元素")

            # 4. 弹幕数
            danmaku_elem = soup.select_one(
                "#bilibili-player > div > div > div.bpx-player-primary-area > div.bpx-player-sending-area > div > div.bpx-player-video-info > div.bpx-player-video-info-dm > span")
            if danmaku_elem:
                danmaku_text = danmaku_elem.get_text(strip=True)
                element_data['danmaku_count'] = self._parse_count(danmaku_text)
                print(f"  ✓ 弹幕数: {danmaku_text} → {element_data['danmaku_count']:,}")
            else:
                # 尝试备用选择器
                danmaku_elem = soup.select_one("span.dm")
                if danmaku_elem:
                    danmaku_text = danmaku_elem.get_text(strip=True)
                    element_data['danmaku_count'] = self._parse_count(danmaku_text)
                    print(f"  ✓ 弹幕数(备用): {danmaku_text} → {element_data['danmaku_count']:,}")
                else:
                    print("  ✗ 未找到弹幕数元素")

            # 5. 点赞数
            like_elem = soup.select_one(
                "#arc_toolbar_report > div.video-toolbar-left > div.video-toolbar-left-main > div:nth-child(1) > div > span")
            if like_elem:
                like_text = like_elem.get_text(strip=True)
                element_data['like_count'] = self._parse_count(like_text)
                print(f"  ✓ 点赞数: {like_text} → {element_data['like_count']:,}")
            else:
                # 尝试备用选择器
                like_elem = soup.select_one("span.like")
                if like_elem:
                    like_text = like_elem.get_text(strip=True)
                    element_data['like_count'] = self._parse_count(like_text)
                    print(f"  ✓ 点赞数(备用): {like_text} → {element_data['like_count']:,}")
                else:
                    print("  ✗ 未找到点赞数元素")

            # 6. 投币数
            coin_elem = soup.select_one(
                "#arc_toolbar_report > div.video-toolbar-left > div.video-toolbar-left-main > div:nth-child(2) > div > span")
            if coin_elem:
                coin_text = coin_elem.get_text(strip=True)
                element_data['coin_count'] = self._parse_count(coin_text)
                print(f"  ✓ 投币数: {coin_text} → {element_data['coin_count']:,}")
            else:
                # 尝试备用选择器
                coin_elem = soup.select_one("span.coin")
                if coin_elem:
                    coin_text = coin_elem.get_text(strip=True)
                    element_data['coin_count'] = self._parse_count(coin_text)
                    print(f"  ✓ 投币数(备用): {coin_text} → {element_data['coin_count']:,}")
                else:
                    print("  ✗ 未找到投币数元素")

            # 7. 收藏数
            fav_elem = soup.select_one(
                "#arc_toolbar_report > div.video-toolbar-left > div.video-toolbar-left-main > div:nth-child(3) > div > span")
            if fav_elem:
                fav_text = fav_elem.get_text(strip=True)
                element_data['favorite_count'] = self._parse_count(fav_text)
                print(f"  ✓ 收藏数: {fav_text} → {element_data['favorite_count']:,}")
            else:
                # 尝试备用选择器
                fav_elem = soup.select_one("span.fav")
                if fav_elem:
                    fav_text = fav_elem.get_text(strip=True)
                    element_data['favorite_count'] = self._parse_count(fav_text)
                    print(f"  ✓ 收藏数(备用): {fav_text} → {element_data['favorite_count']:,}")
                else:
                    print("  ✗ 未找到收藏数元素")

            # 8. 分享数
            share_elem = soup.select_one("#share-btn-outer > div > span")
            if share_elem:
                share_text = share_elem.get_text(strip=True)
                element_data['share_count'] = self._parse_count(share_text)
                print(f"  ✓ 分享数: {share_text} → {element_data['share_count']:,}")
            else:
                # 尝试备用选择器
                share_elem = soup.select_one("span.share")
                if share_elem:
                    share_text = share_elem.get_text(strip=True)
                    element_data['share_count'] = self._parse_count(share_text)
                    print(f"  ✓ 分享数(备用): {share_text} → {element_data['share_count']:,}")
                else:
                    print("  ✗ 未找到分享数元素")

            # 9. UP主信息
            owner_selectors = [
                "#v_upinfo > div.up-info > div.up-detail > a",
                "div.up-info .username",
                ".up-info .name",
                ".up-info span",
                "a.up-name"
            ]

            for selector in owner_selectors:
                owner_elem = soup.select_one(selector)
                if owner_elem and owner_elem.get_text(strip=True):
                    element_data['owner_name'] = owner_elem.get_text(strip=True)
                    print(f"  ✓ UP主: {element_data['owner_name']}")
                    break
            else:
                print("  ✗ 未找到UP主信息")

            # 评论数暂时不在这里提取，因为它在Shadow DOM中
            element_data['comment_count'] = 0

        except Exception as e:
            print(f"✗ 使用选择器提取数据时出错: {str(e)}")
            traceback.print_exc()

        return element_data

    def _extract_with_javascript(self):
        """
        使用JavaScript提取数据
        专门用于处理Shadow DOM中的元素
        """
        js_data = {}

        try:
            print("\n[JavaScript提取] 开始提取Shadow DOM中的数据...")

            # 提取评论数（在Shadow DOM中）
            comment_count_js = """
            // 尝试多种方法获取评论数

            // 方法1: 从window.__INITIAL_STATE__中获取
            if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.videoData && window.__INITIAL_STATE__.videoData.stat) {
                return window.__INITIAL_STATE__.videoData.stat.reply;
            }

            // 方法2: 尝试访问Shadow DOM获取评论数
            try {
                // 找到bili-comments元素
                const commentsElement = document.querySelector('bili-comments');
                if (commentsElement && commentsElement.shadowRoot) {
                    // 进入第一层Shadow DOM
                    const headerRenderer = commentsElement.shadowRoot.querySelector('bili-comments-header-renderer');
                    if (headerRenderer && headerRenderer.shadowRoot) {
                        // 进入第二层Shadow DOM
                        const countElement = headerRenderer.shadowRoot.querySelector('#count');
                        if (countElement) {
                            // 获取文本内容
                            const text = countElement.textContent.trim();
                            // 提取数字
                            const match = text.match(/\\d+/);
                            if (match) {
                                return parseInt(match[0]);
                            }
                        }
                    }
                }
            } catch (e) {
                console.log('访问Shadow DOM失败:', e);
            }

            // 方法3: 直接查询页面中的评论数元素
            const countElements = document.querySelectorAll('[class*="comment"], [class*="reply"], #comment');
            for (let elem of countElements) {
                const text = elem.textContent.trim();
                if (text && /\\d+/.test(text)) {
                    const match = text.match(/\\d+/);
                    if (match) {
                        return parseInt(match[0]);
                    }
                }
            }

            // 方法4: 查找包含"评论"文本的元素
            const allElements = document.querySelectorAll('*');
            for (let elem of allElements) {
                const text = elem.textContent.trim();
                if (text.includes('评论') && /\\d+/.test(text)) {
                    const match = text.match(/\\d+/);
                    if (match) {
                        return parseInt(match[0]);
                    }
                }
            }

            return 0;
            """

            comment_count = self.driver.execute_script(comment_count_js)
            if comment_count:
                js_data['comment_count'] = comment_count
                print(f"  ✓ JavaScript提取评论数: {comment_count:,}")
            else:
                print("  ✗ JavaScript未提取到评论数")

            # 可以添加其他需要JavaScript提取的数据
            # 例如：点赞数、投币数等（如果它们也在Shadow DOM中）

        except Exception as e:
            print(f"✗ 使用JavaScript提取数据时出错: {str(e)}")
            traceback.print_exc()

        return js_data

    def _parse_count(self, text):
        """解析统计数字（处理万、亿等单位）"""
        if not text:
            return 0

        text = text.strip()

        try:
            # 移除所有空格和逗号
            text = text.replace(' ', '').replace(',', '')

            # 处理"万"单位
            if '万' in text:
                num_str = text.replace('万', '')
                if num_str:
                    return int(float(num_str) * 10000)

            # 处理"亿"单位
            if '亿' in text:
                num_str = text.replace('亿', '')
                if num_str:
                    return int(float(num_str) * 100000000)

            # 处理"千"单位
            if '千' in text:
                num_str = text.replace('千', '')
                if num_str:
                    return int(float(num_str) * 1000)

            # 处理"M"单位（百万）
            if 'M' in text:
                num_str = text.replace('M', '')
                if num_str:
                    return int(float(num_str) * 1000000)

            # 处理"K"单位（千）
            if 'K' in text:
                num_str = text.replace('K', '')
                if num_str:
                    return int(float(num_str) * 1000)

            # 直接提取数字
            match = re.search(r'(\d+(\.\d+)?)', text)
            if match:
                return int(float(match.group(1)))

        except Exception as e:
            print(f"✗ 解析统计数字时出错: {text}, 错误: {str(e)}")

        return 0

    def _format_timestamp(self, timestamp):
        """格式化时间戳"""
        if not timestamp or timestamp == 0:
            return ''

        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ''

    def debug_shadow_dom(self, bvid):
        """专门调试Shadow DOM"""
        if not self.driver:
            self.setup_driver()

        url = self.bvid_to_url(bvid)
        print(f"\n{'=' * 60}")
        print(f"调试Shadow DOM: {url}")
        print('=' * 60)

        self.driver.get(url)
        time.sleep(5)

        # 测试JavaScript提取
        test_js = """
        console.log('开始调试Shadow DOM...');

        // 检查是否存在bili-comments元素
        const commentsElement = document.querySelector('bili-comments');
        console.log('bili-comments元素:', commentsElement);

        if (commentsElement) {
            console.log('bili-comments有shadowRoot:', !!commentsElement.shadowRoot);

            if (commentsElement.shadowRoot) {
                // 检查第一层Shadow DOM
                const headerRenderer = commentsElement.shadowRoot.querySelector('bili-comments-header-renderer');
                console.log('bili-comments-header-renderer元素:', headerRenderer);

                if (headerRenderer) {
                    console.log('header-renderer有shadowRoot:', !!headerRenderer.shadowRoot);

                    if (headerRenderer.shadowRoot) {
                        // 检查第二层Shadow DOM
                        const countElement = headerRenderer.shadowRoot.querySelector('#count');
                        console.log('#count元素:', countElement);

                        if (countElement) {
                            console.log('#count文本内容:', countElement.textContent);
                            console.log('#count子节点:', countElement.childNodes.length);

                            // 遍历子节点
                            for (let i = 0; i < countElement.childNodes.length; i++) {
                                console.log(`子节点${i}:`, countElement.childNodes[i].nodeType, countElement.childNodes[i].textContent);
                            }
                        }
                    }
                }
            }
        }

        // 尝试直接获取评论数
        const allElements = document.querySelectorAll('*');
        let foundCount = null;
        for (let elem of allElements) {
            const text = elem.textContent.trim();
            if (text && /\\d+/.test(text) && (elem.id.includes('comment') || elem.className.includes('comment') || text.includes('评论'))) {
                console.log('可能包含评论数的元素:', elem, '文本:', text);
                const match = text.match(/\\d+/);
                if (match) {
                    foundCount = parseInt(match[0]);
                    break;
                }
            }
        }

        console.log('找到的评论数:', foundCount);
        return foundCount;
        """

        try:
            result = self.driver.execute_script(test_js)
            print(f"\nJavaScript调试结果: {result}")
        except Exception as e:
            print(f"JavaScript执行出错: {str(e)}")

        # 同时检查脚本数据
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        script_data = self._extract_from_scripts(soup)

        if script_data.get('comment_count'):
            print(f"脚本数据中的评论数: {script_data['comment_count']}")

        return True

    def batch_crawl(self, bvid_list, delay=2):
        """
        批量爬取视频信息
        :param bvid_list: BVID列表
        :param delay: 每个请求之间的延迟（秒）
        :return: 视频信息列表
        """
        results = []

        for i, bvid in enumerate(bvid_list):
            print(f"\n{'=' * 60}")
            print(f"正在爬取第 {i + 1}/{len(bvid_list)} 个视频: {bvid}")
            print('=' * 60)

            video_info = self.get_video_info_by_bvid(bvid)

            if video_info:
                results.append(video_info)
                self._print_video_info(video_info)
            else:
                print(f"✗ 视频 {bvid} 爬取失败")
                results.append({'bvid': bvid, 'error': '爬取失败'})

            # 添加延迟，避免请求过快
            if i < len(bvid_list) - 1:
                print(f"等待 {delay} 秒...")
                time.sleep(delay)

        return results

    def _print_video_info(self, video_info):
        """打印视频信息"""
        print(f"\n视频信息:")
        print(f"BVID: {video_info.get('bvid')}")
        print(f"标题: {video_info.get('title')}")

        desc = video_info.get('description', '')
        if desc:
            print(f"描述: {desc[:100]}..." if len(desc) > 100 else f"描述: {desc}")

        print(f"UP主: {video_info.get('owner_name', '未知')}")
        print(f"发布时间: {video_info.get('pub_date', '未知')}")
        print(f"播放量: {video_info.get('play_count', 0):,}")
        print(f"弹幕数: {video_info.get('danmaku_count', 0):,}")
        print(f"评论数: {video_info.get('comment_count', 0):,}")
        print(f"收藏数: {video_info.get('favorite_count', 0):,}")
        print(f"投币数: {video_info.get('coin_count', 0):,}")
        print(f"分享数: {video_info.get('share_count', 0):,}")
        print(f"点赞数: {video_info.get('like_count', 0):,}")
        print(f"URL: {video_info.get('url')}")

    def save_to_json(self, data, filename):
        """保存数据到JSON文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ 数据已保存到: {filename}")
        except Exception as e:
            print(f"✗ 保存数据时出错: {str(e)}")

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()

    def __del__(self):
        """析构函数，确保关闭浏览器"""
        self.close()


def main():
    # 使用说明
    print("""
    B站视频信息爬虫 - Shadow DOM优化版
    =================================
    专门解决Shadow DOM中的评论数提取问题

    1. 确保已安装Chrome浏览器和对应版本的ChromeDriver
    2. 安装依赖: pip install selenium beautifulsoup4
    3. 修改bvid_list中的视频ID为你想要爬取的视频

    注意: 请遵守B站的使用条款，不要频繁爬取，尊重网站权益
    """)

    # 创建爬虫实例
    # headless=False 可以看到浏览器界面，适合调试
    # headless=True 无界面模式，适合生产环境
    crawler = BilibiliVideoCrawler(headless=False)

    # 选择操作模式
    print("\n请选择操作模式:")
    print("1. 调试Shadow DOM提取")
    print("2. 测试单个视频爬取")
    print("3. 批量爬取视频")
    print("4. 退出")

    choice = input("请输入选择 (1-4): ").strip()

    if choice == '1':
        # 调试Shadow DOM
        bvid = input("请输入要调试的BVID (默认: BV1GJ411x7h7): ").strip()
        if not bvid:
            bvid = "BV1GJ411x7h7"
        crawler.debug_shadow_dom(bvid)

    elif choice == '2':
        # 测试单个视频爬取
        bvid = input("请输入要爬取的BVID (默认: BV1GJ411x7h7): ").strip()
        if not bvid:
            bvid = "BV1GJ411x7h7"

        print(f"\n正在爬取单个视频: {bvid}")
        video_info = crawler.get_video_info_by_bvid(bvid)

        if video_info:
            print("\n" + "=" * 60)
            print("爬取结果:")
            print("=" * 60)
            crawler._print_video_info(video_info)

            # 保存结果
            save_choice = input("\n是否保存结果到JSON文件? (y/n): ").strip().lower()
            if save_choice == 'y':
                filename = input("请输入文件名 (默认: bilibili_video.json): ").strip()
                if not filename:
                    filename = "bilibili_video.json"
                crawler.save_to_json([video_info], filename)
        else:
            print("✗ 爬取失败")

    elif choice == '3':
        # 批量爬取视频
        print("\n批量爬取视频")
        print("请以逗号分隔输入BVID列表，或按Enter使用示例列表")
        bvid_input = input("BVID列表: ").strip()

        if bvid_input:
            bvid_list = [bvid.strip() for bvid in bvid_input.split(',')]
        else:
            # 使用示例列表
            bvid_list = [
                "BV1GJ411x7h7",
                "BV1xx411c7mD",
                # 可以添加更多BVID
            ]
            print(f"使用示例列表: {bvid_list}")

        delay = input("请输入请求延迟(秒，默认: 5): ").strip()
        if not delay:
            delay = 5
        else:
            delay = int(delay)

        print(f"\n开始批量爬取 {len(bvid_list)} 个视频，延迟 {delay} 秒")
        results = crawler.batch_crawl(bvid_list, delay=delay)

        if results:
            filename = input("\n请输入保存文件名 (默认: bilibili_videos_batch.json): ").strip()
            if not filename:
                filename = "bilibili_videos_batch.json"
            crawler.save_to_json(results, filename)

    elif choice == '4':
        print("退出程序")
    else:
        print("无效选择")

    # 关闭浏览器
    crawler.close()
    print("\n程序结束")


if __name__ == "__main__":
    main()
