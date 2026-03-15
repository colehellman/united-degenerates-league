import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '../services/api'
import { extractErrorMessage } from '../utils/errors'

interface BugReportModalProps {
  isOpen: boolean
  onClose: () => void
}

const CATEGORIES = [
  { value: 'ui', label: 'UI / Layout' },
  { value: 'performance', label: 'Performance' },
  { value: 'data', label: 'Data / Scores' },
  { value: 'auth', label: 'Login / Auth' },
  { value: 'other', label: 'Other' },
]

export default function BugReportModal({ isOpen, onClose }: BugReportModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('other')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (data: { title: string; description: string; category: string; page_url: string }) =>
      api.post('/bug-reports', data),
    onSuccess: () => {
      toast.success('Bug report submitted — thanks!')
      handleClose()
    },
    onError: (err: unknown) => {
      setError(extractErrorMessage(err))
    },
  })

  function handleClose() {
    // Reset form state on close so re-opens start fresh
    setTitle('')
    setDescription('')
    setCategory('other')
    setError('')
    onClose()
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    mutation.mutate({
      title,
      description,
      category,
      page_url: window.location.pathname,
    })
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="card w-full max-w-lg">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Report a Bug</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="br-title" className="block text-sm font-medium text-gray-700 mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              id="br-title"
              type="text"
              className="input"
              placeholder="Brief summary of the issue"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              required
            />
          </div>

          <div>
            <label htmlFor="br-category" className="block text-sm font-medium text-gray-700 mb-1">
              Category
            </label>
            <select
              id="br-category"
              className="input"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="br-description" className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-red-500">*</span>
            </label>
            <textarea
              id="br-description"
              className="input min-h-[120px] resize-y"
              placeholder="Steps to reproduce, what you expected, what happened..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={2000}
              required
            />
            <p className="text-xs text-gray-400 mt-1">{description.length}/2000</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-2">
            <button type="button" onClick={handleClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Submitting…' : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
