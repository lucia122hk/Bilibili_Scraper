import os
import time
import traceback
import random
import json
import asyncio

import pandas as pd
import requests
from bilibili_api import video, comment, Credential, sync
from xml.etree import ElementTree as ET

# 设置复杂的User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# 设置输出目录
OUTPUT_DIR = os.path.join(os.getcwd(), 'data')


def get_random_headers():
    """获取随机的请求头"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }


def ensure_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    return OUTPUT_DIR


def get_credentials():
    # 请在这里设置你的凭证
    sessdata = "0cd79a9c%2C1769858379%2Ced1d9%2A81CjDDxZoBx7nkg_2KxJZtJAsamNvB0tFWyjRgSECHJeTXQwSkEBHLvx7EioCumSDYESESVlBIR090Sk5Ub1B4V3QtRnZDT2pRdGx1dmFxNUZQOVVUSFVBd1ZEZFdPa2hWM2NkTVZ5aTlkdEQ3NHFDa3h1VmxUV29pcWlsNjNMekxWVDlHVlhEMXNnIIEC"
    bilijct = "be43fe5b48b2f98f133a048e7a6bdd9c"
    buvid3 = "A7031780-BA1B-DA2A-613B-75A664CAA4DD91000infoc"

    return Credential(sessdata=sessdata, bili_jct=bilijct, buvid3=buvid3)


def get_video_comments(bvid: str, credential=None, max_comments=10000):
    comments = []
    try:
        v = video.Video(bvid=bvid, credential=credential)
        page = 1
        count = 0
        retry_count = 0
        max_retries = 3

        while count < max_comments and retry_count < max_retries:
            try:
                # 增加随机延迟，模拟人类行为
                delay = random.uniform(2, 5)  # 2-5秒随机延迟
                time.sleep(delay)

                res = sync(comment.get_comments(
                    oid=v.get_aid(),
                    type_=comment.CommentResourceType.VIDEO,
                    page_index=page,
                    credential=credential
                ))

                # 检查返回结果是否有效
                if not res or not isinstance(res, dict):
                    print(f"BV号 {bvid} 第{page}页返回结果无效")
                    retry_count += 1
                    continue

                # 安全地获取replies
                replies = res.get("replies")
                if replies is None:
                    print(f"BV号 {bvid} 第{page}页没有replies字段")
                    break

                if not isinstance(replies, list):
                    print(f"BV号 {bvid} 第{page}页replies字段不是列表类型: {type(replies)}")
                    break

                if not replies:
                    print(f"BV号 {bvid} 第{page}页没有更多评论")
                    break

                print(f"BV号 {bvid} 第{page}页获取到{len(replies)}条评论")

                for r in replies:
                    # 检查评论结构是否完整
                    if not r or not isinstance(r, dict):
                        print(f"跳过无效的评论条目: {r}")
                        continue

                    try:
                        # 安全地获取评论内容
                        content = r.get("content", {})
                        if not content or not isinstance(content, dict):
                            print(f"评论内容格式异常: {r}")
                            continue

                        message = content.get("message", "")
                        if not message:
                            continue

                        comm = {
                            'comment': message,
                            'reply': [],
                        }

                        # 安全地获取用户信息
                        member = r.get("member", {})
                        if member and isinstance(member, dict):
                            uname = member.get("uname", "未知用户")
                        else:
                            uname = "未知用户"

                        # 处理回复
                        reply_list = r.get("replies", [])
                        if reply_list and isinstance(reply_list, list):
                            for reply in reply_list:
                                if not reply or not isinstance(reply, dict):
                                    continue

                                reply_content = reply.get("content", {})
                                if not reply_content or not isinstance(reply_content, dict):
                                    continue

                                reply_message = reply_content.get("message", "")
                                if reply_message:
                                    reply_text = f"回复@{uname}: {reply_message}"
                                    comm['reply'].append(reply_text)

                        comments.append(comm)
                        count += 1

                        # 每处理10条评论增加一个小延迟
                        if count % 10 == 0:
                            time.sleep(random.uniform(0.5, 1.5))

                    except Exception as e:
                        print(f"处理单条评论时出错: {str(e)}")
                        continue

                # 检查是否还有更多页面
                page_info = res.get("page", {})
                if not page_info:
                    print(f"BV号 {bvid} 没有分页信息")
                    break

                current_num = page_info.get("num", 0) * page_info.get("size", 0)
                total_count = page_info.get("count", 0)

                if current_num >= total_count:
                    print(f"BV号 {bvid} 评论获取完成，共{count}条评论")
                    break

                page += 1
                retry_count = 0  # 重置重试计数

            except Exception as e:
                retry_count += 1
                print(f"BV号 {bvid} 第{page}页获取失败，第{retry_count}次重试，错误: {str(e)}")
                traceback.print_exc()

                if retry_count >= max_retries:
                    print(f"BV号 {bvid} 评论获取失败，已达到最大重试次数")
                    break

                # 重试前等待更长时间
                time.sleep(random.uniform(10, 15))

    except Exception as e:
        print(f"获取BV号 {bvid} 评论时发生错误: {str(e)}")
        traceback.print_exc()

    return comments


def get_cid(bvid):
    """通过BV号获取视频cid"""
    url = "https://api.bilibili.com/x/player/pagelist"
    params = {
        "bvid": bvid,
        "jsonp": "jsonp"
    }
    response = requests.get(url, params=params, headers=get_random_headers())
    data = response.json()
    # 获取第一个分P的cid
    cid = data['data'][0]['cid']
    return cid


def get_video_danmaku(bvid: str):
    danmaku = []
    try:
        # 增加延迟
        time.sleep(random.uniform(1, 3))

        url = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}&jsonp=jsonp"
        cid = requests.get(url, headers=get_random_headers()).json()["data"][0]["cid"]

        xml_url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
        response = requests.get(xml_url, headers=get_random_headers())
        response.encoding = "utf-8"
        root = ET.fromstring(response.text)
        for d in root.findall("d"):
            danmaku.append(d.text)
    except Exception as e:
        print(f"获取BV号 {bvid} 弹幕失败: {str(e)}")
    return danmaku


def get_video_info(bvid):
    """
    通过bvid获取B站视频信息
    """
    # 增加延迟
    time.sleep(random.uniform(1, 3))

    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"

    try:
        response = requests.get(url, headers=get_random_headers())
        response.raise_for_status()
        json_data = response.json()

        if json_data['code'] == 0:
            data = json_data['data']
            title = data['title']
            description = data['desc']
            return title, description
        else:
            print(f"BV号 {bvid} API返回错误: {json_data['message']}")
            return None, None

    except Exception as e:
        print(f"BV号 {bvid} 请求视频信息出错: {e}")
        return None, None


async def get_video_stats(bvid):
    try:
        # 实例化Video对象
        v = video.Video(bvid=bvid)
        # 获取视频信息
        info = await v.get_info()
        # 提取播放量和评论数
        stat = info['stat']
        return stat
    except Exception as e:
        print(f"获取BV号 {bvid} 统计信息失败: {str(e)}")
        return {}


def save_to_csv(data, bvid):
    output_dir = ensure_dir_exists()
    path = os.path.join(output_dir, f"BVID_{bvid}.xlsx")

    try:
        df1 = pd.DataFrame(data['comments'])
        df2 = pd.DataFrame(data['danmaku'], columns=['弹幕内容'])
        df3 = pd.DataFrame([{'标题': data['title'], '描述': data['description']}])
        df4 = pd.DataFrame([data['stat']])

        with pd.ExcelWriter(path) as writer:
            df1.to_excel(writer, sheet_name='评论', index=False)
            df2.to_excel(writer, sheet_name='弹幕', index=False)
            df3.to_excel(writer, sheet_name='视频信息', index=False)
            df4.to_excel(writer, sheet_name='统计数据', index=False)
        print(f"BV号 {bvid} 数据已保存至: {path}")
    except Exception as e:
        print(f"保存BV号 {bvid} 数据失败: {str(e)}")


if __name__ == "__main__":
    # 这里需要你提供获取所有BV号的函数

    root = os.getcwd()
    all_file = os.listdir(root)

    if 'all_bvids.json' not in all_file:
        all_bvids = ["BV1xx411c7mQ"]  # 示例BV号，请替换为实际值
        with open('all_bvids.json', 'w', encoding='utf-8') as file:
            json.dump(all_bvids, file, ensure_ascii=False, indent=2)
    else:
        with open('all_bvids.json', 'r', encoding='utf-8') as file:
            all_bvids = json.load(file)

    print(f"开始爬取，共{len(all_bvids)}个视频")

    credential = get_credentials()

    for i, bvid in enumerate(all_bvids, 1):
        print(f"\n正在处理第{i}/{len(all_bvids)}个视频: {bvid}")

        try:
            comments = get_video_comments(bvid, credential)
            danmaku = get_video_danmaku(bvid)
            title, description = get_video_info(bvid)
            stat = asyncio.run(get_video_stats(bvid))

            res = {
                "comments": comments,
                "danmaku": danmaku,
                "title": title,
                "description": description,
                "stat": stat,
            }
            save_to_csv(res, bvid)
            print(f"BV号 {bvid} 处理完成 - 评论数: {len(comments)}, 弹幕数: {len(danmaku)}")

        except Exception as e:
            print(f"处理BV号 {bvid} 时发生严重错误: {str(e)}")
            traceback.print_exc()

        # 视频间的延迟
        if i < len(all_bvids):
            delay = random.uniform(10, 20)  # 10-20秒随机延迟
            print(f"等待{delay:.1f}秒后处理下一个视频...")
            time.sleep(delay)

    print("\n所有视频处理完成！")
