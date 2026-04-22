'use client'

import { useState, useEffect } from 'react'
import { useStore } from '@/lib/store'
import { notify } from '@/lib/notify'
import { isTauri } from '@/lib/api'
import { listProjects, getProject, createProject, saveProject } from '@/lib/api'
import {
  exportFountainFile,
  exportPdfFile,
  exportFdxFile,
  importFountainFile,
} from '@/lib/exportHelpers'
import { Cloud, X } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'

export default function MenuBar() {
  const { projectTitle, setProjectTitle, isDarkMode, toggleDarkMode, projectId, isSaved, setShowHelp } = useStore()
  const [showProjectList, setShowProjectList] = useState(false)
  const [projectList, setProjectList] = useState<Array<{ id: string; name?: string; title?: string; updated_at: string }>>([])

  // Update native window title in Tauri
  useEffect(() => {
    if (isTauri()) {
      const prefix = isSaved ? '' : '* '
      import('@tauri-apps/api/window').then(({ getCurrentWindow }) => {
        getCurrentWindow().setTitle(`${prefix}${projectTitle} - Scriptforge`)
      }).catch(() => {})
    }
  }, [projectTitle, isSaved])
  const handleNewProject = () => {
    useStore.getState().setFountainContent('')
    useStore.getState().setProjectTitle('未命名剧本')
    useStore.getState().setProjectAuthor('')
    useStore.getState().setProjectId(null)
    useStore.getState().setIsSaved(true)
    notify('新建项目', 'info')
  }

  const handleSaveToServer = async () => {
    const store = useStore.getState()
    try {
      store.setStatusMessage('正在保存到服务器...')
      if (store.projectId) {
        await saveProject(store.projectId, {
          title: store.projectTitle,
          author: store.projectAuthor,
          content: store.fountainContent,
        })
      } else {
        const result = await createProject({
          title: store.projectTitle,
          author: store.projectAuthor,
          content: store.fountainContent,
        })
        store.setProjectId(result.id)
      }
      store.setIsSaved(true)
      notify('已保存到服务器', 'success')
    } catch {
      notify('保存失败，请确认后端已启动', 'error')
    }
  }

  const handleLoadFromServer = async () => {
    try {
      const projects = await listProjects()
      setProjectList(projects as Array<{ id: string; name?: string; title?: string; updated_at: string }>)
      setShowProjectList(true)
    } catch {
      notify('加载项目列表失败', 'error')
    }
  }

  const handleSelectProject = async (id: string) => {
    try {
      const project = await getProject(id) as { id: string; name?: string; title?: string; content: string; author?: string }
      const store = useStore.getState()
      store.setProjectId(project.id)
      store.setProjectTitle(project.name || project.title || '未命名剧本')
      if (project.author) store.setProjectAuthor(project.author)
      store.setFountainContent(project.content || '')
      store.setIsSaved(true)
      notify('项目已加载', 'success')
      setShowProjectList(false)
    } catch {
      notify('加载项目失败', 'error')
    }
  }

  return (
    <>
      <div className="h-10 flex items-center justify-between px-4 border-b border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 select-none shrink-0">
        {/* Left: project title + menus */}
        <div className="flex items-center gap-4">
          <span className="font-bold text-sm tracking-tight text-blue-600 dark:text-blue-400">
            Scriptforge
          </span>
          <div className="flex items-center gap-1 text-xs text-zinc-600 dark:text-zinc-400">
            <MenuDropdown
              label="文件"
              items={[
                { label: '新建项目', action: handleNewProject },
                { label: '导入 .fountain', action: importFountainFile },
                { label: '导出 .fountain', action: exportFountainFile },
                { label: '导出 PDF (打印)', action: exportPdfFile },
                { label: '导出 .fdx (Final Draft)', action: exportFdxFile },
                { label: '──────────', action: () => {} },
                { label: '保存到服务器', action: handleSaveToServer },
                { label: '从服务器加载...', action: handleLoadFromServer },
              ]}
            />
            <MenuDropdown
              label="视图"
              items={[
                { label: isDarkMode ? '浅色主题' : '深色主题', action: toggleDarkMode },
              ]}
            />
            <MenuDropdown
              label="帮助"
              items={[
                { label: '格式与快捷键  F1', action: () => setShowHelp(true) },
              ]}
            />
          </div>
        </div>

        {/* Center: editable title */}
        <div className="flex items-center gap-2">
          <input
            className="text-sm font-medium text-center bg-transparent border-none outline-none w-48 text-zinc-700 dark:text-zinc-300 focus:ring-1 focus:ring-blue-400 rounded px-2"
            value={projectTitle}
            onChange={(e) => setProjectTitle(e.target.value)}
          />
          {projectId && (
            <span title="已保存到服务器"><Cloud className="w-4 h-4 text-zinc-400" /></span>
          )}
        </div>

        {/* Right: placeholder */}
        <div className="w-24" />
      </div>

      {/* Project list modal */}
      {showProjectList && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => setShowProjectList(false)}>
          <div className="bg-white dark:bg-zinc-800 rounded-lg shadow-xl w-96 max-h-[60vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 flex justify-between items-center">
              <h2 className="text-sm font-semibold">从服务器加载项目</h2>
              <button className="text-zinc-400 hover:text-zinc-600" onClick={() => setShowProjectList(false)}><X className="w-4 h-4" /></button>
            </div>
            <div className="overflow-y-auto max-h-[50vh]">
              {projectList.length === 0 ? (
                <p className="text-sm text-zinc-400 p-4 text-center">暂无保存的项目</p>
              ) : (
                projectList.map((p) => (
                  <button
                    key={p.id}
                    className="w-full text-left px-4 py-3 hover:bg-zinc-100 dark:hover:bg-zinc-700 border-b border-zinc-100 dark:border-zinc-700 last:border-0"
                    onClick={() => handleSelectProject(p.id)}
                  >
                    <div className="text-sm font-medium">{p.name || p.title || '未命名剧本'}</div>
                    <div className="text-xs text-zinc-400">{new Date(p.updated_at).toLocaleString('zh-CN')}</div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function MenuDropdown({ label, items }: { label: string; items: Array<{ label: string; action: () => void }> }) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="px-2 py-1 rounded hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors outline-none">
          {label}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md shadow-lg py-1 min-w-[160px] z-50"
          sideOffset={2}
          align="start"
        >
          {items.map((item, idx) => (
            item.label.startsWith('──') ? (
              <DropdownMenu.Separator key={idx} className="h-px bg-zinc-200 dark:bg-zinc-700 my-1" />
            ) : (
              <DropdownMenu.Item
                key={item.label}
                className="text-xs px-3 py-1.5 outline-none cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700 data-[highlighted]:bg-zinc-100 dark:data-[highlighted]:bg-zinc-700 transition-colors"
                onSelect={item.action}
              >
                {item.label}
              </DropdownMenu.Item>
            )
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
