# EmotionGap — AI 감정 인식과 문맥 이해 검증 웹앱

Streamlit + 선택적 Google Gemini API를 이용한 감정 해석 비교 실험입니다.

## 주요 기능
- 가상 메시지 12개에 대한 문맥 제공 전후의 참가자 감정 판단
- 실제 Gemini API가 있으면 문맥 전후 AI 분류, 없으면 명확히 표시된 사전 작성 **데모** 결과
- AI·인간·임시 기준 레이블 간 일치율, 응답 변경률, CSV 내보내기
- 외부 API 실패 시 오류 메시지 및 재시도 가능 (결과를 꾸며서 생성하지 않음)

## 로컬 실행
```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## 무료 Gemini API 연결 (선택)
1. https://aistudio.google.com/apikey 에서 키를 발급합니다. 무료 등급 여부·할당량·데이터 이용 정책을 확인하세요.
2. 로컬: `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사하고 키를 입력합니다.
3. Streamlit Cloud: 앱 설정의 Secrets에 아래를 넣습니다 (GitHub에 실제 키 업로드 금지).
```toml
GEMINI_API_KEY = "YOUR_REAL_KEY"
GEMINI_MODEL = "gemini-2.5-flash-lite"
```
4. 해당 모델의 무료 액세스가 계정에서 제공되지 않으면 Google 공식 모델 목록의 무료 지원 모델 ID로 바꿉니다.

## GitHub → Streamlit 배포
1. GitHub 새 저장소 `emotiongap`을 만듭니다.
2. 압축을 풀어 폴더 **안의 내용**을 저장소 루트에 업로드합니다 (`app.py`, `engine.py`, `requirements.txt`, `tests/`, `.streamlit/`).
3. https://share.streamlit.io/ 에서 GitHub 로그인 → Create app → 저장소 선택 → main branch → 엔트리포인트 `app.py` → Deploy.
4. Secrets에 API 키를 추가한 후 앱을 재시작합니다.

## 보고서 연구 설계 관련 주의
- reference는 개발자가 만든 **임시 참고 레이블**입니다. 여러 평가자 검증 전에는 정답이 아닙니다.
- 같은 문항을 문맥 없는 단계 다음 문맥 있는 단계로 평가하므로 순서 효과가 존재합니다.
- 데모 예측은 **실제 AI 출력이 아니므로 AI 성능 검증에 사용하지 마세요**.
- 세션 기록은 영구 DB에 저장하지 않습니다. 페이지 종료 전에 CSV로 내보내세요.
- 실제 상담 메시지나 개인정보는 수집·전송하지 마세요.

## 자체 테스트
```bash
python -m unittest discover -s tests -v
python -m py_compile app.py engine.py
```

## 다음 개선 단계
- 사람 평가자 3명 이상에게 문항 레이블 독립 검증
- 순서 효과를 통제하는 참가자 배정
- 외부 DB(Supabase 등)로 익명 동의 기반 연구 데이터 저장
- 반복 실험 시 AI 모델 버전, 날짜, 프롬프트 기록
