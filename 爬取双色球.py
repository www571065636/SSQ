import requests
import pandas as pd


def fetch_ssq_100():
    # 官方往期查询的JSON数据接口，issueCount=100 代表获取最近100期
    url = 'http://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice'
    params = {
        'name': 'ssq',
        'issueCount': 100
    }

    try:
        # 设置请求头，模拟正常浏览器访问，防止被拦截
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # 检查网络请求是否成功

        # 解析返回的JSON数据
        data = response.json().get('result')
        if not data:
            print("未获取到数据，请稍后重试。")
            return None

        # 提取我们需要的核心字段：期号、日期、红球、蓝球
        lottery_list = []
        for item in data:
            lottery_list.append({
                '期号': item.get('code'),
                '开奖日期': item.get('date'),
                '红球': item.get('red'),  # 红球通常是逗号分隔的字符串
                '蓝球': item.get('blue')
            })

        # 转换为 DataFrame 方便查看和保存
        df = pd.DataFrame(lottery_list)
        return df

    except Exception as e:
        print(f"数据获取失败: {e}")
        return None


# 执行爬取并打印前5行数据
df_ssq = fetch_ssq_100()
if df_ssq is not None:
    print(df_ssq.head())
    # 如果你想保存为Excel，可以取消下面这行的注释
    # df_ssq.to_excel("双色球近100期数据.xlsx", index=False)