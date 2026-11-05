"""EmotionGap — Streamlit web study with optional Gemini API."""
import os
import random
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from engine import CASES, EMOTIONS, get_demo_result, parse_model_json, analyze_row

st.set_page_config(page_title="EmotionGap | 감정 인식 실험", page_icon="🧠", layout="wide")
st.markdown("""<style>
.block-container {max-width:1050px; padding-top:2rem}
[data-testid="stMetric"] {background:#f1f5f9; padding:14px; border-radius:14px; color:#152238}
@media (prefers-color-scheme: dark) {[data-testid="stMetric"] {background:#243042;color:#fff}}
</style>""", unsafe_allow_html=True)


def secret(name):
    try:
        return st.secrets.get(name, "") or os.getenv(name, "")
    except Exception:
        return os.getenv(name, "")

API_KEY = secret("GEMINI_API_KEY")
DEFAULT_MODEL = secret("GEMINI_MODEL") or "gemini-2.5-flash-lite"

@st.cache_data(show_spinner=False, ttl=3600)
def model_classify(text, context, api_key, model):
    from google import genai
    client = genai.Client(api_key=api_key)
    prompt = f'''당신은 한국어 문장 감정 분류 연구를 위한 평가기입니다.
직접 심리 진단하지 말고 이 문장의 화자에게서 추론 가능한 감정을 분류하세요.
감정 레이블은 다음 중 정확히 하나: {', '.join(EMOTIONS)}.
단정할 근거가 부족하거나 감정이 복합적이면 '복합/불확실'을 선택할 수 있습니다.
설명은 한국어로 1문장, 80자 이내. 마크다운 없이 JSON 객체만 출력:
{{"emotion":"감정 레이블", "reason":"설명"}}
문장: {text!r}
{('문맥: '+context) if context else '문맥 정보 없음'}'''
    response = client.models.generate_content(
        model=model, contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 0},
    )
    if not response.text:
        raise ValueError("AI가 비어 있는 응답을 반환했습니다.")
    return parse_model_json(response.text)


def classify(case, with_context, live, model):
    if live:
        return model_classify(case['text'], case['context'] if with_context else '', API_KEY, model)
    return get_demo_result(case['id'], with_context)


def initialize():
    defaults = {"index": 0, "phase": "before", "records": [], "selection": random.sample(CASES, len(CASES)),
                "human_before": None, "human_after": None, "ai_before": None, "ai_after": None,
                "run_mode": "demo", "model": DEFAULT_MODEL, "started_at": datetime.now(timezone.utc).isoformat()}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def next_case():
    st.session_state.index += 1
    st.session_state.phase = "before"
    for key in ("human_before", "human_after", "ai_before", "ai_after"):
        st.session_state[key] = None

initialize()
st.title("🧠 EmotionGap")
st.caption("AI는 문장의 표면을 넘어 말하는 사람의 감정을 얼마나 잘 읽을까?")

with st.sidebar:
    st.subheader("⚙️ 실험 설정")
    live_possible = bool(API_KEY)
    mode_options = ["데모(사전 작성 예측)"] + (["실제 Gemini AI"] if live_possible else [])
    current = "실제 Gemini AI" if st.session_state.run_mode == 'live' and live_possible else mode_options[0]
    mode = st.selectbox("분석 방식", mode_options, index=mode_options.index(current), disabled=st.session_state.index > 0 or bool(st.session_state.records) or st.session_state.phase != 'before')
    st.session_state.run_mode = 'live' if mode == "실제 Gemini AI" else 'demo'
    if live_possible:
        st.success("Gemini API 키가 설정되어 있습니다.")
    else:
        st.info("현재 데모 모드입니다. 실제 AI 분석을 사용하려면 Streamlit Secrets에 GEMINI_API_KEY를 추가하세요.")
    model = st.text_input("Gemini 모델 ID", value=st.session_state.model, disabled=st.session_state.index > 0 or bool(st.session_state.records) or st.session_state.phase != 'before')
    st.session_state.model = model.strip() or DEFAULT_MODEL
    st.divider()
    st.markdown("**연구상 주의사항**")
    st.caption("가상 문장을 사용합니다. 결과는 심리 진단이 아니며, 제시된 참고 감정은 절대적 정답이 아닌 연구용 기준 레이블입니다. 무료 API는 한도·정책이 달라질 수 있습니다.")
    if st.button("🔄 새 실험 시작", use_container_width=True):
        for k in ["index", "phase", "records", "selection", "human_before", "human_after", "ai_before", "ai_after", "started_at"]:
            st.session_state.pop(k, None)
        initialize()
        st.rerun()

