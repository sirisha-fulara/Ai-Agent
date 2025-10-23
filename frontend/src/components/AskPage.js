import React, {
    useEffect,
    useRef,
    useCallback,
    useTransition,
    useState,
} from "react";
import uploadFileIcon from "../assets/upload-file.png";
import sendFileIcon from "../assets/send.png"
import voiceButton from "../assets/voice.png"
import useVoiceChat from "../hooks/useVoiceChat";
import { cn } from "../lib/utils";
import {
    ImageIcon,
    Figma,
    MonitorIcon,
    CircleUserRound,
    ArrowUpIcon,
    Paperclip,
    PlusIcon,
    SendIcon,
    XIcon,
    LoaderIcon,
    Sparkles,
    Command,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// ------------------ Custom Hook ------------------
function useAutoResizeTextarea({ lineHeight = 24, maxLines = 5 }) {
    const textareaRef = useRef(null);

    const adjustHeight = useCallback(() => {
        const textarea = textareaRef.current;
        if (!textarea) return;

        textarea.style.height = "auto"; // reset

        const lines = Math.floor(textarea.scrollHeight / lineHeight);
        const newHeight = Math.min(lines, maxLines) * lineHeight;

        textarea.style.height = `${newHeight}px`;
    }, [lineHeight, maxLines]);

    useEffect(() => {
        adjustHeight(); // initial adjustment
    }, [adjustHeight]);

    return { textareaRef, adjustHeight };
}

// ------------------ Textarea ------------------
const Textarea = React.forwardRef(
    ({ className, containerClassName, showRing = true, ...props }, ref) => {
        const [isFocused, setIsFocused] = useState(false);

        return (
            <div className={cn("relative", containerClassName)}>
                <textarea
                    className={cn(
                        "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                        "transition-all duration-200 ease-in-out",
                        "placeholder:text-muted-foreground",
                        "disabled:cursor-not-allowed disabled:opacity-50",
                        showRing
                            ? "focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
                            : "",
                        className
                    )}
                    ref={ref}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    {...props}
                />

                {showRing && isFocused && (
                    <motion.span
                        className="absolute inset-0 rounded-md pointer-events-none ring-2 ring-offset-0 ring-violet-500/30"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    />
                )}
            </div>
        );
    }
);
Textarea.displayName = "Textarea";


function UploadButton({ setFile, onUpload }) {
    const fileInputRef = useRef(null);

    const handleClick = () => {
        fileInputRef.current.click();
    };

    const handleChange = (e) => {
        setFile(e.target.files);
    };

    return (
        <button
            onClick={() => {
                fileInputRef.current && fileInputRef.current.click();
                if (onUpload) onUpload(); // call upload after selection
            }}
            className="p-2 rounded-md bg-white/10 hover:bg-green-500/20 transition flex items-center justify-center"
        >
            <input
                type="file"
                multiple
                ref={fileInputRef}
                onChange={handleChange}
                className="hidden"
            />

            <img
                src={uploadFileIcon}
                alt="Upload"
                className="w-6 h-6 brightness-0 invert hover:invert-0 hover:brightness-100 transition"
            />
        </button>
    );
}


// ------------------ Main Component ------------------
export function AnimatedAIChat() {
    const [file, setFile] = useState(null);
    const [message, setMessage] = useState("");
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState([]);

    const [value, setValue] = useState("");
    const [attachments, setAttachments] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const [isPending, startTransition] = useTransition();
    const [activeSuggestion, setActiveSuggestion] = useState(-1);
    const [showCommandPalette, setShowCommandPalette] = useState(false);
    const [recentCommand, setRecentCommand] = useState(null);
    const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
    const { textareaRef, adjustHeight } = useAutoResizeTextarea({
        lineHeight: 5, // 1 line height
        maxLines: 5,    // max 5 lines
    });
    const [inputFocused, setInputFocused] = useState(false);
    const commandPaletteRef = useRef(null);
    const { recording, startRecording, stopRecording } = useVoiceChat({
        onAddMessage: (role, text) => setMessages(prev => [...prev, { role, text }])
    });

    // -------------------- Upload PDFs --------------------
    const handleUpload = async () => {
        if (!file) return setMessage("Please select file(s) to upload.");

        const formData = new FormData();
        Array.from(file).forEach((f) => formData.append("files", f));

        try {
            const res = await fetch("https://localhost:5000/upload", {
                method: "POST",
                body: formData,
                credentials: "include",
            });
            const data = await res.json();
            setMessage(data.message || data.error);
        } catch (err) {
            setMessage("Upload failed: " + err.message);
        }
    };

    // -------------------- Ask question --------------------
    const handleQuery = async () => {
        if (!question.trim()) return;

        // 1️⃣ Add user message
        setMessages((prev) => [...prev, { role: "user", text: question }]);
        setQuestion("");

        // 2️⃣ Show AI typing dots
        setIsTyping(true);

        try {
            const res = await fetch("https://localhost:5000/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: question }),
                credentials: "include",
            });

            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            const data = await res.json();
            const aiText = data.answer || "No answer received";

            // 3️⃣ Add AI response
            setMessages((prev) => [...prev, { role: "bot", text: aiText }]);
        } catch (err) {
            setMessages((prev) => [...prev, { role: "bot", text: "Error: " + err.message }]);
        } finally {
            // 4️⃣ Hide typing dots
            setIsTyping(false);
        }
    };


    // -------------------- UI Rendering --------------------
    return (
        <div className="min-h-screen flex flex-col w-full items-center justify-center bg-transparent text-black p-2 relative overflow-hidden">
            {/* Background Blurs
            <div className="absolute inset-0 w-full h-full overflow-hidden">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[128px] animate-pulse" />
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[128px] animate-pulse delay-700" />
                <div className="absolute top-1/4 right-1/3 w-64 h-64 bg-fuchsia-500/10 rounded-full blur-[96px] animate-pulse delay-1000" />
            </div> */}

            <div className="w-full max-w-2xl mx-auto relative">
                <motion.div
                    className="relative z-10 space-y-12"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <div className="text-center space-y-3">
                        <h1 className="text-3xl font-medium tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white/90 to-white/40 pb-1">
                            How can I help today?

                        </h1>
                        <hr className="gradient-line" />
                        <p className="text-sm text-white/40">
                            Upload your paper or ask a question
                        </p>
                    </div>

                    <motion.div className="relative flex flex-col h-[500px]
  rounded-2xl border border-white/10
  bg-white/4 backdrop-blur-lg
  shadow-[0_8px_32px_0_rgba(0,0,0,0.25)]
  transition-all duration-500">
                        {/* Chat messages */}
                        <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
                            {messages.map((m, i) => (
                                <div
                                    key={i}
                                    className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                                >
                                    <div
                                        className={`px-4 py-2 rounded-2xl max-w-[80%] break-words shadow-sm ${m.role === "user"
                                            ? "bg-gray-700/30 text-gray-200 rounded-br-none"
                                            : "bg-gray-900/40 text-gray-100 rounded-bl-none"
                                            }`}
                                    >
                                        <b className="block mb-0.5 text-xs opacity-70">
                                            {m.role === "user" ? "You" : "AI"}
                                        </b>
                                        <p>{m.text}</p>
                                    </div>
                                </div>
                            ))}

                            {isTyping && (
                                <div className="flex justify-start">
                                    <div className="px-4 py-2 rounded-2xl bg-gray-900/40 text-gray-200 max-w-[60%] rounded-bl-none">
                                        <TypingDots />
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Input box */}
                        <div className="p-4 border-t border-white/[0.05] flex flex-col gap-2">
                            <Textarea
                                ref={textareaRef}
                                value={question}
                                onChange={(e) => {
                                    setQuestion(e.target.value);
                                    adjustHeight();
                                }}
                                placeholder="Ask about your paper..."
                                containerClassName="flex-1"
                                className="w-full px-0 py-2 resize-none bg-gray-800/30 border border-gray-800/20 text-white placeholder:text-white/40 text-sm rounded-md focus:outline-none"
                                style={{ overflow: "hidden" }}
                                showRing={false}
                            />

                            <div className="flex gap-2 justify-end">
                                <UploadButton setFile={setFile} onUpload={handleUpload}/>
                                <div className="flex gap-2 justify-end">
                                    <button
                                        onClick={recording ? stopRecording : startRecording}
                                        className={`p-2 rounded-md flex items-center justify-center transition
        ${recording ? "bg-red-500" : "bg-gray-800/30 hover:bg-green-500/20 color-white"}`}
                                    >
                                        <img src={voiceButton} alt="Voice" className="w-6 h-6 brightness-0 invert hover:invert-0 hover:brightness-100 transition" />
                                    </button>
                                </div>
                                <button
                                    className="p-2 rounded-md bg-white/10 hover:bg-green-500/20 transition flex items-center justify-center"
                                    onClick={handleQuery}
                                >
                                    <img
                                        src={sendFileIcon}
                                        alt="Send"
                                        className="w-6 h-6 brightness-0 invert hover:invert-0 hover:brightness-100 transition"
                                    />
                                </button>
                            </div>
                        </div>


                    </motion.div>

                </motion.div>
            </div>
        </div>
    );
}

// ------------------ Typing Dots ------------------
function TypingDots() {
    return (
        <div className="flex items-center ml-1">
            {[1, 2, 3].map((dot) => (
                <motion.div
                    key={dot}
                    className="w-1.5 h-1.5 bg-white/90 rounded-full mx-0.5"
                    initial={{ opacity: 0.3 }}
                    animate={{
                        opacity: [0.3, 0.9, 0.3],
                        scale: [0.85, 1.1, 0.85],
                    }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: dot * 0.15 }}
                />
            ))}
        </div>
    );
}
