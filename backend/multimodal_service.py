import base64
import binascii
import io
import re
from statistics import mean

from PIL import Image, ImageFilter, ImageStat

from rag_service import search_knowledge
from safety_check import check_warning
from vision_llm_service import analyze_images_with_vision_llm


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


def compact_text(value, limit=180):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()

    for marker in ["最终答案：", "最终回答：", "结论：", "回答："]:
        if marker in text:
            text = text.split(marker, 1)[1].strip()
            break

    return text[:limit].rstrip()


def ensure_list(value, limit=5):
    if not value:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]

    cleaned = []
    for item in items:
        text = compact_text(item, 120)
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break

    return cleaned


def get_llm_analysis(llm_result):
    if not llm_result or not llm_result.get("success"):
        return {}
    analysis = llm_result.get("analysis")
    return analysis if isinstance(analysis, dict) else {}


def scene_name(tags):
    mapping = {
        "skin": "皮肤相关图片",
        "medicine": "药品或说明书图片",
        "throat": "咽喉或口腔图片",
        "stool": "排泄物相关图片",
        "wound": "伤口相关图片",
        "low_light": "低光照图片",
        "overexposed": "过曝图片",
        "possibly_blurry": "模糊图片",
        "general_image": "普通图片"
    }

    for tag in tags:
        if tag in mapping:
            return mapping[tag]
    return "普通图片"


URGENT_KEYWORDS = [
    "胸痛", "胸口痛", "呼吸困难", "喘不上气", "咳血", "高热不退",
    "意识模糊", "抽搐", "严重腹痛", "剧烈腹痛", "呕血", "黑便", "便血",
    "面部肿胀", "喉咙肿胀", "吞咽困难", "明显出血", "快速加重",
    "儿童高热", "孕妇", "过敏性休克"
]

COMMON_SYMPTOM_KEYWORDS = [
    "发热", "发烧", "咳嗽", "咽痛", "嗓子疼", "喉咙痛", "流鼻涕",
    "腹痛", "腹泻", "恶心", "呕吐", "胃痛", "头痛", "头晕",
    "红疹", "皮疹", "瘙痒", "疼痛", "肿胀", "出血"
]

COMMON_RED_FLAGS = [
    "出现胸痛、呼吸困难、意识模糊、抽搐、咳血或明显出血时，建议立即急诊。",
    "高热不退、症状快速加重、剧烈疼痛或无法进食饮水时，建议尽快线下就医。",
    "儿童、孕妇、老人、有基础疾病或免疫力低下人群出现明显不适时，不建议只在家观察。"
]


def keyword_negated(text: str, keyword: str):
    start = text.find(keyword)
    if start < 0:
        return False
    prefix = text[max(0, start - 6):start]
    return any(word in prefix for word in ["没有", "无", "未", "不", "否认", "没"])


def text_has_urgent_signal(text: str):
    text = text or ""
    return any(keyword in text and not keyword_negated(text, keyword) for keyword in URGENT_KEYWORDS)


def text_has_common_symptom(text: str):
    text = text or ""
    return any(keyword in text and not keyword_negated(text, keyword) for keyword in COMMON_SYMPTOM_KEYWORDS)


def effective_warning(text: str, warning: dict):
    if not warning.get("has_warning"):
        return warning

    matched = [
        keyword for keyword in warning.get("matched", [])
        if keyword in text and not keyword_negated(text, keyword)
    ]

    if matched:
        return {
            **warning,
            "matched": matched
        }

    if text_has_urgent_signal(text):
        return {
            "has_warning": True,
            "matched": [keyword for keyword in URGENT_KEYWORDS if keyword in text and not keyword_negated(text, keyword)],
            "message": "你描述中包含可能需要尽快处理的危险信号，建议及时线下就医。"
        }

    return {
        "has_warning": False,
        "matched": [],
        "message": ""
    }


