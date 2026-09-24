import type {
  Execution,
  ExecutionLog,
} from './api'


type ExecutionDialogProps = {
  open: boolean
  workflowName: string
  inputJson: string
  loading: boolean
  error: string
  execution: Execution | null
  logs: ExecutionLog[]
  onInputChange: (value: string) => void
  onRun: () => void
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


export function ExecutionDialog({
  open,
  workflowName,
  inputJson,
  loading,
  error,
  execution,
  logs,
  onInputChange,
  onRun,
  onClose,
}: ExecutionDialogProps) {
  if (!open) {
    return null
  }

  const active =
    execution
    && [
      'PENDING',
      'QUEUED',
      'RUNNING',
    ].includes(
      execution.status,
    )

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
              disabled={Boolean(active)}
              onChange={(event) =>
                onInputChange(
                  event.target.value,
                )
              }
              rows={8}
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

                {execution.duration !== null && (
                  <>
                    <span>
                      DURAÇÃO
                    </span>

                    <strong>
                      {execution.duration.toFixed(3)}s
                    </strong>
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
                    Aguardando eventos...
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
            </>
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
            disabled={
              loading
              || Boolean(active)
            }
            onClick={onRun}
          >
            {loading
              ? 'Executando...'
              : active
                ? 'Em execução...'
                : '▶ Executar agora'}
          </button>
        </footer>
      </section>
    </div>
  )
}
