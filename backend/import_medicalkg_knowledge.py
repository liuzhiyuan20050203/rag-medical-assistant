import argparse
import json
import re
from collections import Counter, defaultdict

import requests

from knowledge_service import get_all_diseases, get_all_medicines, save_json
from knowledge_service import DISEASE_FILE, MEDICINE_FILE


SOURCE_URL = "https://raw.githubusercontent.com/liuhuanyong/QASystemOnMedicalKG/master/data/medical.json"
SOURCE_LABEL = "QASystemOnMedicalKG data/medical.json，本地开发测试导入，请勿商用"

COMMON_TOPICS = [
    "感冒", "发热", "咳嗽", "咽炎", "鼻炎", "鼻窦炎", "扁桃体炎", "支气管炎", "肺炎",
    "哮喘", "腹泻", "胃炎", "胃溃疡", "消化不良", "便秘", "痔疮", "高血压", "糖尿病",
    "高脂血症", "冠心病", "贫血", "痛风", "湿疹", "荨麻疹", "皮炎", "过敏", "结膜炎",
    "中耳炎", "牙周炎", "龋齿", "头痛", "偏头痛", "失眠", "焦虑", "抑郁", "尿路感染",
    "膀胱炎", "肾结石", "颈椎病", "腰椎间盘突出", "关节炎", "骨质疏松", "甲亢", "甲减",
    "脂肪肝", "乙肝", "贫血", "水痘", "麻疹", "手足口病", "百日咳", "流感", "新生儿",
    "儿童", "妊娠", "孕妇"
]

HIGH_PRIORITY_EXACT = {
    "感冒", "流行性感冒", "急性上呼吸道感染", "病毒性感冒", "小儿感冒",
    "高血压", "糖尿病", "慢性胃炎", "急性胃炎", "支气管哮喘", "肺炎",
    "过敏性鼻炎", "急性咽炎", "慢性咽炎", "急性扁桃体炎", "湿疹",
    "荨麻疹", "便秘", "腹泻", "痔疮", "失眠", "偏头痛", "痛风",
}


def compact_text(value, max_len=240):
    if isinstance(value, list):
        value = "、".join(str(item) for item in value if item)
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def compact_list(value, max_items=8, max_text_len=None, drop_ellipsis=False):
    if not value:
        return []
    if isinstance(value, str):
        parts = re.split(r"[、,，;；\s]+", value)
    else:
        parts = value

    result = []
    seen = set()
    for item in parts:
        text = str(item or "").strip()
        if drop_ellipsis and ("..." in text or "…" in text):
            continue
        if max_text_len and len(text) > max_text_len:
            continue
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= max_items:
            break
    return result


def read_medicalkg_records(url):
    response = requests.get(url, timeout=90)
    response.raise_for_status()

    records = []
    for line in response.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("name"):
            records.append(item)
    return records


def disease_score(item):
    name = item.get("name", "")
    text = " ".join([
        name,
        compact_text(item.get("category"), 120),
        compact_text(item.get("symptom"), 160),
        compact_text(item.get("desc"), 260),
    ])

    score = 0
    if name in HIGH_PRIORITY_EXACT:
        score += 80
    for topic in COMMON_TOPICS:
        if topic in text:
            score += 8
    if item.get("symptom"):
        score += 15
    if item.get("desc"):
        score += 12
    if item.get("prevent"):
        score += 8
    if item.get("recommand_drug") or item.get("common_drug"):
        score += 5
    if any(word in name for word in ["罕见", "综合征", "肿瘤", "癌"]):
        score -= 6
    return score


def build_disease_record(item):
    symptoms = compact_list(item.get("symptom"), max_items=10, max_text_len=12, drop_ellipsis=True) or ["待补充"]
    checks = compact_list(item.get("check"), max_items=6)
    departments = compact_list(item.get("cure_department"), max_items=4)
    cure_way = compact_list(item.get("cure_way"), max_items=5)
    drugs = compact_list(item.get("recommand_drug"), max_items=8, max_text_len=24)
    common_drugs = compact_list(item.get("common_drug"), max_items=8, max_text_len=24)
    all_drugs = compact_list(drugs + common_drugs, max_items=10, max_text_len=24)

    care_parts = []
    if item.get("prevent"):
        care_parts.append(f"预防与日常管理：{compact_text(item.get('prevent'), 180)}")
    if checks:
        care_parts.append(f"常见检查：{'、'.join(checks)}")
    if cure_way:
        care_parts.append(f"常见处理方向：{'、'.join(cure_way)}")
    if departments:
        care_parts.append(f"建议咨询科室：{'、'.join(departments)}")

    if all_drugs:
        medicine_notice = (
            f"原知识图谱关联药品：{'、'.join(all_drugs)}。"
            "该关联仅用于知识检索，不代表处方建议；具体用药、剂量、禁忌和疗程需由医生或药师确认。"
        )
    else:
        medicine_notice = "是否需要用药、如何用药需结合诊断、药品说明书和医生或药师指导。"

    warning = (
        "如症状持续加重，或出现高热不退、胸痛、呼吸困难、意识改变、明显脱水、剧烈腹痛、"
        "严重过敏反应等危险信号，应及时就医；儿童、孕产妇、老人及慢病患者需更谨慎。"
    )
    if "传染" in compact_text(item.get("get_way"), 80):
        warning += " 疑似传染性疾病时应注意隔离防护，并按当地医疗机构建议处理。"

    return {
        "name": item.get("name", ""),
        "category": " / ".join(compact_list(item.get("category"), max_items=4)) or "公开医疗知识图谱",
        "symptoms": symptoms,
        "description": compact_text(item.get("desc"), 320),
        "care_advice": "；".join(care_parts) or "建议补充病程、严重程度、既往病史等信息，并在需要时咨询医生。",
        "medicine_notice": medicine_notice,
        "warning": warning,
        "source": SOURCE_LABEL,
        "source_url": SOURCE_URL,
    }