tab1, tab2, tab3 = st.tabs(["🔬 감정 실험", "📊 결과 분석", "📚 연구 안내"])
with tab1:
    total = len(st.session_state.selection)
    idx = st.session_state.index
    if idx >= total:
        st.success("모든 실험이 완료됐습니다. '결과 분석' 탭에서 결과를 확인하세요.")
    else:
        case = st.session_state.selection[idx]
        st.progress(idx / total, text=f"실험 {idx+1}/{total} · {case['type']} 유형")
        st.subheader("메시지를 읽고 화자의 감정을 판단해 보세요")
        st.info('“' + case['text'] + '”')
        if st.session_state.phase == 'before':
            st.write("**1단계 · 문맥 없이 판단**")
            with st.form(f"form_before_{idx}"):
                h = st.radio("문장을 쓴 사람의 감정은?", ["선택하세요"] + EMOTIONS, index=0, key=f"before_{idx}")
                confidence = st.slider("내 판단 확신도 (%)", 0, 100, 50, 5, key=f"confidence_{idx}")
                submit = st.form_submit_button("첫 판단 확정 → 문맥 보기", type="primary")
            if submit:
                if h == "선택하세요":
                    st.warning("감정을 먼저 선택해 주세요.")
                else:
                    st.session_state.human_before = h
                    st.session_state.first_confidence = confidence
                    st.session_state.phase = 'after'
                    st.rerun()
        elif st.session_state.phase == 'after':
            st.write(f"첫 판단: **{st.session_state.human_before}**")
            st.write("**2단계 · 문맥 추가 후 다시 판단**")
            st.success('상황: ' + case['context'])
            with st.form(f"form_after_{idx}"):
                h2 = st.radio("문맥을 읽은 뒤 감정은?", ["선택하세요"] + EMOTIONS, index=0, key=f"after_{idx}")
                submit2 = st.form_submit_button("최종 판단 확정 → AI와 비교", type="primary")
            if submit2:
                if h2 == "선택하세요":
                    st.warning("감정을 먼저 선택해 주세요.")
                else:
                    with st.spinner("감정 예측 결과를 계산하는 중입니다…"):
                        try:
                            a1 = classify(case, False, st.session_state.run_mode == 'live', st.session_state.model)
                            a2 = classify(case, True, st.session_state.run_mode == 'live', st.session_state.model)
                        except Exception as e:
                            st.error("AI 요청에 실패했습니다. 비공개 키 설정, 모델 ID, 무료 할당량을 확인하세요. 재시도할 수 있습니다.")
                            st.caption(f"오류 유형: {type(e).__name__}. 데모로 바꾸려면 사이드바에서 새 실험을 시작하세요.")
                        else:
                            st.session_state.human_after = h2
                            st.session_state.ai_before = a1
                            st.session_state.ai_after = a2
                            st.session_state.phase = 'result'
                            st.rerun()
        else:
            st.write("**3단계 · 인간과 AI의 판단 비교**")
            a1 = st.session_state.ai_before
            a2 = st.session_state.ai_after
            if st.session_state.run_mode != 'live':
                st.warning("이 결과는 사전 작성된 데모 예측입니다. 실제 AI 성능을 나타내지 않습니다.")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 문맥 없이")
                st.write("나의 판단: **" + st.session_state.human_before + "**")
                st.write("AI 판단: **" + a1['emotion'] + "**")
                st.caption(a1['reason'])
            with c2:
                st.markdown("#### 문맥 추가 후")
                st.write("나의 판단: **" + st.session_state.human_after + "**")
                st.write("AI 판단: **" + a2['emotion'] + "**")
                st.caption(a2['reason'])
            st.divider()
            st.write("연구용 참고 레이블: **" + case['reference'] + "**")
            st.caption("이 레이블은 개발자가 설정한 임시 기준이며, 실제 감정의 객관적 정답으로 검증된 것은 아닙니다.")
            if st.button("결과 저장하고 다음 문제", type="primary", use_container_width=True):
                st.session_state.records.append({
                    "case_id": case['id'], "category": case['type'], "message": case['text'],
                    "context": case['context'], "reference": case['reference'],
                    "human_before": st.session_state.human_before, "human_after": st.session_state.human_after,
                    "ai_before": a1['emotion'], "ai_after": a2['emotion'],
                    "ai_reason_before": a1['reason'], "ai_reason_after": a2['reason'],
                    "confidence_before": st.session_state.first_confidence,
                    "mode": st.session_state.run_mode, "model": st.session_state.model if st.session_state.run_mode == 'live' else 'DEMO',
                    "recorded_at": datetime.now(timezone.utc).isoformat()
                })
                next_case()
                st.rerun()

