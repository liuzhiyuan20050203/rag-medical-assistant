import base64
import binascii
import io
import re
from statistics import mean

from PIL import Image, ImageFilter, ImageStat

from rag_service import search_knowledge
from safety_check import check_warning


MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_VIDEO_FRAMES = 8


def decode_data_url(data_url: str):
    data_url = (data_url or "").strip()
    media_type = "application/octet-stream"
    payload = data_url

    if data_url.startswith("data:") and "," in data_url:
        header, payload = data_url.split(",", 1)
        media_type = header[5:].split(";", 1)[0] or media_type

    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("文件内容不是有效的Base64数据")

    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("单张图片或关键帧不能超过12MB")

    return raw, media_type


def open_image(data_url: str):
    raw, media_type = decode_data_url(data_url)

    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))
    except Exception as exc:
        raise ValueError(f"无法识别图片文件：{exc}")

    return image, raw, media_type


def classify_level(value, low, high):
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "normal"


def image_statistics(image):
    rgb = image.convert("RGB")
    sample = rgb.copy()
    sample.thumbnail((320, 320))
    gray = sample.convert("L")

    gray_stat = ImageStat.Stat(gray)
    rgb_stat = ImageStat.Stat(sample)
    edge_stat = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))

    brightness = float(gray_stat.mean[0])
    contrast = float(gray_stat.stddev[0])
    sharpness = float(edge_stat.mean[0])
    average_rgb = [round(float(value), 2) for value in rgb_stat.mean]

    red, green, blue = average_rgb
    red_bias = round(red - max(green, blue), 2)
    blue_bias = round(blue - max(red, green), 2)

    return {
        "width": image.width,
        "height": image.height,
        "format": image.format or "unknown",
        "mode": image.mode,
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "sharpness": round(sharpness, 2),
        "average_rgb": average_rgb,
        "brightness_level": classify_level(brightness, 80, 205),
        "contrast_level": classify_level(contrast, 28, 88),
        "sharpness_level": classify_level(sharpness, 8, 38),
        "red_bias": red_bias,
        "blue_bias": blue_bias,
        "aspect_ratio": round(image.width / image.height, 3) if image.height else 0
    }


def infer_scene_tags(file_name: str, note: str, stats: dict):
    text = f"{file_name or ''} {note or ''}".lower()
    tags = []

    tag_rules = [
        ("skin", ["皮肤", "红疹", "皮疹", "湿疹", "过敏", "瘙痒", "skin", "rash"]),
        ("medicine", ["药", "药盒", "说明书", "medicine", "pill", "tablet"]),
        ("throat", ["咽喉", "喉咙", "口腔", "扁桃体", "throat", "mouth"]),
        ("stool", ["大便", "腹泻", "黑便", "便血", "stool"]),
        ("wound", ["伤口", "流血", "破溃", "wound", "cut"])
    ]

    for tag, keywords in tag_rules:
        if any(keyword in text for keyword in keywords):
            tags.append(tag)

    if stats["brightness_level"] == "low":
        tags.append("low_light")
    if stats["brightness_level"] == "high":
        tags.append("overexposed")
    if stats["sharpness_level"] == "low":
        tags.append("possibly_blurry")
    if stats["red_bias"] > 20:
        tags.append("red_tone_visible")

    return sorted(set(tags)) or ["general_image"]


def build_image_observations(stats, tags):
    observations = []

    if stats["brightness_level"] == "low":
        observations.append("画面偏暗，细节可能不够清楚。")
    elif stats["brightness_level"] == "high":
        observations.append("画面偏亮，局部细节可能过曝。")
    else:
        observations.append("画面亮度处于可观察范围。")

    if stats["sharpness_level"] == "low":
        observations.append("画面可能存在模糊，建议重新对焦拍摄。")
    else:
        observations.append("画面清晰度基本可用于记录和复核。")

    if "skin" in tags:
        observations.append("已按皮肤症状图片场景处理，可结合瘙痒、疼痛、范围变化等文字描述继续问诊。")
    if "medicine" in tags:
        observations.append("已按药品或说明书图片场景处理，建议补充药名、规格、用药人群和当前症状。")
    if "throat" in tags:
        observations.append("已按咽喉或口腔图片场景处理，建议补充发热、吞咽困难、持续时间等信息。")
    if "red_tone_visible" in tags:
        observations.append("画面红色通道偏高，可能包含发红区域，但不能仅凭图像判断病因。")

    return observations


