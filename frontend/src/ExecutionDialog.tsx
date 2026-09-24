import type { Execution } from './api'


type ExecutionDialogProps = {
  open: boolean
  workflowName: string
  inputJson: string
  loading: boolean
  error: string
  execution: Execution | null
  onInputChange: (value: string) => void
  onRun: () => void
  onClose: () => void
}


export function ExecutionDialog({
  open,
  workflowName,
  inputJson,
  loading,
  error,
  execution,
  onInputChange,
  onRun,
  onClose,
}: ExecutionDialogProps) {
  if (!open) {
    return null
  }

  return (
    <div className="execution-overlay">
      <section className="execution-dialog">
        <header className="execution-dialog__head">
          <div>
            <span>EXECUÇÃO</span>

            <strong>
              {workflowName}
            </strong>
          </div>

          <button
            type="button"
            onClick={onClose}
            title="Fechar"
          >
            ×
          </button>
        </header>

        <div className="execution-dialog__body">
          <label>
            Input JSON

            <textarea
              value={inputJson}
              onChange={(event) =>
                onInputChange(
                  event.target.value,
                )
              }
              rows={10}
              spellCheck={false}
            />
          </label>

          <small>
            As variáveis ficam disponíveis
            para o workflow durante a execução.
          </small>

          {error && (
            <div className="execution-dialog__error">
              {error}
            </div>
          )}

          {execution && (
            <div className="execution-dialog__result">
              <span>
                EXECUTION ID
              </span>

              <code>
                {execution.id}
              </code>

              <span>
                STATUS
              </span>

              <strong>
                {execution.status}
              </strong>
            </div>
          )}
        </div>

        <footer className="execution-dialog__footer">
          <button
            type="button"
            onClick={onClose}
          >
            Fechar
          </button>

          <button
            type="button"
            className="button-primary"
            disabled={loading}
            onClick={onRun}
          >
            {loading
              ? 'Executando...'
              : '▶ Executar agora'}
          </button>
        </footer>
      </section>
    </div>
  )
}
