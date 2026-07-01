export const WEATHER_OPTIONS = [
  { value: "sunny", label: "Nắng" },
  { value: "cloudy", label: "Có mây" },
  { value: "rainy", label: "Mưa" },
];

export const PROGRAM_LABELS = { quick: "Nhanh", normal: "Thường", heavy: "Mạnh" };

// Job features for the classical ML duration forecaster (matches forecaster.FORECAST_SCHEMA).
export const FLEX_FORECAST = [
  {
    name: "Máy giặt",
    fields: [
      { key: "load_kg", label: "Khối lượng đồ (kg)", type: "number", default: 5, min: 1, max: 9, step: 0.5 },
      { key: "program", label: "Chương trình", type: "select", default: "normal", options: ["quick", "normal", "heavy"] },
    ],
  },
  { name: "Bình nước nóng gián tiếp", fields: [{ key: "people", label: "Số người dùng", type: "number", default: 4, min: 1, max: 6, step: 1 }] },
  { name: "Bình nước nóng trực tiếp", fields: [{ key: "people", label: "Số người dùng", type: "number", default: 4, min: 1, max: 6, step: 1 }] },
];
