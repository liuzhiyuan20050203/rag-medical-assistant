import json
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SOURCE_FILE = DATA_DIR / "knowledge_quality_sources.json"

load_dotenv(BASE_DIR / ".env", override=True)


def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "rag_medical"),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


SOURCE_NOTE = (
    "本批知识为项目实训用保守版结构化整理初稿，未直接爬取或复制网页正文；"
    "参考公开权威健康科普、药品说明书信息和常见临床安全边界进行人工归纳，"
    "不包含具体诊断结论和用药剂量，正式展示前建议由小组人工复核。"
)


REFERENCE_SOURCES = [
    {
        "name": "国家药品监督管理局药品数据查询",
        "url": "https://www.nmpa.gov.cn/datasearch/home-index.html",
        "usage": "药品名称、适应症、禁忌、不良反应等说明书信息的复核入口。",
    },
    {
        "name": "国家卫生健康委员会健康科普",
        "url": "https://www.nhc.gov.cn/",
        "usage": "常见病症、健康提示、就医提醒等内容的参考来源。",
    },
    {
        "name": "中国疾控中心健康科普",
        "url": "https://www.chinacdc.cn/jkkp/",
        "usage": "传染病、呼吸道症状、发热、老年人健康提示等内容的参考来源。",
    },
    {
        "name": "MedlinePlus Medical Encyclopedia",
        "url": "https://medlineplus.gov/encyclopedia.html",
        "usage": "常见症状、居家护理、何时就医等英文权威资料的辅助参考。",
    },
    {
        "name": "MedlinePlus Drug Information",
        "url": "https://medlineplus.gov/druginformation.html",
        "usage": "常见药品用途、注意事项、不良反应等药品信息的辅助参考。",
    },
]


