"use client";

import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  TrendingDown,
  Info,
  AlertTriangle,
  Calendar,
  DollarSign,
  Globe,
  Building,
  Activity,
  Download,
  RefreshCw,
  Sliders,
  Search,
  CheckCircle2,
  FileSpreadsheet
} from "lucide-react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from "recharts";

interface CompanyInfo {
  name: string;
  sector: string;
  exchange: string;
  market_cap: number | null;
  pe_ratio: number | null;
  current_price: number | null;
  currency: string;
  symbol: string;
}

interface HistoricalDataRecord {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20: number;
  sma50: number;
  ema20: number;
  rsi14: number;
}

interface ForecastRecord {
  day: number;
  date: string;
  prediction: number;
}

interface PredictData {
  tomorrow_prediction: number;
  expected_growth_pct: number;
  metrics: {
    available: boolean;
    rmse: number;
    mae: number;
    mape: number;
    accuracy: number;
  };
  forecast: ForecastRecord[];
}

export default function Home() {
  const [isMounted, setIsMounted] = useState(false);

  // Lists of stocks
  const [stocksList, setStocksList] = useState<{
    predefined: Record<string, string>;
    local_scrips: Record<string, string>;
    local_indices: string[];
  }>({
    predefined: {},
    local_scrips: {},
    local_indices: []
  });

  // Inputs
  const [selectionMode, setSelectionMode] = useState<string>("Predefined US Stocks");
  const [selectedTicker, setSelectedTicker] = useState<string>("AAPL");
  const [customTickerInput, setCustomTickerInput] = useState<string>("TSLA");
  
  // Date states
  const [isLocal, setIsLocal] = useState<boolean>(false);
  const [minDate, setMinDate] = useState<string>("2010-01-01");
  const [maxDate, setMaxDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [startDate, setStartDate] = useState<string>("2021-01-01");
  const [endDate, setEndDate] = useState<string>(new Date().toISOString().split("T")[0]);

  // UI state
  const [loadingStocks, setLoadingStocks] = useState<boolean>(true);
  const [loadingData, setLoadingData] = useState<boolean>(false);
  const [loadingPrediction, setLoadingPrediction] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [predictErrorMsg, setPredictErrorMsg] = useState<string | null>(null);

  // Data states
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo | null>(null);
  const [historicalData, setHistoricalData] = useState<HistoricalDataRecord[]>([]);
  const [predictionData, setPredictionData] = useState<PredictData | null>(null);

  // Multi-step options
  const [forecastLen, setForecastLen] = useState<number>(30);

  // Technical toggles
  const [showSma20, setShowSma20] = useState<boolean>(true);
  const [showSma50, setShowSma50] = useState<boolean>(false);
  const [showEma20, setShowEma20] = useState<boolean>(false);

  // Initialize
  useEffect(() => {
    setIsMounted(true);
    fetchStocks();
  }, []);

  // Whenever selectionMode changes, reset selectedTicker to a default
  useEffect(() => {
    if (selectionMode === "Predefined US Stocks") {
      setSelectedTicker("AAPL");
    } else if (selectionMode === "Local NSE Scrips (Datasets)") {
      const keys = Object.keys(stocksList.local_scrips);
      if (keys.length > 0) setSelectedTicker(keys[0]);
    } else if (selectionMode === "Local NSE Indices (Datasets)") {
      if (stocksList.local_indices.length > 0) setSelectedTicker(stocksList.local_indices[0]);
    } else if (selectionMode === "Local S&P 500 Index (Datasets)") {
      setSelectedTicker("SPX");
    } else {
      setSelectedTicker(customTickerInput);
    }
  }, [selectionMode, stocksList]);

  // Whenever selectedTicker or customTickerInput changes, update range constraints and load historical
  useEffect(() => {
    const activeTicker = getActiveTicker();
    if (activeTicker) {
      updateDateRange(activeTicker);
    }
  }, [selectedTicker, customTickerInput, selectionMode]);

  // Helper to fetch list of stocks
  const fetchStocks = async () => {
    try {
      setLoadingStocks(true);
      const res = await fetch("/api/stocks");
      if (!res.ok) throw new Error("Failed to load available stocks.");
      const data = await res.json();
      setStocksList(data);
    } catch (err: any) {
      console.error(err);
      setErrorMsg("Error loading stock list. Please refresh.");
    } finally {
      setLoadingStocks(false);
    }
  };

  // Helper to resolve the ticker currently selected
  const getActiveTicker = () => {
    if (selectionMode === "Search Custom Ticker (Online)") {
      return customTickerInput.trim().toUpperCase();
    }
    return selectedTicker;
  };

  // Update date boundaries dynamically
  const updateDateRange = async (ticker: string) => {
    try {
      setErrorMsg(null);
      const res = await fetch(`/api/stock-range?ticker=${ticker}`);
      if (!res.ok) throw new Error("Failed to get stock date range.");
      const data = await res.json();
      setIsLocal(data.is_local);
      setMinDate(data.min_date);
      setMaxDate(data.max_date);
      setStartDate(data.default_start);
      setEndDate(data.max_date);
    } catch (err: any) {
      console.error(err);
    }
  };

  // Fetch historical data
  const handleLoadData = async () => {
    const ticker = getActiveTicker();
    if (!ticker) {
      setErrorMsg("Please enter/select a valid stock ticker.");
      return;
    }

    try {
      setLoadingData(true);
      setErrorMsg(null);
      setPredictionData(null); // Reset predictions
      setPredictErrorMsg(null);

      const res = await fetch("/api/historical", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: ticker,
          start_date: startDate,
          end_date: endDate
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to fetch stock data.");
      }

      const data = await res.json();
      setCompanyInfo(data.company_info);
      setHistoricalData(data.historical_data);
    } catch (err: any) {
      setHistoricalData([]);
      setCompanyInfo(null);
      setErrorMsg(err.message || "An unexpected error occurred.");
    } finally {
      setLoadingData(false);
    }
  };

  // Run ML Prediction
  const handlePredict = async () => {
    const ticker = getActiveTicker();
    if (!ticker || historicalData.length === 0) return;

    try {
      setLoadingPrediction(true);
      setPredictErrorMsg(null);
      setPredictionData(null);

      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: ticker,
          start_date: startDate,
          end_date: endDate,
          forecast_len: forecastLen
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Prediction failed.");
      }

      const data = await res.json();
      setPredictionData(data);
    } catch (err: any) {
      setPredictErrorMsg(err.message || "Prediction execution error.");
    } finally {
      setLoadingPrediction(false);
    }
  };

  // Load historical automatically on click of Load Button or when ticker loaded
  useEffect(() => {
    if (getActiveTicker()) {
      handleLoadData();
    }
  }, [startDate, endDate, selectedTicker, customTickerInput, selectionMode]);

  // Formatter helpers
  const getCurrencySymbol = () => {
    return companyInfo?.currency === "INR" ? "₹" : "$";
  };

  const formatLargeNum = (num: number | null) => {
    if (num === null) return "N/A";
    const symbol = getCurrencySymbol();
    if (num >= 1e12) return `${symbol}${(num / 1e12).toFixed(2)}T`;
    if (num >= 1e9) return `${symbol}${(num / 1e9).toFixed(2)}B`;
    if (num >= 1e6) return `${symbol}${(num / 1e6).toFixed(2)}M`;
    return `${symbol}${num.toLocaleString()}`;
  };

  const formatVolume = (num: number) => {
    if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
    if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
    return num.toString();
  };

  // Prepare combined chart data for historical + forecast
  const getCombinedChartData = () => {
    if (!historicalData.length) return [];
    
    // Last 90 days for clean visual context
    const subset = historicalData.slice(-90).map(d => ({
      date: d.date,
      close: d.close,
      type: "Historical"
    }));

    if (!predictionData || !predictionData.forecast.length) {
      return subset;
    }

    // Connect the last historical point with the first forecast point
    const forecastPoints = predictionData.forecast.map((f, i) => ({
      date: f.date,
      forecast: f.prediction,
      type: "Forecast"
    }));

    // Insert connecting line point
    const lastHist = subset[subset.length - 1];
    const connectingPoint = {
      date: lastHist.date,
      forecast: lastHist.close,
      type: "Forecast"
    };

    return [...subset, connectingPoint, ...forecastPoints];
  };

  const downloadForecastCSV = () => {
    if (!predictionData || !companyInfo) return;
    const headers = "Day,Date,Prediction\n";
    const rows = predictionData.forecast
      .map(f => `${f.day},${f.date},${f.prediction.toFixed(2)}`)
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.setAttribute("href", url);
    a.setAttribute("download", `${companyInfo.symbol}_forecast_${forecastLen}days.csv`);
    a.click();
  };

  // Compute 52w high and low
  const get52wHigh = () => {
    if (!historicalData.length) return 0;
    return Math.max(...historicalData.slice(-252).map(d => d.high));
  };

  const get52wLow = () => {
    if (!historicalData.length) return 0;
    return Math.min(...historicalData.slice(-252).map(d => d.low));
  };

  const getLastRow = () => {
    return historicalData[historicalData.length - 1];
  };

  const getPrevClose = () => {
    if (historicalData.length < 2) return 0;
    return historicalData[historicalData.length - 2].close;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20 text-emerald-400">
            <Activity className="h-6 w-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
              Stock Prediction Engine
            </h1>
            <p className="text-xs text-slate-400">Next.js & LSTM serverless inference app</p>
          </div>
        </div>
        <div className="text-xs text-slate-500 flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800">
          <Globe className="h-3.5 w-3.5" />
          Vercel Serverless Ready
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 max-w-[1600px] w-full mx-auto p-6 flex flex-col lg:flex-row gap-6">
        {/* Sidebar / Left Column */}
        <aside className="w-full lg:w-80 flex flex-col gap-6 shrink-0">
          <div className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80 backdrop-blur-sm flex flex-col gap-5">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Sliders className="h-4 w-4 text-emerald-400" />
              Controls & Search
            </h2>

            {/* Selection Mode */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-slate-400">Search Mode</label>
              <div className="flex flex-col gap-1.5">
                {[
                  "Predefined US Stocks",
                  "Local NSE Scrips (Datasets)",
                  "Local NSE Indices (Datasets)",
                  "Local S&P 500 Index (Datasets)",
                  "Search Custom Ticker (Online)"
                ].map(mode => (
                  <button
                    key={mode}
                    onClick={() => setSelectionMode(mode)}
                    className={`text-left text-xs px-3.5 py-2.5 rounded-xl border transition-all duration-200 ${
                      selectionMode === mode
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 font-medium"
                        : "bg-slate-950/40 border-transparent hover:border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            {/* Selector Dropdown / Custom Ticker */}
            <div className="flex flex-col gap-2 border-t border-slate-800/50 pt-4">
              <label className="text-xs font-semibold text-slate-400">Select Symbol</label>
              {loadingStocks ? (
                <div className="flex items-center gap-2 text-xs text-slate-500 py-2">
                  <RefreshCw className="h-3 w-3 animate-spin" /> Loading list...
                </div>
              ) : (
                <>
                  {selectionMode === "Predefined US Stocks" && (
                    <select
                      value={selectedTicker}
                      onChange={e => setSelectedTicker(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500/60"
                    >
                      {Object.entries(stocksList.predefined).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  )}

                  {selectionMode === "Local NSE Scrips (Datasets)" && (
                    <select
                      value={selectedTicker}
                      onChange={e => setSelectedTicker(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500/60"
                    >
                      {Object.entries(stocksList.local_scrips).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  )}

                  {selectionMode === "Local NSE Indices (Datasets)" && (
                    <select
                      value={selectedTicker}
                      onChange={e => setSelectedTicker(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500/60"
                    >
                      {stocksList.local_indices.map(idx => (
                        <option key={idx} value={idx}>
                          {idx}
                        </option>
                      ))}
                    </select>
                  )}

                  {selectionMode === "Local S&P 500 Index (Datasets)" && (
                    <div className="bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-300">
                      S&P 500 Index (SPX)
                    </div>
                  )}

                  {selectionMode === "Search Custom Ticker (Online)" && (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={customTickerInput}
                        onChange={e => setCustomTickerInput(e.target.value.toUpperCase())}
                        placeholder="e.g. TSLA, NVDA"
                        className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500/60 w-full"
                      />
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Date Pickers */}
            <div className="flex flex-col gap-3 border-t border-slate-800/50 pt-4">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-400">📅 Date Range</label>
                {isLocal && (
                  <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded border border-indigo-500/20">
                    Local Dataset Limits
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-slate-500 uppercase">Start</span>
                  <input
                    type="date"
                    value={startDate}
                    min={minDate}
                    max={maxDate}
                    onChange={e => setStartDate(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500/60"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-slate-500 uppercase">End</span>
                  <input
                    type="date"
                    value={endDate}
                    min={minDate}
                    max={maxDate}
                    onChange={e => setEndDate(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500/60"
                  />
                </div>
              </div>
            </div>

            {/* Predict Button */}
            <div className="border-t border-slate-800/50 pt-4 flex flex-col gap-3">
              <button
                onClick={handlePredict}
                disabled={loadingPrediction || loadingData || historicalData.length === 0}
                className="w-full bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 font-semibold text-sm py-3 px-4 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-emerald-500/10"
              >
                {loadingPrediction ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" /> Running LSTM...
                  </>
                ) : (
                  <>
                    <TrendingUp className="h-4 w-4" /> Predict Stock Price
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Model Note */}
          <div className="bg-slate-900/30 p-4 rounded-2xl border border-slate-800/50 flex flex-col gap-2">
            <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-indigo-400" />
              Generalization Notice
            </h3>
            <p className="text-[11px] leading-relaxed text-slate-400">
              The core LSTM model was trained on historical Apple (AAPL) data. For other stocks, prices are scaled
              locally using a fitted MinMaxScaler. Predictions assume relative trend mapping.
            </p>
          </div>
        </aside>

        {/* Content Area */}
        <main className="flex-1 flex flex-col gap-6 overflow-hidden">
          {/* Messages & Errors */}
          {errorMsg && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold">Error Loading Data</h4>
                <p className="text-xs mt-1 text-red-400/80">{errorMsg}</p>
              </div>
            </div>
          )}

          {/* Company Header & Stats */}
          {companyInfo && historicalData.length > 0 && (
            <div className="bg-slate-900/40 p-6 rounded-2xl border border-slate-800/80 backdrop-blur-sm flex flex-col gap-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs bg-slate-800 text-slate-300 font-semibold px-2 py-0.5 rounded border border-slate-700">
                      {companyInfo.exchange}
                    </span>
                    <h2 className="text-2xl font-bold tracking-tight text-white">
                      {companyInfo.name}
                    </h2>
                    <span className="text-slate-400">({companyInfo.symbol})</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Sector: <span className="text-slate-200">{companyInfo.sector}</span>
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-extrabold text-white tracking-tight">
                    {getCurrencySymbol()}{getLastRow().close.toFixed(2)}
                  </div>
                  <div
                    className={`text-xs font-semibold mt-1 flex items-center justify-end gap-1 ${
                      getLastRow().close - getPrevClose() >= 0 ? "text-emerald-400" : "text-rose-400"
                    }`}
                  >
                    {getLastRow().close - getPrevClose() >= 0 ? (
                      <TrendingUp className="h-3.5 w-3.5" />
                    ) : (
                      <TrendingDown className="h-3.5 w-3.5" />
                    )}
                    {(getLastRow().close - getPrevClose()).toFixed(2)} (Daily Change)
                  </div>
                </div>
              </div>

              {/* Grid Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 border-t border-slate-800/60 pt-6">
                <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/50">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">
                    52-Week High
                  </span>
                  <p className="text-lg font-bold text-slate-200 mt-1">
                    {getCurrencySymbol()}{get52wHigh().toFixed(2)}
                  </p>
                </div>
                <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/50">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">
                    52-Week Low
                  </span>
                  <p className="text-lg font-bold text-slate-200 mt-1">
                    {getCurrencySymbol()}{get52wLow().toFixed(2)}
                  </p>
                </div>
                <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/50">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">
                    Daily Volume
                  </span>
                  <p className="text-lg font-bold text-slate-200 mt-1">
                    {formatVolume(getLastRow().volume)}
                  </p>
                </div>
                <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/50">
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">
                    Market Cap
                  </span>
                  <p className="text-lg font-bold text-slate-200 mt-1">
                    {formatLargeNum(companyInfo.market_cap)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Machine Learning Predictions Block */}
          {loadingPrediction && (
            <div className="bg-slate-900/20 border border-slate-800 p-8 rounded-2xl flex flex-col items-center justify-center gap-3 text-slate-400">
              <RefreshCw className="h-8 w-8 text-emerald-400 animate-spin" />
              <p className="text-sm font-medium">Running Autoregressive Forecast & Accuracy Evaluations...</p>
            </div>
          )}

          {predictErrorMsg && (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 p-4 rounded-xl flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              <p className="text-xs">{predictErrorMsg}</p>
            </div>
          )}

          {predictionData && companyInfo && (
            <div className="bg-slate-900/40 p-6 rounded-2xl border border-slate-850 backdrop-blur-sm flex flex-col gap-6">
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                <Sliders className="h-5 w-5 text-emerald-400" />
                LSTM Machine Learning Predictions
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Prediction Metric */}
                <div className="bg-slate-950/60 p-5 rounded-xl border border-slate-800 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">
                      Tomorrow's Prediction
                    </span>
                    <p className="text-3xl font-black text-emerald-400 tracking-tight mt-1.5">
                      {getCurrencySymbol()}{predictionData.tomorrow_prediction.toFixed(2)}
                    </p>
                  </div>
                  <div className="mt-3 flex items-center gap-1 text-xs">
                    {predictionData.expected_growth_pct >= 0 ? (
                      <span className="text-emerald-400 font-semibold">
                        +{predictionData.expected_growth_pct.toFixed(2)}%
                      </span>
                    ) : (
                      <span className="text-rose-400 font-semibold">
                        {predictionData.expected_growth_pct.toFixed(2)}%
                      </span>
                    )}
                    <span className="text-slate-400">expected change</span>
                  </div>
                </div>

                {/* Accuracy Score */}
                <div className="bg-slate-950/60 p-5 rounded-xl border border-slate-800 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">
                      Forecast Accuracy
                    </span>
                    <p className="text-3xl font-black text-slate-100 tracking-tight mt-1.5">
                      {predictionData.metrics.available
                        ? `${predictionData.metrics.accuracy.toFixed(2)}%`
                        : "N/A"}
                    </p>
                  </div>
                  <span className="text-[11px] text-slate-400 mt-3">
                    Calculated as 100 - MAPE on test evaluation slice
                  </span>
                </div>

                {/* Evaluation Metrics */}
                <div className="bg-slate-950/60 p-5 rounded-xl border border-slate-800 flex flex-col justify-between text-xs gap-3">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">
                    Model Performance (Test Set)
                  </span>
                  {predictionData.metrics.available ? (
                    <div className="grid grid-cols-2 gap-3 text-slate-300 font-medium">
                      <div>
                        <span className="text-slate-500 block text-[9px] uppercase">RMSE</span>
                        {predictionData.metrics.rmse.toFixed(4)}
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[9px] uppercase">MAE</span>
                        {predictionData.metrics.mae.toFixed(4)}
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500 block text-[9px] uppercase">MAPE (Error)</span>
                        {predictionData.metrics.mape.toFixed(2)}%
                      </div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-500 leading-normal">
                      Not enough data points to compute evaluations. Set a wider date range to test accuracy.
                    </p>
                  )}
                </div>
              </div>

              {/* Combined Chart & Forecast Table */}
              <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 border-t border-slate-800/60 pt-6">
                {/* Line Chart */}
                <div className="xl:col-span-3 h-80 flex flex-col">
                  <span className="text-xs font-bold text-slate-400 mb-4 block">
                    Historical Trend vs. Future Forecast
                  </span>
                  <div className="flex-1 w-full text-xs">
                    {isMounted && (
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={getCombinedChartData()}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="date" stroke="#64748b" />
                          <YAxis stroke="#64748b" domain={["auto", "auto"]} />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#020617", borderColor: "#334155" }}
                            labelStyle={{ fontWeight: "bold" }}
                          />
                          <Legend />
                          <Line
                            type="monotone"
                            dataKey="close"
                            name="Historical Close"
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={false}
                          />
                          <Line
                            type="monotone"
                            dataKey="forecast"
                            name="Forecast"
                            stroke="#ec4899"
                            strokeWidth={2.5}
                            strokeDasharray="5 5"
                            dot={false}
                          />
                          {/* Split Reference Line */}
                          {historicalData.length > 0 && (
                            <ReferenceLine
                              x={getLastRow().date}
                              stroke="#e2e8f0"
                              strokeWidth={1.5}
                              strokeDasharray="3 3"
                              label={{
                                value: "Forecast Start",
                                position: "top",
                                fill: "#e2e8f0",
                                fontSize: 10
                              }}
                            />
                          )}
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

                {/* Forecast Table */}
                <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase">
                      Forecast Horizon
                    </span>
                    <select
                      value={forecastLen}
                      onChange={e => setForecastLen(Number(e.target.value))}
                      className="bg-slate-900 border border-slate-850 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none"
                    >
                      <option value={7}>7 Days</option>
                      <option value={30}>30 Days</option>
                      <option value={90}>90 Days</option>
                    </select>
                  </div>

                  <div className="flex-1 overflow-y-auto max-h-56 scrollbar-thin text-xs border border-slate-800/80 rounded-lg">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-900 border-b border-slate-850 text-[10px] text-slate-500 uppercase font-semibold">
                          <th className="py-2.5 px-3">Day</th>
                          <th className="py-2.5 px-3">Date</th>
                          <th className="py-2.5 px-3 text-right">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {predictionData.forecast.map(row => (
                          <tr key={row.day} className="border-b border-slate-900 hover:bg-slate-900/30">
                            <td className="py-2 px-3 text-slate-400">{row.day}</td>
                            <td className="py-2 px-3 font-medium">{row.date}</td>
                            <td className="py-2 px-3 text-right font-semibold text-emerald-400">
                              {getCurrencySymbol()}{row.prediction.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <button
                    onClick={downloadForecastCSV}
                    className="w-full bg-slate-800 hover:bg-slate-700 hover:text-slate-100 text-slate-300 font-semibold text-xs py-2.5 px-3 rounded-lg border border-slate-700/80 transition-all duration-200 flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Download className="h-3.5 w-3.5" /> Download CSV
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Historical Price & Indicator Analysis */}
          {historicalData.length > 0 && companyInfo && (
            <div className="bg-slate-900/40 p-6 rounded-2xl border border-slate-850 backdrop-blur-sm flex flex-col gap-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/60 pb-4">
                <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                  <Sliders className="h-5 w-5 text-emerald-400" />
                  Technical Analysis & Indicators
                </h2>
                {/* Indicators checkboxes */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showSma20}
                      onChange={() => setShowSma20(!showSma20)}
                      className="accent-emerald-500"
                    />
                    SMA 20
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showSma50}
                      onChange={() => setShowSma50(!showSma50)}
                      className="accent-emerald-500"
                    />
                    SMA 50
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showEma20}
                      onChange={() => setShowEma20(!showEma20)}
                      className="accent-emerald-500"
                    />
                    EMA 20
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
                {/* Main chart */}
                <div className="xl:col-span-3 flex flex-col gap-6">
                  {/* Prices Composed Chart */}
                  <div className="h-72 w-full text-xs">
                    {isMounted && (
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={historicalData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="date" stroke="#64748b" />
                          <YAxis stroke="#64748b" domain={["auto", "auto"]} />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#020617", borderColor: "#334155" }}
                            labelStyle={{ fontWeight: "bold" }}
                          />
                          <Legend />
                          <Line
                            type="monotone"
                            dataKey="close"
                            name="Close Price"
                            stroke="#3b82f6"
                            strokeWidth={2}
                            dot={false}
                          />
                          {showSma20 && (
                            <Line
                              type="monotone"
                              dataKey="sma20"
                              name="SMA 20"
                              stroke="#f59e0b"
                              strokeWidth={1.2}
                              strokeDasharray="4 4"
                              dot={false}
                            />
                          )}
                          {showSma50 && (
                            <Line
                              type="monotone"
                              dataKey="sma50"
                              name="SMA 50"
                              stroke="#10b981"
                              strokeWidth={1.2}
                              strokeDasharray="6 6"
                              dot={false}
                            />
                          )}
                          {showEma20 && (
                            <Line
                              type="monotone"
                              dataKey="ema20"
                              name="EMA 20"
                              stroke="#ef4444"
                              strokeWidth={1.2}
                              strokeDasharray="3 1"
                              dot={false}
                            />
                          )}
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                  </div>

                  {/* Volume Chart */}
                  <div className="h-32 w-full text-xs">
                    {isMounted && (
                      <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={historicalData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="date" stroke="#64748b" />
                          <YAxis stroke="#64748b" />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#020617", borderColor: "#334155" }}
                          />
                          <Bar dataKey="volume" name="Volume" fill="#06b6d4" />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

                {/* Table details & summary */}
                <div className="flex flex-col gap-5">
                  <div className="bg-slate-950/60 p-4.5 rounded-xl border border-slate-800/80 flex flex-col gap-4 text-xs">
                    <span className="font-bold text-slate-400 uppercase">Technical Summary</span>
                    <div className="flex flex-col gap-2.5 font-medium text-slate-300">
                      <div className="flex justify-between">
                        <span className="text-slate-500">SMA 20:</span>
                        <span>{getCurrencySymbol()}{getLastRow().sma20.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">SMA 50:</span>
                        <span>{getCurrencySymbol()}{getLastRow().sma50.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">EMA 20:</span>
                        <span>{getCurrencySymbol()}{getLastRow().ema20.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between border-t border-slate-850 pt-2.5">
                        <span className="text-slate-500">RSI 14:</span>
                        <span className={getLastRow().rsi14 > 70 ? "text-amber-400" : getLastRow().rsi14 < 30 ? "text-emerald-400" : "text-slate-300"}>
                          {getLastRow().rsi14.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <div className="mt-1 border-t border-slate-850 pt-3">
                      {getLastRow().rsi14 > 70 ? (
                        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 px-3 py-2 rounded-lg text-[11px] leading-relaxed flex gap-2">
                          <AlertTriangle className="h-4 w-4 shrink-0" />
                          <span>RSI indicates Overbought (&gt; 70)</span>
                        </div>
                      ) : getLastRow().rsi14 < 30 ? (
                        <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-2 rounded-lg text-[11px] leading-relaxed flex gap-2">
                          <CheckCircle2 className="h-4 w-4 shrink-0" />
                          <span>RSI indicates Oversold (&lt; 30)</span>
                        </div>
                      ) : (
                        <div className="bg-slate-800/40 border border-slate-800/80 text-slate-400 px-3 py-2 rounded-lg text-[11px] leading-relaxed flex gap-2">
                          <Info className="h-4 w-4 shrink-0" />
                          <span>RSI indicates Neutral Range (30-70)</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Recent table */}
                  <div className="bg-slate-950/40 rounded-xl border border-slate-800 flex-1 overflow-hidden flex flex-col">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3.5 py-3 border-b border-slate-850 block">
                      Recent Historical Records
                    </span>
                    <div className="flex-1 overflow-y-auto max-h-48 text-[11px]">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="bg-slate-900 border-b border-slate-850 text-[10px] text-slate-500 uppercase font-semibold">
                            <th className="py-2 px-3">Date</th>
                            <th className="py-2 px-3 text-right">Close</th>
                            <th className="py-2 px-3 text-right">RSI</th>
                          </tr>
                        </thead>
                        <tbody>
                          {historicalData.slice(-5).reverse().map(row => (
                            <tr key={row.date} className="border-b border-slate-900 hover:bg-slate-900/30">
                              <td className="py-2 px-3 text-slate-400">{row.date}</td>
                              <td className="py-2 px-3 text-right font-medium">{getCurrencySymbol()}{row.close.toFixed(2)}</td>
                              <td className="py-2 px-3 text-right text-slate-400">{row.rsi14.toFixed(1)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!companyInfo && !loadingData && (
            <div className="flex-1 bg-slate-900/20 border border-slate-800/60 rounded-2xl flex flex-col items-center justify-center p-12 text-slate-400 text-center gap-4">
              <Search className="h-10 w-10 text-slate-600" />
              <div>
                <h3 className="text-base font-semibold text-slate-200">No stock selected</h3>
                <p className="text-xs text-slate-500 max-w-xs mt-1 leading-normal">
                  Use the left controls panel to select a predefined stock or input a custom ticker to load.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
