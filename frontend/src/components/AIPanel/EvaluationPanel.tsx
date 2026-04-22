'use client'

import { useState } from 'react'
import { useStore } from '@/lib/store'
import { evaluateDialogue, type EvaluateResponse } from '@/lib/api'
import { extractDialogues } from '@/lib/fountain'

function ScoreBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-zinc-500 dark:text-zinc-400 w-8 text-right">{pct}%</span>
    </div>
  )
}

function MetricCard({ title, data }: { title: string; data: Record<string, unknown> }) {
  const score = typeof data.score === 'number' ? data.score : null
  const error = typeof data.error === 'string' ? data.error : null

  return (
    <div className="rounded-md border border-zinc-200 dark:border-zinc-700 p-3 space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-300">{title}</span>
        {score !== null && (
          <span className="text-xs font-mono text-zinc-500">{score.toFixed(2)}</span>
        )}
      </div>
      {error ? (
        <p className="text-xs text-red-400">{error}</p>
      ) : score !== null ? (
        <ScoreBar value={score} />
      ) : null}
      {Object.entries(data)
        .filter(([k]) => k !== 'score' && k !== 'error')
        .map(([k, v]) => (
          <div key={k} className="flex justify-between text-xs text-zinc-400">
            <span>{k}</span>
            <span className="font-mono">{typeof v === 'number' ? v.toFixed(3) : String(v)}</span>
          </div>
        ))}
    </div>
  )
}

export default function EvaluationPanel() {
  const { fountainContent, characters, apiKey, model, provider, customBaseUrl } = useStore()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EvaluateResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const conversations = extractDialogues(fountainContent)

  const handleEvaluate = async () => {
    if (!apiKey) {
      setError('请先设置 API Key')
      return
    }
    if (conversations.length < 2) {
      setError('剧本内容不足，无法评测（需要至少 2 句对白）')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const profiles: Record<string, string> = {}
      for (const c of characters) {
        if (c.personality) profiles[c.name] = c.personality
      }
      const res = await evaluateDialogue({
        conversations,
        character_profiles: Object.keys(profiles).length ? profiles : undefined,
        model,
        provider,
        ...(provider === 'custom' && customBaseUrl ? { base_url: customBaseUrl } : {}),
      })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : '评测失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
        对白质量评测
      </h3>

      <div className="text-xs text-zinc-400 dark:text-zinc-500">
        已解析 {conversations.length} 句对白
        {characters.length > 0 && `，${characters.length} 个角色`}
      </div>

      <button
        className="w-full text-sm bg-indigo-500 hover:bg-indigo-600 text-white rounded-md py-2 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
        onClick={handleEvaluate}
        disabled={loading || conversations.length < 2}
      >
        {loading ? (
          <>
            <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
            评测中...
          </>
        ) : '开始评测'}
      </button>

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}

      {result && (
        <div className="space-y-3">
          {/* 综合评分 */}
          <div className="rounded-md bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 p-3 text-center">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
              {Math.round(result.overall_score * 100)}
            </div>
            <div className="text-xs text-indigo-500 dark:text-indigo-400 mt-0.5">综合评分 / 100</div>
            <ScoreBar value={result.overall_score} />
          </div>

          <MetricCard title="CPD 角色性格偏差" data={result.cpd} />
          <MetricCard title="DE 对白效率" data={result.de} />
          <MetricCard title="OOC 出戏率" data={result.ooc} />

          {Object.keys(result.summary).length > 0 && (
            <div className="rounded-md border border-zinc-200 dark:border-zinc-700 p-3 space-y-1">
              <span className="text-xs font-semibold text-zinc-600 dark:text-zinc-300">评测摘要</span>
              {Object.entries(result.summary).map(([k, v]) => (
                <div key={k} className="text-xs text-zinc-400">{k}: {String(v)}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