def query_from_parts(*parts):
    return " ".join(compact_text(part, 240) for part in parts if compact_text(part, 240))


def fallback_query_for_tags(tags):
    tag_query = {
        "skin": "皮肤 瘙痒 红疹 过敏 湿疹",
        "throat": "咽痛 咳嗽 发热 咽炎 感冒",
        "stool": "腹泻 腹痛 大便异常 消化",
        "wound": "伤口 出血 感染 疼痛",
        "medicine": "药品 用药 注意事项 禁忌"
    }

    for tag in tags:
        if tag in tag_query:
            return tag_query[tag]
    return ""


def retrieve_condition_docs(query_text: str, tags=None, top_k=3):
    tags = tags or []
    query_text = compact_text(query_text, 500) or fallback_query_for_tags(tags)

    if not query_text:
        return []

    try:
        docs = search_knowledge(query_text, top_k=top_k + 2)
    except Exception:
        return []

    disease_docs = [doc for doc in docs if doc.get("doc_type") == "disease"]
    return disease_docs[:top_k]


def condition_items_from_docs(docs):
    items = []

    for doc in docs:
        raw = doc.get("raw") or {}
        name = raw.get("name") or doc.get("title") or "相关常见病方向"
        symptoms = "、".join(ensure_list(raw.get("symptoms"), limit=4))
        description = compact_text(raw.get("description") or doc.get("content"), 100)

        if symptoms:
            item = f"{name}：可能相关表现包括{symptoms}。"
        else:
            item = f"{name}：与当前描述有一定相关性。"

        if description:
            item += description

        items.append(item)

    return items


def fallback_conditions(tags, query_text=""):
    if "medicine" in tags:
        return ["药品或用药问题：建议结合药品名称、规格、用药人群和当前症状，由医生或药师判断是否适合使用。"]
    if "skin" in tags or any(word in query_text for word in ["红疹", "瘙痒", "皮肤", "过敏", "湿疹"]):
        return ["皮肤过敏、湿疹或其他皮肤炎症方向：常见表现可包括发红、瘙痒、皮疹、风团或脱屑。"]
    if "throat" in tags or any(word in query_text for word in ["咽痛", "嗓子疼", "咳嗽", "发热"]):
        return ["咽炎、普通感冒或流感样症状方向：常见表现可包括咽痛、咳嗽、鼻塞、流涕、发热或乏力。"]
    if "stool" in tags or any(word in query_text for word in ["腹泻", "腹痛", "呕吐", "黑便", "便血"]):
        return ["腹泻、胃肠炎或其他消化道问题方向：常见表现可包括腹痛、恶心、呕吐、大便次数增多或大便异常。"]
    if "wound" in tags or any(word in query_text for word in ["伤口", "出血", "感染", "红肿"]):
        return ["伤口感染或外伤相关问题方向：需要关注红肿热痛、渗液、出血、活动受限和发热。"]
    return ["目前信息不足，暂不能给出明确的常见病方向；请补充主要症状、持续时间、年龄和伴随症状。"]


def department_from_context(tags, docs, query_text):
    categories = " ".join(compact_text((doc.get("raw") or {}).get("category"), 30) for doc in docs)
    text = f"{query_text} {' '.join(tags)} {categories}"

    if text_has_urgent_signal(text):
        return "急诊科"
    if "medicine" in tags or "药" in text:
        return "药师咨询或开药医生"
    if "skin" in tags or "皮肤" in text or "红疹" in text or "瘙痒" in text:
        return "皮肤科"
    if "throat" in tags or "咽" in text or "嗓子" in text or "喉咙" in text or "发热" in text or "咳嗽" in text:
        return "耳鼻喉科或呼吸内科"
    if "腹" in text or "胃" in text or "消化" in text or "stool" in tags:
        return "消化内科"
    if "wound" in tags or "伤口" in text or "出血" in text:
        return "外科或急诊科"
    if "头痛" in text or "头晕" in text:
        return "全科、神经内科或急诊科"
    return "全科或普通内科"