with tab2:
    rows = st.session_state.records
    st.subheader("실험 결과 대시보드")
    if not rows:
        st.info("실험을 1회 이상 완료하면 분석 결과가 나타납니다.")
    else:
        df = pd.DataFrame([analyze_row(r) for r in rows])
        n = len(df)
        a, b, c, d = st.columns(4)
        a.metric("완료한 문제", f"{n}개")
        b.metric("AI 기준 일치율 · 문맥 전", f"{df.ai_match_before.mean():.0%}")
        c.metric("AI 기준 일치율 · 문맥 후", f"{df.ai_match_after.mean():.0%}")
        d.metric("AI-인간 일치율 · 문맥 후", f"{df.agreement_after.mean():.0%}")
        st.caption("일치율은 이 앱의 임시 참고 레이블 또는 참가자 선택과의 일치 비율입니다. 실제 감정 인식 정확도로 단정할 수 없습니다.")
        chart_df = pd.DataFrame({
            '조건': ['문맥 없음', '문맥 있음'],
            'AI-기준 일치': [df.ai_match_before.mean(), df.ai_match_after.mean()],
            '인간-기준 일치': [df.human_match_before.mean(), df.human_match_after.mean()],
            'AI-인간 일치': [df.agreement_before.mean(), df.agreement_after.mean()]
        }).set_index('조건')
        st.bar_chart(chart_df, y_label='비율 (0~1)')
        st.write(f"AI 예측이 문맥에 따라 변경된 문항: **{int(df.ai_changed.sum())}/{n}**")
        st.write(f"사람의 판단이 문맥에 따라 변경된 문항: **{int(df.human_changed.sum())}/{n}**")
        st.dataframe(df[['case_id','category','human_before','human_after','ai_before','ai_after','reference','ai_match_after']], use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button('📥 연구 기록 CSV 다운로드', csv, 'emotiongap_results.csv', mime='text/csv', use_container_width=True)
        st.caption('기록은 현재 브라우저 세션에만 유지되며 서버에 영구 저장하지 않습니다. 새로고침·세션 만료 시 소실될 수 있으므로 CSV를 다운로드하세요.')

with tab3:
    st.markdown('''### 연구 질문
**문맥 정보 제공 전후 AI의 감정 분류 결과는 어떻게 달라지는가?**

### 연구 설계
- 모든 참가자가 같은 문항을 **문맥 없음 → 문맥 있음** 순서로 평가합니다. 따라서 순서 효과가 있을 수 있습니다.
- AI는 동일한 모델과 프롬프트 형식을 사용해 문맥만 바꾸어 두 번 분류합니다.
- 비교 지표: AI와 연구용 기준의 일치, 인간과 AI의 일치, 문맥 전후 응답 변경률.
- '참고 감정'은 개발자가 만든 **임시 레이블**입니다. 여러 사람의 독립 평가로 검증 전에는 객관적인 정답이 아닙니다.
- 데모 모드의 결과는 실제 AI의 예측이 아니므로 연구 성능 분석에서 제외해야 합니다.

### 한계와 윤리
이 프로그램은 가상의 메시지를 분석하며 진단이나 상담 서비스를 제공하지 않습니다. 실제 개인의 민감한 대화 내용은 입력하거나 전송하지 마세요. 이 실험만으로 AI가 실제 사람의 내면 감정을 이해한다고 결론 낼 수 없습니다. 외부 API 무료 등급의 데이터 이용 정책을 확인하세요.

### 추가 연구 방향
여러 참가자의 레이블을 익명으로 수집해 평가자 간 일치도를 구하고, 문장 종류별 성능과 모델 간 차이를 비교할 수 있습니다.''')
