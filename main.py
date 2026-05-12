import streamlit as st
from groq import Groq
import google.generativeai as genai
import os
import re
import hashlib
import requests
import json
import random

# ── 1. 페이지 설정 ───────────────────────────────────────────
st.set_page_config(page_title="당신의 이야기", page_icon="📖", layout="wide")

# ── 2. API 클라이언트 설정 ───────────────────────────────────
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

# ── 3. 캐릭터 랜덤 생성 풀 ──────────────────────────────────
CHAR_NAME_POOL = {
    "남자": [
        "차도진", "서하준", "강이엘", "한유리", "윤재혁",
        "이강호", "박시온", "최도현", "김지호", "오세준",
        "정우혁", "남건우", "류시현", "손태양", "백준서",
    ],
    "여자": [
        "이하늘", "김서아", "박채원", "정유나", "한소희",
        "오지수", "윤하린", "최아라", "서민지", "강다은",
        "류이나", "남예린", "송지안", "배수아", "임나연",
    ],
}

CHAR_ROLES = [
    {"role": "남자 주인공",       "emoji": "🖤", "color": "#7EB8D4", "gender": "남자"},
    {"role": "서브 남자 주인공",  "emoji": "☀️", "color": "#F5C842", "gender": "남자"},
    {"role": "갈등 유발자",       "emoji": "🌹", "color": "#E8837A", "gender": "여자"},
    {"role": "절친",              "emoji": "🍑", "color": "#F4A261", "gender": "여자"},
    {"role": "조력자",            "emoji": "🍵", "color": "#80C9A0", "gender": "남자"},
]

PERSONALITY_POOL = [

# --- 여성향/부드러운 캐릭터 위주 ---
    ("냉철하고 분석적인 완벽주의자. 감정이 격해지면 특유의 습관이 나온다. 말투: 단답형, 간결함.", "단답형이 많고 불필요한 말은 하지 않음."),
    ("세련된 외면 뒤에 욕망을 숨긴 라이벌. 계산이 빠르고 우아하게 독설을 날린다. 말투: 뼈 있는 우아함.", "우아하지만 뼈 있는 말투."),
    ("조용하지만 내면에 강렬한 감정을 숨긴 인물. 말투: 말이 적고 의미심장함.", "말이 적고 짧게 끊어 말함."),
    ("전형적인 츤데레. 겉으론 쌀쌀맞지만 뒤에서 몰래 챙겨주는 타입. 말투: 툭툭 내뱉는 스타일.", "무심한 듯하지만 끝에 애정이 묻어남."),
    ("화려한 외모의 인플루언서 타입. 자존감이 높고 당당하며 가끔 허당미가 있음. 말투: 화려하고 감탄사가 많음.", "이모티콘을 쓰는 듯한 텐션 높은 말투."),
    ("차분하고 어른스러운 연상 스타일. 안정감을 주지만 속을 알 수 없는 미소. 말투: 정중하고 부드러움.", "나긋나긋하고 여유 있는 문장 사용."),
    ("대형견 같은 멍뭉미가 넘치는 순정파. 좋아하는 마음을 못 숨김. 말투: 리액션이 크고 직설적.", "좋고 싫음이 분명하며 감정에 솔직한 말투."),
    ("날카로운 첫인상과 달리 소심하고 배려심 많은 내향인. 말투: 조심스럽고 망설임이 느껴짐.", "말끝을 흐리거나 '...그게' 같은 표현을 자주 사용."),
    ("이성보다 본능이 앞서는 야생마 스타일. 승부욕이 강하고 직진함. 말투: 거칠고 힘이 있음.", "강한 어조와 확신에 찬 표현."),
    ("어린 시절의 상처로 인해 방어적인 태도를 가진 인물. 비꼬는 투의 농담을 즐김. 말투: 냉소적이고 방어적.", "냉소적이며 비꼬는 듯한 대화 스타일."),
    ("매사 무기력해 보이지만 자기 분야에는 천재적인 집중력을 보임. 말투: 귀찮음이 묻어나는 느린 어조.", "느릿하고 나른함이 느껴지는 어투."),

# --- 로맨스 웹툰 특화 속성 추가 ---
("전형적인 '츤데레'. 챙겨줄 건 다 챙겨주면서 말은 밉게 한다. 말투: 투덜거림, 츤츤댐.", "투덜거리면서도 상대방의 안부를 묻는 말투."),
("여유 넘치는 능글남 스타일. 어떤 상황에서도 당황하지 않고 장난을 친다. 말투: 나른하고 유머러스함.", "끝을 늘리는 나른한 말투와 농담 섞인 어조."),
("보호 본능을 자극하는 병약미 혹은 섬세한 감수성의 소유자. 말투: 힘없지만 서정적임.", "감성적인 단어 선택과 느린 템포의 말투."),
("철두철미한 원칙주의자. 규칙을 어기는 것을 싫어하지만 사랑에는 서투르다. 말투: 딱딱하고 교과서적.", "문어체에 가까운 딱딱한 말투."),
("자존감이 높고 화려한 것을 좋아하는 화력형 캐릭터. 말투: 자기중심적, 당당함.", "자기 주장이 강하고 화려한 수식어를 사용하는 말투."),
("항상 피곤해 보이지만 일 처리만큼은 확실한 무기력 천재형. 말투: 귀찮음이 묻어남.", "말수가 적고 '...귀찮아' 같은 표현을 자주 씀."),
("비밀스러운 과거를 가진 미스터리한 인물. 항상 웃고 있지만 눈은 웃지 않는다. 말투: 상냥하지만 모호함.", "속내를 알 수 없는 은유적인 표현."),
("강강약약 스타일의 정의로운 열혈파. 불의를 보면 참지 못한다. 말투: 목소리가 크고 확신에 참.", "힘 있는 어조와 에너지가 느껴지는 말투."),
("전교 1등 스타일의 지독한 공부벌레. 모든 상황을 확률로 계산한다. 말투: 논리적, T발언 위주.", "논리적 근거를 따지며 팩트 위주로 말함."),
("예술가적 기질이 강해 자기 세계에 빠져 사는 4차원. 말투: 독특한 비유, 엉뚱함.", "맥락에서 벗어난 엉뚱하고 독특한 비유 사용.")

]

