import { useState } from 'react'

interface FileUploadProps {
  onFileSelect: (file: File) => Promise<void>
  isLoading: boolean
}

export function FileUploader({ onFileSelect, isLoading }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setError(null)

    // Validare tip fișier
    const validTypes = ['application/pdf', 'text/html']
    if (!validTypes.includes(file.type)) {
      setError('⚠️ Doar PDF și HTML sunt suportate')
      return
    }

    // Validare dimensiune (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('⚠️ Fișierul e prea mare (max 10MB)')
      return
    }

    try {
      await onFileSelect(file)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    const files = e.dataTransfer.files
    if (files?.length > 0) {
      handleFile(files[0])
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      handleFile(e.target.files[0])
    }
  }

  return (
    <div
      className={`file-upload ${dragActive ? 'drag-active' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <input
        type="file"
        id="file-input"
        accept=".pdf,.html"
        onChange={handleChange}
        disabled={isLoading}
        className="file-input"
      />
      <label htmlFor="file-input" className="file-label">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <div className="file-text">
          <p className="file-title">📤 Upload Bank Statement</p>
          <p className="file-hint">PDF sau HTML • Max 10MB</p>
        </div>
      </label>
      {error && <div className="error-message">{error}</div>}
    </div>
  )
}
