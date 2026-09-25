import {
  useRef,
  useState,
} from 'react'

import type {
  Application,
} from './api'


type RecorderDialogProps = {
  open: boolean
  application: Application | null
  onImport: (
    file: File,
  ) => Promise<boolean>
  onClose: () => void
}


export function RecorderDialog({
  open,
  application,
  onImport,
  onClose,
}: RecorderDialogProps) {
  const inputRef =
    useRef<HTMLInputElement | null>(
      null,
    )

  const [
    importing,
    setImporting,
  ] = useState(false)

  const [
    error,
    setError,
  ] = useState('')


  if (!open) {
    return null
  }


  const openRecorder = () => {
    window.open(
      'http://127.0.0.1:8877',
      '_blank',
      'noopener',
    )
  }


  const selectFile = () => {
    setError('')

    inputRef.current?.click()
  }


  const importFile = async (
    file: File,
  ) => {
    if (
      file.size
      > 1_000_000
    ) {
      setError(
        'O arquivo de gravação excede 1 MB.',
      )

      return
    }

    setImporting(true)
    setError('')

    try {
      const imported =
        await onImport(file)

      if (!imported) {
        return
      }

      onClose()
    } catch (exc) {
      setError(
        exc instanceof Error
          ? exc.message
          : 'Falha ao importar gravação',
      )
    } finally {
      setImporting(false)

      if (inputRef.current) {
        inputRef.current.value = ''
      }
    }
  }


  return (
    <div className="execution-overlay">
      <section className="execution-dialog">
        <header className="execution-dialog__head">
          <div>
            <span>RECORDER LOCAL</span>

            <strong>
              Gravar processo
            </strong>
          </div>

          <button
            type="button"
            title="Fechar"
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <div className="execution-dialog__body">
          {application && (
            <div className="recorder-target">
              <span>
                Aplicação
              </span>

              <strong>
                {application.name}
              </strong>

              <code>
                {application.url}
              </code>
            </div>
          )}

          <div className="recorder-info">
            <strong>
              Como funciona
            </strong>

            <ol>
              <li>
                Execute o agente Recorder no computador
                onde você vai usar o navegador.
              </li>

              <li>
                Abra o Recorder local e inicie uma gravação.
              </li>

              <li>
                Faça normalmente os cliques,
                preenchimentos e seleções.
              </li>

              <li>
                Pare a gravação e exporte o JSON.
              </li>

              <li>
                Importe o JSON aqui para gerar os nós
                ACTION automaticamente.
              </li>
            </ol>
          </div>

          <div className="recorder-command">
            <span>
              Agente local
            </span>

            <code>
              python -m recorder.agent
            </code>
          </div>

          <div className="recorder-security">
            🔒 Valores digitados em campos não são
            gravados pelo Recorder. Os preenchimentos
            viram referências como
            {' '}
            <code>
              {'{{username}}'}
            </code>
            .
          </div>

          {error && (
            <div className="execution-dialog__error">
              {error}
            </div>
          )}

          <input
            ref={inputRef}
            type="file"
            accept="application/json,.json"
            hidden
            onChange={(event) => {
              const file =
                event.target.files?.[0]

              if (file) {
                void importFile(file)
              }
            }}
          />
        </div>

        <footer className="execution-dialog__footer">
          <button
            type="button"
            onClick={onClose}
          >
            Cancelar
          </button>

          <button
            type="button"
            onClick={openRecorder}
          >
            ◉ Abrir Recorder
          </button>

          <button
            type="button"
            className="button-primary"
            disabled={importing}
            onClick={selectFile}
          >
            {importing
              ? 'Importando...'
              : '↥ Importar gravação'}
          </button>
        </footer>
      </section>
    </div>
  )
}
