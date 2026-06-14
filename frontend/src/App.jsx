import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const API_BASE_URL = `http://${window.location.hostname}:8000`;

export default function App() {
  const [files, setFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // Generate a unique session ID for the user's chat session
  const [sessionId, setSessionId] = useState(() => {
    const existing = localStorage.getItem("chat_session_id");
    if (existing) return existing;
    const newId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2) + Date.now().toString(36);
    localStorage.setItem("chat_session_id", newId);
    return newId;
  });

  const chatEndRef = useRef(null);

  // Scroll to bottom of chat thread when messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Reset the backend database on page load (reload)
  useEffect(() => {
    const resetDB = async () => {
      try {
        await fetch(`${API_BASE_URL}/reset`, { method: "POST" });
        console.log("Database and documents cleared on page load.");
      } catch (err) {
        console.error("Failed to reset database on load:", err);
      }
    };
    resetDB();

    // Reset chat history and session on page load
    const newId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2) + Date.now().toString(36);
    localStorage.setItem("chat_session_id", newId);
    setSessionId(newId);
    setMessages([]);
  }, []);

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    setFiles((prev) => {
      const updated = [...prev];
      selected.forEach((file) => {
        if (!updated.some((f) => f.name === file.name && f.size === file.size)) {
          updated.push(file);
        }
      });
      return updated;
    });
  };

  const handleRemoveFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // 1. Upload Handler
  const handleUpload = async () => {
    if (files.length === 0) {
      alert("Please select files first.");
      return;
    }
    setUploadStatus("Uploading...");

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const response = await fetch(`${API_BASE_URL}/upload_pdf`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      
      if (response.ok) {
        const fileNames = data.uploaded_files.map(f => f.filename).join(", ");
        const chunkCount = data.new_chunks;
        setUploadStatus(`Success! Uploaded: ${fileNames} (${chunkCount} chunks generated).`);
        setFiles([]); // Clear selected files list after successful upload
      } else {
        setUploadStatus(`Upload failed: ${data.detail || "Server error"}`);
      }
    } catch (error) {
      setUploadStatus("Connection error: Make sure the FastAPI server is running.");
    }
  };

  // 2. Query Handler
  const handleAsk = async (e) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userQuery = query.trim();
    setQuery(""); // Clear input early for responsive UI

    // 1. Add user message
    const userMessage = { role: "user", content: userQuery };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // 2. Add temporary placeholder message for assistant
    const placeholderMessage = {
      role: "assistant",
      content: "Thinking...",
      sources: [],
      isPlaceholder: true,
    };
    setMessages((prev) => [...prev, placeholderMessage]);

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userQuery, session_id: sessionId }),
      });
      const data = await response.json();

      if (response.ok) {
        // Replace placeholder with response
        setMessages((prev) => {
          const updated = [...prev];
          const placeholderIdx = updated.findLastIndex((msg) => msg.isPlaceholder);
          if (placeholderIdx !== -1) {
            updated[placeholderIdx] = {
              role: "assistant",
              content: data.answer,
              sources: data.sources || [],
            };
          }
          return updated;
        });
      } else {
        setMessages((prev) => {
          const updated = [...prev];
          const placeholderIdx = updated.findLastIndex((msg) => msg.isPlaceholder);
          if (placeholderIdx !== -1) {
            updated[placeholderIdx] = {
              role: "assistant",
              content: `Error: ${data.detail || "Unable to retrieve response."}`,
              sources: [],
            };
          }
          return updated;
        });
      }
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        const placeholderIdx = updated.findLastIndex((msg) => msg.isPlaceholder);
        if (placeholderIdx !== -1) {
          updated[placeholderIdx] = {
            role: "assistant",
            content: "Connection error: Unable to contact the query endpoint.",
            sources: [],
          };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 3. Reset Handler (DB & Session)
  const handleReset = async () => {
    if (!window.confirm("Are you sure you want to delete all uploaded documents and reset the conversation?")) {
      return;
    }
    
    try {
      await fetch(`${API_BASE_URL}/reset`, { method: "POST" });
      
      const newId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2) + Date.now().toString(36);
      localStorage.setItem("chat_session_id", newId);
      setSessionId(newId);
      setMessages([]);
      setFiles([]);
      setUploadStatus("Database and chat session cleared successfully.");
    } catch (err) {
      console.error("Failed to reset database:", err);
      alert("Failed to reset database. Connection error.");
    }
  };

  return (
    <div className="app-container">
      <h2 className="app-title">Document AI Assistant UI</h2>
      <p className="app-subtitle">Conversational RAG interface with persistent memory.</p>
      
      <hr className="separator" />

      {/* 1. PDF Upload Section */}
      <div className="card upload-section">
        <h3>Step 1: Upload PDFs</h3>
        
        <div className="file-upload-wrapper">
          <div className="file-input-custom">
            Choose PDF Files
            <input 
              type="file" 
              accept=".pdf" 
              multiple
              className="file-input-hidden"
              onChange={handleFileChange} 
            />
          </div>
          <button className="btn btn-primary" onClick={handleUpload}>
            Upload
          </button>
        </div>

        {/* Selected Files List */}
        {files.length > 0 && (
          <div className="selected-files-container">
            <strong className="selected-files-title">Selected Files:</strong>
            <ul className="files-list">
              {files.map((file, idx) => (
                <li key={idx} className="file-item">
                  <span className="file-name">
                    {file.name} <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                  </span>
                  <button className="btn-remove" onClick={() => handleRemoveFile(idx)}>
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="status-text">
          Status: {uploadStatus || "Ready"}
        </p>
      </div>

      {/* 2. Ask Question Section */}
      <div className="card query-section">
        <h3>Step 2: Ask the Assistant</h3>
        
        <div className="chat-container">
          {messages.length === 0 ? (
            <div className="empty-chat">
              <p>No messages yet. Upload some PDFs above and start asking questions!</p>
            </div>
          ) : (
            <div className="chat-thread">
              {messages.map((msg, index) => (
                <div key={index} className={`chat-message ${msg.role}`}>
                  <div className="message-bubble">
                    <div className="message-content">{msg.content}</div>
                    
                    {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                      <div className="message-sources">
                        <details className="sources-details">
                          <summary className="sources-summary">
                            Sources Consulted ({msg.sources.length})
                          </summary>
                          <ul className="sources-list-inline">
                            {msg.sources.map((src, idx) => (
                              <li key={idx} className="source-item-inline">
                                <span className="source-meta-inline">
                                  Page {src.page === "Unknown" ? "N/A" : src.page} ({src.source.split(/[\\/]/).pop()}):
                                </span>
                                <p className="source-quote-inline">
                                  "{src.content.substring(0,150)}..."
                                </p>
                              </li>
                            ))}
                          </ul>
                        </details>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        <form className="query-form" onSubmit={handleAsk}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about the documents..."
            className="query-input"
            disabled={isLoading}
          />
          <button 
            type="submit" 
            disabled={isLoading || !query.trim()} 
            className="btn btn-secondary"
          >
            Send
          </button>
        </form>

        <div className="chat-actions">
          <button className="btn btn-danger-outline" onClick={handleReset}>
            Reset Database & Conversation
          </button>
        </div>
      </div>
    </div>
  );
}