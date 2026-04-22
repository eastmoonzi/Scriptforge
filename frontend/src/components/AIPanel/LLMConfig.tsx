'use client'

import { useStore } from '@/lib/store'
import { PROVIDERS, getProvider } from '@/lib/providers'

export default function LLMConfig() {
  const { provider, apiKey, model, customBaseUrl } = useStore()

  return (
    <div className="space-y-2 p-3 border-b border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50 shrink-0">
      <div className="flex gap-2">
        <div className="flex-1 min-w-0">
          <select
            className="w-full text-xs bg-white dark:bg-zinc-900 rounded px-2 py-1 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
            value={provider}
            onChange={(e) => useStore.getState().setProvider(e.target.value)}
          >
            {PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-0">
          {(() => {
            const config = getProvider(provider)
            if (!config || config.id === 'custom') {
              return (
                <input
                  type="text"
                  className="w-full text-xs bg-white dark:bg-zinc-900 rounded px-2 py-1 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
                  placeholder="模型名称"
                  value={model}
                  onChange={(e) => useStore.getState().setModel(e.target.value)}
                />
              )
            }
            return (
              <select
                className="w-full text-xs bg-white dark:bg-zinc-900 rounded px-2 py-1 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
                value={model}
                onChange={(e) => useStore.getState().setModel(e.target.value)}
              >
                {config.models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            )
          })()}
        </div>
      </div>
      <div>
        <input
          type="password"
          className="w-full text-xs bg-white dark:bg-zinc-900 rounded px-2 py-1 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
          placeholder={getProvider(provider)?.apiKeyPlaceholder ?? 'API Key'}
          value={apiKey}
          onChange={(e) => useStore.getState().setApiKey(e.target.value)}
        />
      </div>
      {provider === 'custom' && (
        <div>
          <input
            type="text"
            className="w-full text-xs bg-white dark:bg-zinc-900 rounded px-2 py-1 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
            placeholder="API Base URL"
            value={customBaseUrl}
            onChange={(e) => useStore.getState().setCustomBaseUrl(e.target.value)}
          />
        </div>
      )}
    </div>
  )
}