DISEASES = [
    {
        "name": "咳嗽",
        "category": "呼吸系统",
        "symptoms": "咳嗽、干咳、咳痰、黄痰、咽痒、胸闷、气短、发热、夜间咳嗽",
        "description": "咳嗽是常见呼吸道症状，可与普通感冒、流感样症状、急性支气管炎、过敏、咽喉刺激、胃酸反流等多种情况有关。需要结合持续时间、是否有痰、痰液颜色、是否发热、胸痛、气短和既往慢病史综合判断。",
        "care_advice": "注意休息，多饮温水，避免烟尘、冷空气、油烟和刺激性气味，保持室内通风和适当湿度。若有痰，应观察痰液颜色和量的变化，不建议盲目长期强行止咳。老人或慢性呼吸系统疾病患者应更早关注症状变化。",
        "medicine_notice": "不建议自行使用抗生素、激素或多种复方感冒止咳药。止咳、祛痰、抗过敏类药物应结合症状和说明书短期使用；老人、孕妇、儿童、肝肾功能异常或正在服用多种药物者应先咨询医生或药师。",
        "warning": "如果咳嗽伴呼吸困难、胸痛、咳血、持续高热、口唇发紫、意识异常、明显乏力，或老人症状持续加重，应及时就医。咳嗽超过数周不缓解、反复夜间咳嗽或伴体重下降也建议线下评估。",
    },
    {
        "name": "发热",
        "category": "全身症状",
        "symptoms": "发热、低热、高热、畏寒、寒战、乏力、头痛、肌肉酸痛、出汗",
        "description": "发热是身体对感染、炎症、环境高温或其他疾病的常见反应。需要关注体温变化、持续时间、伴随症状、近期接触史和基础疾病情况。老人有时感染表现不典型，即使体温不特别高也可能需要重视。",
        "care_advice": "注意休息，补充水分，保持环境通风，避免过度捂汗。可记录体温变化和伴随症状。饮食以清淡易消化为主，出现出汗多、口干、尿量减少时要注意补液。",
        "medicine_notice": "退热药应按说明书或医嘱短期使用，避免多种含同类退热成分的感冒药重复服用。老人、儿童、孕妇、肝肾功能异常、胃病或正在服用抗凝药者，用药前应咨询医生或药师。",
        "warning": "持续高热、发热伴意识异常、抽搐、呼吸困难、胸痛、皮疹、颈部僵硬、严重脱水，或老人精神明显变差，应及时就医。婴幼儿、孕妇、免疫功能低下者发热也应更谨慎。",
    },
    {
        "name": "头痛",
        "category": "疼痛问题",
        "symptoms": "头痛、偏头痛、头晕、恶心、畏光、颈部僵硬、视物模糊、睡眠不足",
        "description": "头痛可与睡眠不足、压力、感冒、偏头痛、眼疲劳、血压异常等多种因素有关。需要关注头痛出现速度、部位、程度、持续时间、是否反复发作，以及是否伴随神经系统症状。",
        "care_advice": "轻度头痛可先休息，保证睡眠，减少长时间用眼，避免饮酒和过度疲劳。可记录诱发因素，如熬夜、情绪紧张、饮食、月经周期或血压波动。频繁发作建议线下评估原因。",
        "medicine_notice": "止痛药不建议长期或频繁自行使用，以免掩盖病情或导致药物相关头痛。老人、高血压、胃病、肝肾功能异常或正在服用抗凝药者，应谨慎选择解热镇痛药。",
        "warning": "突发剧烈头痛、头痛伴视物模糊、言语不清、一侧肢体无力、意识异常、颈部僵硬、发热、外伤后头痛，或与以往明显不同的头痛，应及时就医。",
    },
    {
        "name": "头晕",
        "category": "全身症状",
        "symptoms": "头晕、眩晕、站立不稳、恶心、心慌、出汗、乏力、耳鸣、视物旋转",
        "description": "头晕可与睡眠不足、低血糖、低血压、贫血、耳部问题、血压波动、药物影响或心脑血管风险有关。老人出现头晕时尤其要关注跌倒风险和神经系统表现。",
        "care_advice": "出现头晕时应先坐下或躺下，避免独自行走、开车或登高。可补充少量水分，观察是否与饥饿、体位改变、熬夜或用药有关。老人应注意防跌倒，必要时让家属陪同。",
        "medicine_notice": "不建议在原因不明时自行使用止晕药或镇静类药物。若怀疑与降压药、降糖药、安眠药等有关，应咨询医生或药师，不要自行停药或加减剂量。",
        "warning": "头晕伴一侧肢体无力、口角歪斜、言语不清、胸痛、晕厥、剧烈头痛、持续呕吐、走路明显不稳，或老人反复跌倒，应及时就医。",
    },
    {
        "name": "腹泻",
        "category": "消化系统",
        "symptoms": "腹泻、拉肚子、大便次数增多、水样便、腹痛、恶心、呕吐、发热、口干、尿少",
        "description": "腹泻表现为大便次数增多或粪便稀薄，可与饮食不洁、胃肠感染、消化不良、药物影响或肠道功能紊乱有关。需要关注持续时间、是否发热、是否便血、是否脱水。",
        "care_advice": "注意补充水分和电解质，饮食清淡，避免油腻、生冷、酒精和刺激性食物。观察大便颜色、次数和尿量。老人、儿童腹泻更容易脱水，应更早关注精神状态和尿量。",
        "medicine_notice": "不建议自行使用抗生素。止泻药、吸附剂或益生菌应按说明书使用，并注意与其他药物间隔。若出现发热、便血或剧烈腹痛，不宜单纯依赖止泻药。",
        "warning": "腹泻伴严重脱水、持续高热、便血或黑便、剧烈腹痛、频繁呕吐、尿量明显减少，或老人儿童精神差，应及时就医。",
    },
    {
        "name": "胃痛",
        "category": "消化系统",
        "symptoms": "胃痛、上腹痛、反酸、烧心、腹胀、恶心、嗳气、食欲不振、黑便",
        "description": "胃痛常表现为上腹部不适、隐痛、灼痛或胀痛，可与饮食不规律、胃酸刺激、胃炎、胃食管反流、药物刺激等有关。需要结合疼痛部位、与进食关系、持续时间和危险信号判断。",
        "care_advice": "规律饮食，少量多餐，避免暴饮暴食、空腹饮酒、辛辣油腻和过冷过热食物。记录疼痛与进食、情绪、用药之间的关系。反复胃痛或夜间痛不宜长期拖延。",
        "medicine_notice": "胃药应按症状和说明书合理使用，不建议长期自行服用抑酸药或止痛药。老人、正在服用阿司匹林/抗凝药/止痛药者，出现胃痛应关注消化道出血风险。",
        "warning": "如果出现剧烈腹痛、呕血、黑便、体重明显下降、吞咽困难、持续呕吐、胸痛样不适或疼痛持续加重，应及时就医。",
    },
    {
        "name": "便秘",
        "category": "消化系统",
        "symptoms": "便秘、大便干结、排便困难、腹胀、排便次数减少、肛门疼痛、便后不尽感",
        "description": "便秘常与饮水不足、膳食纤维摄入少、活动减少、排便习惯改变、药物影响或肠道功能减弱有关。老人更容易因活动少、饮水少和多药同用出现便秘。",
        "care_advice": "增加饮水和膳食纤维，适量活动，建立规律排便习惯，避免长时间忍便和用力过猛。可观察是否与近期饮食、活动减少或新用药有关。",
        "medicine_notice": "通便药不建议长期依赖。乳果糖、开塞露等应按说明书短期合理使用；老人、孕妇、腹痛原因不明或长期便秘者应咨询医生。",
        "warning": "便秘伴剧烈腹痛、呕吐、腹胀明显、便血、黑便、体重下降，或突然出现长期排便习惯改变，应及时就医。",
    },
    {
        "name": "失眠",
        "category": "睡眠问题",
        "symptoms": "入睡困难、早醒、多梦、睡眠浅、白天困倦、注意力下降、焦虑紧张",
        "description": "失眠可与压力、作息紊乱、睡前使用电子设备、咖啡因摄入、疼痛、夜尿、焦虑情绪或慢性疾病有关。老人睡眠变浅较常见，但长期睡眠差会影响白天功能。",
        "care_advice": "保持规律作息，减少午后咖啡浓茶，睡前避免长时间看手机，营造安静舒适睡眠环境。白天适度活动，避免长期卧床。记录失眠持续时间和诱因。",
        "medicine_notice": "不建议自行长期使用安眠药或镇静类药物，老人尤其要注意跌倒、嗜睡和记忆影响风险。若已在使用相关药物，不要自行突然停药或加量。",
        "warning": "如果失眠持续数周影响生活，伴明显焦虑抑郁、胸闷心悸、夜间憋醒、严重打鼾或自伤想法，应及时寻求医生帮助。",
    },
    {
        "name": "心悸",
        "category": "心血管相关",
        "symptoms": "心悸、心慌、胸闷、气短、出汗、头晕、乏力、心跳不齐、焦虑紧张",
        "description": "心悸是自觉心跳快、心跳重或心跳不规律的感觉，可与情绪紧张、咖啡因、睡眠不足、发热、贫血、甲状腺问题、药物影响或心律失常有关。老人和有心血管病史者需要更谨慎。",
        "care_advice": "发作时先停止活动，坐下休息，记录持续时间、心率、诱因和伴随症状。减少浓茶咖啡、酒精和熬夜。若反复发作，建议线下检查心电图等。",
        "medicine_notice": "不建议自行服用抗心律失常药、降压药或镇静药。若怀疑与正在服用的药物有关，应咨询医生或药师，不要自行停药。",
        "warning": "心悸伴胸痛、呼吸困难、晕厥、持续头晕、大汗、口唇发紫，或老人有冠心病、心衰等病史时，应及时就医。",
    },
    {
        "name": "胸闷",
        "category": "心血管相关",
        "symptoms": "胸闷、胸痛、气短、呼吸不畅、心慌、出汗、乏力、活动后加重",
        "description": "胸闷可与心脏、肺部、胃食管反流、焦虑紧张或环境因素有关。老人、高血压、糖尿病、冠心病患者出现胸闷时，需要优先排除心肺急症。",
        "care_advice": "出现胸闷时应停止活动，保持安静，避免独自外出或剧烈运动。记录是否与活动、情绪、进食、体位有关，以及是否伴胸痛、气短、出汗。",
        "medicine_notice": "不建议自行服用心脏药、降压药或镇静药来处理胸闷。已有心血管病用药者应按医嘱使用，不要自行加减。",
        "warning": "胸闷伴胸痛、呼吸困难、大汗、恶心、放射至左臂/下颌/背部、晕厥，或老人活动后胸闷加重，应立即就医或寻求急救。",
    },
    {
        "name": "湿疹",
        "category": "皮肤问题",
        "symptoms": "湿疹、皮肤瘙痒、红斑、丘疹、渗出、脱屑、皮肤干燥、反复发作",
        "description": "湿疹是一类常见炎症性皮肤问题，常表现为瘙痒、红斑、丘疹、脱屑或渗出，可能与皮肤屏障受损、过敏体质、环境刺激、清洁过度等有关。",
        "care_advice": "避免搔抓和热水烫洗，减少香精、强清洁剂、羊毛等刺激，保持皮肤适度保湿。发作期记录可能诱因，如食物、洗护用品、潮湿闷热或接触物。",
        "medicine_notice": "外用激素、抗感染或止痒药应根据皮损情况合理使用，不建议面部、大面积或长期自行使用激素类药膏。儿童、孕妇和反复发作者应咨询医生。",
        "warning": "如果皮肤红肿热痛、渗液化脓、发热、范围迅速扩大，或婴幼儿/老人皮损严重，应及时就医。",
    },
    {
        "name": "皮肤瘙痒",
        "category": "皮肤问题",
        "symptoms": "皮肤瘙痒、干燥、红疹、风团、脱屑、抓痕、夜间瘙痒、全身瘙痒",
        "description": "皮肤瘙痒可由皮肤干燥、过敏、湿疹、荨麻疹、蚊虫叮咬、药物反应或全身性疾病引起。老人常因皮肤干燥、洗澡过勤或基础疾病出现瘙痒。",
        "care_advice": "避免搔抓、热水烫洗和刺激性洗护用品，洗后及时保湿，穿宽松透气衣物。观察是否有新药、新食物、新洗护用品或环境变化。",
        "medicine_notice": "抗过敏药或外用止痒药只能缓解部分症状，不能替代病因判断。老人服用抗过敏药要注意嗜睡、口干、跌倒风险；长期或全身瘙痒应查明原因。",
        "warning": "瘙痒伴呼吸困难、面唇肿胀、大面积皮疹、皮肤紫斑、发热、黄疸，或全身瘙痒长期不缓解，应及时就医。",
    },
]


