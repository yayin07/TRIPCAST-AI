import streamlit as st
import requests
import openai
import os
from fpdf import FPDF
from datetime import datetime

# --- Streamlit UI config ---
st.set_page_config(page_title="TripCast AI", layout="centered")
st.title("🌍 TripCast AI")
st.subheader("Plan your day based on weather and nearby activities")

# --- Sidebar API Key Input ---
st.sidebar.title("🔐 API Configuration")

if "api_keys_applied" not in st.session_state:
    st.session_state.api_keys_applied = False
    st.session_state.openai_api_key = ""
    st.session_state.weather_api_key = ""

openai_key_input = st.sidebar.text_input("OpenAI API Key", type="password")
weather_key_input = st.sidebar.text_input("Weather API Key", type="password")

if st.sidebar.button("✅ Apply API Keys"):
    st.session_state.openai_api_key = openai_key_input
    st.session_state.weather_api_key = weather_key_input
    st.session_state.api_keys_applied = True
    st.sidebar.success("API keys applied!")

# Use session keys or fallback to env
openai.api_key = st.session_state.openai_api_key or os.getenv("OPENAI_API_KEY")
WEATHER_API_KEY = st.session_state.weather_api_key or os.getenv("WEATHER_API_KEY")

# --- Input Location ---
location = st.text_input("Enter your current city or location (e.g., Tokyo, Japan)")

# --- Weather Forecast Function ---
def get_weather_forecast(city):
    """Fetch current + hourly forecast using OpenWeatherMap 5-day/3-hour API."""
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url)

    if response.status_code != 200:
        return "❌ Weather data not available.", "unknown weather"

    data = response.json()
    city_name = data["city"]["name"]
    country = data["city"]["country"]

    current = data["list"][0]
    current_temp = round(current["main"]["temp"])
    current_desc = current["weather"][0]["description"].capitalize()

    hourly_summary = ""
    for forecast in data["list"][1:7]:
        time = datetime.fromtimestamp(forecast["dt"]).strftime("%I %p").lstrip("0")
        temp = round(forecast["main"]["temp"])
        desc = forecast["weather"][0]["description"].capitalize()
        hourly_summary += f"{time}\n{temp}°C\n{desc}\n\n"

    weather_report = (
        f"🌤️ Currently {current_temp}°C · {current_desc}\n"
        f"{city_name}, {country}\n\n"
        f"📅 Later today:\n\n" + hourly_summary
    )

    return weather_report.strip(), f"{current_desc}, {current_temp}°C"

# --- Itinerary Generator ---
def generate_itinerary(location, weather_desc):
    prompt = f"""
    I'm a tourist currently in {location}. The weather today is {weather_desc}.
    Suggest a 1-day travel itinerary with 3–4 activities or destinations within short distance of each other.
    If it's rainy or bad weather, recommend indoor activities.
    Include local tips and best time for each activity.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful travel assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message['content'].strip()

# --- PDF Formatter ---
def create_pdf(text, filename="tripcast_itinerary.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "TripCast AI - Personalized Itinerary", ln=True)
    pdf.ln(5)

    safe_text = text.encode("latin-1", "replace").decode("latin-1")
    sections = safe_text.split("\n\n")

    activity_number = 1
    for section in sections:
        lines = section.strip().split("\n")
        if len(lines) == 1:
            pdf.set_font("Arial", 'B', 13)
            pdf.set_text_color(30, 30, 120)
            pdf.cell(0, 10, f"-- {lines[0]} --", ln=True)
        else:
            pdf.set_font("Arial", size=12)
            pdf.set_text_color(0, 0, 0)
            for line in lines:
                bullet = f"{activity_number}. "
                pdf.multi_cell(0, 10, f"{bullet}{line}")
                activity_number += 1
        pdf.ln(2)

    pdf.output(filename)
    return filename

# --- Main Execution ---
if st.button("🧭 Generate My Trip Plan"):
    if not st.session_state.api_keys_applied:
        st.error("❗ Please apply your API keys from the sidebar first.")
    elif not location:
        st.warning("Please enter a location to continue.")
    else:
        with st.spinner("🔍 Checking weather and planning your day..."):
            weather_display, weather_brief = get_weather_forecast(location)
            st.info(weather_display)

            plan = generate_itinerary(location, weather_brief)
            st.success("📅 Here's your suggested itinerary:")
            st.markdown(plan)

            # PDF download
            pdf_filename = "tripcast_itinerary.pdf"
            create_pdf(plan, pdf_filename)
            with open(pdf_filename, "rb") as pdf_file:
                st.download_button(
                    label="⬇️ Download Itinerary as PDF",
                    data=pdf_file,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
