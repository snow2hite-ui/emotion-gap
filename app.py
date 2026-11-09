"""EmotionGap v2: progressive emotion-perception research app."""
import os
import time
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from study import EMOTIONS, LEVELS, safe_code, identifier, select_cases, summarize, parse_ai
from storage import Store

st.set_page_config(page_title='EmotionGap | 감정의 틈을 탐구하다', page_icon='🧠', layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@600;700;800&family=Noto+Sans+KR:wght@400;500;600;700&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'Noto Sans KR',sans-serif}
[data-testid="stAppViewContainer"] {background:linear-gradient(145deg,#f6f5ff 0%,#f4f9ff 56%,#fcfaff 100%);color:#20263c}
[data-testid="stSidebar"] {background:#f0f0fc}
.block-container {max-width:1100px;padding-top:2rem;padding-bottom:4rem}
.hero {background:linear-gradient(115deg,#322e78,#6455c9 65%,#8879e0);color:white;padding:32px 36px;border-radius:26px;box-shadow:0 16px 40px #493a9c22;margin-bottom:20px}
.hero h1{font-family:Nunito,'Noto Sans KR',sans-serif;letter-spacing:-1px;font-size:2.6rem;color:#fff;margin:0}
.hero p {color:#e8e5ff;line-height:1.7;margin:9px 0 0}
.eyebrow{font-size:0.76rem;letter-spacing:2px;color:#c8c2ff;font-weight:800}
.question {background:#fff;border:1px solid #e7e6f5;border-radius:22px;padding:27px 30px;margin:18px 0;box-shadow:0 10px 28px #3633760d}
.question .message{font-size:1.45rem;font-weight:700;color:#353278;margin:14px 0}
.label-pill{background:#edeaff;padding:7px 12px;border-radius:20px;color:#5147aa;font-size:.85rem;font-weight:700;display:inline-block}
[data-testid="stMetric"] {background:white;border:1px solid #e8e9f5;padding:16px;border-radius:18px;box-shadow:0 5px 20px #3431760c}
[data-testid="stMetricLabel"]{color:#505678}
div.stButton>button[kind="primary"],div.stFormSubmitButton>button[kind="primary"]{background:#6555cf;border:0;border-radius:13px;min-height:46px}
.stTabs [data-baseweb="tab"]{font-weight:700}
@media(max-width:640px){.hero{padding:24px 22px}.hero h1{font-size:2rem}.question{padding:20px}.question .message{font-size:1.15rem}}
</style>''', unsafe_allow_html=True)


def secret(name, default=''):
    try:
        return str(st.secrets.get(name, os.getenv(name, default)) or default)
    except Exception:
        return str(os.getenv(name, default))

API_KEY=secret('GEMINI_API_KEY')
MODEL=secret('GEMINI_MODEL', 'gemini-3.5-flash-lite')
SALT=secret('EMOTIONGAP_HASH_SALT')
STORE=Store(secret('SUPABASE_URL'),secret('SUPABASE_SERVICE_ROLE_KEY'))
if not SALT:
    STORE.enabled=False


def initial():
    return {'participant':None,'run_number':None,'level':None,'cases':[], 'index':0,
            'phase':'before','records':[],'before':None,'after':None,'confidence':50,
            'ai_before':None,'ai_after':None,'saved':False,'mode':'live' if API_KEY else 'demo',
            'run_id':None,'previous':[], 'start_error':None}

if 'study' not in st.session_state:
    st.session_state.study=initial()
s=st.session_state.study


def classify(text, context):
    if s['mode']=='demo':
        words=text+' '+context
        emotion= '복합/불확실' if any(w in words for w in ['하지만','그런데','아쉽','마음이 무거','불확실']) else ('불안' if '걱정' in words or '겁나' in words else ('기쁨' if any(w in words for w in ['기뻐','합격','상']) else '중립'))
        return {'emotion':emotion,'reason':'시연용 단순 규칙 결과입니다. 실제 AI의 예측이 아닙니다.'}
    from google import genai
    client=genai.Client(api_key=API_KEY)
    prompt=f'''한국어 감정 인식 평가 실험이다. 문장의 발화자가 느낄 가능성이 높은 감정을 추론하되 단정하지 말라.
허용 감정: {', '.join(EMOTIONS)}. 반드시 하나만 선택한다.
화자의 실제 감정이 불명확하거나 여러 감정이 뚜렷하게 공존하면 '복합/불확실'을 사용한다.
반어법과 부족한 단서에 주의하라. 설명은 90자 이내의 한국어 1문장.
반드시 JSON 객체만 반환: {{"emotion":"감정","reason":"근거"}}
분석 문장: {text!r}
문맥: {context if context else '제공되지 않음'}'''
    for attempt in range(3):
        try:
            response=client.models.generate_content(model=MODEL,contents=prompt,
                config={'response_mime_type':'application/json','temperature':0})
            if not response.text:
                raise ValueError('빈 AI 응답')
            return parse_ai(response.text)
        except Exception as exc:
            code=str(getattr(exc,'code',''))
            transient=code in ('500','503','504') or type(exc).__name__ in ('ServerError',)
            if not transient or attempt==2:
                raise
            time.sleep(2**attempt)


def start_study(code):
    p=identifier(code, SALT)
    previous=STORE.get_runs(p) if STORE.enabled else []
    number=len(previous)+1
    cases=select_cases(p,number)
    mode='live' if API_KEY else 'demo'
    st.session_state.study={**initial(),'participant':p,'run_number':number,'level':min(number,max(LEVELS)),
       'cases':cases,'previous':previous,'mode':mode,'run_id':str(uuid.uuid4())}


def next_case():
    s['index']+=1
    s['phase']='before'
    for field in ('before','after','ai_before','ai_after'):
        s[field]=None


def save_final():
    if s['saved']:
        return True
    if not STORE.enabled:
        return False
    run={'run_id':s['run_id'],'participant_id':s['participant'], 'run_number':s['run_number'],
         'level':s['level'],'mode':s['mode'],'model':MODEL if s['mode']=='live' else 'DEMO',
         'answers':s['records'],'created_at':datetime.now(timezone.utc).isoformat()}
    STORE.save(run)
    s['saved']=True
    s['previous']=[*s['previous'],run]
    return True


with st.sidebar:
    st.markdown('### 🧠 EmotionGap')
    st.caption('사람과 AI 사이, 감정 해석의 간격을 측정합니다.')
    st.divider()
    st.markdown('**연구 환경**')
    if API_KEY:
        st.success('실제 Gemini AI 사용 가능')
        st.caption(f'모델: {MODEL}')
    else:
        st.warning('API 키 없음 · 시연 모드')
    if STORE.enabled:
        st.success('누적 연구 DB 연결 설정됨')
    else:
        st.warning('누적 저장 미설정 · CSV만 가능')
    st.caption('Supabase 연결 설정과 실제 접속 성공은 별개입니다. 해시 SALT까지 설정해야 장기 저장이 활성화됩니다.')
    st.divider()
    st.markdown('**연구 윤리**')
    st.caption('가상 문항만 사용합니다. 참가자 코드에는 이름·연락처 등을 넣지 마세요. 참고 레이블은 객관적인 정답이 아닙니다.')
    if s['participant'] and st.button('↩ 새 참가자 / 홈으로',use_container_width=True):
        st.session_state.study=initial()
        st.rerun()

st.markdown('''<div class="hero"><div class="eyebrow">EMOTION × CONTEXT × AI</div>
<h1>EmotionGap</h1><p>문장만 읽었을 때와 그 상황을 알게 됐을 때, 우리의 감정 해석은 얼마나 달라질까요?<br>
반복 연구로 난이도를 높이고 AI와 인간의 판단 차이를 살펴보세요.</p></div>''',unsafe_allow_html=True)

if not s['participant']:
    left,right=st.columns([1.45,1],gap='large')
    with left:
        st.subheader('새로운 감정 연구 시작')
        code=st.text_input('나만의 익명 참가자 코드',placeholder='예: skyblue07',max_chars=24,help='다음에도 같은 코드를 입력하면 누적 연구를 확인할 수 있습니다.')
        st.caption('개인정보가 아닌 임의의 영문·숫자 코드 4~24자. 코드는 서버에서 해시로 변환합니다. 코드를 잃어버리면 기록을 다시 조회할 수 없습니다.')
        consent=st.checkbox('가상의 문항에 참여하며, 선택 결과를 익명 연구 통계로 저장하는 데 동의합니다. (선택 참여)')
        if st.button('연구 시작하기',type='primary',use_container_width=True,disabled=not consent):
            try:
                safe_code(code)
                start_study(code)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error('연구 기록 서버에 접속하지 못했습니다. Supabase URL·키·테이블 설정을 확인해 주세요.')
                st.caption(f'오류 유형: {type(e).__name__}')
    with right:
        st.markdown('### 연구의 세 단계')
        for level,(label,count) in LEVELS.items():
            st.markdown(f'**LEVEL {level} · {label}**  \n{count}문항 · 연구를 반복하면 단계가 올라갑니다.')
        st.caption('5단계 이후에는 고급 문항을 조합해 반복합니다. 문항 저장소가 한정되어 있어 장기적으로는 일부 문항이 재등장합니다.')
        if not STORE.enabled:
            st.info('현재는 브라우저 내 기록만 유지됩니다. 여러 연구를 누적하려면 README의 무료 Supabase 설정을 진행해 주세요.')
else:
    lvl=s['level']; label,total=LEVELS[lvl]
    tabs=st.tabs(['🧪 감정 실험','📈 나의 연구 기록','📖 연구 방법과 한계'])
    with tabs[0]:
        st.markdown(f'<span class="label-pill">LEVEL {lvl} · {label} · {s["mode"].upper()}</span>',unsafe_allow_html=True)
        idx=s['index']
        st.progress(min(idx/len(s['cases']),1.0), text=f'{min(idx+1,len(s["cases"]))} / {len(s["cases"])} 문항')
        if idx >= len(s['cases']):
            st.success('이번 연구를 완료했습니다. 결과 기록 탭에서 비교해 보세요.')
            if not s['saved'] and STORE.enabled:
                try:
                    save_final()
                    st.success('연구 결과가 데이터베이스에 누적 저장되었습니다.')
                except Exception as e:
                    st.error(f'저장 실패({type(e).__name__}). 아래에서 저장을 다시 시도할 수 있습니다.')
                    if st.button('연구 결과 다시 저장',type='primary'):
                        try:
                            save_final(); st.rerun()
                        except Exception as retry_exc:
                            st.error(f'저장 재시도 실패: {type(retry_exc).__name__}')
            if not STORE.enabled:
                st.warning('DB가 없으므로 현재 연구 결과만 CSV로 저장할 수 있습니다. 다음 연구와 난이도 누적 기능은 Supabase 연결 후 사용 가능합니다.')
            if s['records']:
                df=pd.DataFrame(s['records'])
                st.download_button('이번 연구 CSV 다운로드',df.to_csv(index=False).encode('utf-8-sig'),
                                   file_name=f'emotiongap_run{s["run_number"]}.csv',mime='text/csv',use_container_width=True)
            if st.button('다음 연구 시작',type='primary',use_container_width=True,disabled=not STORE.enabled or not s['saved']):
                # Do not advance unless the previous study is durably saved.
                if STORE.enabled:
                    s['run_number']+=1
                    s['level']=min(s['run_number'],max(LEVELS))
                    s['cases']=select_cases(s['participant'],s['run_number'])
                    s['index']=0;s['phase']='before';s['records']=[];s['saved']=False
                    s['run_id']=str(uuid.uuid4())
                    for name in ('before','after','ai_before','ai_after'):
                        s[name]=None
                    st.rerun()
                else:
                    st.warning('난이도 누적을 위해 Supabase 연결이 필요합니다.')
        else:
            case=s['cases'][idx]
            st.markdown(f'''<div class="question"><span class="label-pill">{case['type']} 유형 · 문항 {idx+1}</span>
            <div class="message">“{case['text']}”</div><small>이 문장의 화자가 느끼는 감정을 추론해 보세요.</small></div>''',unsafe_allow_html=True)
            if s['phase']=='before':
                st.markdown('#### STEP 01 · 문장만 보고 판단하기')
                with st.form(f'before_{s["run_number"]}_{idx}'):
                    ans=st.radio('어떤 감정이 가장 가깝나요?', ['선택하세요']+EMOTIONS,index=0)
                    conf=st.slider('판단에 대한 확신도',0,100,50,5)
                    pressed=st.form_submit_button('첫 판단 저장하고 문맥 보기',type='primary',use_container_width=True)
                if pressed:
                    if ans=='선택하세요':st.warning('감정을 선택해 주세요.')
                    else:
                        s['before']=ans;s['confidence']=conf;s['phase']='after';st.rerun()
            elif s['phase']=='after':
                st.markdown('#### STEP 02 · 상황을 읽고 다시 판단하기')
                st.info('💬 상황: '+case['context'])
                st.caption('첫 번째 답변: '+s['before'])
                with st.form(f'after_{s["run_number"]}_{idx}'):
                    ans=st.radio('상황을 알게 된 뒤에는 어떻게 해석하나요?', ['선택하세요']+EMOTIONS,index=0)
                    why=st.selectbox('판단이 바뀌거나 유지된 이유', ['선택하지 않음','문맥에서 새로운 단서 발견','반어법 가능성','복합적인 감정','감정이 명확하지 않음','처음 판단을 유지함'])
                    pressed=st.form_submit_button('AI와 결과 비교하기',type='primary',use_container_width=True)
                if pressed:
                    if ans=='선택하세요':st.warning('감정을 선택해 주세요.')
                    else:
                        try:
                            with st.spinner('문맥 유무에 따라 AI를 두 번 분석하고 있어요…'):
                                a=classify(case['text'],'')
                                b=classify(case['text'],case['context'])
                            s['after']=ans;s['why']=why;s['ai_before']=a;s['ai_after']=b;s['phase']='result'
                            st.rerun()
                        except Exception as e:
                            msg=str(e).replace(API_KEY,'[REDACTED]') if API_KEY else str(e)
                            st.error('AI 요청 실패: 오류가 해결된 후 다시 시도할 수 있습니다.')
                            st.caption(f'오류 종류: {type(e).__name__} · {msg[:280]}')
            else:
                st.markdown('#### STEP 03 · 사람과 AI의 해석 비교')
                if s['mode']=='demo':st.warning('데모 결과이며 실제 AI의 성능 자료로 사용할 수 없습니다.')
                a,b=st.columns(2,gap='medium')
                with a:
                    st.markdown('**문맥 없이**')
                    st.metric('나의 감정 판단',s['before'])
                    st.metric('AI 감정 판단',s['ai_before']['emotion'])
                    st.caption(s['ai_before']['reason'])
                with b:
                    st.markdown('**문맥을 읽은 뒤**')
                    st.metric('나의 감정 판단',s['after'])
                    st.metric('AI 감정 판단',s['ai_after']['emotion'])
                    st.caption(s['ai_after']['reason'])
                st.info('연구자 참고 레이블: '+case['reference']+' · '+case['note']+' (정답으로 검증된 값이 아닙니다)')
                if st.button('이 문항의 결과 기록하기',type='primary',use_container_width=True):
                    s['records'].append({'case_id':case['id'],'level':lvl,'type':case['type'],
                        'human_before':s['before'],'human_after':s['after'],
                        'ai_before':s['ai_before']['emotion'],'ai_after':s['ai_after']['emotion'],
                        'reference':case['reference'],'confidence_before':s['confidence'],
                        'reason_selected':s.get('why',''), 'mode':s['mode'], 'model': MODEL if s['mode']=='live' else 'DEMO'})
                    next_case();st.rerun()

    with tabs[1]:
        st.subheader('연구 결과 누적 분석')
        all_runs=list(s['previous'])
        if s['records'] and not s['saved']:
            all_runs.append({'run_number':s['run_number'],'level':lvl,'mode':s['mode'],'model':MODEL if s['mode']=='live' else 'DEMO','answers':s['records']})
        if all_runs:
            summary=[]
            all_records=[]
            for run in all_runs:
                rows=run.get('answers') or []
                stats=summarize(rows)
                summary.append({'연구 회차':run['run_number'],'난이도':run['level'], '실험 모드':run['mode'],
                       '문항 수':stats['count'], 'AI·인간 일치율(문맥 전)':stats['agreement_before'],
                       'AI·인간 일치율(문맥 후)':stats['agreement_after'],
                       'AI 참고레이블 일치율(문맥 후)':stats['ai_reference_after'],
                       'AI 판단 변경률':stats['ai_changes']})
                for item in rows:
                    all_records.append({'회차':run['run_number'],**item})
            statdf=pd.DataFrame(summary)
            displaydf=statdf.copy()
            percent_cols=['AI·인간 일치율(문맥 전)','AI·인간 일치율(문맥 후)','AI 참고레이블 일치율(문맥 후)','AI 판단 변경률']
            for col in percent_cols:
                displaydf[col]=displaydf[col].map(lambda x: f'{x:.0%}' if pd.notna(x) else '-')
            live_df=statdf[statdf['실험 모드']=='live']
            c1,c2,c3=st.columns(3)
            c1.metric('저장/진행한 연구',f'{len(all_runs)}회')
            c2.metric('총 응답 문항',f'{int(statdf["문항 수"].sum())}개')
            c3.metric('실제 AI 연구 회차',f'{len(live_df)}회')
            st.caption('서로 다른 난이도의 회차는 직접적인 모델 성능 비교가 아닙니다. 아래 차트는 실제 AI 회차만 표시합니다.')
            if not live_df.empty:
                chart=live_df.set_index('연구 회차')[['AI·인간 일치율(문맥 전)','AI·인간 일치율(문맥 후)']]
                st.line_chart(chart,y_label='일치율 (0~1)')
            else:
                st.info('실제 Gemini AI 연구를 수행해야 성능 관련 그래프가 나타납니다.')
            st.dataframe(displaydf,use_container_width=True,hide_index=True)
            st.download_button('모든 연구 결과 CSV 다운로드',pd.DataFrame(all_records).to_csv(index=False).encode('utf-8-sig'),
                              file_name='emotiongap_history.csv',mime='text/csv')
            if not STORE.enabled:st.warning('이 데이터는 현재 브라우저 세션에만 있습니다. 서버에 누적 저장되지 않습니다.')
        else:
            st.info('첫 번째 문항을 완료하면 결과가 나타납니다.')
    with tabs[2]:
        st.markdown('''### 왜 이런 실험을 하나요?
이전 AI 심리상담 탐구에서 출발하여, **AI가 공감하기 전 감정을 어떻게 판단하는가**를 직접 시험합니다.

- **독립변수:** 문맥 제공 여부, 실험 난이도(회차별 단계)
- **관찰 결과:** 인간과 AI 감정 일치율, 문맥 전후 판단 변화, 임시 참고 레이블과의 일치
- **해석상의 한계:** 일치율은 화자의 실제 감정을 알아맞힌 정확도가 아닙니다. 참가자와 AI가 일치해도 둘 다 틀릴 수 있습니다.
- **실험 설계상 한계:** 모든 문항에서 문맥을 나중에 제공하므로 순서 효과가 있으며, 난이도가 올라가는 회차 간 점수는 직접 비교하기 어렵습니다.
- **윤리:** 입력하지 않은 실제 사람의 감정을 확정하지 않습니다. 이 앱은 심리 진단이나 상담이 아닙니다.

향후 개선: 여러 평가자가 독립적으로 정한 레이블, 대조 조건 무작위 배정, 모델 간 비교, 충분한 참여자 수와 통계적 검정.''')
