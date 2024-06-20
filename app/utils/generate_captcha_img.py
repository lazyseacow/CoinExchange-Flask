import base64
import time
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import random
import string


def generate_captcha_text(length=4):
    """生成随机验证码文本"""
    timestamp = str(int(time.time_ns()))  # 微秒级别的时间戳
    random.seed(int.from_bytes(timestamp.encode(), 'big'))  # 使用时间戳作为随机数种子
    text = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return text


def generate_captcha_image(text):
    """根据文本生成验证码图片"""
    width, height = 120, 40
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype('arial.ttf', size=30)  # 确保你有这个字体文件或使用其他可用字体
    fill_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    draw.text((5, 2), text=text, fill=fill_color, font=font)

    # 添加干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))  # 随机颜色
        draw.line(((x1, y1), (x2, y2)), fill=color)

    # 添加随机颜色的斑点
    for _ in range(100):  # 控制斑点的数量，可以根据需要调整
        x = random.randint(0, width)
        y = random.randint(0, height)
        radius = random.randint(0, 1)  # 斑点的大小
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))  # 随机颜色
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    # 将图片转换为二进制数据并返回
    buf = BytesIO()
    img.save(buf, 'jpeg')
    # 转换为base64编码
    img_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return img_str
