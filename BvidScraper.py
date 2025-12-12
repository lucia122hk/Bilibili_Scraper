import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BilibiliRankingCrawler:
    def __init__(self):
        self.setup_driver()
        self.base_url = "https://www.bilibili.com/v/popular/rank/tech"

    def setup_driver(self):
        """配置浏览器驱动，设置反反爬措施"""
        chrome_options = Options()

        # 反反爬设置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')

        # 设置用户代理
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')

        # 初始化浏览器
        self.driver = webdriver.Chrome(options=chrome_options)

        # 执行脚本隐藏webdriver属性
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def random_delay(self, min_seconds=1, max_seconds=3):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def scroll_page(self):
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while True:
            scroll_height = random.randint(300, 800)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_height});")
            self.random_delay(0.5, 1.5)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_bv_numbers(self):
        """获取BV号"""
        try:
            print("正在访问B站科技数码区排行榜...")
            self.driver.get(self.base_url)

            # 等待页面加载
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rank-item")))

            print("页面加载完成，开始滚动页面...")
            self.scroll_page()

            # 再次等待内容加载
            self.random_delay(2, 4)

            # 查找所有视频项
            video_items = self.driver.find_elements(By.CLASS_NAME, "rank-item")
            print(f"找到 {len(video_items)} 个视频项目")

            bv_numbers = []

            for index, item in enumerate(video_items, 1):
                try:
                    # 查找包含BV号的链接
                    link_element = item.find_element(By.TAG_NAME, "a")
                    href = link_element.get_attribute("href")

                    # 从链接中提取BV号
                    if "BV" in href:
                        bv_start = href.find("BV")
                        bv_end = bv_start + 12  # BV号固定为12位
                        bv_number = href[bv_start:bv_end]

                        if len(bv_number) == 12 and bv_number.startswith("BV"):
                            bv_numbers.append(bv_number)
                            print(f"{index:3d}. {bv_number}")
                        else:
                            print(f"{index:3d}. 无效的BV号格式: {bv_number}")

                    self.random_delay(0.1, 0.3)  # 处理每个项目间的短暂延迟

                except NoSuchElementException:
                    print(f"{index:3d}. 无法找到BV号")
                    continue
                except Exception as e:
                    print(f"{index:3d}. 处理视频时出错: {str(e)}")
                    continue

            return bv_numbers

        except TimeoutException:
            print("页面加载超时，请检查网络连接或网站状态")
            return []
        except Exception as e:
            print(f"爬取过程中出现错误: {str(e)}")
            return []

    def save_to_file(self, bv_numbers, filename="bilibili_tech_rank_bv.txt"):
        """将结果保存到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            for bv in bv_numbers:
                f.write(bv + '\n')
        print(f"\nBV号已保存到文件: {filename}")

    def run(self):
        """运行爬虫"""
        try:
            print("开始爬取B站科技数码区排行榜BV号...")
            bv_numbers = self.get_bv_numbers()

            if bv_numbers:
                print(f"\n成功获取 {len(bv_numbers)} 个BV号")
                self.save_to_file(bv_numbers)

                # 显示前10个BV号作为示例
                print("\n前10个BV号:")
                for i, bv in enumerate(bv_numbers[:10], 1):
                    print(f"{i}. {bv}")
            else:
                print("未能获取到任何BV号")

        finally:
            # 关闭浏览器
            self.driver.quit()
            print("\n浏览器已关闭")


if __name__ == "__main__":
    crawler = BilibiliRankingCrawler()
    crawler.run()
