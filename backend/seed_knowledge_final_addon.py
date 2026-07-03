from pathlib import Path
from dotenv import load_dotenv

from db import (
    ensure_normalized_schema,
    get_connection as mysql_connection,
    upsert_disease_record,
    upsert_medicine_record,
    upsert_warning_rule,
)


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


def get_connection():
    ensure_normalized_schema()
    return mysql_connection()


DISEASES = [
    {
        "name": "结膜炎",
        "category": "眼部问题",
        "symptoms": "眼红、眼痒、流泪、分泌物增多、异物感",
        "description": "结膜炎常表现为眼红、流泪、异物感和分泌物增多，可与感染、过敏或刺激因素有关。",
        "care_advice": "注意眼部卫生，避免揉眼，不共用毛巾，减少隐形眼镜佩戴，保持手部清洁。",
        "medicine_notice": "不建议自行使用含抗生素或激素的眼药水，眼部用药应确认适应情况。",
        "warning": "如果出现明显眼痛、视力下降、畏光严重、外伤后眼红或症状迅速加重，应及时就医。"
    },
    {
        "name": "过敏性结膜炎",
        "category": "眼部问题",
        "symptoms": "眼痒、流泪、眼红、眼睑肿胀、打喷嚏",
        "description": "过敏性结膜炎多与花粉、尘螨、动物毛屑等过敏原有关，常伴明显眼痒和流泪。",
        "care_advice": "减少接触过敏原，避免揉眼，可冷敷缓解不适，注意室内清洁。",
        "medicine_notice": "抗过敏滴眼液或口服抗过敏药应按说明书使用，儿童和孕妇应咨询医生或药师。",
        "warning": "如果出现视力下降、眼痛明显、眼部分泌物大量增多或症状持续不缓解，应及时就医。"
    },
    {
        "name": "麦粒肿",
        "category": "眼部问题",
        "symptoms": "眼睑红肿、眼皮疼痛、局部硬结、压痛、流泪",
        "description": "麦粒肿常表现为眼睑局部红肿疼痛，多与眼睑腺体炎症有关。",
        "care_advice": "保持眼部清洁，避免挤压患处，减少熬夜和揉眼，可适当热敷。",
        "medicine_notice": "不建议自行挤压或随意使用眼药，反复发作或肿痛明显应咨询医生。",
        "warning": "如果红肿范围扩大、发热、视力受影响或疼痛明显加重，应及时就医。"
    },
    {
        "name": "鼻出血",
        "category": "耳鼻喉问题",
        "symptoms": "流鼻血、鼻腔干燥、鼻痒、鼻塞、鼻部不适",
        "description": "鼻出血可与鼻腔干燥、抠鼻、外伤、鼻炎或血压等因素有关，多数轻微鼻出血可先局部处理观察。",
        "care_advice": "保持坐位并身体微微前倾，避免仰头，轻压鼻翼，保持鼻腔湿润，避免用力擤鼻。",
        "medicine_notice": "不建议自行向鼻腔塞入不洁物品或随意使用刺激性药物。",
        "warning": "如果出血量大、反复出血、伴头晕乏力、外伤后出血或正在使用抗凝药，应及时就医。"
    },
    {
        "name": "慢性咽炎",
        "category": "耳鼻喉问题",
        "symptoms": "咽干、咽痒、咽部异物感、清嗓、轻微咳嗽",
        "description": "慢性咽炎常表现为咽部干痒、异物感、反复清嗓，可与用嗓过度、烟酒刺激、反流或环境因素有关。",
        "care_advice": "减少烟酒和辛辣刺激，避免长时间大声说话，保持室内湿度，规律作息。",
        "medicine_notice": "含片或咽喉局部用药只能缓解不适，长期反复症状应查明诱因。",
        "warning": "如果出现吞咽困难、声音嘶哑长期不缓解、咽部明显疼痛或发热，应及时就医。"
    },
    {
        "name": "牙龈炎",
        "category": "口腔问题",
        "symptoms": "牙龈出血、牙龈红肿、口臭、刷牙出血、牙龈疼痛",
        "description": "牙龈炎常与口腔清洁不足、牙菌斑和牙结石有关，表现为牙龈红肿和刷牙出血。",
        "care_advice": "坚持正确刷牙，使用牙线或牙间刷，减少甜食和刺激性食物，定期口腔检查。",
        "medicine_notice": "漱口液只能辅助改善口腔环境，不能替代洁牙和口腔治疗。",
        "warning": "如果牙龈反复出血、牙齿松动、面部肿胀或疼痛明显，应及时看口腔科。"
    },
    {
        "name": "智齿冠周炎",
        "category": "口腔问题",
        "symptoms": "智齿疼痛、牙龈肿痛、张口困难、吞咽痛、口臭",
        "description": "智齿冠周炎常见于智齿周围牙龈发炎，可能出现局部肿痛、张口困难和吞咽不适。",
        "care_advice": "保持口腔清洁，避免用患侧咀嚼，减少辛辣刺激食物。",
        "medicine_notice": "止痛药只能临时缓解，不建议自行使用抗生素，反复发作应看口腔科。",
        "warning": "如果出现面部肿胀、发热、张口困难明显或吞咽呼吸受影响，应及时就医。"
    },
    {
        "name": "口臭",
        "category": "口腔问题",
        "symptoms": "口腔异味、口干、舌苔厚、牙龈出血、反酸",
        "description": "口臭可与口腔卫生、牙龈问题、舌苔、胃酸反流或饮食习惯有关。",
        "care_advice": "注意刷牙和清洁舌苔，使用牙线，保持饮水，减少烟酒和重口味食物。",
        "medicine_notice": "不建议长期依赖口气清新产品掩盖症状，应根据原因处理。",
        "warning": "如果伴牙龈出血、牙痛、反酸明显、体重下降或长期不缓解，应及时就医。"
    },
    {
        "name": "痔疮",
        "category": "肛肠问题",
        "symptoms": "便后出血、肛门疼痛、肛门瘙痒、肛门坠胀、排便困难",
        "description": "痔疮常与久坐、便秘、排便用力等有关，可出现便后鲜血、肛门不适和疼痛。",
        "care_advice": "增加膳食纤维和饮水，避免久坐久蹲，保持排便通畅，注意肛周清洁。",
        "medicine_notice": "外用痔疮药只能缓解部分症状，反复出血不应长期自行处理。",
        "warning": "如果便血量多、黑便、疼痛剧烈、肿物不能回纳或反复出血，应及时就医。"
    },
    {
        "name": "肛裂",
        "category": "肛肠问题",
        "symptoms": "排便疼痛、便后滴血、肛门疼痛、大便干结、肛门痉挛",
        "description": "肛裂常与大便干硬、排便用力有关，表现为排便时或排便后肛门疼痛和少量鲜血。",
        "care_advice": "保持大便软化，增加饮水和膳食纤维，避免用力排便，注意肛周清洁。",
        "medicine_notice": "不建议长期自行使用通便药或外用药，反复发作应咨询医生。",
        "warning": "如果出血明显、疼痛严重、反复不愈或伴发热肿胀，应及时就医。"
    },
    {
        "name": "尿路感染样症状",
        "category": "泌尿系统",
        "symptoms": "尿频、尿急、尿痛、下腹痛、尿液浑浊",
        "description": "尿路感染样症状常表现为尿频、尿急、尿痛或下腹不适，需要结合发热、腰痛和尿液变化判断。",
        "care_advice": "适量饮水，避免憋尿，注意个人卫生，观察是否有发热、腰痛或血尿。",
        "medicine_notice": "不建议自行使用抗生素，症状明显、反复或特殊人群应就医检查。",
        "warning": "如果出现发热、腰痛、血尿、孕妇尿痛或症状持续加重，应及时就医。"
    },
    {
        "name": "阴道炎样不适",
        "category": "女性健康",
        "symptoms": "外阴瘙痒、白带异常、异味、灼热感、尿痛",
        "description": "阴道炎样不适可表现为外阴瘙痒、白带异常、异味或灼热感，原因可能不同，需要结合检查判断。",
        "care_advice": "注意局部清洁干燥，避免过度清洗和刺激性洗液，穿透气内衣，避免自行反复用药。",
        "medicine_notice": "不建议自行使用抗生素或阴道用药，孕妇、反复发作或症状明显者应咨询医生。",
        "warning": "如果伴下腹痛、发热、出血、孕期不适或症状反复，应及时就医。"
    },
    {
        "name": "毛囊炎",
        "category": "皮肤问题",
        "symptoms": "红色丘疹、脓疱、局部疼痛、皮肤红肿、瘙痒",
        "description": "毛囊炎常表现为毛囊周围红色丘疹或小脓疱，可与出汗、摩擦、皮肤清洁和感染有关。",
        "care_advice": "保持皮肤清洁干爽，避免挤压和搔抓，减少摩擦和闷热刺激。",
        "medicine_notice": "外用抗菌药应按说明书或医生建议使用，不建议大面积长期自行用药。",
        "warning": "如果红肿迅速扩大、疼痛明显、发热、反复化脓或位于面部危险区域，应及时就医。"
    },
    {
        "name": "脂溢性皮炎",
        "category": "皮肤问题",
        "symptoms": "头皮屑、头皮痒、皮肤油腻、红斑、脱屑",
        "description": "脂溢性皮炎常见于头皮、面部等皮脂分泌较多部位，表现为瘙痒、红斑和脱屑。",
        "care_advice": "保持规律作息，避免过度清洁或刺激性洗护用品，减少熬夜和油腻饮食。",
        "medicine_notice": "去屑洗剂或外用药应按说明书使用，面部或长期反复皮损应咨询医生。",
        "warning": "如果皮损明显扩大、渗液、感染或长期不缓解，应及时就医。"
    },
    {
        "name": "皮肤干燥",
        "category": "皮肤问题",
        "symptoms": "皮肤干、脱屑、瘙痒、紧绷、皲裂",
        "description": "皮肤干燥常与天气干燥、热水洗澡、清洁过度或皮肤屏障受损有关。",
        "care_advice": "减少热水烫洗，使用温和清洁产品，洗后及时保湿，避免搔抓。",
        "medicine_notice": "保湿类产品通常可辅助缓解，若伴明显红斑、渗出或瘙痒严重应咨询医生。",
        "warning": "如果出现皮肤裂口感染、渗液、疼痛明显或长期瘙痒不缓解，应及时就医。"
    },
    {
        "name": "晒伤",
        "category": "皮肤损伤",
        "symptoms": "皮肤发红、灼热疼痛、脱皮、水疱、晒后刺痛",
        "description": "晒伤常因紫外线暴露过多造成，轻者皮肤发红灼热，重者可出现水疱和明显疼痛。",
        "care_advice": "尽快避免继续日晒，可冷敷降温，补充水分，避免挑破水疱。",
        "medicine_notice": "外用舒缓或保湿产品应按说明书使用，大面积水疱或严重疼痛不适合自行处理。",
        "warning": "如果晒伤面积大、出现大水疱、发热寒战、头晕或儿童严重晒伤，应及时就医。"
    },
    {
        "name": "手癣",
        "category": "皮肤问题",
        "symptoms": "手掌脱皮、瘙痒、水疱、皮肤增厚、裂口",
        "description": "手癣多与真菌感染有关，可表现为手部瘙痒、脱皮、水疱或皮肤增厚。",
        "care_advice": "保持手部干燥，避免共用毛巾，减少接触刺激性清洁剂，注意是否伴足癣。",
        "medicine_notice": "抗真菌外用药应按说明书坚持使用，不建议症状稍缓解就立即停药。",
        "warning": "如果出现明显破溃、感染、疼痛加重或长期反复不愈，应及时就医。"
    },
    {
        "name": "轻度擦伤",
        "category": "皮肤损伤",
        "symptoms": "皮肤破损、少量出血、局部疼痛、红肿、渗液",
        "description": "轻度擦伤常见于表浅皮肤损伤，多数可通过清洁、消毒和保护伤口处理。",
        "care_advice": "用清洁水冲洗污物，保持伤口清洁干燥，避免反复摩擦和污染。",
        "medicine_notice": "消毒用品应按说明书使用，不要在深部伤口或严重污染伤口上自行乱用药。",
        "warning": "如果伤口较深、污染严重、动物咬伤、持续出血、红肿化脓或破伤风风险不明，应及时就医。"
    },
    {
        "name": "踝关节扭伤",
        "category": "运动损伤",
        "symptoms": "脚踝疼痛、肿胀、活动受限、淤青、走路疼",
        "description": "踝关节扭伤常因运动或走路时崴脚引起，可出现疼痛、肿胀和活动受限。",
        "care_advice": "早期减少活动，抬高患肢，避免继续负重，观察肿胀和疼痛变化。",
        "medicine_notice": "外用止痛药可辅助缓解不适，但不能替代对严重损伤的检查。",
        "warning": "如果无法负重行走、明显畸形、剧烈疼痛、肿胀迅速加重或麻木，应及时就医。"
    },
    {
        "name": "落枕",
        "category": "疼痛问题",
        "symptoms": "颈部疼痛、转头困难、颈肩僵硬、局部酸痛、活动受限",
        "description": "落枕常与睡姿不当、受凉或颈部肌肉紧张有关，表现为颈部疼痛和活动受限。",
        "care_advice": "避免强行扭动颈部，可适当热敷，减少低头时间，保持舒适姿势。",
        "medicine_notice": "外用止痛药或口服止痛药应按说明书使用，反复发作应注意颈椎问题。",
        "warning": "如果伴手臂麻木无力、外伤、发热、头痛剧烈或疼痛持续加重，应及时就医。"
    },
    {
        "name": "颈肩酸痛",
        "category": "疼痛问题",
        "symptoms": "颈部酸痛、肩膀酸痛、肌肉僵硬、低头后加重、头晕",
        "description": "颈肩酸痛常与久坐、低头、姿势不良、肌肉劳损有关。",
        "care_advice": "减少长时间低头，规律活动颈肩，调整坐姿和屏幕高度，避免受凉。",
        "medicine_notice": "外用止痛药只能缓解部分不适，长期反复或伴神经症状应咨询医生。",
        "warning": "如果伴手麻无力、走路不稳、头晕明显、胸痛或外伤后疼痛，应及时就医。"
    },
    {
        "name": "轻度焦虑紧张",
        "category": "心理与睡眠",
        "symptoms": "紧张、心慌、睡不着、注意力下降、坐立不安",
        "description": "轻度焦虑紧张可与学习压力、生活事件、睡眠不足有关，常表现为紧张、心慌或入睡困难。",
        "care_advice": "尝试规律作息、适度运动、深呼吸放松、减少咖啡因摄入，并与可信任的人沟通。",
        "medicine_notice": "不建议自行使用镇静催眠类药物或网络购买精神类药物。",
        "warning": "如果焦虑持续加重、严重影响生活、伴明显抑郁或自伤想法，应尽快寻求专业帮助。"
    },
    {
        "name": "手足口病样皮疹",
        "category": "儿童常见问题",
        "symptoms": "手足皮疹、口腔疱疹、发热、食欲下降、咽痛",
        "description": "手足口病样表现常见于儿童，可出现手足皮疹、口腔疱疹和发热，需要注意传染和病情变化。",
        "care_advice": "注意隔离和手卫生，保持口腔清洁，选择清淡软食，观察体温和精神状态。",
        "medicine_notice": "不建议自行使用抗生素或不明抗病毒药，儿童用药应咨询医生。",
        "warning": "如果儿童高热不退、精神差、频繁呕吐、抽搐、呼吸异常或嗜睡，应及时就医。"
    },
    {
        "name": "水痘样皮疹",
        "category": "感染相关",
        "symptoms": "水疱、皮疹、发热、瘙痒、结痂",
        "description": "水痘样皮疹可表现为成批出现的水疱、瘙痒和发热，具有传染性，需要与其他皮疹区分。",
        "care_advice": "避免搔抓，保持皮肤清洁，减少与他人密切接触，注意休息和观察体温。",
        "medicine_notice": "不建议自行使用抗生素或激素类药物，儿童、孕妇或免疫功能低下者应咨询医生。",
        "warning": "如果高热不退、皮疹感染、呼吸困难、孕妇感染或精神状态差，应及时就医。"
    },
    {
        "name": "口唇疱疹",
        "category": "皮肤与口腔问题",
        "symptoms": "嘴唇水疱、刺痛、灼热、结痂、局部疼痛",
        "description": "口唇疱疹常表现为嘴唇周围小水疱、刺痛或灼热感，可能反复出现。",
        "care_advice": "避免抠破水疱，注意手卫生，发作期间避免共用餐具和亲密接触。",
        "medicine_notice": "外用或口服抗病毒药应在医生或药师指导下使用，不建议随意长期使用。",
        "warning": "如果疱疹范围扩大、眼部受累、反复严重发作或免疫功能低下者发作，应及时就医。"
    },
    {
        "name": "过敏反应",
        "category": "过敏相关",
        "symptoms": "皮疹、瘙痒、面唇肿胀、胸闷、呼吸困难",
        "description": "过敏反应可表现为皮疹、瘙痒、风团，也可能出现面唇肿胀、胸闷和呼吸困难等严重表现。",
        "care_advice": "尽量停止接触可疑过敏原，记录食物、药物或环境诱因，避免搔抓。",
        "medicine_notice": "抗过敏药可缓解轻度症状，但严重过敏不能只依赖口服药。",
        "warning": "如果出现呼吸困难、喉咙发紧、面唇肿胀、头晕或意识异常，应立即就医。"
    }
]


