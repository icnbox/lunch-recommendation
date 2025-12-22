import streamlit as st
from google import genai
from google.genai import types
import re
import time

# --- 1. 설정 구간 ---
# 🚨 Secrets에서 키 가져오기 (배포용) 또는 직접 입력 (테스트용)
# 배포할 때는 st.secrets["API_KEY"]를 쓰는 게 좋아!
try:
    API_KEY = st.secrets["API_KEY"]
except:
    API_KEY = "여기에_네_API_키를_넣어줘" 

st.set_page_config(page_title="오늘의 점심 추천", page_icon="🍱", layout="centered")

# --- 2. 핵심: AI에게 기억력(캐시) 선물하기 🧠 ---
# 이 함수 위에 붙은 @st.cache_data가 마법의 주문이야!
# 'ttl=3600'은 "1시간 동안은 기억해라"라는 뜻이야.
@st.cache_data(show_spinner=False, ttl=3600)
def get_lunch_recommendation(loc, food, trigger_count):
    # trigger_count는 "재검색" 버튼을 누를 때마다 숫자를 바꿔서 억지로 새로 찾게 만드는 용도야.
    
    client = genai.Client(api_key=API_KEY)
    
    prompt = f"""
    너는 {loc} 지역의 맛집 큐레이터야.
    구글 검색을 통해 '{loc}' 반경 1km 이내의 '{food}' 식당 중
    **가장 평점이 높고 인기 있는 식당 딱 한 곳**을 찾아줘.
    
    (이전 프롬프트 내용과 동일...)
    
    **[매우 중요 - 출력 규칙]**
    1. 대답의 **맨 첫 줄**에 반드시 추천하는 메뉴의 이름을 `[MENU:메뉴이름]` 형식으로 적어줘.
    
    [출력 예시]
    [MENU:비빔밥]
    ## 🥢 오늘의 추천: 돌솥비빔밥
    ...
    """

    # 모델은 안전하게 flash 최신 버전 사용
    response = client.models.generate_content(
        model="gemini-1.5-flash-latest", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_modalities=["TEXT"]
        )
    )
    return response.text

# --- 3. UI 구성 ---
st.title("🍱 오늘 뭐 먹지..?  (오늘의 점심)")

# 입력받는 곳을 'form'으로 감싸면, 다 입력하고 버튼 누를 때만 실행돼서 더 안전해!
with st.sidebar:
    st.header("옵션 설정")
    new_location = st.text_input("위치", value="하노이 미딩")
    new_food = st.text_input("메뉴", value="한식")
    
    # '재검색'을 위한 카운터 (버튼 누를 때마다 1씩 증가)
    if 'search_count' not in st.session_state:
        st.session_state.search_count = 0
        
    if st.button("새로운 추천 받기 🔄"):
        st.session_state.search_count += 1
        st.rerun() # 화면 다시 그리기

# --- 4. 메인 로직 ---
# 위치, 음식종류, 그리고 '버튼 누른 횟수'가 바뀔 때만 AI가 실행됨!
# 즉, 화면 크기를 바꾸거나 다른 짓을 해도 AI 호출 안 함 (돈/제한 절약!)
try:
    with st.spinner(f"👨‍🍳 {new_location}의 {new_food} 맛집 검색 중..."):
        # 여기서 위에서 만든 '기억력 있는 함수'를 호출해
        full_text = get_lunch_recommendation(new_location, new_food, st.session_state.search_count)
        
        # --- 결과 보여주기 (기존 코드와 동일) ---
        full_text = re.sub(r'<style.*?>.*?</style>', '', full_text, flags=re.DOTALL)
        full_text = re.sub(r'<svg.*?>.*?</svg>', '', full_text, flags=re.DOTALL)
        full_text = re.sub(r'<[^>]+>', '', full_text)

        match = re.search(r'\[MENU:(.*?)\]', full_text)
        if match:
            final_display_text = full_text.replace(match.group(0), "").strip()
        else:
            final_display_text = full_text

        st.markdown(final_display_text)

except Exception as e:
    error_message = str(e)
    if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
        st.warning("🚦 AI가 지금 너무 바빠요! (사용량 제한)")
        st.info("🕒 **30초만 쉬었다가** 왼쪽 사이드바의 [새로운 추천 받기] 버튼을 눌러주세요.")
    else:
        st.error(f"오류가 발생했어요: {e}")