MEDICINES = [
    {
        "name": "布洛芬片",
        "type": "解热镇痛抗炎类",
        "usage_info": "常用于缓解轻至中度疼痛，如头痛、牙痛、关节痛、肌肉痛、痛经等，也可用于发热相关症状。具体使用应以药品说明书或医嘱为准。",
        "notice": "应按说明书短期使用，不建议超量、长期或与其他非甾体抗炎药、复方感冒药中的同类成分重复使用。老人、有胃病、肾功能异常、高血压、心血管疾病或正在服用抗凝药者应谨慎。",
        "contraindication": "对布洛芬、阿司匹林或其他非甾体抗炎药过敏者不宜使用；活动性消化道溃疡或出血、严重肝肾功能异常、孕晚期等情况不宜自行使用。",
        "side_effect": "可能出现胃部不适、恶心、皮疹、头晕等反应，少数情况下可能增加消化道出血、过敏反应、哮喘加重或肾功能损害风险。出现明显不适应停用并就医。",
    },
    {
        "name": "对乙酰氨基酚",
        "type": "解热镇痛类",
        "usage_info": "常用于缓解发热和轻至中度疼痛，如头痛、咽痛、牙痛、肌肉酸痛等。具体使用应以说明书或医嘱为准。",
        "notice": "应避免与其他含对乙酰氨基酚成分的复方感冒药重复使用，以免超量。饮酒、肝病、长期营养不良或正在使用影响肝功能药物者应谨慎。",
        "contraindication": "对本品过敏者禁用，严重肝功能不全者不宜自行使用。儿童、孕妇、老人和肝肾功能异常者使用前应咨询医生或药师。",
        "side_effect": "一般按说明书短期使用较常见不良反应较少，但过量可能导致严重肝损伤。少数人可出现皮疹、恶心、过敏反应等。",
    },
    {
        "name": "阿莫西林胶囊",
        "type": "青霉素类抗菌药",
        "usage_info": "属于处方抗菌药，常用于医生判断为敏感细菌感染相关情况时。是否需要使用应由医生结合感染部位、病情和过敏史判断。",
        "notice": "不建议因感冒、咳嗽、咽痛等自行使用抗生素。使用前需要确认青霉素过敏史，并按医嘱完成疗程。腹泻、皮疹等异常反应应及时咨询医生。",
        "contraindication": "对青霉素类药物或阿莫西林过敏者禁用。有严重药物过敏史、哮喘或多种药物过敏者应特别谨慎。",
        "side_effect": "可能出现恶心、腹泻、皮疹、瘙痒等反应，少数情况下可能出现严重过敏反应。若出现呼吸困难、面唇肿胀、全身皮疹等应立即就医。",
    },
    {
        "name": "氯雷他定",
        "type": "抗过敏类",
        "usage_info": "常用于缓解过敏性鼻炎、荨麻疹、皮肤瘙痒等过敏相关症状。具体使用应以说明书或医嘱为准。",
        "notice": "多数情况下嗜睡较少，但个体反应不同，驾驶、操作机械或老人使用时仍需观察。症状反复或严重过敏时应查找诱因，不宜长期自行依赖。",
        "contraindication": "对本品过敏者禁用。孕妇、哺乳期女性、儿童、老人以及肝肾功能异常者使用前应咨询医生或药师。",
        "side_effect": "可能出现口干、乏力、头痛、嗜睡或胃肠不适，少数人可出现过敏反应。",
    },
    {
        "name": "蒙脱石散",
        "type": "止泻吸附类",
        "usage_info": "常用于腹泻时辅助减少大便次数、改善稀便情况。腹泻处理仍应重视补液和观察脱水风险。",
        "notice": "使用时应注意与其他药物间隔，以免影响其他药物吸收。若腹泻伴发热、便血、剧烈腹痛或明显脱水，不应只依赖止泻药。",
        "contraindication": "对本品过敏者禁用。严重便秘、肠梗阻可疑、持续腹痛或便血者不宜自行使用。",
        "side_effect": "可能出现便秘、腹胀等。若症状不缓解或出现脱水表现，应及时就医。",
    },
    {
        "name": "奥美拉唑",
        "type": "抑酸类",
        "usage_info": "常用于胃酸相关不适、反酸、烧心等情况的抑酸治疗，具体适应症和疗程应以说明书或医嘱为准。",
        "notice": "不建议长期自行服用来掩盖反复胃痛、黑便、呕血、吞咽困难或体重下降等问题。与部分药物可能存在相互作用，长期用药需医生评估。",
        "contraindication": "对本品或同类药物过敏者禁用。孕妇、哺乳期女性、肝功能异常或正在服用多种药物者应咨询医生。",
        "side_effect": "可能出现腹胀、恶心、腹泻、便秘、头痛等。长期不当使用可能带来营养吸收、感染风险等问题，应遵医嘱。",
    },
    {
        "name": "法莫替丁",
        "type": "抑酸类",
        "usage_info": "常用于胃酸相关不适、反酸、烧心等情况的短期缓解，具体使用应以说明书或医嘱为准。",
        "notice": "老人、肾功能异常者应谨慎。若出现黑便、呕血、持续胃痛、体重下降或吞咽困难，不应长期自行用药，应及时就医。",
        "contraindication": "对法莫替丁或同类药物过敏者禁用。严重肾功能异常或正在服用多种药物者应咨询医生。",
        "side_effect": "可能出现头痛、头晕、便秘、腹泻、乏力等，少数人可出现皮疹或过敏反应。",
    },
    {
        "name": "乳果糖",
        "type": "通便类",
        "usage_info": "常用于缓解便秘，帮助软化大便、改善排便困难。具体使用应以说明书或医嘱为准。",
        "notice": "通便药不能替代饮水、膳食纤维和规律排便习惯。老人长期便秘、腹痛或排便习惯突然改变时应就医评估。糖尿病患者使用前应咨询医生或药师。",
        "contraindication": "对本品过敏者禁用。疑似肠梗阻、原因不明腹痛、半乳糖血症等情况不宜自行使用。",
        "side_effect": "可能出现腹胀、腹痛、排气增多、腹泻等。若腹泻明显应停止自行使用并咨询医生。",
    },
    {
        "name": "炉甘石洗剂",
        "type": "外用止痒类",
        "usage_info": "常用于轻度皮肤瘙痒、蚊虫叮咬、痱子等皮肤不适的外用缓解。仅适用于部分轻症皮肤问题。",
        "notice": "仅供外用，避免接触眼睛、口腔和破损渗液明显的皮肤。若皮疹范围扩大、渗液化脓或伴发热，不宜继续自行处理。",
        "contraindication": "对本品成分过敏者禁用。大面积破溃、感染明显或严重皮肤病变不宜自行使用。",
        "side_effect": "可能出现局部干燥、刺激、烧灼感或过敏。出现明显红肿、疼痛或皮疹加重应停用并就医。",
    },
    {
        "name": "莫匹罗星软膏",
        "type": "外用抗菌类",
        "usage_info": "常用于医生或药师判断为轻度细菌相关皮肤感染时的局部外用处理，如小范围脓疱、毛囊炎样表现等。",
        "notice": "仅供外用，不建议大面积、长期或反复自行使用。若皮肤问题是真菌、病毒、过敏或湿疹，并不一定适合使用抗菌药膏。",
        "contraindication": "对本品成分过敏者禁用。深部伤口、大面积感染、动物咬伤、严重烫伤或糖尿病足破溃应及时就医。",
        "side_effect": "可能出现局部烧灼感、刺痛、瘙痒、红斑或过敏反应。若红肿扩散、疼痛加重或发热，应及时就医。",
    },
    {
        "name": "他汀类药物",
        "type": "调脂类处方药",
        "usage_info": "他汀类药物常用于医生评估后的血脂管理和心脑血管风险控制，属于需要长期规范管理的处方药类别。具体药品和使用方案应由医生决定。",
        "notice": "不建议自行开始、停用或更换他汀。使用期间应按医嘱复查血脂、肝功能等指标。老人、肝病患者、饮酒较多者或正在服用多种药物者应特别注意相互作用。",
        "contraindication": "活动性肝病、妊娠或哺乳期、对相关药物过敏者通常不适合自行使用。具体禁忌需以具体药品说明书和医嘱为准。",
        "side_effect": "可能出现肌肉酸痛、乏力、肝酶异常、胃肠不适等。若出现明显肌痛、无力、深色尿或黄疸等，应及时就医。",
    },
    {
        "name": "健胃消食片",
        "type": "消化不良辅助用药",
        "usage_info": "常用于饮食积滞、消化不良相关的腹胀、食欲不振等轻度不适。具体使用应以说明书或医嘱为准。",
        "notice": "不能替代对长期胃痛、反酸、黑便、体重下降等问题的检查。糖尿病患者、儿童、孕妇、老人或正在服用多种药物者应先查看说明书并咨询医生或药师。",
        "contraindication": "对本品成分过敏者禁用。严重胃痛、持续呕吐、黑便、呕血或腹痛原因不明者不宜自行使用。",
        "side_effect": "可能出现胃肠不适、过敏等。若症状持续不缓解或加重，应停止自行处理并就医。",
    },
]


