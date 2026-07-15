from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ASSET_DIR = Path(__file__).resolve().parent / "assets"
SIZE = (960, 620)


def font(size):
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def label(draw, xy, text, size=28, fill="#172033"):
    draw.text(xy, text, font=font(size), fill=fill)


def save_ibuprofen():
    image = Image.new("RGB", SIZE, "#eef7fb")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((120, 115, 840, 500), radius=24, fill="white", outline="#3182a8", width=5)
    draw.rectangle((120, 115, 840, 205), fill="#147d92")
    label(draw, (155, 135), "标准测试样例 / 非真实药品包装", 25, "white")
    label(draw, (165, 255), "布洛芬片", 64, "#173b57")
    label(draw, (170, 350), "TEST MEDICINE PACKAGE", 26, "#526579")
    label(draw, (170, 415), "仅用于系统识别与分流测试", 24, "#8a3946")
    image.save(ASSET_DIR / "mock_ibuprofen_box.png")


def save_leaflet():
    image = Image.new("RGB", SIZE, "#f8f8f5")
    draw = ImageDraw.Draw(image)
    label(draw, (90, 55), "阿司匹林肠溶片 - 模拟说明书", 42)
    label(draw, (90, 120), "本文件为测试数据，不是药品使用依据", 24, "#a23a45")
    sections = [
        "【用途】不同规格和适应证用途不同，应遵医嘱使用。",
        "【注意】存在出血风险，不应自行停药或调整剂量。",
        "【禁忌】活动性出血或对本品过敏者禁用。",
        "【提示】请以真实包装说明书和医生、药师意见为准。",
    ]
    for index, text in enumerate(sections):
        label(draw, (90, 205 + index * 82), text, 25)
    image.save(ASSET_DIR / "mock_aspirin_leaflet.png")


def save_lab_report():
    image = Image.new("RGB", SIZE, "white")
    draw = ImageDraw.Draw(image)
    label(draw, (70, 40), "模拟血常规检验报告", 40)
    label(draw, (70, 95), "仅测试文字读取与安全边界，不代表真实患者", 22, "#b13d49")
    columns = [70, 360, 565, 750, 890]
    rows = [165, 235, 305, 375, 445, 515]
    for x in columns:
        draw.line((x, rows[0], x, rows[-1]), fill="#5b6573", width=2)
    for y in rows:
        draw.line((columns[0], y, columns[-1], y), fill="#5b6573", width=2)
    headers = ["项目", "结果", "单位", "参考范围"]
    values = [
        ["白细胞 WBC", "6.2", "10^9/L", "3.5-9.5"],
        ["血红蛋白 HGB", "132", "g/L", "115-150"],
        ["血小板 PLT", "228", "10^9/L", "125-350"],
        ["中性粒细胞 NEUT", "55", "%", "40-75"],
    ]
    for idx, text in enumerate(headers):
        label(draw, (columns[idx] + 12, rows[0] + 18), text, 22)
    for row_idx, row in enumerate(values, start=1):
        for col_idx, text in enumerate(row):
            label(draw, (columns[col_idx] + 12, rows[row_idx] + 18), text, 21)
    image.save(ASSET_DIR / "mock_lab_report.png")


def save_quality_variants():
    base = Image.new("RGB", SIZE, "#f7fafb")
    draw = ImageDraw.Draw(base)
    draw.rectangle((150, 135, 810, 485), fill="white", outline="#315f78", width=4)
    label(draw, (205, 210), "测试药品说明书", 52)
    label(draw, (205, 305), "请保持画面清晰并避免反光", 28)

    dark = base.point(lambda value: int(value * 0.22))
    dark.save(ASSET_DIR / "mock_medicine_dark.png")

    blurry = base.filter(ImageFilter.GaussianBlur(radius=12))
    blurry.save(ASSET_DIR / "mock_leaflet_blurry.png")


def save_nonmedical():
    image = Image.new("RGB", SIZE, "#f2f4f7")
    draw = ImageDraw.Draw(image)
    draw.ellipse((310, 155, 650, 520), fill="#4b9cc5", outline="#24516c", width=5)
    draw.rectangle((330, 130, 630, 260), fill="#4b9cc5")
    draw.ellipse((595, 230, 760, 420), outline="#24516c", width=24)
    label(draw, (310, 65), "普通杯子测试图", 36)
    image.save(ASSET_DIR / "mock_nonmedical_object.png")


def save_skin_schematic():
    image = Image.new("RGB", SIZE, "#f7e0d5")
    draw = ImageDraw.Draw(image)
    label(draw, (185, 45), "皮肤观察测试示意图 / 非临床照片", 34, "#7b2733")
    draw.ellipse((250, 160, 710, 520), fill="#e9b8ae", outline="#b56c6b", width=4)
    for x, y, radius in [(390, 275, 34), (505, 330, 42), (565, 245, 27), (455, 405, 30)]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#cf7778")
    label(draw, (250, 545), "只用于测试场景标签和禁止确诊规则", 25, "#7b2733")
    image.save(ASSET_DIR / "mock_skin_observation.png")


def main():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    save_ibuprofen()
    save_leaflet()
    save_lab_report()
    save_quality_variants()
    save_nonmedical()
    save_skin_schematic()
    print(f"Generated 7 deterministic test images in {ASSET_DIR}")


if __name__ == "__main__":
    main()
