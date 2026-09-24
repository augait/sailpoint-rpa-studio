import {
  useState,
  type FormEvent,
} from 'react'

import {
  login,
  type AuthSession,
} from './api'


type LoginProps = {
  onAuthenticated:
    (session: AuthSession) => void
}


export function Login({
  onAuthenticated,
}: LoginProps) {
  const [username, setUsername] =
    useState('')

  const [password, setPassword] =
    useState('')

  const [error, setError] =
    useState('')

  const [loading, setLoading] =
    useState(false)


  async function submit(
    event: FormEvent,
  ) {
    event.preventDefault()

    setError('')
    setLoading(true)

    try {
      const session =
        await login(
          username,
          password,
        )

      onAuthenticated(session)
    } catch (exc) {
      setError(
        exc instanceof Error
          ? exc.message
          : 'Falha na autenticação',
      )
    } finally {
      setLoading(false)
    }
  }


  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span className="login-logo">
            S
          </span>

          <div>
            <strong>
              SailPoint
            </strong>

            <small>
              RPA STUDIO · V2
            </small>
          </div>
        </div>

        <div className="login-heading">
          <span className="eyebrow">
            AUTOMAÇÃO DE IDENTIDADES
          </span>

          <h1>
            Entrar no Studio
          </h1>

          <p>
            Use sua conta existente
            do RPA Studio.
          </p>
        </div>

        <form
          className="login-form"
          onSubmit={submit}
        >
          <label>
            Usuário

            <input
              value={username}
              onChange={(event) =>
                setUsername(
                  event.target.value,
                )
              }
              autoComplete="username"
              required
            />
          </label>

          <label>
            Senha

            <input
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(
                  event.target.value,
                )
              }
              autoComplete={
                'current-password'
              }
              required
            />
          </label>

          {error && (
            <div
              className="login-error"
              role="alert"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-submit"
            disabled={loading}
          >
            {loading
              ? 'Entrando...'
              : 'Entrar'}
          </button>
        </form>
      </section>
    </main>
  )
}
