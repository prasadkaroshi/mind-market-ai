import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ArrowUpRight, BarChart3, CircleHelp, Search, ShieldCheck, Sparkles, TrendingDown, TrendingUp } from 'lucide-react'
import './styles.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function formatNumber(value, digits = 2) {
  return value == null ? '--' : Number(value).toLocaleString('en-IN', { maximumFractionDigits: digits })
}

function Metric({ label, value, hint }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>
}

function CandlestickChart({ data }) {
  const width = 900
  const height = 310
  const padding = { top: 12, right: 10, bottom: 24, left: 10 }
  const values = data.flatMap((item) => [item.high, item.low]).filter((value) => value != null)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const scaleY = (value) => padding.top + ((max - value) / (max - min || 1)) * (height - padding.top - padding.bottom)
  const step = (width - padding.left - padding.right) / Math.max(data.length, 1)
  const candleWidth = Math.max(3, step * 0.56)
  const movingAverage = data.filter((item) => item.sma20 != null).map((item, index) => `${padding.left + (data.indexOf(item) + 0.5) * step},${scaleY(item.sma20)}`).join(' ')

  return <svg className="candlestick-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Candlestick price action chart">
    {[0, 1, 2, 3].map((line) => { const y = padding.top + line * ((height - padding.top - padding.bottom) / 3); return <line key={line} x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="chart-grid-line" /> })}
    {data.map((item, index) => {
      const x = padding.left + (index + 0.5) * step
      const bullish = item.close >= item.open
      const bodyTop = scaleY(Math.max(item.open, item.close))
      const bodyHeight = Math.max(1.5, Math.abs(scaleY(item.open) - scaleY(item.close)))
      return <g key={item.date}><line x1={x} x2={x} y1={scaleY(item.high)} y2={scaleY(item.low)} className={bullish ? 'candle-wick bullish' : 'candle-wick bearish'} /><rect x={x - candleWidth / 2} y={bodyTop} width={candleWidth} height={bodyHeight} className={bullish ? 'candle-body bullish' : 'candle-body bearish'} /></g>
    })}
    <polyline points={movingAverage} className="moving-average-line" />
  </svg>
}