def collect_drug_links(records):
    links = defaultdict(list)
    for item in records:
        disease_name = item.get("name", "")
        if not disease_name:
            continue
        drugs = compact_list(item.get("recommand_drug"), max_items=20)
        drugs += compact_list(item.get("common_drug"), max_items=20)
        for drug in compact_list(drugs, max_items=30, max_text_len=24):
            links[drug].append(disease_name)
    return links


def build_medicine_records(drug_links, max_items):
    counts = Counter({drug: len(set(diseases)) for drug, diseases in drug_links.items()})
    records = []
    for drug, _count in counts.most_common(max_items):
        diseases = sorted(set(drug_links[drug]))[:12]
        records.append({
            "name": drug,
            "type": "知识图谱关联药品",
            "usage": f"在公开医疗知识图谱中与以下疾病或症状场景有关联：{'、'.join(diseases)}。",
            "notice": "该条目来自疾病-药品关联数据，不等同于正式药品说明书或处方建议；请结合医生、药师指导使用。",
            "contraindication": "禁忌、相互作用、孕产妇/儿童/老人/肝肾功能异常等特殊人群限制，请以药品说明书和专业指导为准。",
            "side_effect": "不良反应需参考正式药品说明书；用药后如出现严重不适或过敏反应，应及时就医。",
            "source": SOURCE_LABEL,
            "source_url": SOURCE_URL,
        })
    return records


def merge_by_name(existing, incoming, refresh_source=False):
    incoming_by_name = {
        item.get("name", ""): item
        for item in incoming
        if item.get("name")
    }
    existing_names = {item.get("name", "") for item in existing if item.get("name")}
    merged = []
    updated = []

    for item in existing:
        name = item.get("name", "")
        if refresh_source and name in incoming_by_name and item.get("source") == SOURCE_LABEL:
            updated_item = incoming_by_name.pop(name)
            merged.append(updated_item)
            updated.append(updated_item)
        else:
            merged.append(item)

    additions = [
        item
        for name, item in incoming_by_name.items()
        if name not in existing_names
    ]
    return merged + additions, additions, updated


def main():
    parser = argparse.ArgumentParser(description="Import a Chinese MedicalKG sample into the local RAG knowledge store.")
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--max-diseases", type=int, default=1500)
    parser.add_argument("--max-medicines", type=int, default=800)
    parser.add_argument("--refresh-source", action="store_true", help="Refresh records previously imported from this source.")
    args = parser.parse_args()

    raw_records = read_medicalkg_records(args.source_url)
    ranked = sorted(enumerate(raw_records), key=lambda pair: (disease_score(pair[1]), -pair[0]), reverse=True)
    selected_diseases = [build_disease_record(item) for _index, item in ranked[:args.max_diseases]]
    selected_medicines = build_medicine_records(collect_drug_links(raw_records), args.max_medicines)

    current_diseases = get_all_diseases()
    current_medicines = get_all_medicines()

    merged_diseases, added_diseases, updated_diseases = merge_by_name(
        current_diseases,
        selected_diseases,
        refresh_source=args.refresh_source,
    )
    merged_medicines, added_medicines, updated_medicines = merge_by_name(
        current_medicines,
        selected_medicines,
        refresh_source=args.refresh_source,
    )

    save_json(DISEASE_FILE, merged_diseases)
    save_json(MEDICINE_FILE, merged_medicines)

    print(json.dumps({
        "source_records": len(raw_records),
        "selected_diseases": len(selected_diseases),
        "selected_medicines": len(selected_medicines),
        "added_diseases": len(added_diseases),
        "added_medicines": len(added_medicines),
        "updated_diseases": len(updated_diseases),
        "updated_medicines": len(updated_medicines),
        "total_diseases": len(merged_diseases),
        "total_medicines": len(merged_medicines),
        "source_url": args.source_url,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
