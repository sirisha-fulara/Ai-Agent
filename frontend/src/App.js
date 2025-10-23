import "./App.css";
import { useState, useEffect } from "react";
import { AnimatedAIChat } from "./components/AskPage";
import HeroSection from "./components/HeroSection";

function App() {
  const [user, setUser] = useState(null);
  const [provider, setProvider] = useState(null); // "google" or "github"

  // -------------------- Fetch session on load --------------------
  useEffect(() => {
    const fetchSession = async () => {
      try {
        const res = await fetch("https://localhost:5000/me", {
          credentials: "include",
        });
        const data = await res.json();

        if (res.ok && !data.error) {
          setUser(data.user);
          setProvider(data.provider); // "google" or "github"
        } else {
          setUser(null);
          setProvider(null);
        }
      } catch (err) {
        console.error("Session fetch failed:", err);
        setUser(null);
        setProvider(null);
      }
    };
    fetchSession();
  }, []);

  // -------------------- Login & Logout --------------------
  const handleLoginGoogle = () => {
    window.location.href = "https://localhost:5000/login";
  };

  const handleLoginGithub = () => {
    window.location.href = "https://localhost:5000/login/github";
  };

  const handleLogout = async () => {
    try {
      const res = await fetch("https://localhost:5000/logout", {
        method: "GET",
        credentials: "include",
      });

      if (res.ok) {
        console.log("✅ Logged out successfully");
        setUser(null);
        setProvider(null);
        window.location.reload(); // ensures cookies are cleared + UI resets
      } else {
        const errData = await res.json();
        console.error("❌ Logout failed:", errData);
      }
    } catch (err) {
      console.error("Logout error:", err);
    }
  };



  // -------------------- UI --------------------
  return (
    <div className="App min-h-screen w-full items-center justify-center bg-black text-black p-2  overflow-hidden relative z-10">
      <div className="absolute inset-0 w-full h-full overflow-hidden  pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[128px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[128px] animate-pulse delay-700" />
        <div className="absolute top-1/4 right-1/3 w-64 h-64 bg-fuchsia-500/10 rounded-full blur-[96px] animate-pulse delay-1000" />
      </div>
      {/* Header / Auth Section */}
      
       <HeroSection
        user={user}
        provider={provider}
        onLoginGoogle={handleLoginGoogle}
        onLoginGithub={handleLoginGithub}
        onLogout={handleLogout}
      />

      {/* Chat Section */}
      {user && (
        <div className="relative isolate z-10">
          <div className="!bg-[#0b0b0f] text-white overflow-hidden shadow-xl rounded-2xl p-4">
            <AnimatedAIChat />
          </div>
        </div>
      )}
      
    </div>
  );
}

export default App;