def generate_characters():
    """캐릭터 5명 랜덤 생성"""
    used_names = set()
    characters = {}
    for role_info in CHAR_ROLES:
        gender = role_info["gender"]
        name_pool = CHAR_NAME_POOL[gender]
        available = [n for n in name_pool if n not in used_names]
        name = random.choice(available)
        used_names.add(name)
        personality_pick = random.choice(PERSONALITY_POOL)
        characters[name] = {
            "role":        role_info["role"],
            "emoji":       role_info["emoji"],
            "color":       role_info["color"],
            "personality": personality_pick[0],
            "tone_hint":   personality_pick[1],
        }
    return characters

# ── 4. 장르 설정 ─────────────────────────────────────────────
GENRES = {
    "🏫 학원 로맨스":    "서열 1위가 지배하는 명문고. 남주는 속을 모르는 서늘한 재벌가 후계자, "
                        "서브남주는 '나'를 짝사랑하는 불량해 보이는 순정파, 갈등 유발자는 집안끼리 엮인 약혼녀 후보. "
                        "조력자는 정보통인 전교 1등. '나'는 정체를 숨기고 입학한 가난한 장학생.",
    "🌆 오피스·현대":    "살벌한 비즈니스계. 남주는 유능하지만 인간미 없는 워커홀릭 본부장, "
                        "서브남주는 '나'를 지지해 주는 다정한 라이벌사 최연소 팀장, 갈등 유발자는 '나'의 성과를 가로채는 상사. "
                        "조력자는 눈치 백단 대리님. '나'는 과거의 트라우마를 딛고 성공하려는 신입 사원.",
    "🎨 캠퍼스·청춘":   "미대 혹은 공대 배경. 남주는 과탑이자 '얼굴 천재'지만 타인에게 무관심한 선배, "
                        "서브남주는 '나'의 과거 흑역사를 아는 장난기 많은 남사친, 갈등 유발자는 여론을 조작하는 캠퍼스 여신. "
                        "조력자는 술자리 대장 동기. '나'는 갓 스무 살이 되어 자아를 찾아가는 새내기.",
    "⚽ 스포츠":        "프로 스포츠 구단. 남주는 에이스 선수 혹은 냉철한 감독, 서브남주는 팀 주치의, 갈등 유발자는 라이벌 팀 관계자. '나'는 구단 관계자.",
    "🍰 힐링·일상":      "조용한 동네의 감성 카페/공방. 남주는 번아웃이 와서 내려온 까칠한 전직 천재 작가, "
                        "서브남주는 매일 아침 꽃을 배달하는 햇살 같은 꽃집 주인, 갈등 유발자는 '나'의 과거를 캐는 가십 기사. "
                        "조력자는 길고양이를 돌보는 편의점 사장님. '나'는 소소한 행복을 찾아 정착한 초보 사장.",
}