def build_visit_advice(risk_level, department, warning, docs):
    if risk_level == "高":
        return {
            "urgency": "建议立即线下就医",
            "timing": "现在就去急诊；若症状很重或行动困难，优先拨打当地急救电话。",
            "department": department or "急诊科",
            "reason": warning.get("message") or "描述中出现较高风险信号，需要专业医生当面评估。"
        }

    if risk_level == "中":
        return {
            "urgency": "建议尽快门诊评估",
            "timing": "建议今天或近1-2天内到门诊/线上问诊；如果加重，提前去急诊。",
            "department": department,
            "reason": "当前信息能匹配到常见病方向，但还不能仅凭图片、视频或文字自行判断病因。"
        }

    return {
        "urgency": "可先补充信息并观察",
        "timing": "如果症状轻微且没有危险信号，可先记录变化；持续不缓解、反复出现或加重时去门诊。",
        "department": department,
        "reason": "目前没有明显高危信号，但信息仍不足以替代医生判断。"
    }


def care_items_from_docs(docs):
    items = []
    for doc in docs:
        raw = doc.get("raw") or {}
        care = compact_text(raw.get("care_advice"), 130)
        if care and care not in items:
            items.append(care)
    return items[:3]


def medicine_items_from_docs(docs):
    items = []
    for doc in docs:
        raw = doc.get("raw") or {}
        notice = compact_text(raw.get("medicine_notice"), 130)
        if notice and notice not in items:
            items.append(notice)
    if not items:
        items.append("不要仅凭图片或语音结果自行使用处方药、抗生素或调整剂量；用药请按说明书、医生或药师指导。")
    return items[:3]


def red_flags_from_docs(docs, warning):
    items = []
    if warning.get("message"):
        items.append(warning.get("message"))

    for doc in docs:
        raw = doc.get("raw") or {}
        item = compact_text(raw.get("warning"), 150)
        if item and item not in items:
            items.append(item)

    for item in COMMON_RED_FLAGS:
        if item not in items:
            items.append(item)

    return items[:5]


def determine_risk(query_text, tags, warning, condition_docs):
    if warning.get("has_warning") or text_has_urgent_signal(query_text):
        return "高"
    if condition_docs or {"skin", "throat", "wound", "stool", "medicine"} & set(tags):
        return "中"
    if text_has_common_symptom(query_text):
        return "中"
    return "低"


def build_patient_conclusion(source, condition_docs, conditions, visit_advice):
    if condition_docs:
        names = "、".join(compact_text((doc.get("raw") or {}).get("name") or doc.get("title"), 30) for doc in condition_docs[:2])
        return f"根据你提供的{source}，目前更像是与{names}等方向相关。建议按下面的就诊级别处理，不要仅凭识别结果自行确诊或用药。"

    return f"根据你提供的{source}，目前信息还不足以判断具体病因。建议先补充症状细节，并按“{visit_advice['urgency']}”处理。"


