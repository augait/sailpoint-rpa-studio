import type {
  WorkflowVersion,
} from './api'


type VersionDialogProps = {
  open: boolean
  loading: boolean
  publishing: boolean
  error: string
  currentVersion: number | null
  versions: WorkflowVersion[]
  canPublish: boolean
  onRefresh: () => void
  onPublish: () => void
  onSelect: (version: WorkflowVersion) => void
  onClose: () => void
}


function formatDate(
  value: string | null | undefined,
) {
  if (!value) {
    return '—'
  }

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


export function VersionDialog({
  open,
  loading,
  publishing,
  error,
  currentVersion,
  versions,
  canPublish,
  onRefresh,
  onPublish,
  onSelect,
  onClose,
}: VersionDialogProps) {
  if (!open) {
    return null
  }

  const current =
    versions.find(
      (version) =>
        version.version === currentVersion,
    ) || null

  return (
    <div className="execution-overlay">
      <section className="version-dialog">
        <header className="execution-dialog__head">
          <div>
            <span>VERSIONAMENTO</span>

            <strong>
              Versões do workflow
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

        <div className="version-dialog__toolbar">
          <div>
            {current ? (
              <>
                Versão atual:
                {' '}
                <strong>
                  v{current.version}
                </strong>
                {' · '}
                <span
                  className={
                    `version-status version-status--${current.status.toLowerCase()}`
                  }
                >
                  {current.status}
                </span>
              </>
            ) : (
              'Versão atual indisponível'
            )}
          </div>

          <div className="version-dialog__actions">
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
            >
              {loading
                ? 'Atualizando...'
                : '↻ Atualizar'}
            </button>

            {current?.status === 'DRAFT'
              && canPublish
              && (
                <button
                  type="button"
                  className="button-primary"
                  disabled={publishing}
                  onClick={onPublish}
                >
                  {publishing
                    ? 'Publicando...'
                    : `Publicar v${current.version}`}
                </button>
              )}
          </div>
        </div>

        {error && (
          <div className="execution-dialog__error version-dialog__error">
            {error}
          </div>
        )}

        <div className="version-dialog__body">
          {loading
            && versions.length === 0
            && (
              <div className="history-empty">
                Carregando versões...
              </div>
            )}

          {!loading
            && versions.length === 0
            && !error
            && (
              <div className="history-empty">
                Nenhuma versão encontrada.
              </div>
            )}

          {versions.map(
            (version) => (
              <button
                type="button"
                className={
                  version.version === currentVersion
                    ? 'version-row version-row--current'
                    : 'version-row'
                }
                key={version.id}
                onClick={() =>
                  onSelect(version)
                }
              >
                <div className="version-row__head">
                  <div>
                    <strong>
                      v{version.version}
                    </strong>

                    {version.version
                      === currentVersion
                      && (
                        <span className="version-current">
                          ATUAL
                        </span>
                      )}
                  </div>

                  <span
                    className={
                      `version-status version-status--${version.status.toLowerCase()}`
                    }
                  >
                    {version.status}
                  </span>
                </div>

                <div className="version-row__meta">
                  <span>
                    Nome
                  </span>

                  <strong>
                    {version.name}
                  </strong>

                  <span>
                    Operação
                  </span>

                  <code>
                    {version.operation}
                  </code>

                  <span>
                    Criada em
                  </span>

                  <strong>
                    {formatDate(
                      version.created_at,
                    )}
                  </strong>

                  <span>
                    Publicada em
                  </span>

                  <strong>
                    {formatDate(
                      version.published_at,
                    )}
                  </strong>
                </div>
                <span className="version-row__open">
                  Abrir no canvas →
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
