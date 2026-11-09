# EmotionGap v2 — 반복 심리 실험 웹앱

Streamlit + Gemini + **Supabase 무료 플랜** 기반의 감정 해석 연구 앱입니다.

## 개선점
- 카드형 반응형 화면, 보라색 테마, 진행 단계 표시
- 연구를 마칠 때마다 레벨 1(기본) → 레벨 2(반어·문맥) → 레벨 3(복합·불확실) → 레벨 4(상충하는 단서) → 레벨 5(고난도 추론)로 진화
- 레벨별 5·6·7·8·8문항을 제시하고 각 단계는 8~10개 문항 후보에서 선택. 참가자·회차에 따라 문항 구성이 달라짐
- 같은 익명 참가자 코드로 다시 접속하면 완료한 회차를 조회하고 다음 난이도에서 시작
- Supabase 연결 시 누적 연구 저장, 과거 회차 집계, CSV 다운로드
- 실제 Gemini AI와 데모를 분리하여 **데모 결과를 AI 성능 차트에 포함하지 않음**

## 1. GitHub에 배포
기존 저장소 최상위의 `app.py`, `requirements.txt`를 이 프로젝트 파일로 바꾸고 `study.py`, `storage.py`, `supabase_setup.sql`을 새로 추가하세요. `.streamlit/secrets.toml.example`은 예시일 뿐 실제 비밀키를 업로드하지 마세요.

Streamlit Community Cloud의 Main file path는 `app.py`입니다.

## 2. Supabase 무료 데이터베이스 연결 (장기 누적을 위해 필수)
1. https://supabase.com 에 가입해 새 프로젝트를 만듭니다. 무료 플랜의 제공 여부와 한도는 가입 화면에서 확인하세요.
2. 프로젝트의 **SQL Editor**에서 `supabase_setup.sql` 내용을 한 번 실행하세요.
3. Project Settings 또는 API Keys 메뉴에서 프로젝트 URL과 `service_role` **secret key**를 찾으세요. API 화면 표시는 바뀔 수 있습니다.
4. Streamlit Community Cloud > 앱 > Settings > Secrets에 다음을 입력합니다.

```toml
GEMINI_API_KEY = "본인의 Gemini API 키"
GEMINI_MODEL = "본인 계정에서 사용 가능한 Gemini 모델 ID"
SUPABASE_URL = "https://PROJECT-ID.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "본인의 Supabase service_role 비밀키"
EMOTIONGAP_HASH_SALT = "길고 추측하기 어려운 임의 문자열을 직접 입력"
```

**보안 주의:** Supabase `service_role` 키는 RLS를 우회하는 강력한 비밀키입니다. GitHub, 화면, 채팅 등에 절대 올리지 마세요. Streamlit의 서버 측 Secrets에만 보관합니다. 이 앱은 연구용 익명 데이터만 수집하며, 개인정보를 입력하도록 만들지 않았습니다. 코드 해시와 원본 코드는 다른 값입니다. 동일 코드를 재사용한 사람은 해당 기록에 접근할 수 있으므로 코드 공유를 피하세요.

**기존 DB 업그레이드:** 이전 EmotionGap v2의 SQL을 적용했다면 `supabase_setup.sql`을 다시 실행하세요. 기존 기록은 유지하면서 난이도 4~5의 저장을 허용합니다.

**데이터 처리:** 웹앱이 Streamlit 서버를 통해 Supabase에 `participant_id(해시)`, `회차`, `문항별 선택 결과`, `모델 ID` 등을 저장합니다. 이름, 전화번호, 개인 메시지는 수집하지 않습니다. 참여자 수, 데이터 보관 기간, 동의 절차는 연구를 시작하기 전에 결정하세요.

**기본 보안:** SQL 설정은 RLS를 활성화하고 공개 정책을 만들지 않습니다. DB 작업은 Streamlit 서버의 비밀키로만 이루어집니다. 공개 배포 시 남용 방지를 위해 서버/DB 사용량을 모니터링하세요.

## 3. 사용 방법
1. 첫 방문: 영문·숫자로 된 가명 코드(예: `bluebird23`) 입력 → 연구 참여 동의 체크 → 시작.
2. 질문에 처음 판단 → 문맥 공개 후 다시 판단 → 실제 Gemini AI 예측 결과 확인.
3. 모든 문항 완료 → 자동 DB 저장 → 연구 기록 탭에서 누적 결과 확인.
4. 다음 회차 시작 또는 나중에 **같은 코드**로 재방문 → 다음 난이도 진행.
5. 5단계를 넘어가면 고급 문항을 조합하여 반복합니다. 문항 풀이를 기억하는 학습 효과를 통제하지 못하므로 실제 연구 결과 해석에 주의하세요.

## 4. 테스트 / 제한사항
- API 키가 없으면 `demo` 모드로 제한됩니다. 데모는 AI 성능 평가에서 제외합니다.
- Supabase 연결이 없으면 앱은 현재 브라우저에서만 한 번의 연구를 수행하며 누적 난이도 기능이 잠깁니다.
- 문항 후보는 단계당 8~10개, 실제 문항은 5~8개/회차. 무한히 새로운 질문을 생성하지는 않습니다. 연구용 문항은 답변 조건을 통제하기 위해 직접 검토한 고정 자극으로 구성했습니다.
- 높은 AI/인간 일치율은 실제 감정의 정확한 인식을 입증하지 않습니다.
- API 요청은 `500/503/504` 오류에서만 최대 3번 재시도합니다.

## 5. 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 6. 향후 확장
가상 문항을 AI로 생성하고 사람의 검토/승인 후 배포하는 관리자 워크플로, 난이도별 시험지 구성, 여러 사람의 결과 통계(동의 및 연구 윤리 검토 선행), 도표 및 논문형 보고서.
