import axios from 'axios';
import { Platform } from "react-native";


let baseURL = "http://localhost:8000";

if (Platform.OS != "web") {
  // running on device or emulator
  baseURL = "http://192.1.1.258:8000"; // put the real ip here
}

const api = axios.create({
  baseURL: baseURL, 

});

export default api;