def build_image_answer(stats, tags, observations, capture_tips, llm_result, note):
    analysis = get_llm_analysis(llm_result)
    visible_findings = ensure_list(analysis.get("visible_findings")) or observations[:3]
    query_text = query_from_parts(
        note,
        analysis.get("summary"),
        analysis.get("likely_scene"),
        " ".join(visible_findings),
        fallback_query_for_tags(tags)
    )
    warning = effective_warning(query_text, check_warning(query_text))
    condition_docs = retrieve_condition_docs(query_text, tags)
    possible_conditions = condition_items_from_docs(condition_docs) or fallback_conditions(tags, query_text)
    risk_level = determine_risk(query_text, tags, warning, condition_docs)
    department = department_from_context(tags, condition_docs, query_text)
    visit_advice = build_visit_advice(risk_level, department, warning, condition_docs)

    return {
        "title": "就诊建议",
        "conclusion": build_patient_conclusion("图片和补充描述", condition_docs, possible_conditions, visit_advice),
        "risk_level": risk_level,
        "visit_advice": visit_advice,
        "possible_conditions": possible_conditions,
        "evidence": visible_findings,
        "actions": care_items_from_docs(condition_docs) or [
            "先补充症状持续时间、是否疼痛/瘙痒/发热、范围是否扩大、是否已经用药。",
            "保留清晰图片和症状变化记录，方便医生判断。"
        ],
        "medication_reminder": medicine_items_from_docs(condition_docs),
        "red_flags": red_flags_from_docs(condition_docs, warning),
        "follow_up_questions": ensure_list(analysis.get("recommended_questions"), limit=4) or [
            "症状从什么时候开始？",
            "是否正在加重，是否伴随发热、疼痛、瘙痒、出血或肿胀？",
            "是否已经用药，用的是什么药？"
        ],
        "medical_notice": "以上是基于图片、描述和本地知识库的就诊建议，不等同于确诊；最终诊断和用药请以医生或药师意见为准。"
    }


def build_video_answer(frame_results, weak_frames, llm_result, note):
    analysis = get_llm_analysis(llm_result)
    tags = sorted({tag for item in frame_results for tag in item.get("tags", [])})
    visible_findings = ensure_list(analysis.get("visible_findings")) or [
        f"已从视频中抽取 {len(frame_results)} 个关键帧进行判断。",
        f"有 {len(weak_frames)} 个关键帧可能影响判断清晰度。"
    ]
    query_text = query_from_parts(
        note,
        analysis.get("summary"),
        analysis.get("likely_scene"),
        " ".join(visible_findings),
        fallback_query_for_tags(tags)
    )
    warning = effective_warning(query_text, check_warning(query_text))
    condition_docs = retrieve_condition_docs(query_text, tags)
    possible_conditions = condition_items_from_docs(condition_docs) or fallback_conditions(tags, query_text)
    risk_level = determine_risk(query_text, tags, warning, condition_docs)
    department = department_from_context(tags, condition_docs, query_text)
    visit_advice = build_visit_advice(risk_level, department, warning, condition_docs)

    return {
        "title": "就诊建议",
        "conclusion": build_patient_conclusion("视频关键帧和补充描述", condition_docs, possible_conditions, visit_advice),
        "risk_level": risk_level,
        "visit_advice": visit_advice,
        "possible_conditions": possible_conditions,
        "evidence": visible_findings,
        "actions": care_items_from_docs(condition_docs) or [
            "优先选择清晰、稳定、主体完整的画面重新分析。",
            "补充症状持续时间、变化过程、是否加重和伴随症状。"
        ],
        "medication_reminder": medicine_items_from_docs(condition_docs),
        "red_flags": red_flags_from_docs(condition_docs, warning),
        "follow_up_questions": ensure_list(analysis.get("recommended_questions"), limit=4) or [
            "视频中的不适持续了多久？",
            "是否伴随发热、疼痛、出血、呼吸困难或快速加重？",
            "是否已经处理或用药？"
        ],
        "medical_notice": "以上是基于视频关键帧、描述和本地知识库的就诊建议，不等同于确诊；最终诊断和用药请以医生或药师意见为准。"
    }


