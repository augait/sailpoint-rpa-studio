import type { Execution } from './api'


type ExecutionHistoryProps = {
  open: boolean
  loading: boolean
  error: string
  executions: Execution[]
  onRefresh: () => void
  onSelect: (execution: Execution) => void
  onClose: () => void
}


function formatDate(
  value: string,
) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleString(
    'pt-BR',
    {
      dateStyle: 'short',
      timeStyle: 'medium',
    },
  )
}


export function ExecutionHistory({
  open,
  loading,
  error,
  executions,
  onRefresh,
  onSelect,
  onClose,
}: ExecutionHistoryProps) {
  if (!open) {
    return null
  }

  return (
    <div className="execution-overlay">
      <section className="history-dialog">
        <header className="execution-dialog__head">
          <div>
            <span>EXECUÇÕES</span>

            <strong>
              Histórico recente
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

        <div className="history-dialog__toolbar">
          <span>
            Últimas {executions.length} execuções
          </span>

          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
          >
            {loading
              ? 'Atualizando...'
              : '↻ Atualizar'}
          </button>
        </div>

        {error && (
          <div className="execution-dialog__error history-dialog__error">
            {error}
          </div>
        )}

        <div className="history-dialog__body">
          {loading
            && executions.length === 0
            && (
              <div className="history-empty">
                Carregando execuções...
              </div>
            )}

          {!loading
            && executions.length === 0
            && !error
            && (
              <div className="history-empty">
                Nenhuma execução encontrada.
              </div>
            )}

          {executions.map(
            (execution) => (
              <button
                type="button"
                className="history-row"
                key={execution.id}
                onClick={() =>
                  onSelect(execution)
                }
              >
                <div className="history-row__main">
                  <strong
                    className={
                      `execution-status execution-status--${execution.status.toLowerCase()}`
                    }
                  >
                    {execution.status}
                  </strong>

                  <time>
                    {formatDate(
                      execution.created_at,
                    )}
                  </time>
                </div>

                <div className="history-row__meta">
                  <span>
                    Execution
                  </span>

                  <code>
                    {execution.id}
                  </code>

                  <span>
                    Workflow
                  </span>

                  <code>
                    {execution.workflow_id}
                  </code>

                  <span>
                    Duração
                  </span>

                  <strong>
                    {execution.duration === null
                      ? '—'
                      : `${execution.duration.toFixed(3)}s`}
                  </strong>
                </div>
                <span className="history-row__open">
                  Ver detalhes →
                </span>
              </button>
            ),
          )}
        </div>

        <footer className="execution-dialog__footer">
          <button
            type="button"
            onClick={onClose}
          >
            Fechar
          </button>
        </footer>
      </section>
    </div>
  )
}
