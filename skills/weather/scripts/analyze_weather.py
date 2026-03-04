from datetime import datetime


def get_weather(city: str) -> str:
    """
    查询指定城市的天气信息（示例版本）。

    当前实现为本地模拟数据，仅用于演示 Skill 结构。
    你可以在此基础上接入真实天气 API。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 示例模拟结果
    return (
        f"{now}，{city} 当前为多云，气温 23℃，"
        "西南风 2 级，空气质量良，适合外出。"
        "（以上为示例数据，请根据需要接入真实天气 API）"
    )


if __name__ == "__main__":
    # 简单自测
    print(get_weather("上海"))

