import streamlit as st
from google import genai
from google.genai import types
import re
import time

# --- 1. 설정 구간 ---
# 🚨 주의: API 키는 절대 공개된 곳에 올리지 마세요! 새로 발급받은 키를 넣어주세요.
API_KEY = st.secrets["API_KEY"]

# 페이지 설정
st.set_page_config(page_title="오늘의 점심 추천", page_icon="🍱", layout="centered")

# --- 2. 상태 초기화 ---
if 'location' not in st.session_state:
    st.session_state['location'] = "하노이 미딩"
if 'food_type' not in st.session_state:
    st.session_state['food_type'] = "한식 점심"
if 'search_trigger' not in st.session_state:
    st.session_state['search_trigger'] = True

# --- 3. UI 구성 ---
st.title("🍱 오늘 뭐 먹지..?  (오늘의 점심)")

with st.expander("📍 위치 및 메뉴 변경하기 (클릭)"):
    col1, col2 = st.columns(2)
    with col1:
        new_location = st.text_input("위치", value=st.session_state['location'])
    with col2:
        new_food = st.text_input("메뉴", value=st.session_state['food_type'])
    
    if st.button("이 조건으로 다시 찾기 🔄"):
        st.session_state['location'] = new_location
        st.session_state['food_type'] = new_food
        st.session_state['search_trigger'] = True
        st.rerun()

# --- 4. 검색 로직 ---
if st.session_state['search_trigger']:
    current_loc = st.session_state['location']
    current_food = st.session_state['food_type']

    with st.spinner(f"👨‍🍳 {current_loc}의 {current_food} 맛집 검색 중..."):
        try:
            client = genai.Client(api_key=API_KEY)
            
            # [프롬프트]
            prompt = f"""
            너는 {current_loc} 지역의 맛집 큐레이터야.
            구글 검색을 통해 '{current_loc}' 반경 1km 이내의 '{current_food}' 식당 중
            **가장 평점이 높고 인기 있는 식당 딱 한 곳**을 찾아줘.

            그 식당의 **'대표 메뉴'를 주인공**으로 소개해줘.

            **[매우 중요 - 출력 규칙]**
            1. 대답의 **맨 첫 줄**에 반드시 추천하는 메뉴의 이름을 `[MENU:메뉴이름]` 형식으로 적어줘. (예: [MENU:비빔밥])
            2. 이 태그는 내가 이미지 검색에 쓸 거야.

            **[링크 규칙]**
            구글 지도 URL의 공백은 반드시 **+** 기호로 바꿔.
            (예: query=하노이+미딩+맛집)
            
            **[형식]**
            절대 HTML 코드(<style>, <svg>) 포함 금지.

            [출력 예시]
            [MENU:돌솥비빔밥]
            ## 🥢 오늘의 추천: 돌솥비빔밥
            
            **"지글지글 소리까지 맛있는 최고의 선택!"**
            
            ---
            ### 🏠 식당 정보
            * **상호명:** [식당 이름] (⭐ [평점])
            * **주소:** [도로명 주소]
            * **지도:** 🔗 [구글 지도 바로가기](https://www.google.com/maps/search/?api=1&query={current_loc.replace(" ", "+")}+[식당이름(공백은+로)])
            
            ---
            ### 📋 이 식당의 다른 인기 메뉴
            * [메뉴 1] - [가격(선택)]
            * [메뉴 2] - [가격(선택)]
            * [메뉴 3]
            """

            response = client.models.generate_content(
                model="gemini-flash-latest", # 💡 팁: 최신 모델을 쓰면 조금 더 빠를 수 있어!
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_modalities=["TEXT"]
                )
            )
            
            full_text = response.text
            
            # 외계어 청소 (HTML 태그 삭제)
            full_text = re.sub(r'<style.*?>.*?</style>', '', full_text, flags=re.DOTALL)
            full_text = re.sub(r'<svg.*?>.*?</svg>', '', full_text, flags=re.DOTALL)
            full_text = re.sub(r'<[^>]+>', '', full_text)

            # [MENU:...] 태그 찾기
            match = re.search(r'\[MENU:(.*?)\]', full_text)
            
            if match:
                recommended_menu = match.group(1)
                final_display_text = full_text.replace(match.group(0), "").strip()
            else:
                recommended_menu = current_food
                final_display_text = full_text

            # 3. 텍스트 결과 출력
            st.markdown(final_display_text)
            
            # 검색 완료
            st.session_state['search_trigger'] = False

        except Exception as e:
            # 🛡️ 에러 핸들링 업그레이드!
            error_message = str(e)
            
            # 429 에러나 RESOURCE_EXHAUSTED가 메시지에 포함되어 있는지 확인
            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                st.warning("🚦 AI가 지금 주문이 너무 밀렸어요! (사용량 제한)")
                st.info("🕒 **30초만 쉬었다가** 다시 시도해 주세요. 커피 한 잔의 여유를 가져볼까요? ☕")
                # (선택사항) 에러 내용을 나만 볼 수 있게 작게 출력하려면 아래 주석 해제
                # st.caption(f"개발자용 에러 코드: {error_message}")
            else:
                st.error(f"앗, 알 수 없는 오류가 발생했어요. 다시 시도해 주세요!")

                st.error(f"에러 내용: {e}")