WARNING_RULES = [
    {"keyword": "胸痛伴呼吸困难", "risk_level": "critical", "advice": "胸痛伴呼吸困难可能提示心肺急症，应立即就医或寻求急救。"},
    {"keyword": "胸闷伴大汗", "risk_level": "critical", "advice": "胸闷伴大汗、恶心或气短需要警惕心血管急症，应立即就医。"},
    {"keyword": "头痛伴视物模糊", "risk_level": "high", "advice": "头痛伴视物模糊可能涉及神经系统或眼科风险，应及时就医。"},
    {"keyword": "头痛伴颈部僵硬", "risk_level": "high", "advice": "头痛伴颈部僵硬，尤其伴发热时需要及时就医评估。"},
    {"keyword": "皮疹伴呼吸困难", "risk_level": "critical", "advice": "皮疹伴呼吸困难可能提示严重过敏反应，应立即就医。"},
    {"keyword": "老人跌倒后意识异常", "risk_level": "critical", "advice": "老人跌倒后出现意识异常或明显头痛，需警惕头部损伤，应立即就医。"},
    {"keyword": "咳血", "risk_level": "high", "advice": "咳血可能提示呼吸系统或其他严重问题，应及时就医。"},
    {"keyword": "黑便", "risk_level": "high", "advice": "黑便可能提示消化道出血风险，应及时就医。"},
]