MEDICINES = [
    {
        "name": "氯雷他定",
        "type": "抗过敏类",
        "usage_info": "常用于缓解过敏性鼻炎、荨麻疹、皮肤瘙痒等过敏相关症状。",
        "notice": "应按说明书使用，部分人可能出现嗜睡或口干，驾驶和学习考试前应注意个体反应。",
        "contraindication": "对本品过敏者禁用，孕妇、哺乳期女性、儿童和肝肾功能异常者应咨询医生或药师。",
        "side_effect": "可能出现嗜睡、口干、头痛、乏力等。"
    },
    {
        "name": "蒙脱石散",
        "type": "止泻吸附类",
        "usage_info": "常用于腹泻时辅助减少大便次数和改善稀便情况。",
        "notice": "腹泻时补液更重要，使用时应注意与其他药物间隔，避免影响其他药物吸收。",
        "contraindication": "对本品过敏者禁用，严重便秘、持续腹痛或便血者不宜自行使用。",
        "side_effect": "可能出现便秘、腹胀等。"
    },
    {
        "name": "铝碳酸镁",
        "type": "抗酸护胃类",
        "usage_info": "常用于缓解反酸、烧心、胃部灼热等胃酸相关不适。",
        "notice": "长期反复胃痛、黑便、呕血或体重下降不应自行长期服药，应及时就医。",
        "contraindication": "对本品过敏者禁用，严重肾功能异常者应咨询医生。",
        "side_effect": "可能出现便秘、腹泻、胃部不适等。"
    },
    {
        "name": "布洛芬",
        "type": "退热止痛类",
        "usage_info": "常用于缓解发热、头痛、牙痛、痛经、肌肉酸痛等症状。",
        "notice": "应按说明书使用，避免与其他非甾体抗炎药重复使用，胃病、肾功能异常者应谨慎。",
        "contraindication": "对布洛芬或阿司匹林类药物过敏者禁用，活动性消化道溃疡或出血者应避免使用。",
        "side_effect": "可能出现胃部不适、恶心、皮疹、胃肠道出血风险增加等。"
    },
    {
        "name": "玻璃酸钠滴眼液",
        "type": "眼部润滑类",
        "usage_info": "常用于缓解眼干、眼涩、用眼疲劳等眼表干燥不适。",
        "notice": "使用前注意产品是否适合隐形眼镜人群，开封后应按说明书保存和使用。",
        "contraindication": "对成分过敏者禁用。",
        "side_effect": "可能出现短暂视物模糊、眼部刺激或过敏。"
    },
    {
        "name": "硝酸咪康唑乳膏",
        "type": "抗真菌外用类",
        "usage_info": "常用于足癣、手癣、体癣等真菌相关皮肤问题。",
        "notice": "应按说明书坚持使用，避免接触眼睛和口腔，症状反复应咨询医生。",
        "contraindication": "对咪唑类药物或本品成分过敏者禁用。",
        "side_effect": "可能出现局部刺激、烧灼感、红斑或瘙痒。"
    },
    {
        "name": "克霉唑乳膏",
        "type": "抗真菌外用类",
        "usage_info": "常用于手癣、足癣、体癣等浅表真菌感染相关皮肤问题。",
        "notice": "应按说明书使用，保持患处干燥，不建议症状稍缓解就立即停用。",
        "contraindication": "对本品过敏者禁用。",
        "side_effect": "可能出现局部刺激、瘙痒、红斑或脱皮。"
    },
    {
        "name": "双氯芬酸二乙胺乳胶剂",
        "type": "外用止痛抗炎类",
        "usage_info": "常用于缓解肌肉酸痛、关节痛、扭伤等局部疼痛不适。",
        "notice": "仅供外用，不要用于破损皮肤，避免大面积长期使用。",
        "contraindication": "对双氯芬酸、阿司匹林或其他非甾体抗炎药过敏者应避免使用。",
        "side_effect": "可能出现局部皮肤刺激、瘙痒、红斑等。"
    },
    {
        "name": "氢化可的松乳膏",
        "type": "外用抗炎类",
        "usage_info": "常用于部分轻度皮炎、湿疹、瘙痒等炎症性皮肤问题的短期缓解。",
        "notice": "属于激素类外用药，不建议长期、大面积或面部自行使用，儿童使用应谨慎。",
        "contraindication": "皮肤感染未控制、对本品过敏者应避免使用。",
        "side_effect": "长期不当使用可能导致皮肤变薄、色素改变、毛细血管扩张等。"
    },
    {
        "name": "马来酸氯苯那敏",
        "type": "抗过敏类",
        "usage_info": "常用于缓解过敏性鼻炎、皮肤瘙痒、荨麻疹等过敏症状。",
        "notice": "较容易引起嗜睡，驾驶、操作机械或上课考试前应谨慎。",
        "contraindication": "对本品过敏者禁用，青光眼、前列腺问题、孕妇和老人应咨询医生。",
        "side_effect": "可能出现嗜睡、口干、头晕、乏力等。"
    },
    {
        "name": "维生素B2",
        "type": "维生素类",
        "usage_info": "常用于维生素B2缺乏相关口角炎、口腔黏膜不适等辅助补充。",
        "notice": "不能替代对反复口腔溃疡或长期口腔问题的病因检查。",
        "contraindication": "对本品过敏者禁用。",
        "side_effect": "可能出现尿液颜色变黄，一般为常见现象，少数人可有胃肠不适。"
    },
    {
        "name": "复方氯己定含漱液",
        "type": "口腔局部护理类",
        "usage_info": "常用于口腔炎症、牙龈问题时辅助清洁和抑菌。",
        "notice": "应按说明书含漱，不建议长期频繁使用，不能替代口腔科治疗。",
        "contraindication": "对氯己定或相关成分过敏者禁用。",
        "side_effect": "可能出现口腔刺激、味觉改变、牙面着色等。"
    },
    {
        "name": "生理盐水冲洗液",
        "type": "清洁冲洗类",
        "usage_info": "常用于鼻腔、伤口周围或皮肤表面的温和清洁。",
        "notice": "应使用正规无菌产品，深部伤口、严重污染伤口或眼部问题应按医生建议处理。",
        "contraindication": "对产品成分或包装材料过敏者慎用。",
        "side_effect": "一般较少，可能出现短暂刺激感。"
    },
    {
        "name": "苯扎氯铵贴",
        "type": "伤口护理类",
        "usage_info": "常用于小面积表浅擦伤、割伤后的临时保护和局部护理。",
        "notice": "使用前应清洁伤口，深部伤口、动物咬伤、严重污染伤口不适合只贴创可贴。",
        "contraindication": "对胶布、苯扎氯铵或相关材料过敏者应避免使用。",
        "side_effect": "可能出现局部过敏、发红、闷湿或刺激。"
    },
    {
        "name": "聚维酮碘溶液",
        "type": "皮肤消毒类",
        "usage_info": "常用于小面积皮肤破损、擦伤等局部消毒。",
        "notice": "仅供外用，避免进入眼睛和口腔，大面积或深部伤口应就医处理。",
        "contraindication": "对碘制剂过敏者禁用，甲状腺疾病患者大面积使用应咨询医生。",
        "side_effect": "可能出现局部刺激、过敏或皮肤着色。"
    },
    {
        "name": "氧化锌软膏",
        "type": "皮肤保护类",
        "usage_info": "常用于轻度皮肤刺激、潮湿摩擦相关皮肤不适的保护和辅助护理。",
        "notice": "仅供外用，避免接触眼睛和口腔，明显感染或渗液皮损应咨询医生。",
        "contraindication": "对本品成分过敏者禁用。",
        "side_effect": "可能出现局部刺激、干燥或过敏。"
    },
    {
        "name": "尿素乳膏",
        "type": "皮肤保湿软化类",
        "usage_info": "常用于皮肤干燥、粗糙、皲裂等情况的辅助护理。",
        "notice": "避免用于破溃、渗液或感染皮肤，使用后如刺激明显应停止使用。",
        "contraindication": "对本品过敏者禁用。",
        "side_effect": "可能出现局部刺痛、烧灼感或过敏。"
    },
    {
        "name": "洛索洛芬钠贴剂",
        "type": "外用止痛类",
        "usage_info": "常用于肌肉痛、关节痛、扭伤等局部疼痛的短期缓解。",
        "notice": "外用贴剂不应贴在破损皮肤上，不建议大面积或长期连续使用。",
        "contraindication": "对非甾体抗炎药过敏者、贴剂成分过敏者应避免使用。",
        "side_effect": "可能出现局部皮疹、瘙痒、发红或刺激。"
    },
    {
        "name": "地氯雷他定",
        "type": "抗过敏类",
        "usage_info": "常用于缓解过敏性鼻炎、荨麻疹等过敏相关症状。",
        "notice": "应按说明书使用，症状严重或反复过敏应查找诱因。",
        "contraindication": "对本品过敏者禁用，孕妇、哺乳期女性、儿童和肝肾功能异常者应咨询医生。",
        "side_effect": "可能出现口干、乏力、头痛、嗜睡等。"
    },
    {
        "name": "复方薄荷脑软膏",
        "type": "外用清凉止痒类",
        "usage_info": "常用于蚊虫叮咬、轻度皮肤瘙痒等局部不适的短期缓解。",
        "notice": "仅供外用，避免接触眼睛、口腔和破损皮肤，儿童使用应注意说明书限制。",
        "contraindication": "对薄荷脑或相关成分过敏者禁用。",
        "side_effect": "可能出现局部刺激、烧灼感或过敏。"
    }
]


