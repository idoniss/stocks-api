import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_URL = 'https://stocks-api-41681714781.us-central1.run.app'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    const newHeight = Math.min(ta.scrollHeight, 160)
    ta.style.height = `${newHeight}px`
    ta.style.overflowY = ta.scrollHeight > 160 ? 'auto' : 'hidden'
  }, [input])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  useEffect(() => {
    function setAppHeight() {
      const h = window.visualViewport?.height ?? window.innerHeight
      document.documentElement.style.setProperty('--app-height', `${h}px`)
    }
    setAppHeight()
    window.visualViewport?.addEventListener('resize', setAppHeight)
    return () => window.visualViewport?.removeEventListener('resize', setAppHeight)
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return

    const userMessage = { role: 'user', content: trimmed }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Request failed (${res.status})`)
      }
      const data = await res.json()
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1>Stocks Chat</h1>
      <p className="subtitle">Ask about any publicly traded company — prices, recent news, or both.</p>

      <div className="messages">
        {messages.length === 0 && (
          <p className="empty-hint">Try: "What's happening with NVDA?" or "Price of AAPL?"</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <pre dir="auto">{m.content}</pre>
          </div>
        ))}
        {loading && (
          <div className="message assistant loading-bubble">
            <span>•</span><span>•</span><span>•</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && <p className="error">{error}</p>}

      <form onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          rows={1}
          dir="auto"
          placeholder="Ask something…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </main>
  )
}

export default App
