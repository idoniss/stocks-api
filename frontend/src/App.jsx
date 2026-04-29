import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_URL = 'https://stocks-api-41681714781.us-central1.run.app'
const STORAGE_KEY = 'stocks-chats-v1'

function loadChats() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  return []
}

function App() {
  const [chats, setChats] = useState(loadChats)
  const [activeChatId, setActiveChatId] = useState(() => loadChats()[0]?.id ?? null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  const activeChat = chats.find((c) => c.id === activeChatId)
  const messages = activeChat?.messages ?? []

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats))
  }, [chats])

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
    const vv = window.visualViewport
    if (!vv) {
      document.documentElement.style.setProperty('--app-height', `${window.innerHeight}px`)
      return
    }
    function update() {
      document.documentElement.style.setProperty('--app-height', `${vv.height}px`)
      document.documentElement.style.setProperty('--app-offset', `${vv.offsetTop}px`)
    }
    update()
    vv.addEventListener('resize', update)
    vv.addEventListener('scroll', update)
    return () => {
      vv.removeEventListener('resize', update)
      vv.removeEventListener('scroll', update)
    }
  }, [])

  function createNewChat() {
    const id = Date.now().toString()
    const newChat = { id, title: 'New chat', messages: [] }
    setChats((prev) => [newChat, ...prev])
    setActiveChatId(id)
    setSidebarOpen(false)
  }

  function selectChat(id) {
    setActiveChatId(id)
    setSidebarOpen(false)
    setError(null)
  }

  function updateLastAssistant(chatId, updater) {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id !== chatId) return c
        const lastIdx = c.messages.length - 1
        if (lastIdx < 0 || c.messages[lastIdx].role !== 'assistant') return c
        return {
          ...c,
          messages: c.messages.map((m, i) => (i === lastIdx ? updater(m) : m)),
        }
      }),
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return

    let chat = activeChat
    if (!chat) {
      chat = { id: Date.now().toString(), title: trimmed.slice(0, 40), messages: [] }
      setChats((prev) => [chat, ...prev])
      setActiveChatId(chat.id)
    }

    const userMessage = { role: 'user', content: trimmed }
    const placeholderAssistant = { role: 'assistant', content: '', steps: [], pending: true }
    const newMessages = [...chat.messages, userMessage, placeholderAssistant]
    const messagesForRequest = [...chat.messages, userMessage]
    const isFirstMessage = chat.messages.length === 0
    const chatId = chat.id

    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? { ...c, messages: newMessages, title: isFirstMessage ? trimmed.slice(0, 40) : c.title }
          : c,
      ),
    )

    setInput('')
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: messagesForRequest }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Request failed (${res.status})`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop()
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          const event = JSON.parse(part.slice(6))
          if (event.type === 'tool_call') {
            updateLastAssistant(chatId, (m) => ({
              ...m,
              steps: [...(m.steps || []), { type: 'tool_call', name: event.name, args: event.args }],
            }))
          } else if (event.type === 'tool_result') {
            updateLastAssistant(chatId, (m) => ({
              ...m,
              steps: [...(m.steps || []), { type: 'tool_result', name: event.name }],
            }))
          } else if (event.type === 'reply') {
            updateLastAssistant(chatId, (m) => ({ ...m, content: event.content }))
          } else if (event.type === 'done') {
            updateLastAssistant(chatId, (m) => ({ ...m, pending: false }))
          }
        }
      }
    } catch (err) {
      setError(err.message)
      updateLastAssistant(chatId, (m) => ({ ...m, pending: false }))
    } finally {
      setLoading(false)
    }
  }

  function renderStep(s) {
    const sym = s.args?.symbol ?? ''
    if (s.type === 'tool_call') {
      if (s.name === 'get_news') return `Looking up news for ${sym}…`
      if (s.name === 'get_stock_price') return `Looking up price for ${sym}…`
      return `Calling ${s.name}…`
    }
    return `Got ${s.name === 'get_news' ? 'news' : s.name === 'get_stock_price' ? 'price' : 'result'}`
  }

  return (
    <div className="app">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <button className="new-chat-btn" onClick={createNewChat}>
          + New chat
        </button>
        <ul className="chat-list">
          {chats.map((c) => (
            <li
              key={c.id}
              className={`chat-item ${c.id === activeChatId ? 'active' : ''}`}
              onClick={() => selectChat(c.id)}
            >
              {c.title || 'New chat'}
            </li>
          ))}
        </ul>
      </aside>

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      <main>
        <header className="topbar">
          <button className="menu-btn" onClick={() => setSidebarOpen((o) => !o)} aria-label="Toggle menu">
            ☰
          </button>
          <h1>Stocks Chat</h1>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <p className="empty-hint">Try: "What's happening with NVDA?" or "Price of AAPL?"</p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`message ${m.role}`}>
              {m.role === 'assistant' && m.steps?.length > 0 && (
                <ul className="message-steps">
                  {m.steps.map((s, j) => (
                    <li key={j}>{renderStep(s)}</li>
                  ))}
                </ul>
              )}
              {m.content ? (
                <pre dir="auto">{m.content}</pre>
              ) : m.pending ? (
                <div className="loading-bubble">
                  <span>•</span><span>•</span><span>•</span>
                </div>
              ) : null}
            </div>
          ))}
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
    </div>
  )
}

export default App
