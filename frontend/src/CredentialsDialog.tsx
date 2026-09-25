import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  createApplicationCredential,
  deleteApplicationCredential,
  listApplicationCredentials,
  updateApplicationCredential,
  type Application,
  type ApplicationCredential,
} from './api'


type CredentialField = {
  key: string
  value: string
}


type CredentialsDialogProps = {
  open: boolean
  application: Application | null
  token: string
  canManage: boolean
  onClose: () => void
}


const credentialNamePattern =
  /^[A-Za-z_][A-Za-z0-9_]{0,119}$/

const fieldNamePattern =
  /^[A-Za-z_][A-Za-z0-9_]{0,59}$/


export function CredentialsDialog({
  open,
  application,
  token,
  canManage,
  onClose,
}: CredentialsDialogProps) {
  const [
    credentials,
    setCredentials,
  ] = useState<ApplicationCredential[]>([])

  const [
    loading,
    setLoading,
  ] = useState(false)

  const [
    saving,
    setSaving,
  ] = useState(false)

  const [
    deletingId,
    setDeletingId,
  ] = useState<string | null>(null)

  const [
    error,
    setError,
  ] = useState('')

  const [
    formOpen,
    setFormOpen,
  ] = useState(false)

  const [
    editing,
    setEditing,
  ] = useState<ApplicationCredential | null>(
    null,
  )

  const [
    name,
    setName,
  ] = useState('')

  const [
    description,
    setDescription,
  ] = useState('')

  const [
    fields,
    setFields,
  ] = useState<CredentialField[]>([
    {
      key: 'username',
      value: '',
    },
    {
      key: 'password',
      value: '',
    },
  ])


  const resetForm = useCallback(() => {
    setEditing(null)
    setName('')
    setDescription('')
    setFields([
      {
        key: 'username',
        value: '',
      },
      {
        key: 'password',
        value: '',
      },
    ])
    setFormOpen(false)
  }, [])


  const loadCredentials = useCallback(
    async () => {
      if (
        !open
        || !application
      ) {
        return
      }

      setLoading(true)
      setError('')

      try {
        const rows =
          await listApplicationCredentials(
            token,
            application.id,
          )

        setCredentials(rows)
      } catch (exc) {
        setError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao carregar credenciais',
        )
      } finally {
        setLoading(false)
      }
    },
    [
      application,
      open,
      token,
    ],
  )


  useEffect(() => {
    if (!open) {
      return
    }

    const timer = window.setTimeout(
      () => {
        void loadCredentials()
      },
      0,
    )

    return () => {
      window.clearTimeout(timer)
    }
  }, [
    loadCredentials,
    open,
  ])


  const closeDialog = () => {
    resetForm()
    setError('')
    onClose()
  }


  if (
    !open
    || !application
  ) {
    return null
  }


  const openCreate = () => {
    setError('')
    setEditing(null)
    setName('')
    setDescription('')
    setFields([
      {
        key: 'username',
        value: '',
      },
      {
        key: 'password',
        value: '',
      },
    ])
    setFormOpen(true)
  }


  const openEdit = (
    credential: ApplicationCredential,
  ) => {
    setError('')
    setEditing(credential)
    setName(credential.name)
    setDescription(
      credential.description,
    )

    setFields(
      credential.fields.map(
        (key) => ({
          key,
          value: '',
        }),
      ),
    )

    setFormOpen(true)
  }


  const addField = () => {
    if (fields.length >= 20) {
      return
    }

    setFields(
      (current) => [
        ...current,
        {
          key: '',
          value: '',
        },
      ],
    )
  }


  const removeField = (
    index: number,
  ) => {
    if (fields.length <= 1) {
      return
    }

    setFields(
      (current) =>
        current.filter(
          (_, itemIndex) =>
            itemIndex !== index,
        ),
    )
  }


  const updateField = (
    index: number,
    property: keyof CredentialField,
    value: string,
  ) => {
    setFields(
      (current) =>
        current.map(
          (field, itemIndex) =>
            itemIndex === index
              ? {
                  ...field,
                  [property]: value,
                }
              : field,
        ),
    )
  }


  const submit = async () => {
    const cleanName =
      name.trim()

    if (
      !credentialNamePattern.test(
        cleanName,
      )
    ) {
      setError(
        'Nome da credencial inválido. Use letras, números e underscore, começando por letra ou underscore.',
      )

      return
    }

    const values: Record<string, string> = {}

    for (const field of fields) {
      const cleanKey =
        field.key.trim()

      if (
        !fieldNamePattern.test(
          cleanKey,
        )
      ) {
        setError(
          `Campo inválido: ${cleanKey || '(vazio)'}`,
        )

        return
      }

      if (
        Object.prototype.hasOwnProperty.call(
          values,
          cleanKey,
        )
      ) {
        setError(
          `Campo duplicado: ${cleanKey}`,
        )

        return
      }

      if (!field.value) {
        setError(
          `Informe o valor do campo ${cleanKey}`,
        )

        return
      }

      values[cleanKey] =
        field.value
    }

    setSaving(true)
    setError('')

    try {
      const body = {
        name: cleanName,
        description:
          description.trim(),
        values,
      }

      if (editing) {
        const updated =
          await updateApplicationCredential(
            token,
            application.id,
            editing.id,
            body,
          )

        setCredentials(
          (current) =>
            current.map(
              (credential) =>
                credential.id
                  === updated.id
                  ? updated
                  : credential,
            ),
        )
      } else {
        const created =
          await createApplicationCredential(
            token,
            application.id,
            body,
          )

        setCredentials(
          (current) => [
            created,
            ...current,
          ],
        )
      }

      resetForm()
    } catch (exc) {
      setError(
        exc instanceof Error
          ? exc.message
          : 'Falha ao salvar credencial',
      )
    } finally {
      setSaving(false)
    }
  }


  const removeCredential = async (
    credential: ApplicationCredential,
  ) => {
    if (
      !window.confirm(
        `Excluir a credencial "${credential.name}"?`,
      )
    ) {
      return
    }

    setDeletingId(
      credential.id,
    )

    setError('')

    try {
      await deleteApplicationCredential(
        token,
        application.id,
        credential.id,
      )

      setCredentials(
        (current) =>
          current.filter(
            (item) =>
              item.id
              !== credential.id,
          ),
      )

      if (
        editing?.id
        === credential.id
      ) {
        resetForm()
      }
    } catch (exc) {
      setError(
        exc instanceof Error
          ? exc.message
          : 'Falha ao excluir credencial',
      )
    } finally {
      setDeletingId(null)
    }
  }


  return (
    <div className="execution-overlay">
      <section className="credentials-dialog">
        <header className="execution-dialog__head">
          <div>
            <span>CREDENCIAIS</span>

            <strong>
              {application.name}
            </strong>
          </div>

          <button
            type="button"
            onClick={closeDialog}
            title="Fechar"
          >
            ×
          </button>
        </header>

        <div className="credentials-toolbar">
          <span>
            {credentials.length}
            {' '}
            credencial(is)
          </span>

          <div>
            <button
              type="button"
              disabled={loading}
              onClick={() => {
                void loadCredentials()
              }}
            >
              {loading
                ? 'Atualizando...'
                : '↻ Atualizar'}
            </button>

            {canManage && (
              <button
                type="button"
                className="button-primary"
                onClick={
                  formOpen
                    ? resetForm
                    : openCreate
                }
              >
                {formOpen
                  ? 'Cancelar'
                  : '+ Nova credencial'}
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="execution-dialog__error credentials-error">
            {error}
          </div>
        )}

        {formOpen && (
          <div className="credential-form">
            <div className="credential-form__header">
              <strong>
                {editing
                  ? 'Substituir credencial'
                  : 'Nova credencial'}
              </strong>

              {editing && (
                <small>
                  Os valores atuais nunca são retornados.
                  Informe novamente todos os campos.
                </small>
              )}
            </div>

            <label>
              Nome

              <input
                value={name}
                maxLength={120}
                placeholder="legacy_login"
                onChange={(event) =>
                  setName(
                    event.target.value,
                  )
                }
              />

              <small>
                Referência:
                {' '}
                {'{{credential.'}
                {name || 'nome'}
                {'.campo}}'}
              </small>
            </label>

            <label>
              Descrição

              <textarea
                value={description}
                maxLength={2000}
                rows={2}
                placeholder="Login administrativo do sistema legado"
                onChange={(event) =>
                  setDescription(
                    event.target.value,
                  )
                }
              />
            </label>

            <div className="credential-fields">
              <div className="credential-fields__head">
                <strong>
                  Campos secretos
                </strong>

                <button
                  type="button"
                  disabled={
                    fields.length >= 20
                  }
                  onClick={addField}
                >
                  + Campo
                </button>
              </div>

              {fields.map(
                (field, index) => (
                  <div
                    className="credential-field"
                    key={index}
                  >
                    <input
                      value={field.key}
                      maxLength={60}
                      placeholder="password"
                      aria-label={
                        `Nome do campo ${index + 1}`
                      }
                      onChange={(event) =>
                        updateField(
                          index,
                          'key',
                          event.target.value,
                        )
                      }
                    />

                    <input
                      type="password"
                      value={field.value}
                      maxLength={10000}
                      autoComplete="new-password"
                      placeholder={
                        editing
                          ? 'Digite o novo valor'
                          : 'Valor secreto'
                      }
                      aria-label={
                        `Valor do campo ${index + 1}`
                      }
                      onChange={(event) =>
                        updateField(
                          index,
                          'value',
                          event.target.value,
                        )
                      }
                    />

                    <button
                      type="button"
                      title="Remover campo"
                      disabled={
                        fields.length <= 1
                      }
                      onClick={() =>
                        removeField(index)
                      }
                    >
                      ×
                    </button>
                  </div>
                ),
              )}
            </div>

            <div className="credential-form__actions">
              <button
                type="button"
                onClick={resetForm}
              >
                Cancelar
              </button>

              <button
                type="button"
                className="button-primary"
                disabled={
                  saving
                  || !name.trim()
                }
                onClick={() => {
                  void submit()
                }}
              >
                {saving
                  ? 'Salvando...'
                  : editing
                    ? 'Substituir credencial'
                    : 'Criar credencial'}
              </button>
            </div>
          </div>
        )}

        <div className="credentials-body">
          {loading
            && credentials.length === 0
            && (
              <div className="history-empty">
                Carregando credenciais...
              </div>
            )}

          {!loading
            && credentials.length === 0
            && !error
            && (
              <div className="history-empty">
                Nenhuma credencial cadastrada.
              </div>
            )}

          {credentials.map(
            (credential) => (
              <article
                className="credential-row"
                key={credential.id}
              >
                <div className="credential-row__head">
                  <div>
                    <strong>
                      {credential.name}
                    </strong>

                    {credential.description && (
                      <p>
                        {credential.description}
                      </p>
                    )}
                  </div>

                  {canManage && (
                    <div className="credential-row__actions">
                      <button
                        type="button"
                        onClick={() =>
                          openEdit(
                            credential,
                          )
                        }
                      >
                        Editar
                      </button>

                      <button
                        type="button"
                        disabled={
                          deletingId
                          === credential.id
                        }
                        onClick={() => {
                          void removeCredential(
                            credential,
                          )
                        }}
                      >
                        {deletingId
                          === credential.id
                          ? 'Excluindo...'
                          : 'Excluir'}
                      </button>
                    </div>
                  )}
                </div>

                <div className="credential-row__fields">
                  {credential.fields.map(
                    (field) => (
                      <code key={field}>
                        {'{{credential.'}
                        {credential.name}
                        {'.'}
                        {field}
                        {'}}'}
                      </code>
                    ),
                  )}
                </div>

                <small>
                  Valores protegidos e não exibidos pela API.
                </small>
              </article>
            ),
          )}
        </div>

        <footer className="execution-dialog__footer">
          <button
            type="button"
            onClick={closeDialog}
          >
            Fechar
          </button>
        </footer>
      </section>
    </div>
  )
}