RATINGS = {
    "🌸 순애":        "감정선 중심. 스킨십은 손잡기·포옹 수준. 설렘과 감정 묘사에 집중.",
    "💫 로맨스":      "자연스러운 감정 표현과 적당한 스킨십 허용. 키스 등 포함 가능.",
    "🥂 성인 로맨스": "성인 감정선. 농밀한 분위기와 욕망 묘사. 절제된 표현 안에서 최대한의 긴장감.",
}

RELATIONS = {
    "🤝 처음 만나는 사이": {"start_affection": 5,  "desc": "오늘 처음 마주친 완전한 초면."},
    "📖 인연이 있던 사이": {"start_affection": 20, "desc": "과거에 스친 적 있거나 짧게 알고 지낸 사이."},
    "💫 재회하는 사이":    {"start_affection": 35, "desc": "한때 가까웠지만 오랫동안 떨어져 있다 다시 만난 사이."},
}

PERSONALITY_OPTIONS = [
    "당차고 독립적", "소심하지만 따뜻함", "4차원 엉뚱함",
    "현실적이고 냉정함", "감성적이고 예민함", "유머감각 넘침",
    "호기심 많고 활발함", "조용하지만 관찰력 뛰어남"
]

# ── 5. Supabase ───────────────────────────────────────────────
def save_game(user_id: str):
    data = {
        "user_id":        user_id,
        "my_name":        st.session_state.my_name,
        "my_gender":      st.session_state.my_gender,
        "my_personality": json.dumps(st.session_state.my_personality, ensure_ascii=False),
        "my_intro":       st.session_state.my_intro,
        "genre":          st.session_state.genre,
        "messages":       st.session_state.messages,
        "affection":      st.session_state.affection,
        "turn_count":     st.session_state.turn_count,
        "char_name":      json.dumps(st.session_state.characters, ensure_ascii=False),
        "my_personality": json.dumps(st.session_state.my_personality, ensure_ascii=False),
    }
    # rating, relation 추가
    data["my_intro"]  = st.session_state.my_intro
    data["genre"]     = st.session_state.genre
    data["char_name"] = json.dumps(st.session_state.characters, ensure_ascii=False)
    requests.post(f"{SUPABASE_URL}/rest/v1/save_data", headers=HEADERS, json=data)

def load_game(user_id: str):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}",
        headers=HEADERS
    )
    data = res.json()
    return data[0] if data else None

# ── 6. 외국어 필터 ───────────────────────────────────────────

# 허용할 영문 약어 목록
WHITELIST = {
    # 기존
    "CEO", "TV", "PC", "SNS", 
    # SNS & 커뮤니케이션
    "DM", "ID", "MBTI", "OTT",
    # 학교 & 직장
    "OT", "MT", "CC", "PPT", "TF", "IT",
    # 일상
    "AS", "VS", "VIP", "K-"
}

