import type {
  Execution,
  ExecutionLog,
} from './api'


type ExecutionDetailProps = {
  open: boolean
  loading: boolean
  error: string
  execution: Execution | null
  logs: ExecutionLog[]
  onBack: () => void
  onClose: () => void
}


function formatTime(
  value: string,
) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleTimeString(
    'pt-BR',
    {
      hour12: false,
    },
  )
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


export function ExecutionDetail({
  open,
  loading,
  error,
  execution,
  logs,
  onBack,
  onClose,
}: ExecutionDetailProps) {
  if (!open) {
    return null
  }

  return (
    <div className="execution-overlay">
      <section className="execution-detail">
        <header className="execution-dialog__head">
          <div>
            <span>EXECUÇÃO</span>

            <strong>
              Detalhes da execução
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

        <div className="execution-detail__body">
          {loading && (
            <div className="history-empty">
              Carregando execução...
            </div>
          )}

          {error && (
            <div className="execution-dialog__error">
              {error}
            </div>
          )}

          {!loading
            && execution
            && (
              <>
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

                  <strong
                    className={
                      `execution-status execution-status--${execution.status.toLowerCase()}`
                    }
                  >
                    {execution.status}
                  </strong>

                  <span>
                    WORKFLOW
                  </span>

                  <code>
                    {execution.workflow_id}
                  </code>

                  <span>
                    CRIADA EM
                  </span>

                  <strong>
                    {formatDate(
                      execution.created_at,
                    )}
                  </strong>

                  <span>
                    DURAÇÃO
                  </span>

                  <strong>
                    {execution.duration === null
                      ? '—'
                      : `${execution.duration.toFixed(3)}s`}
                  </strong>

                  {execution.worker && (
                    <>
                      <span>
                        WORKER
                      </span>

                      <code>
                        {execution.worker}
                      </code>
                    </>
                  )}
                </div>

                {execution.error && (
                  <div className="execution-dialog__error">
                    {execution.error}
                  </div>
                )}

                <div className="execution-logs">
                  <div className="execution-logs__head">
                    <strong>
                      LOGS
                    </strong>

                    <span>
                      {logs.length}
                    </span>
                  </div>

                  {logs.length === 0 ? (
                    <div className="execution-logs__empty">
                      Nenhum evento registrado.
                    </div>
                  ) : (
                    <div className="execution-logs__list">
                      {logs.map((log) => (
                        <div
                          className="execution-log"
                          key={log.id}
                        >
                          <time>
                            {formatTime(
                              log.timestamp,
                            )}
                          </time>

                          <strong>
                            {log.event}
                          </strong>

                          {log.step_id && (
                            <code>
                              {log.step_id}
                            </code>
                          )}

                          {Object.keys(
                            log.details,
                          ).length > 0 && (
                            <pre>
                              {JSON.stringify(
                                log.details,
                                null,
                                2,
                              )}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {Object.keys(
                  execution.output || {},
                ).length > 0 && (
                  <div className="execution-detail__output">
                    <strong>
                      OUTPUT
                    </strong>

                    <pre>
                      {JSON.stringify(
                        execution.output,
                        null,
                        2,
                      )}
                    </pre>
                  </div>
                )}
              </>
            )}
        </div>

        <footer className="execution-dialog__footer">
          <button
            type="button"
            onClick={onBack}
          >
            ← Histórico
          </button>

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
