import { createApp } from "vue";
import {
  Chart,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  BarElement,
  Filler,
  Tooltip,
  Legend,
  LineController,
  BarController,
  ScatterController,
} from "chart.js";
import App from "@/App.vue";
import "@/assets/style.css";

Chart.register(LineElement, PointElement, LinearScale, CategoryScale, BarElement, Filler, Tooltip, Legend, LineController, BarController, ScatterController);
Chart.defaults.font.family = '"Poppins", system-ui, sans-serif';
Chart.defaults.font.size = 11;

createApp(App).mount("#app");