def filter_foreign(text: str) -> str:
    placeholders = []

    def preserve(m):
        placeholders.append(m.group(0))
        return f"__PRESERVE_{len(placeholders)-1}__"

    # HTML 태그, 코드블록 보호
    text = re.sub(r'<[^>]+>|```[\s\S]*?```|`[^`]*`', preserve, text)

    # 화이트리스트 단어 먼저 보호
    for word in WHITELIST:
        text = re.sub(
            rf'\b{word}\b',
            lambda m: preserve(m),
            text,
            flags=re.IGNORECASE
        )

    # 나머지 영문 2자 이상 제거
    text = re.sub(r'\b[A-Za-z]{2,}\b', '', text)
    text = re.sub(r'  +', ' ', text).strip()

    # 보호된 부분 복원
    for i, p in enumerate(placeholders):
        text = text.replace(f"__PRESERVE_{i}__", p)

    return text

# ── 7. 호감도 파싱 ───────────────────────────────────────────
def parse_affection(text: str, current: dict) -> dict:
    updated = current.copy()
    characters = st.session_state.characters
    for char in characters:
        match = re.search(rf"\[{re.escape(char)}\s*([+-]\d+)\]", text)
        if match:
            delta = int(match.group(1))
            delta = max(-5, min(5, delta))
            old_val = current.get(char, 5)
            updated[char] = max(0, min(100, old_val + delta))
    return updated

# ── 8. AI 응답 (Groq → Gemini 폴백) ─────────────────────────
def get_ai_response(system_prompt: str, api_messages: list) -> tuple[str, str]:
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + api_messages,
            temperature=0.92,
            top_p=0.9,
            max_tokens=900,
        )
        return completion.choices[0].message.content, "Groq"
    except Exception as e:
        if "429" in str(e) or "rate_limit" in str(e).lower():
            try:
                gemini_history = []
                for msg in api_messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append({"role": role, "parts": [msg["content"]]})
                last_msg = api_messages[-1]["content"]
                gemini_model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=system_prompt
                )
                chat = gemini_model.start_chat(history=gemini_history)
                response = chat.send_message(last_msg)
                return response.text, "Gemini"
            except Exception as gemini_err:
                raise Exception(f"Groq·Gemini 모두 실패: {gemini_err}")
        else:
            raise e

MAX_TURNS = 10
def get_trimmed_messages():
    return st.session_state.messages[-(MAX_TURNS * 2):]

# ── 9. 텍스트 정제 & 색상 적용 ──────────────────────────────
def clean_text(text: str) -> str:
    return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL).strip()

def colorize_dialogue(text: str) -> str:
    characters = st.session_state.get("characters", {})
    for name, info in characters.items():
        color = info["color"]
        text = re.sub(
            rf'({re.escape(name)}:\s*"[^"]*")',
            rf'<span style="color:{color}; font-weight:600">\1</span>',
            text
        )
    return text

def render_message(text: str):
    cleaned  = clean_text(text)
    filtered = filter_foreign(cleaned)
    colored  = colorize_dialogue(filtered)
    st.markdown(colored, unsafe_allow_html=True)

