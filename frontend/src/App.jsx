import { useState } from 'react'
import './App.css'

const API_URL = 'https://stocks-api-41681714781.us-central1.run.app'

function App() {
  const [symbol, setSymbol] = useState('')
  const [quote, setQuote] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [news, setNews] = useState(null)
  const [newsLoading, setNewsLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = symbol.trim().toUpperCase()
    if (!trimmed) return

    setLoading(true)
    setError(null)
    setQuote(null)
    setNews(null)

    try {
      const res = await fetch(`${API_URL}/stock/${trimmed}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Request failed (${res.status})`)
      }
      setQuote(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleGetNews() {
    if (!quote) return
    setNewsLoading(true)
    setNews(null)

    try {
      const res = await fetch(`${API_URL}/news/${quote.symbol}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Request failed (${res.status})`)
      }
      const data = await res.json()
      setNews(data.summary)
    } catch (err) {
      setError(err.message)
    } finally {
      setNewsLoading(false)
    }
  }

  return (
    <main>
      <h1>Stock Lookup</h1>
      <p className="subtitle">Enter a ticker symbol to see its price — then get an AI-generated news summary.</p>

      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="e.g. AAPL"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />
        <button type="submit" disabled={loading || !symbol.trim()}>
          {loading ? 'Loading…' : 'Get price'}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {quote && (() => {
        const up = parseFloat(quote.change) >= 0
        return (
          <section className="quote" key={quote.symbol + quote.price}>
            <h2>{quote.symbol}</h2>
            <p className="price">${quote.price}</p>
            <p className={`change ${up ? 'up' : 'down'}`}>
              <span className="arrow">{up ? '▲' : '▼'}</span>
              {' '}{quote.change} ({quote.change_percent})
            </p>
          </section>
        )
      })()}

      {quote && (
        <section className="news">
          <button onClick={handleGetNews} disabled={newsLoading}>
            {newsLoading ? 'Loading…' : 'Get news summary'}
          </button>
          {news && <pre className="news-summary">{news}</pre>}
        </section>
      )}
    </main>
  )
}

export default App