WARNING_RULES = [
    {"keyword": "剧烈胸痛", "risk_level": "critical", "advice": "剧烈胸痛可能提示心肺急症，应立即寻求急救。"},
    {"keyword": "胸痛伴出汗", "risk_level": "critical", "advice": "胸痛伴出汗、恶心或呼吸困难需要高度警惕，应立即就医。"},
    {"keyword": "呼吸困难加重", "risk_level": "critical", "advice": "呼吸困难加重可能危及生命，应立即就医。"},
    {"keyword": "持续腹痛", "risk_level": "high", "advice": "持续腹痛可能与急腹症或其他严重情况有关，应及时就医。"},
    {"keyword": "剧烈呕吐", "risk_level": "high", "advice": "剧烈呕吐可能导致脱水和电解质紊乱，应及时就医。"},
    {"keyword": "小便明显减少", "risk_level": "high", "advice": "小便明显减少可能提示脱水或肾脏相关风险，应及时就医。"},
    {"keyword": "高热伴皮疹", "risk_level": "high", "advice": "高热伴皮疹需要警惕感染或过敏等情况，应及时就医。"},
    {"keyword": "皮肤大片紫斑", "risk_level": "high", "advice": "皮肤大片紫斑可能与出血或感染风险有关，应及时就医。"},
    {"keyword": "眼痛视力下降", "risk_level": "high", "advice": "眼痛伴视力下降属于眼科警示症状，应及时就医。"},
    {"keyword": "严重头部外伤", "risk_level": "critical", "advice": "严重头部外伤可能存在颅脑损伤风险，应立即就医。"},
    {"keyword": "动物咬伤出血", "risk_level": "high", "advice": "动物咬伤出血存在感染和狂犬病暴露风险，应及时就医处理。"},
    {"keyword": "烫伤面积大", "risk_level": "high", "advice": "大面积烫伤或特殊部位烫伤不适合自行处理，应及时就医。"}
]


def upsert_diseases(cursor):
    for item in DISEASES:
        upsert_disease_record(cursor, item)


def upsert_medicines(cursor):
    for item in MEDICINES:
        upsert_medicine_record(cursor, item)


def upsert_warning_rules(cursor):
    for item in WARNING_RULES:
        upsert_warning_rule(cursor, item)


def count_table(cursor, table_name):
    cursor.execute(f"SELECT COUNT(*) AS total FROM {table_name}")
    row = cursor.fetchone()
    return row["total"]


def main():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            upsert_diseases(cursor)
            upsert_medicines(cursor)
            upsert_warning_rules(cursor)

            disease_count = count_table(cursor, "diseases")
            medicine_count = count_table(cursor, "medicines")
            warning_count = count_table(cursor, "warning_rules")

    print("[完成] 第二批知识库扩展写入成功")
    print(f"[统计] diseases 当前总数：{disease_count}")
    print(f"[统计] medicines 当前总数：{medicine_count}")
    print(f"[统计] warning_rules 当前总数：{warning_count}")
    print("[提示] 接下来请访问 /api/rag/init 重建 RAG 向量索引")


if __name__ == "__main__":
    main()