function App() {
  const [ticker, setTicker] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [timeframe, setTimeframe] = useState('3M')

  async function analyzeTicker(symbol, selectedTimeframe = timeframe) {
    if (!symbol) return
    setLoading(true); setError(''); setResult(null)
    try {
      const response = await fetch(`${API_URL}/api/analyze/${encodeURIComponent(symbol)}?timeframe=${selectedTimeframe}`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Unable to analyze this ticker.')
      setResult(data)
      setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    } catch (requestError) {
      setError(requestError.message)
    } finally { setLoading(false) }
  }

  async function analyze(event) {
    event.preventDefault()
    await analyzeTicker(ticker.trim().toUpperCase())
  }

  async function changeTimeframe(selectedTimeframe) {
    setTimeframe(selectedTimeframe)
    if (ticker.trim()) await analyzeTicker(ticker.trim().toUpperCase(), selectedTimeframe)
  }

  const technical = result?.technical
  const isUp = technical?.trend === 'Up'

  return <main className="app-shell">
    <nav className="topbar"><div className="brand"><span className="brand-mark"><Sparkles size={16} /></span><span>Mind Market <b>AI</b></span></div><div className="nav-status"><span className="status-dot" /> Live NSE analysis <CircleHelp size={15} /></div></nav>
    <section className="hero">
      <div className="hero-copy"><p className="eyebrow">INDIAN EQUITY INTELLIGENCE</p><h1>See the signal<br /><em>before the noise.</em></h1><p className="hero-note">A calm, two-lens read on technical momentum and fundamental quality for NSE-listed stocks.</p></div>
      <form className="search-panel" onSubmit={analyze}><label htmlFor="ticker">Analyze an NSE ticker</label><div className="search-row"><Search size={19} /><input id="ticker" value={ticker} onChange={(event) => setTicker(event.target.value)} onKeyDown={(event) => { if (event.key === 'Tab' && ticker.trim() && !loading) { event.preventDefault(); analyzeTicker(ticker.trim().toUpperCase()) } }} placeholder="Try TCS, INFY, RELIANCE..." /><button type="submit" disabled={loading}>{loading ? 'Reading market...' : 'Analyze'} <ArrowUpRight size={17} /></button></div><small>Press Tab or Enter to analyze. Uses Yahoo Finance market data.</small></form>
    </section>
    {error && <div className="error-banner">{error}</div>}
    {!result && !loading && !error && <section className="empty-state"><div className="empty-icon"><BarChart3 size={24} /></div><h2>Your next read starts here.</h2><p>Search a stock to bring its momentum, risk levels, and market snapshot into focus.</p><div className="chips"><button onClick={() => setTicker('TCS')}>TCS</button><button onClick={() => setTicker('INFY')}>INFY</button><button onClick={() => setTicker('RELIANCE')}>RELIANCE</button></div></section>}
    {loading && <section className="loading-state"><div className="loader" /><p>Pulling market history for {ticker.toUpperCase()}...</p></section>}
    {result && <section id="results" className="results"><div className="result-heading"><div><p className="eyebrow">MARKET READ / {result.ticker}</p><h2>{result.companyName}</h2></div><span className={`trend-pill ${isUp ? 'up' : 'down'}`}>{isUp ? <TrendingUp size={17} /> : <TrendingDown size={17} />} {technical.trend}trend</span></div>
      <div className="metrics-grid"><Metric label="Last traded price" value={`₹${formatNumber(technical.price)}`} hint="Latest close" /><Metric label="Target zone" value={`₹${formatNumber(technical.target)}`} hint="Pivot-based level" /><Metric label="Risk marker" value={`₹${formatNumber(technical.stopLoss)}`} hint="Indicative stop loss" /><Metric label="Confirmation" value={`${technical.confirmationScore}/3`} hint="Signal strength" /></div>
      <div className="content-grid"><article className="panel chart-panel"><div className="panel-heading"><div><p className="eyebrow">PRICE ACTION CHART</p><h3>Open, high, low and close</h3></div><span className="legend"><i className="line-orange" /> Candle <i className="line-green" /> 20D MA</span></div><div className="timeframe-row"><span>Timeframe</span><div className="timeframe-options">{['1M', '3M', '6M', '1Y', '2Y'].map((option) => <button key={option} className={timeframe === option ? 'active' : ''} onClick={() => changeTimeframe(option)} disabled={loading}>{option}</button>)}</div></div><div className="chart"><CandlestickChart data={technical.chart} /></div></article>
        <article className="panel signal-panel"><div className="panel-heading"><div><p className="eyebrow">TECHNICAL CHECK</p><h3>What is confirming it?</h3></div><ShieldCheck size={22} color="#4d8b70" /></div><div className="checks">{technical.confirmations.map((item) => <div className="check" key={item.label}><span className={item.passed ? 'check-dot passed' : 'check-dot'}>{item.passed ? '✓' : '–'}</span><span>{item.label}</span></div>)}</div><div className="level-list"><div><span>Support</span><b>₹{formatNumber(technical.support)}</b></div><div><span>Resistance</span><b>₹{formatNumber(technical.resistance)}</b></div></div></article></div>
      <article className="panel fundamentals"><div className="panel-heading"><div><p className="eyebrow">FUNDAMENTAL SNAPSHOT</p><h3>Quality at a glance</h3></div><span className="snapshot-label">{result.fundamental.recommendation}</span></div><div className="fundamental-grid"><Metric label="P/E ratio" value={formatNumber(result.fundamental.metrics.pe)} hint="Trailing" /><Metric label="P/B ratio" value={formatNumber(result.fundamental.metrics.pb)} hint="Price to book" /><Metric label="Return on equity" value={result.fundamental.metrics.roe == null ? '--' : `${formatNumber(result.fundamental.metrics.roe * 100)}%`} hint="Profitability" /><Metric label="Current ratio" value={formatNumber(result.fundamental.metrics.currentRatio)} hint="Liquidity" /></div></article>
    </section>}
    <footer><span>Mind Market AI</span><span>Research support, not investment advice.</span></footer>
  </main>
}

export default App

createRoot(document.getElementById('root')).render(<App />)
