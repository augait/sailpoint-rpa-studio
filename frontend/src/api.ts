export type AuthSession = {
  access_token: string
  token_type: string
  role: string
  username: string
}


export type Selector = {
  kind:
    | 'css'
    | 'testid'
    | 'role'
    | 'label'
    | 'placeholder'
    | 'text'
    | 'xpath'
  value: string
  name?: string | null
}


export type WorkflowStep = {
  id: string
  type:
    | 'navigate'
    | 'click'
    | 'fill'
    | 'wait'
    | 'select'
    | 'screenshot'
    | 'extract_text'
    | 'assert_text'
    | 'check'
    | 'press'
    | 'hover'
  name: string
  enabled: boolean
  selectors: Selector[]
  value: string
  url: string
  output: string
  timeout_ms: number
  wait_ms: number
  secret: boolean
}


export type WorkflowGraphNode = {
  id: string
  kind:
    | 'start'
    | 'end'
    | 'action'
    | 'condition'
    | 'loop'
  step?: WorkflowStep | null
  expression: string
  max_iterations?: number | null
}


export type WorkflowGraphEdge = {
  id: string
  source: string
  target: string
  branch:
    | 'default'
    | 'true'
    | 'false'
    | 'body'
    | 'exit'
}


export type WorkflowGraph = {
  nodes: WorkflowGraphNode[]
  edges: WorkflowGraphEdge[]
  start_node_id: string
  end_node_id: string
}


export type Workflow = {
  id: string
  application_id: string
  name: string
  operation: string
  steps: WorkflowStep[]
  revision: number
  current_version: number
  timeout_seconds: number
  created_at: string
  updated_at: string
}


export type WorkflowVersion = {
  id: string
  workflow_id: string
  version: number
  status:
    | 'DRAFT'
    | 'PUBLISHED'
    | 'ARCHIVED'
  application_id: string
  name: string
  operation: string
  steps: WorkflowStep[]
  graph: WorkflowGraph | null
  timeout_seconds: number
  created_by?: string | null
  created_at: string
  published_at?: string | null
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


export async function getMe(
  token: string,
): Promise<{
  username: string
  role: string
}> {
  return api(
    '/auth/me',
    {
      token,
    },
  )
}


export async function listWorkflows(
  token: string,
): Promise<Workflow[]> {
  return api<Workflow[]>(
    '/workflows',
    {
      token,
    },
  )
}


export async function getWorkflow(
  token: string,
  workflowId: string,
): Promise<Workflow> {
  return api<Workflow>(
    `/workflows/${workflowId}`,
    {
      token,
    },
  )
}


export async function listWorkflowVersions(
  token: string,
  workflowId: string,
): Promise<WorkflowVersion[]> {
  return api<WorkflowVersion[]>(
    `/workflows/${workflowId}/versions`,
    {
      token,
    },
  )
}


export async function getWorkflowVersion(
  token: string,
  workflowId: string,
  version: number,
): Promise<WorkflowVersion> {
  return api<WorkflowVersion>(
    `/workflows/${workflowId}/versions/${version}`,
    {
      token,
    },
  )
}
