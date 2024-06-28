import qrcode
import base64
from io import BytesIO


def generate_qr_code(address):
    """
    生成指定地址的二维码。

    :param address: 需要生成二维码的地址字符串。
    :return: 该地址的二维码 base64 编码字符串。
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    # 添加数据到二维码
    qr.add_data(address)
    qr.make(fit=True)

    # 创建并保存图像至字节流
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    # 转换为base64编码
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    image_url = f"data:image/png;base64,{img_str}"
    return image_url