# ── 10. 시스템 프롬프트 생성 ─────────────────────────────────
def build_system_prompt() -> str:
    my         = st.session_state.my_name
    gender     = st.session_state.my_gender
    traits     = ", ".join(st.session_state.my_personality)
    intro      = st.session_state.my_intro or "특별한 소개 없음"
    genre      = st.session_state.genre
    rating     = st.session_state.get("rating", "💫 로맨스")
    relation   = st.session_state.get("relation", "🤝 처음 만나는 사이")
    world      = GENRES.get(genre, "")
    rating_guide   = RATINGS.get(rating, "")
    relation_desc  = RELATIONS.get(relation, {}).get("desc", "")
    aff            = st.session_state.affection
    characters     = st.session_state.characters
    user_notes     = st.session_state.get("user_notes", "")

    char_desc = ""
    for name, info in characters.items():
        a = aff.get(name, 5)
        if a >= 90:
            tone = "감정을 숨기지 않는 다정하고 솔직한 말투. 연인처럼 자연스러운 반말."
        elif a >= 60:
            tone = "이름을 불러줄 때 사용자의 이름만 불러줬으면 좋겠어(ex.예진아~). 자주 장난기도 섞임."
        elif a >= 30:
            tone = f"편한 친구 같은 자연스러운 반말. 가끔 장난기도 섞임. {info.get('tone_hint','')}"
        else:
            tone = f"친근해지는 10~20대 반말 시작. 아직 약간의 거리감. {info.get('tone_hint','')} 고어체·번역투 절대 금지."
        char_desc += f"\n### {name} ({info['role']})\n{info['personality']}\n현재 말투: {tone}\n"

    user_note_section = ""
    if user_notes.strip():
        user_note_section = f"\n■ 유저 메모 (반드시 반영)\n{user_notes}\n"

    return f"""\
너는 한국 웹소설 작가야. 독자가 직접 참여하는 인터랙티브 웹소설을 써줘.

■ 세계관: {genre}
{world}

■ 주인공 설정
- 이름: {my}
- 성별: {gender} (절대 혼동 금지. 모든 장면에서 일관되게 유지.)
- 성격: {traits}
- 소개: {intro}

■ 관계 설정: {relation}
{relation_desc}

■ 수위: {rating}
{rating_guide}

■ 등장인물
{char_desc}
{user_note_section}
■ 출력 형식 (반드시 준수)
1. [장소 — 시간대] 형식으로 배경 표시
2. 별도 태그 없이 바로 소설 문체로 서술. '[전지적 작가 시점]' 같은 메타 태그 절대 사용 금지.
3. 문체는 한국 정통 웹소설 스타일. 간결하고 감각적인 문장. 너무 길거나 설명적인 문장 금지.
   좋은 예: "차도진이 서류를 덮었다. 그의 시선이 천천히 정예진에게로 향했다."
   나쁜 예: "정예진은 이 세계의 이치와 법칙을 풀어헤쳐 볼 수 있는 기회가 있을까 생각했습니다."
4. 등장인물 대사는 반드시 앞뒤로 빈 줄을 넣어 단독 줄로 표기:
   형식: 이름: "대사"
   
   좋은 예:
   차도진이 천천히 고개를 들었다. 그의 눈빛이 싸늘하게 가라앉았다.
   
   차도진: "늦었군."
   
   정예진은 아무 말도 하지 못했다.
   
   나쁜 예:
   차도진이 고개를 들며 차도진: "늦었군." 이라고 말했다.
5. 상황에 맞는 인물만 등장 (1~3명)
6. 본문 마지막에 아래 형식으로 호감도 변화량만 HTML 주석으로 표기:
   <!-- [캐릭터이름 +숫자] [캐릭터이름 -숫자] -->
   예: <!-- [차도진 +2] [서하준 -1] -->
   - 등장한 캐릭터만 표기할 것
   - 변화량은 반드시 -5 ~ +5 사이로만 작성
   - 절댓값 호감도 숫자는 절대 쓰지 마라
   - 본문에 호감도 관련 텍스트가 보이면 절대 안 됨

■ 호감도 규칙
- 각 캐릭터 시작값: 5 / 범위: 0~100
- '나'의 행동·말에 따라 자연스럽게 변동
- 한 턴에 최대 ±5점 변동
- 호감도가 높아질수록 말투가 자연스럽고 친근하게 변함

■ 말투 변화 분기
- 0~29점: 친근해지는 10~20대 반말 시작
- 30~59점: 편한 친구 같은 자연스러운 반말
- 60~89점: 이름을 불러줄 때 사용자의 이름만 불러줬으면 좋겠어.
- 90~100점: 감정 솔직한 다정한 말투

■ /호감도 명령어
사용자가 "/호감도" 입력 시에만 모든 캐릭터 호감도를 표로 출력

■ 장르별 분위기
- 로맨스/학원: 설렘과 감정선 중심
- 성인로맨스: 농밀한 감정선, 절제된 표현 안에서 최대한의 긴장감과 욕망 묘사

■ 절대 규칙
- 오직 완벽한 한국어만 사용
- 영어·한자·러시아어·일본어 등 외국어 한 글자도 절대 금지
- 몰입감 있는 문학적 문체 유지
- 사용자 입력을 자연스럽게 스토리에 녹여낼 것
- 본인을 3인칭 시점으로 부르지 않았으면 좋겠어
- 똑같은 단어를 지속적으로 반복하는 행위 금지

■ 문장 품질 규칙
- 같은 단어를 한 문단에서 2회 이상 반복 금지
- 같은 장소 표현 반복 금지. 한 번 쓴 장소명은 이후 생략하거나 다르게 표현
- 나쁜 예: "서재 안에서 회의를 하는 동안 차도진은 서재 안에서 그녀를 기다렸다. 차도진은 그녀의 마음을 읽는 차도진이었다."
- 좋은 예: "밀폐된 서재 너머로 낮은 목소리들이 흘러나왔다. 도진은 문가에 기댄 채 묵묵히 시간을 죽였다. 이따금씩 문 쪽을 향하는 그의 서늘한 눈빛만이 초조함을 드러낼 뿐이었다."
"""

