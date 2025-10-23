// src/hooks/useVoiceChat.js
import { useState } from "react";
import axios from "axios";

export default function useVoiceChat({ onAddMessage }) {
  const [recording, setRecording] = useState(false);
  const [recorder, setRecorder] = useState(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const newRecorder = new MediaRecorder(stream);
      let audioChunks = [];

      newRecorder.ondataavailable = (e) => audioChunks.push(e.data);

      newRecorder.onstop = async () => {
        try {
          const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
          const formData = new FormData();
          formData.append("audio", audioBlob, "speech.wav");

          const sttRes = await axios.post("https://localhost:5000/stt", formData, {
            headers: { "Content-Type": "multipart/form-data" },
            withCredentials: true,
          });
          const userText = sttRes.data.text;
          onAddMessage("user", userText);

          const botRes = await axios.post("https://localhost:5000/ask", { query: userText }, {withCredentials: true,});
          const botText = botRes.data.answer;
          onAddMessage("bot", botText);

          const ttsRes = await axios.post(
            "https://localhost:5000/tts",
            { text: botText },
            { responseType: "blob" , withCredentials: true},
            
          );
          const audioUrl = URL.createObjectURL(new Blob([ttsRes.data], { type: "audio/mpeg" }));
          new Audio(audioUrl).play();
        } catch (err) {
          console.error("Error in onstop:", err);
        }
      };

      newRecorder.start();
      setRecorder(newRecorder);
      setRecording(true);
    } catch (err) {
      console.error("Error starting recording:", err);
    }
  };

  const stopRecording = () => {
    if (recorder) recorder.stop();
    setRecording(false);
  };

  return { recording, startRecording, stopRecording };
}
