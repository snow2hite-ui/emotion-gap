"""EmotionGap experimental logic: pure functions, separately testable."""
import json
import re
from dataclasses import dataclass

EMOTIONS = ["기쁨", "슬픔", "분노", "불안", "놀람", "중립", "복합/불확실"]

CASES = [
    {"id": 1, "type": "반어", "text": "와, 정말 잘한다.", "context": "친구가 약속을 세 번 연속 어기자 상대방이 이 말을 했다.", "reference": "분노", "note": "반어적 표현의 감정 해석"},
    {"id": 2, "type": "기본", "text": "드디어 합격했어! 너무 기뻐.", "context": "오랫동안 준비하던 시험의 합격 문자를 받았다.", "reference": "기쁨", "note": "명시적 긍정 감정"},
    {"id": 3, "type": "문맥", "text": "괜찮아. 신경 쓰지 마.", "context": "상대가 큰 실수를 한 뒤 눈물을 참으며 말하고 있다.", "reference": "슬픔", "note": "문맥이 없으면 감정 단정이 어려움"},
    {"id": 4, "type": "복합", "text": "합격해서 좋은데 친구가 떨어져서 마음이 무겁다.", "context": "두 사람은 같은 시험을 함께 준비했다.", "reference": "복합/불확실", "note": "긍정과 부정 감정의 공존"},
    {"id": 5, "type": "불안", "text": "내일 발표인데 자꾸 실수할까 봐 걱정돼.", "context": "처음으로 많은 사람 앞에서 발표한다.", "reference": "불안", "note": "명시적 불안 표현"},
    {"id": 6, "type": "반어", "text": "정말 고맙다, 덕분에 숙제 다 날아갔네.", "context": "친구가 파일을 덮어써 숙제 내용을 잃었다.", "reference": "분노", "note": "긍정 단어와 부정적 상황의 충돌"},
    {"id": 7, "type": "문맥", "text": "그래, 그렇게 하자.", "context": "친구들이 점심 메뉴를 정했고, 말한 사람도 동의했다.", "reference": "중립", "note": "중립적 의사 표시"},
    {"id": 8, "type": "놀람", "text": "어? 네가 여기 올 줄은 몰랐어!", "context": "오랜만에 만난 친구가 갑자기 나타났다.", "reference": "놀람", "note": "놀람의 직접적 표현"},
    {"id": 9, "type": "슬픔", "text": "오랫동안 키운 강아지가 떠나서 너무 허전해.", "context": "반려동물을 잃은 다음 날 쓴 메시지다.", "reference": "슬픔", "note": "상실 관련 슬픔"},
    {"id": 10, "type": "반어", "text": "오늘도 완벽한 하루네.", "context": "버스를 놓치고 지갑도 잃어버린 직후 작성했다.", "reference": "분노", "note": "표면적으로 긍정적인 표현"},
    {"id": 11, "type": "문맥", "text": "어떻게 이런 일이 생겼지?", "context": "예상하지 못한 선물 상자를 열고 말했다.", "reference": "놀람", "note": "상황에 따른 다의성"},
    {"id": 12, "type": "복합", "text": "이사 간다니 기대되지만 친구들이 보고 싶을 것 같아.", "context": "가족과 함께 새로운 도시로 이사할 예정이다.", "reference": "복합/불확실", "note": "기대와 슬픔의 공존"},
]

# Predetermined demonstrations; NOT actual model outputs.
DEMO = {
    1: ("기쁨", "분노"), 2: ("기쁨", "기쁨"), 3: ("중립", "슬픔"),
    4: ("기쁨", "복합/불확실"), 5: ("불안", "불안"), 6: ("기쁨", "분노"),
    7: ("중립", "중립"), 8: ("놀람", "놀람"), 9: ("슬픔", "슬픔"),
    10: ("기쁨", "분노"), 11: ("불안", "놀람"), 12: ("기쁨", "복합/불확실")
}

def normalize_emotion(value):
    if value not in EMOTIONS:
        raise ValueError("지원하지 않는 감정 레이블입니다.")
    return value

def parse_model_json(raw):
    """Validate model response; do not silently fabricate a result."""
    clean = raw.strip()
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean).strip()
    obj = json.loads(clean)
    if not isinstance(obj, dict):
        raise ValueError("AI 결과가 JSON 객체가 아닙니다.")
    label = normalize_emotion(obj.get("emotion"))
    reason = obj.get("reason", "")
    if not isinstance(reason, str):
        raise ValueError("AI 설명 형식이 잘못되었습니다.")
    return {"emotion": label, "reason": reason[:240]}

def get_demo_result(case_id, with_context):
    no_context, contextual = DEMO[case_id]
    return {"emotion": contextual if with_context else no_context,
            "reason": "사전에 작성한 시연용 예측입니다. 실제 AI 모델 출력이 아닙니다."}

def analyze_row(row):
    before = row["ai_before"]
    after = row["ai_after"]
    ref = row["reference"]
    return {
        **row,
        "ai_changed": before != after,
        "human_changed": row["human_before"] != row["human_after"],
        "ai_match_before": before == ref,
        "ai_match_after": after == ref,
        "human_match_before": row["human_before"] == ref,
        "human_match_after": row["human_after"] == ref,
        "agreement_before": before == row["human_before"],
        "agreement_after": after == row["human_after"],
    }

def summarize(rows):
    if not rows:
        return {"n": 0, "ai_before": 0.0, "ai_after": 0.0, "human_before": 0.0, "human_after": 0.0, "agreement_before": 0.0, "agreement_after": 0.0}
    analyzed = [analyze_row(r) for r in rows]
    n = len(analyzed)
    keys = ["ai_match_before", "ai_match_after", "human_match_before", "human_match_after", "agreement_before", "agreement_after"]
    return {"n": n, **{k.replace("_match", ""): sum(bool(r[k]) for r in analyzed) / n for k in keys}}