# ════════════════════════════════════════════════════════════
# UI 시작
# ════════════════════════════════════════════════════════════

# ── 11. 세션 초기화 ──────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step           = "login"
    st.session_state.user_id        = None
    st.session_state.my_name        = ""
    st.session_state.my_gender      = "여성"
    st.session_state.my_personality = []
    st.session_state.my_intro       = ""
    st.session_state.genre          = ""
    st.session_state.rating         = ""
    st.session_state.relation       = ""
    st.session_state.messages       = []
    st.session_state.affection      = {}
    st.session_state.turn_count     = 0
    st.session_state.characters     = {}
    st.session_state.user_notes     = ""

# ── 12. STEP 1: 로그인 ───────────────────────────────────────
if st.session_state.step == "login":
    st.title("📖 당신의 이야기")
    st.caption("나만의 웹소설을 시작하세요.")
    st.divider()

    name     = st.text_input("이름", placeholder="예: 종완")
    password = st.text_input("비밀번호", type="password", placeholder="본인만 아는 비밀번호")

    col1, col2 = st.columns(2)
    with col1:
        start = st.button("▶ 시작 / 이어하기", use_container_width=True)
    with col2:
        reset = st.button("🗑 처음부터 다시", use_container_width=True)

    if (start or reset) and name and password:
        user_id = hashlib.sha256(f"{name}{password}".encode()).hexdigest()[:16]
        st.session_state.user_id = user_id

        if reset:
            requests.delete(
                f"{SUPABASE_URL}/rest/v1/save_data?user_id=eq.{user_id}",
                headers=HEADERS
            )
            st.session_state.step = "setup"
        else:
            saved = load_game(user_id)
            if saved:
                st.session_state.my_name        = saved["my_name"]
                st.session_state.my_gender      = saved.get("my_gender", "여성")
                st.session_state.my_personality = json.loads(saved["my_personality"])
                st.session_state.my_intro       = saved.get("my_intro", "")
                st.session_state.genre          = saved.get("genre", "")
                st.session_state.rating         = saved.get("rating", "💫 로맨스")
                st.session_state.relation       = saved.get("relation", "🤝 처음 만나는 사이")
                st.session_state.messages       = saved["messages"]
                st.session_state.affection      = saved["affection"]
                st.session_state.turn_count     = saved["turn_count"]
                raw_chars = saved.get("char_name", "{}")
                st.session_state.characters     = json.loads(raw_chars) if isinstance(raw_chars, str) else raw_chars
                st.session_state.step           = "story"
            else:
                st.session_state.step = "setup"
        st.rerun()

    elif (start or reset) and not (name and password):
        st.warning("이름과 비밀번호를 입력해주세요.")

# ── 13. STEP 2: 주인공 설정 ──────────────────────────────────
elif st.session_state.step == "setup":
    st.title("✍️ 주인공 설정")
    st.caption("이야기 속 '나'를 만들어주세요.")
    st.divider()

    my_name   = st.text_input("주인공 이름", placeholder="예: 이하늘")
    my_gender = st.radio("성별", ["여성", "남성"], horizontal=True)

    st.markdown("**성격 키워드** (최대 3개 선택)")
    selected = []
    cols = st.columns(2)
    for i, opt in enumerate(PERSONALITY_OPTIONS):
        with cols[i % 2]:
            if st.checkbox(opt, key=f"trait_{i}"):
                selected.append(opt)

    my_intro = st.text_input("한 줄 소개 (선택)", placeholder="예: 평범한 척하지만 반전매력 있음")

    if len(selected) > 3:
        st.warning("성격 키워드는 최대 3개까지만 선택할 수 있어요.")

    if st.button("다음 →", use_container_width=True):
        if not my_name:
            st.warning("주인공 이름을 입력해주세요.")
        elif len(selected) == 0:
            st.warning("성격 키워드를 최소 1개 선택해주세요.")
        elif len(selected) > 3:
            st.warning("성격 키워드는 최대 3개까지만 선택할 수 있어요.")
        else:
            st.session_state.my_name        = my_name
            st.session_state.my_gender      = my_gender
            st.session_state.my_personality = selected
            st.session_state.my_intro       = my_intro
            st.session_state.characters     = generate_characters()
            st.session_state.step           = "genre"
            st.rerun()