def build_voice_answer(transcript, warning, retrieved_docs):
    query_text = compact_text(transcript, 500)
    urgent_warning = effective_warning(query_text, warning)
    if text_has_urgent_signal(query_text) and not warning.get("has_warning"):
        urgent_warning = {
            "has_warning": True,
            "matched": [keyword for keyword in URGENT_KEYWORDS if keyword in query_text],
            "message": "你描述中包含可能需要尽快处理的危险信号，建议及时线下就医。"
        }

    condition_docs = [doc for doc in retrieved_docs if doc.get("doc_type") == "disease"][:3]
    possible_conditions = condition_items_from_docs(condition_docs) or fallback_conditions([], query_text)
    risk_level = determine_risk(query_text, [], urgent_warning, condition_docs)
    department = department_from_context([], condition_docs, query_text)
    visit_advice = build_visit_advice(risk_level, department, urgent_warning, condition_docs)

    return {
        "title": "就诊建议",
        "conclusion": build_patient_conclusion("症状描述", condition_docs, possible_conditions, visit_advice),
        "risk_level": risk_level,
        "visit_advice": visit_advice,
        "possible_conditions": possible_conditions,
        "evidence": [f"你描述的症状：{query_text}"],
        "actions": care_items_from_docs(condition_docs) or [
            "记录体温、疼痛程度、症状开始时间和是否加重。",
            "如果症状轻微，可先休息、补水并观察变化；加重或反复时去门诊。"
        ],
        "medication_reminder": medicine_items_from_docs(condition_docs),
        "red_flags": red_flags_from_docs(condition_docs, urgent_warning),
        "follow_up_questions": [
            "最主要的不适是什么，持续了多久？",
            "有没有发热、呼吸困难、胸痛、出血、呕吐、意识异常等情况？",
            "年龄、是否怀孕、是否有基础疾病或正在用药？",
            "症状是在变轻、持平还是加重？"
        ],
        "medical_notice": "以上是基于症状描述和本地知识库的就诊建议，不等同于确诊；最终诊断和用药请以医生或药师意见为准。"
    }


def analyze_image_payload(
    image_data: str,
    file_name: str = "",
    note: str = "",
    include_llm: bool = True
):
    image, raw, media_type = open_image(image_data)
    stats = image_statistics(image)
    tags = infer_scene_tags(file_name, note, stats)
    llm_result = (
        analyze_images_with_vision_llm([image_data], note=note)
        if include_llm
        else None
    )
    observations = build_image_observations(stats, tags)
    capture_tips = build_capture_tips(stats)

    return {
        "success": True,
        "module": "image",
        "file_name": file_name,
        "media_type": media_type,
        "file_size": len(raw),
        "visual": stats,
        "tags": tags,
        "answer": build_image_answer(stats, tags, observations, capture_tips, llm_result, note),
        "observations": observations,
        "capture_tips": capture_tips,
        "llm": llm_result,
        "medical_notice": "图片识别结果仅用于辅助记录和描述，不能替代医生面诊或影像诊断。"
    }


def analyze_video_payload(frames, file_name: str = "", note: str = "", duration=0):
    if not frames:
        raise ValueError("请至少提供一个视频关键帧")

    selected_frames = frames[:MAX_VIDEO_FRAMES]
    frame_results = []
    frame_images = []

    for index, frame in enumerate(selected_frames, start=1):
        if isinstance(frame, dict):
            image_data = frame.get("image", "")
            timestamp = frame.get("timestamp", 0)
        else:
            image_data = frame
            timestamp = 0

        frame_images.append(image_data)
        result = analyze_image_payload(
            image_data,
            file_name=f"{file_name or 'video'}#frame-{index}",
            note=note,
            include_llm=False
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

    llm_result = analyze_images_with_vision_llm(frame_images, note=note)

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
        "answer": build_video_answer(frame_results, weak_frames, llm_result, note),
        "llm": llm_result,
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
            "transcript": "",
            "answer": {
                "title": "语音文本分析结论",
                "conclusion": "没有收到可分析的语音文本。",
                "risk_level": "未知",
                "evidence": [],
                "actions": ["请重新语音输入，或直接在文本框中输入症状后再分析。"],
                "follow_up_questions": [],
                "medical_notice": "本结果用于辅助整理健康信息，不能替代医生诊断或药师指导。"
            }
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
        "answer": build_voice_answer(transcript, warning, retrieved_docs),
        "next_action": "trigger_warning" if warning.get("has_warning") else "send_to_chat",
        "message": "已完成语音文本分析"
    }
