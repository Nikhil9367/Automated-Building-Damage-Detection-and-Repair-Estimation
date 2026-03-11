// frontend/src/WeatherPanel.js
import React, { useEffect, useState } from "react";
import axios from "axios";
import { FaTint, FaWind, FaCloudSun, FaCloudMoon } from "react-icons/fa";

const API_KEY = "cdd342711e257c641f0347407ab192c2";

const cities = [
  "Delhi",
  "Mumbai",
  "Chennai",
  "Kolkata",
  "Bengaluru",
  "Hyderabad",
  "Jaipur",
  "Ahmedabad",
  "Pune",
  "Surat",
];

const icons = {
  Clear: "☀️",
  Clouds: "☁️",
  Rain: "🌧",
  Drizzle: "🌦",
  Thunderstorm: "⛈",
  Snow: "❄️",
  Mist: "🌫",
};

function WeatherPanel({ darkMode }) {
  const [city, setCity] = useState("Delhi");
  const [weather, setWeather] = useState(null);
  const [forecast, setForecast] = useState([]);

  useEffect(() => {
    fetchWeather(city);
    fetchForecast(city);
  }, [city]);

  const fetchWeather = async (cityName) => {
    try {
      const url = `https://api.openweathermap.org/data/2.5/weather?q=${cityName}&units=metric&appid=${API_KEY}`;
      const res = await axios.get(url);
      setWeather(res.data);
    } catch (e) {
      setWeather(null);
    }
  };

  const fetchForecast = async (cityName) => {
    try {
      const url = `https://api.openweathermap.org/data/2.5/forecast?q=${cityName}&units=metric&appid=${API_KEY}`;
      const res = await axios.get(url);
      // pick midday items for next 3 days
      const daily = res.data.list.filter((i) => i.dt_txt.includes("12:00:00"));
      setForecast(daily.slice(0, 3));
    } catch (e) {
      setForecast([]);
    }
  };

  const bgFor = (main) => {
    if (darkMode) {
      if (!main) return "linear-gradient(180deg,#071026,#04102b)";
      if (main === "Rain") return "linear-gradient(135deg,#1f2a44,#15304d)";
      if (main === "Clouds") return "linear-gradient(135deg,#1f2333,#2b3046)";
      if (main === "Clear") return "linear-gradient(135deg,#0f1724,#08263a)";
      return "linear-gradient(135deg,#071026,#04102b)";
    } else {
      if (!main) return "linear-gradient(180deg,#e0f2fe,#bae6fd)";
      if (main === "Rain") return "linear-gradient(135deg,#cbd5e1,#94a3b8)";
      if (main === "Clouds") return "linear-gradient(135deg,#f1f5f9,#cbd5e1)";
      if (main === "Clear") return "linear-gradient(135deg,#f0f9ff,#e0f2fe)";
      return "linear-gradient(135deg,#f0f9ff,#e0f2fe)";
    }
  };

  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", month: "short", day: "numeric" });

  const textColor = darkMode ? "#e6f7ff" : "#1e293b";
  const subTextColor = darkMode ? "#9fb7d8" : "#64748b";
  const cardBg = darkMode ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.6)";

  return (
    <div style={{
      borderRadius: 16,
      overflow: "hidden",
      padding: 18,
      color: textColor,
      background: bgFor(weather?.weather?.[0]?.main),
      boxShadow: darkMode ? "0 10px 30px rgba(2,6,23,0.6), inset 0 1px 0 rgba(255,255,255,0.02)" : "0 10px 30px rgba(0,0,0,0.1)",
      width: "100%",
      boxSizing: "border-box"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>Live Weather</div>
          <div style={{ fontSize: 13, color: subTextColor }}>{today}</div>
        </div>
        <div style={{ fontSize: 28 }}>{icons[weather?.weather?.[0]?.main] ?? "🌤"}</div>
      </div>

      <div style={{ marginTop: 12 }}>
        <select value={city} onChange={(e) => setCity(e.target.value)} style={{
          width: "100%",
          padding: 10,
          borderRadius: 10,
          border: "none",
          marginBottom: 12,
          background: cardBg,
          color: textColor,
        }}>
          {cities.map((c) => (
            <option key={c} value={c} style={{ background: darkMode ? "#0b0f1a" : "#fff", color: darkMode ? "#fff" : "#000" }}>
              {c}
            </option>
          ))}
        </select>

        {weather ? (
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <div style={{ fontSize: 44, fontWeight: 800 }}>{Math.round(weather.main.temp)}°C</div>
              <div style={{ color: subTextColor }}>{weather.weather[0].description}</div>
            </div>

            <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
              <div style={{ padding: 10, borderRadius: 10, background: cardBg, flex: 1 }}>
                <div style={{ fontSize: 12, color: subTextColor }}>Feels</div>
                <div style={{ fontWeight: 700 }}>{Math.round(weather.main.feels_like)}°C</div>
              </div>

              <div style={{ padding: 10, borderRadius: 10, background: cardBg, flex: 1 }}>
                <div style={{ fontSize: 12, color: subTextColor }}>Humidity</div>
                <div style={{ fontWeight: 700 }}>{weather.main.humidity}%</div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 12, marginTop: 10 }}>
              <div style={{ padding: 10, borderRadius: 10, background: cardBg, flex: 1 }}>
                <div style={{ fontSize: 12, color: subTextColor }}>Wind</div>
                <div style={{ fontWeight: 700 }}>{weather.wind.speed} m/s</div>
              </div>
              <div style={{ padding: 10, borderRadius: 10, background: cardBg, flex: 1 }}>
                <div style={{ fontSize: 12, color: subTextColor }}>Pressure</div>
                <div style={{ fontWeight: 700 }}>{weather.main.pressure} hPa</div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ color: subTextColor, marginTop: 8 }}>Weather not available</div>
        )}

        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>3-day forecast</div>
          <div style={{ display: "grid", gap: 8 }}>
            {forecast.length ? forecast.map((f, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: 10, borderRadius: 8, background: cardBg }}>
                <div style={{ color: textColor }}>{new Date(f.dt_txt).toLocaleDateString("en-IN", { weekday: "short" })}</div>
                <div style={{ color: subTextColor }}>{icons[f.weather[0].main] ?? "🌤"} {Math.round(f.main.temp)}°C</div>
              </div>
            )) : <div style={{ color: subTextColor }}>No forecast</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default WeatherPanel;