def build_capture_tips(stats):
    tips = []

    if stats["brightness_level"] != "normal":
        tips.append("在自然光或均匀补光下重新拍摄，避免强反光和阴影。")
    if stats["sharpness_level"] == "low":
        tips.append("保持镜头稳定并点击主体区域对焦。")
    if stats["width"] < 640 or stats["height"] < 480:
        tips.append("图片分辨率偏低，建议上传更清晰的原图。")

    tips.append("请同时用文字描述症状、持续时间、是否加重、是否用药和特殊人群情况。")
    return tips


def analyze_image_payload(image_data: str, file_name: str = "", note: str = ""):
    image, raw, media_type = open_image(image_data)
    stats = image_statistics(image)
    tags = infer_scene_tags(file_name, note, stats)

    return {
        "success": True,
        "module": "image",
        "file_name": file_name,
        "media_type": media_type,
        "file_size": len(raw),
        "visual": stats,
        "tags": tags,
        "observations": build_image_observations(stats, tags),
        "capture_tips": build_capture_tips(stats),
        "medical_notice": "图片识别结果仅用于辅助记录和描述，不能替代医生面诊或影像诊断。"
    }


def analyze_video_payload(frames, file_name: str = "", note: str = "", duration=0):
    if not frames:
        raise ValueError("请至少提供一个视频关键帧")

    selected_frames = frames[:MAX_VIDEO_FRAMES]
    frame_results = []

    for index, frame in enumerate(selected_frames, start=1):
        if isinstance(frame, dict):
            image_data = frame.get("image", "")
            timestamp = frame.get("timestamp", 0)
        else:
            image_data = frame
            timestamp = 0

        result = analyze_image_payload(
            image_data,
            file_name=f"{file_name or 'video'}#frame-{index}",
            note=note
        )
        result["frame_index"] = index
        result["timestamp"] = timestamp
        frame_results.append(result)

    brightness_values = [item["visual"]["brightness"] for item in frame_results]
    sharpness_values = [item["visual"]["sharpness"] for item in frame_results]
    tags = sorted({tag for item in frame_results for tag in item.get("tags", [])})

    weak_frames = [
        {
            "frame_index": item["frame_index"],
            "timestamp": item["timestamp"],
            "reason": "画面偏暗或可能模糊"
        }
        for item in frame_results
        if item["visual"]["brightness_level"] != "normal"
        or item["visual"]["sharpness_level"] == "low"
    ]

    return {
        "success": True,
        "module": "video",
        "file_name": file_name,
        "duration": duration,
        "frame_count": len(frame_results),
        "sample_limit": MAX_VIDEO_FRAMES,
        "summary": {
            "average_brightness": round(mean(brightness_values), 2),
            "average_sharpness": round(mean(sharpness_values), 2),
            "tags": tags,
            "weak_frame_count": len(weak_frames)
        },
        "weak_frames": weak_frames,
        "frames": frame_results,
        "medical_notice": "视频关键帧识别仅用于辅助观察画面质量和可见线索，不能替代医生检查。"
    }


def normalize_transcript(text: str):
    text = re.sub(r"\s+", " ", text or "").strip()
    text = text.replace("，", "，").replace(",", "，")
    return text


def analyze_voice_transcript(text: str):
    transcript = normalize_transcript(text)

    if not transcript:
        return {
            "success": False,
            "message": "没有识别到有效语音文本",
            "transcript": ""
        }

    warning = check_warning(transcript)
    retrieved_docs = [] if warning.get("has_warning") else search_knowledge(transcript, top_k=2)

    return {
        "success": True,
        "module": "voice",
        "transcript": transcript,
        "character_count": len(transcript),
        "warning": warning,
        "retrieved_docs": retrieved_docs,
        "next_action": "trigger_warning" if warning.get("has_warning") else "send_to_chat",
        "message": "已完成语音文本分析"
    }