def upsert_diseases(cursor):
    sql = """
        INSERT INTO diseases
        (name, category, symptoms, description, care_advice, medicine_notice, warning)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            category = VALUES(category),
            symptoms = VALUES(symptoms),
            description = VALUES(description),
            care_advice = VALUES(care_advice),
            medicine_notice = VALUES(medicine_notice),
            warning = VALUES(warning),
            updated_at = CURRENT_TIMESTAMP
    """
    for item in DISEASES:
        cursor.execute(
            sql,
            (
                item["name"],
                item["category"],
                item["symptoms"],
                item["description"],
                item["care_advice"],
                item["medicine_notice"],
                item["warning"],
            ),
        )


def upsert_medicines(cursor):
    sql = """
        INSERT INTO medicines
        (name, type, usage_info, notice, contraindication, side_effect)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            type = VALUES(type),
            usage_info = VALUES(usage_info),
            notice = VALUES(notice),
            contraindication = VALUES(contraindication),
            side_effect = VALUES(side_effect),
            updated_at = CURRENT_TIMESTAMP
    """
    for item in MEDICINES:
        cursor.execute(
            sql,
            (
                item["name"],
                item["type"],
                item["usage_info"],
                item["notice"],
                item["contraindication"],
                item["side_effect"],
            ),
        )


