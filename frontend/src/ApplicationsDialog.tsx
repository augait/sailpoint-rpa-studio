import {
  useState,
} from 'react'

import type {
  Application,
  CreateApplicationInput,
} from './api'


type ApplicationsDialogProps = {
  open: boolean
  loading: boolean
  creating: boolean
  error: string
  applications: Application[]
  canCreate: boolean
  onRefresh: () => void
  onCreate: (
    input: CreateApplicationInput,
  ) => Promise<boolean>
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
      timeStyle: 'short',
    },
  )
}


export function ApplicationsDialog({
  open,
  loading,
  creating,
  error,
  applications,
  canCreate,
  onRefresh,
  onCreate,
  onClose,
}: ApplicationsDialogProps) {
  const [
    formOpen,
    setFormOpen,
  ] = useState(false)

  const [
    name,
    setName,
  ] = useState('')

  const [
    description,
    setDescription,
  ] = useState('')

  const [
    url,
    setUrl,
  ] = useState('')

  const [
    environment,
    setEnvironment,
  ] = useState<
    'DEV'
    | 'HML'
    | 'PRD'
  >('DEV')

  const [
    browser,
    setBrowser,
  ] = useState<
    'chromium'
    | 'firefox'
    | 'chrome'
    | 'msedge'
  >('chromium')

  const [
    headless,
    setHeadless,
  ] = useState(true)

  const [
    timeoutMs,
    setTimeoutMs,
  ] = useState(30000)

  const [
    tags,
    setTags,
  ] = useState('')

  if (!open) {
    return null
  }

  const submit = async () => {
    const cleanName =
      name.trim()

    const cleanUrl =
      url.trim()

    if (
      !cleanName
      || !cleanUrl
    ) {
      return
    }

    const created =
      await onCreate({
        name: cleanName,
        description:
          description.trim(),
        url: cleanUrl,
        environment,
        browser,
        headless,
        timeout_ms: timeoutMs,
        tags:
          tags
            .split(',')
            .map(
              (item) =>
                item.trim(),
            )
            .filter(Boolean),
      })

    if (!created) {
      return
    }

    setName('')
    setDescription('')
    setUrl('')
    setEnvironment('DEV')
    setBrowser('chromium')
    setHeadless(true)
    setTimeoutMs(30000)
    setTags('')
    setFormOpen(false)
  }

  return (
    <div className="execution-overlay">
      <section className="applications-dialog">
        <header className="execution-dialog__head">
          <div>
            <span>RPA STUDIO</span>

            <strong>
              Aplicações
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

        <div className="applications-dialog__toolbar">
          <span>
            {applications.length}
            {' '}
            aplicação(ões)
          </span>

          <div>
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
            >
              {loading
                ? 'Atualizando...'
                : '↻ Atualizar'}
            </button>

            {canCreate && (
              <button
                type="button"
                className="button-primary"
                onClick={() =>
                  setFormOpen(
                    (value) => !value,
                  )
                }
              >
                {formOpen
                  ? 'Cancelar cadastro'
                  : '+ Nova aplicação'}
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="execution-dialog__error applications-dialog__error">
            {error}
          </div>
        )}

        {formOpen && (
          <div className="application-form">
            <div className="application-form__grid">
              <label>
                Nome

                <input
                  value={name}
                  maxLength={120}
                  onChange={(event) =>
                    setName(
                      event.target.value,
                    )
                  }
                  placeholder="Legacy IAM Portal"
                />
              </label>

              <label>
                Ambiente

                <select
                  value={environment}
                  onChange={(event) =>
                    setEnvironment(
                      (event.target.value as 'DEV' | 'HML' | 'PRD'),
                    )
                  }
                >
                  <option value="DEV">
                    DEV
                  </option>

                  <option value="HML">
                    HML
                  </option>

                  <option value="PRD">
                    PRD
                  </option>
                </select>
              </label>

              <label className="application-form__wide">
                URL

                <input
                  value={url}
                  maxLength={2000}
                  onChange={(event) =>
                    setUrl(
                      event.target.value,
                    )
                  }
                  placeholder="https://sistema.exemplo.local"
                />
              </label>

              <label>
                Browser

                <select
                  value={browser}
                  onChange={(event) =>
                    setBrowser(
                      (event.target.value as 'chromium' | 'firefox' | 'chrome' | 'msedge'),
                    )
                  }
                >
                  <option value="chromium">
                    Chromium
                  </option>

                  <option value="chrome">
                    Chrome
                  </option>

                  <option value="firefox">
                    Firefox
                  </option>

                  <option value="msedge">
                    Edge
                  </option>
                </select>
              </label>

              <label>
                Timeout (ms)

                <input
                  type="number"
                  min={500}
                  max={60000}
                  value={timeoutMs}
                  onChange={(event) =>
                    setTimeoutMs(
                      Number(
                        event.target.value,
                      ),
                    )
                  }
                />
              </label>

              <label className="application-form__wide">
                Descrição

                <textarea
                  value={description}
                  maxLength={2000}
                  rows={3}
                  onChange={(event) =>
                    setDescription(
                      event.target.value,
                    )
                  }
                  placeholder="Descrição da aplicação legada"
                />
              </label>

              <label className="application-form__wide">
                Tags

                <input
                  value={tags}
                  onChange={(event) =>
                    setTags(
                      event.target.value,
                    )
                  }
                  placeholder="iam, legado, rh"
                />

                <small>
                  Separe as tags por vírgula.
                </small>
              </label>
            </div>

            <label className="application-form__check">
              <input
                type="checkbox"
                checked={headless}
                onChange={(event) =>
                  setHeadless(
                    event.target.checked,
                  )
                }
              />

              Executar navegador em modo headless
            </label>

            <div className="application-form__actions">
              <button
                type="button"
                className="button-primary"
                disabled={
                  creating
                  || !name.trim()
                  || !url.trim()
                  || timeoutMs < 500
                  || timeoutMs > 60000
                }
                onClick={() => {
                  void submit()
                }}
              >
                {creating
                  ? 'Criando...'
                  : 'Criar aplicação'}
              </button>
            </div>
          </div>
        )}

        <div className="applications-dialog__body">
          {loading
            && applications.length === 0
            && (
              <div className="history-empty">
                Carregando aplicações...
              </div>
            )}

          {!loading
            && applications.length === 0
            && !error
            && (
              <div className="history-empty">
                Nenhuma aplicação cadastrada.
              </div>
            )}

          {applications.map(
            (application) => (
              <article
                className="application-row"
                key={application.id}
              >
                <div className="application-row__head">
                  <strong>
                    {application.name}
                  </strong>

                  <span
                    className={
                      `application-environment application-environment--${application.environment.toLowerCase()}`
                    }
                  >
                    {application.environment}
                  </span>
                </div>

                {application.description && (
                  <p>
                    {application.description}
                  </p>
                )}

                <div className="application-row__meta">
                  <span>URL</span>

                  <code>
                    {application.url}
                  </code>

                  <span>Browser</span>

                  <strong>
                    {application.browser}
                    {' · '}
                    {application.headless
                      ? 'headless'
                      : 'visual'}
                  </strong>

                  <span>Timeout</span>

                  <strong>
                    {application.timeout_ms} ms
                  </strong>

                  <span>Criada em</span>

                  <strong>
                    {formatDate(
                      application.created_at,
                    )}
                  </strong>
                </div>

                {application.tags.length > 0 && (
                  <div className="application-row__tags">
                    {application.tags.map(
                      (tag) => (
                        <span key={tag}>
                          {tag}
                        </span>
                      ),
                    )}
                  </div>
                )}
              </article>
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