# ── 14. STEP 3: 장르 선택 ────────────────────────────────────
elif st.session_state.step == "genre":
    st.title("🃏 장르 선택")
    st.caption("이야기의 배경을 골라주세요.")
    st.divider()

    cols = st.columns(2)
    for i, (genre_name, world_desc) in enumerate(GENRES.items()):
        with cols[i % 2]:
            st.markdown(f"### {genre_name}")
            st.caption(world_desc[:45] + "...")
            if st.button("선택", key=f"genre_{i}", use_container_width=True):
                st.session_state.genre = genre_name
                st.session_state.step  = "rating"
                st.rerun()

# ── 15. STEP 4: 수위 선택 ────────────────────────────────────
elif st.session_state.step == "rating":
    st.title("✨ 수위 선택")
    st.caption("이야기의 분위기를 설정해주세요.")
    st.divider()

    for rating_name, rating_desc in RATINGS.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{rating_name}**")
            st.caption(rating_desc)
        with col2:
            if st.button("선택", key=f"rating_{rating_name}", use_container_width=True):
                st.session_state.rating = rating_name
                st.session_state.step   = "relation"
                st.rerun()
        st.divider()

# ── 16. STEP 5: 관계 프리셋 ──────────────────────────────────
elif st.session_state.step == "relation":
    st.title("💫 관계 설정")
    st.caption("등장인물들과의 관계를 설정해주세요.")
    st.divider()

    for rel_name, rel_info in RELATIONS.items():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{rel_name}**")
            st.caption(rel_info["desc"])
        with col2:
            if st.button("선택", key=f"rel_{rel_name}", use_container_width=True):
                st.session_state.relation  = rel_name
                start_aff = rel_info["start_affection"]
                st.session_state.affection = {
                    name: start_aff for name in st.session_state.characters
                }
                st.session_state.step = "intro"
                st.rerun()
        st.divider()

# ── 17. STEP 6: 캐릭터 소개 ──────────────────────────────────
elif st.session_state.step == "intro":
    st.title("📖 등장인물")
    st.caption(
        f"{st.session_state.genre}  |  "
        f"{st.session_state.rating}  |  "
        f"{st.session_state.relation}"
    )
    st.divider()

    characters = st.session_state.characters
    for name, info in characters.items():
        with st.expander(f"{info['emoji']} {name}"):
            st.markdown(
                f"<span style='color:{info['color']}'>{info['personality']}</span>",
                unsafe_allow_html=True
            )

    st.divider()
    if st.button("📖 이야기 시작하기", use_container_width=True):
        system_prompt = build_system_prompt()
        relation = st.session_state.relation
        if relation == "🤝 처음 만나는 사이":
            opening_req = "이야기를 시작해줘. 주인공과 등장인물들이 처음 만나는 첫 장면을 웹소설 도입부처럼 감각적으로 써줘."
        elif relation == "📖 인연이 있던 사이":
            opening_req = "이야기를 시작해줘. 먼저 2~3문장으로 두 사람의 짧은 과거 인연을 프롤로그처럼 써준 뒤, 현재 장면으로 자연스럽게 이어줘."
        else:
            opening_req = "이야기를 시작해줘. 먼저 3~4문장으로 과거 가까웠던 시절과 이별의 서사를 프롤로그처럼 써준 뒤, 오랜만의 재회 장면으로 자연스럽게 이어줘."

        with st.spinner("첫 번째 장면을 쓰는 중..."):
            try:
                response, _ = get_ai_response(system_prompt, [{"role": "user", "content": opening_req}])
                st.session_state.messages   = [{"role": "assistant", "content": response}]
                st.session_state.turn_count = 0
                save_game(st.session_state.user_id)
                st.session_state.step = "story"
                st.rerun()
            except Exception as e:
                st.error(f"오류가 발생했어요: {e}")