def upsert_warning_rules(cursor):
    sql = """
        INSERT INTO warning_rules
        (keyword, risk_level, advice)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            risk_level = VALUES(risk_level),
            advice = VALUES(advice)
    """
    for item in WARNING_RULES:
        cursor.execute(sql, (item["keyword"], item["risk_level"], item["advice"]))


def count_table(cursor, table_name):
    cursor.execute(f"SELECT COUNT(*) AS total FROM {table_name}")
    return cursor.fetchone()["total"]


def write_source_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "batch": "knowledge_quality_enrichment_2026_07",
        "review_status": "待小组人工复核",
        "method": "人工整理与结构化归纳；未使用爬虫；未直接复制网页正文；不包含具体诊断结论和剂量。",
        "source_note": SOURCE_NOTE,
        "reference_sources": REFERENCE_SOURCES,
        "enriched_diseases": [item["name"] for item in DISEASES],
        "enriched_medicines": [item["name"] for item in MEDICINES],
        "enriched_warning_rules": [item["keyword"] for item in WARNING_RULES],
    }
    SOURCE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            upsert_diseases(cursor)
            upsert_medicines(cursor)
            upsert_warning_rules(cursor)
            disease_count = count_table(cursor, "diseases")
            medicine_count = count_table(cursor, "medicines")
            warning_count = count_table(cursor, "warning_rules")

    write_source_file()
    print("[完成] 第一批知识库质量增厚导入成功")
    print(f"[更新] 疾病/症状条目：{len(DISEASES)}")
    print(f"[更新] 药品条目：{len(MEDICINES)}")
    print(f"[更新] 危险规则：{len(WARNING_RULES)}")
    print(f"[统计] diseases 当前总数：{disease_count}")
    print(f"[统计] medicines 当前总数：{medicine_count}")
    print(f"[统计] warning_rules 当前总数：{warning_count}")
    print(f"[来源] 已写入：{SOURCE_FILE}")
    print("[提示] 接下来请重建 RAG 向量索引")


if __name__ == "__main__":
    main()
