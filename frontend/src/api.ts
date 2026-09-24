export type AuthSession = {
  access_token: string
  token_type: string
  role: string
  username: string
}


type ApiOptions = {
  method?: string
  body?: unknown
  token?: string
}


async function parseResponse(
  response: Response,
) {
  const data = await response.json()

  if (!response.ok) {
    let detail = data.detail

    if (Array.isArray(detail)) {
      detail = detail
        .map(
          (item) =>
            `${item.loc?.join('.')}: ${item.msg}`,
        )
        .join('\n')
    }

    if (
      detail
      && typeof detail === 'object'
    ) {
      detail = JSON.stringify(detail)
    }

    throw new Error(
      detail || 'Falha na requisição',
    )
  }

  return data
}


export async function api<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const response = await fetch(
    `/api/v1${path}`,
    {
      method:
        options.method || 'GET',

      headers: {
        'Content-Type':
          'application/json',

        ...(options.token
          ? {
              Authorization:
                `Bearer ${options.token}`,
            }
          : {}),
      },

      ...(options.body !== undefined
        ? {
            body: JSON.stringify(
              options.body,
            ),
          }
        : {}),
    },
  )

  return parseResponse(response)
}


export async function login(
  username: string,
  password: string,
): Promise<AuthSession> {
  return api<AuthSession>(
    '/auth/login',
    {
      method: 'POST',
      body: {
        username,
        password,
      },
    },
  )
}
