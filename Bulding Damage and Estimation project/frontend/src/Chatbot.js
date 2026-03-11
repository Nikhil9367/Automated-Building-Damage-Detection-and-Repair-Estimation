import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import { FaPaperPlane, FaRobot } from "react-icons/fa";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const Chatbot = ({ darkMode }) => {
    const [messages, setMessages] = useState([
        { role: "model", content: "Hello! I'm the BuildSenseAI assistant. Ask me anything about building damage or repair." }
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const messagesContainerRef = useRef(null);

    const scrollToBottom = () => {
        setTimeout(() => {
            if (messagesContainerRef.current) {
                messagesContainerRef.current.scrollTo({
                    top: messagesContainerRef.current.scrollHeight,
                    behavior: "smooth"
                });
            }
        }, 100);
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const sendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = { role: "user", content: input };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            const history = messages.map(m => ({ role: m.role, content: m.content }));

            const res = await axios.post("http://127.0.0.1:8000/api/chat", {
                message: userMsg.content,
                history: history
            });

            const botMsg = { role: "model", content: res.data.response };
            setMessages((prev) => [...prev, botMsg]);
        } catch (err) {
            setMessages((prev) => [...prev, { role: "model", content: "Sorry, I encountered an error. Please try again." }]);
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    // Styles based on darkMode
    const bg = darkMode ? "rgba(11, 15, 26, 0.6)" : "rgba(255, 255, 255, 0.8)";
    const border = darkMode ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";
    const text = darkMode ? "#dbeafe" : "#1e293b";
    const inputBg = darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
    const userMsgBg = "linear-gradient(135deg, #39a2ff, #8e2de2)";
    const modelMsgBg = darkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";

    return (
        <div style={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
            maxHeight: "100%",
            background: bg,
            backdropFilter: "blur(10px)",
            borderRadius: 16,
            border: `1px solid ${border}`,
            overflow: "hidden"
        }}>
            {/* Header */}
            <div style={{
                padding: "15px 20px",
                background: darkMode ? "linear-gradient(90deg, rgba(58,117,255,0.1), rgba(142,45,226,0.1))" : "rgba(58,117,255,0.1)",
                borderBottom: `1px solid ${border}`,
                display: "flex",
                alignItems: "center",
                gap: 10
            }}>
                <FaRobot color="#9be2ff" />
                <span style={{ fontWeight: "bold", color: text }}>AI Assistant</span>
            </div>

            {/* Messages */}
            <div
                ref={messagesContainerRef}
                className="chatbot-messages"
                style={{
                    flex: 1,
                    padding: 20,
                    overflowY: "scroll",
                    display: "flex",
                    flexDirection: "column",
                    gap: 15,
                    scrollbarWidth: "thin",
                    scrollbarColor: darkMode ? "rgba(255,255,255,0.4) rgba(255,255,255,0.05)" : "rgba(0,0,0,0.4) rgba(0,0,0,0.05)"
                }}>
                <style>
                    {`
                        .chatbot-messages::-webkit-scrollbar {
                            width: 8px;
                        }
                        .chatbot-messages::-webkit-scrollbar-track {
                            background: transparent;
                        }
                        .chatbot-messages::-webkit-scrollbar-thumb {
                            background-color: ${darkMode ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)"};
                            border-radius: 4px;
                        }
                        
                        /* Markdown Content Styles */
                        .markdown-content {
                            font-size: 14px;
                            line-height: 1.6;
                            word-wrap: break-word;
                            overflow-wrap: break-word;
                        }
                        .markdown-content p {
                            margin-bottom: 0.8em;
                        }
                        .markdown-content p:last-child {
                            margin-bottom: 0;
                        }
                        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
                            margin-top: 1em;
                            margin-bottom: 0.5em;
                            font-weight: 600;
                            line-height: 1.3;
                        }
                        .markdown-content h1 { font-size: 1.4em; border-bottom: 1px solid ${border}; padding-bottom: 0.3em; }
                        .markdown-content h2 { font-size: 1.2em; }
                        .markdown-content h3 { font-size: 1.1em; }
                        
                        .markdown-content ul, .markdown-content ol {
                            margin-left: 1.5em;
                            margin-bottom: 0.8em;
                        }
                        .markdown-content li {
                            margin-bottom: 0.3em;
                        }
                        
                        .markdown-content code {
                            background-color: ${darkMode ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)"};
                            padding: 0.2em 0.4em;
                            border-radius: 4px;
                            font-family: 'Consolas', 'Monaco', monospace;
                            font-size: 0.9em;
                        }
                        .markdown-content pre {
                            background-color: ${darkMode ? "#1e1e1e" : "#f5f5f5"};
                            padding: 1em;
                            border-radius: 8px;
                            overflow-x: auto;
                            margin-bottom: 0.8em;
                            border: 1px solid ${border};
                        }
                        .markdown-content pre code {
                            background: none;
                            padding: 0;
                            color: ${darkMode ? "#d4d4d4" : "#333"};
                        }
                        
                        .markdown-content table {
                            border-collapse: collapse;
                            width: 100%;
                            margin-bottom: 0.8em;
                            font-size: 0.9em;
                        }
                        .markdown-content th, .markdown-content td {
                            border: 1px solid ${border};
                            padding: 0.5em 0.8em;
                            text-align: left;
                        }
                        .markdown-content th {
                            background-color: ${darkMode ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.05)"};
                            font-weight: 600;
                        }
                        .markdown-content blockquote {
                            border-left: 3px solid #3b82f6;
                            padding-left: 1em;
                            color: ${darkMode ? "rgba(255,255,255,0.7)" : "rgba(0,0,0,0.6)"};
                            font-style: italic;
                            margin: 0.8em 0;
                        }
                        .markdown-content a {
                            color: #60a5fa;
                            text-decoration: none;
                        }
                        .markdown-content a:hover {
                            text-decoration: underline;
                        }
                    `}
                </style>
                {messages.map((msg, idx) => (
                    <div key={idx} style={{
                        display: "flex",
                        justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                        alignItems: "flex-start", // Crucial for top alignment of avatar
                        gap: 12
                    }}>
                        {msg.role === "model" && (
                            <div style={{
                                width: 32, height: 32, borderRadius: "50%", background: modelMsgBg,
                                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16,
                                flexShrink: 0,
                                marginTop: 2 // Tiny optical adjustment
                            }}>
                                <FaRobot color="#9be2ff" />
                            </div>
                        )}
                        <div style={{
                            maxWidth: "85%",
                            padding: "12px 16px",
                            borderRadius: 16,
                            background: msg.role === "user" ? userMsgBg : modelMsgBg,
                            color: msg.role === "user" ? "white" : text,
                            fontSize: 14,
                            lineHeight: "1.6",
                            borderTopLeftRadius: msg.role === "model" ? 4 : 16,
                            borderTopRightRadius: msg.role === "user" ? 4 : 16,
                            boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
                            wordBreak: "break-word"
                        }}>
                            {msg.role === "user" ? (
                                <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
                            ) : (
                                <div className="markdown-content">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                        <div style={{
                            width: 32, height: 32, borderRadius: "50%", background: modelMsgBg,
                            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16
                        }}>
                            <FaRobot color="#9be2ff" />
                        </div>
                        <div style={{
                            padding: "10px 16px",
                            borderRadius: 16,
                            background: modelMsgBg,
                            color: text,
                            fontSize: 13,
                            fontStyle: "italic",
                            borderTopLeftRadius: 4
                        }}>
                            <span className="typing-indicator" style={{ opacity: 0.7 }}>Thinking...</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Input */}
            <form onSubmit={sendMessage} style={{
                padding: 15,
                borderTop: `1px solid ${border}`,
                display: "flex",
                gap: 10,
                alignItems: "center"
            }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about repairs, costs, or structural damage..."
                    style={{
                        flex: 1,
                        background: inputBg,
                        border: "1px solid transparent",
                        borderColor: "transparent",
                        borderRadius: 24,
                        padding: "12px 20px",
                        color: text,
                        outline: "none",
                        fontSize: 14,
                        transition: "all 0.2s"
                    }}
                    onFocus={(e) => e.target.style.borderColor = "rgba(59, 130, 246, 0.5)"}
                    onBlur={(e) => e.target.style.borderColor = "transparent"}
                />
                <button
                    type="submit"
                    disabled={!input.trim() || loading}
                    style={{
                        background: input.trim() ? "#3b82f6" : "rgba(100,100,100,0.2)",
                        border: "none",
                        width: 42,
                        height: 42,
                        borderRadius: "50%",
                        color: "white",
                        cursor: input.trim() ? "pointer" : "default",
                        fontSize: 16,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.2s"
                    }}
                >
                    <FaPaperPlane style={{ marginLeft: -2 }} />
                </button>
            </form>
        </div>
    );
};

export default Chatbot;