# ── 18. STEP 7: 메인 스토리 ──────────────────────────────────
elif st.session_state.step == "story":
    characters  = st.session_state.characters
    genre_emoji = st.session_state.genre.split()[0]

    # ── 사이드바 ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 📋 정보")
        st.caption(
            f"**{st.session_state.my_name}** ({st.session_state.my_gender})\n\n"
            f"{st.session_state.genre}\n\n"
            f"{st.session_state.rating}  |  {st.session_state.relation}"
        )
        st.divider()

        # 캐릭터 색상 범례
        st.markdown("### 🎨 등장인물")
        for name, info in characters.items():
            st.markdown(
                f"<span style='color:{info['color']}'>■</span> **{name}** ({info['role']})",
                unsafe_allow_html=True
            )

        st.divider()

        # 유저 노트
        st.markdown("### 📝 유저 노트")
        st.caption("이벤트, 성격 추가, 요청사항을 자유롭게 적어주세요. AI가 다음 장면부터 반영해요.")
        user_notes_input = st.text_area(
            label="노트",
            value=st.session_state.user_notes,
            height=200,
            placeholder=(
                "예시:\n"
                "- 차도진과 하준이 오늘 처음으로 말다툼을 함\n"
                "- 주인공이 비를 무서워하는 설정 추가\n"
                "- 다음 장면에 김치즈가 깜짝 등장했으면 좋겠어"
            ),
            label_visibility="collapsed"
        )
        if st.button("💾 노트 저장", use_container_width=True):
            st.session_state.user_notes = user_notes_input
            st.success("반영됐어요!")

        st.divider()
        if st.button("← 로그아웃", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ── 메인 화면 ─────────────────────────────────────────────
    st.title(f"{genre_emoji} 당신의 이야기")
    st.caption(
        f"**{st.session_state.my_name}** ({st.session_state.my_gender})  |  "
        f"{' · '.join(st.session_state.my_personality)}"
    )
    st.divider()

    # 대화 출력
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="📖"):
                render_message(msg["content"])

    # 입력 처리
    if prompt := st.chat_input("이야기를 이어가세요... (호감도 확인: /호감도)"):

        if prompt.strip() == "/호감도":
            aff    = st.session_state.affection
            result = "### 📊 현재 호감도\n\n"
            for char, val in aff.items():
                if char not in characters:
                    continue
                info  = characters[char]
                bar   = "█" * (val // 10) + "░" * (10 - val // 10)
                label = (
                    "💗 연인 단계"   if val >= 90 else
                    "🌸 친밀한 사이" if val >= 60 else
                    "😐 평범한 관계" if val >= 30 else
                    "🧊 차가운 사이"
                )
                result += (
                    f"<span style='color:{info['color']}'>"
                    f"**{info['emoji']} {char}**</span> ({info['role']})\n"
                    f"`{bar}` {val}/100  {label}\n\n"
                )
            with st.chat_message("assistant", avatar="📊"):
                st.markdown(result, unsafe_allow_html=True)

        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="📖"):
                with st.spinner("이야기를 쓰는 중..."):
                    try:
                        system_prompt = build_system_prompt()
                        response, used_model = get_ai_response(
                            system_prompt,
                            get_trimmed_messages()
                        )
                        render_message(response)

                        if used_model == "Gemini":
                            st.toast("⚡ Gemini로 자동 전환됐어요!", icon="🔄")

                        new_aff = parse_affection(response, st.session_state.affection)
                        st.session_state.affection = new_aff

                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.session_state.turn_count += 1
                        save_game(st.session_state.user_id)
                        st.rerun()

                    except Exception as e:
                        st.error(f"오류가 발생했어요: {e}")
