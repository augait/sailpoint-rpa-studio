import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
  type ReactFlowInstance,
} from '@xyflow/react'

import '@xyflow/react/dist/style.css'
import './App.css'
import { Login } from './Login'
import { ApplicationsDialog } from './ApplicationsDialog'
import { ExecutionDetail } from './ExecutionDetail'
import { ExecutionDialog } from './ExecutionDialog'
import { ExecutionHistory } from './ExecutionHistory'
import { VersionDialog } from './VersionDialog'
import {
  NodeInspector,
  type InspectorNodeData,
} from './NodeInspector'
import {
  cancelExecution,
  createApplication,
  executeWorkflow,
  getExecution,
  getExecutionLogs,
  getWorkflow,
  getWorkflowVersion,
  listApplications,
  listExecutions,
  listWorkflowVersions,
  listWorkflows,
  publishWorkflow,
  saveWorkflow,
  type Application,
  type AuthSession,
  type CreateApplicationInput,
  type Execution,
  type ExecutionLog,
  type Selector,
  type Workflow,
  type WorkflowGraph,
  type WorkflowVersion,
} from './api'


type StudioNodeKind =
  | 'start'
  | 'end'
  | 'action'
  | 'condition'
  | 'loop'


type EdgeBranch =
  | 'default'
  | 'true'
  | 'false'
  | 'body'
  | 'exit'


type ActionStep = {
  id: string
  type: string
  name?: string
  enabled?: boolean
  selectors?: Selector[]
  value?: string
  url?: string
  output?: string
  timeout_ms?: number
  wait_ms?: number
  secret?: boolean
}


type StudioNodeData = Record<string, unknown> & {
  kind: StudioNodeKind
  title: string
  subtitle?: string
  expression?: string
  maxIterations?: number
  step?: ActionStep
}


type GraphNodePayload = {
  id: string
  kind: StudioNodeKind
  step?: ActionStep
  expression?: string
  max_iterations?: number
}


type GraphEdgePayload = {
  id: string
  source: string
  target: string
  branch: string
}


type WorkflowGraphPayload = {
  nodes: GraphNodePayload[]
  edges: GraphEdgePayload[]
  start_node_id: string
  end_node_id: string
}


type ValidationResult = {
  ok: boolean
  errors: string[]
}


const allowedBranches = new Set<EdgeBranch>([
  'default',
  'true',
  'false',
  'body',
  'exit',
])


function StudioNode({ data }: NodeProps) {
  const node = data as StudioNodeData

  const isStart = node.kind === 'start'
  const isEnd = node.kind === 'end'
  const isCondition = node.kind === 'condition'
  const isLoop = node.kind === 'loop'

  return (
    <div
      className={
        `studio-node studio-node--${node.kind}`
      }
    >
      {!isStart && (
        <Handle
          type="target"
          position={Position.Top}
          id="target"
          className="studio-handle"
        />
      )}

      <div className="studio-node__header">
        <span className="studio-node__icon">
          {node.kind === 'start' && '▶'}
          {node.kind === 'end' && '■'}
          {node.kind === 'action' && '⚙'}
          {node.kind === 'condition' && '◇'}
          {node.kind === 'loop' && '↻'}
        </span>

        <div>
          <strong>
            {node.title}
          </strong>

          {node.subtitle && (
            <small>
              {node.subtitle}
            </small>
          )}
        </div>
      </div>

      {node.expression && (
        <div className="studio-node__expression">
          {node.expression}
        </div>
      )}

      {isLoop && (
        <div className="studio-node__meta">
          máximo: {node.maxIterations ?? 1}
        </div>
      )}

      {!isEnd && !isCondition && !isLoop && (
        <Handle
          type="source"
          position={Position.Bottom}
          id="default"
          className="studio-handle"
        />
      )}

      {isCondition && (
        <>
          <div
            className={
              'branch-label branch-label--left'
            }
          >
            true
          </div>

          <div
            className={
              'branch-label branch-label--right'
            }
          >
            false
          </div>

          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            className={
              'studio-handle studio-handle--left'
            }
            style={{ left: '30%' }}
          />

          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            className={
              'studio-handle studio-handle--right'
            }
            style={{ left: '70%' }}
          />
        </>
      )}

      {isLoop && (
        <>
          <div
            className={
              'branch-label branch-label--left'
            }
          >
            body
          </div>

          <div
            className={
              'branch-label branch-label--right'
            }
          >
            exit
          </div>

          <Handle
            type="source"
            position={Position.Bottom}
            id="body"
            className={
              'studio-handle studio-handle--left'
            }
            style={{ left: '30%' }}
          />

          <Handle
            type="source"
            position={Position.Bottom}
            id="exit"
            className={
              'studio-handle studio-handle--right'
            }
            style={{ left: '70%' }}
          />
        </>
      )}
    </div>
  )
}


const nodeTypes = {
  studio: StudioNode,
}


const initialNodes: Node<StudioNodeData>[] = [
  {
    id: '__start__',
    type: 'studio',
    deletable: false,
    position: {
      x: 430,
      y: 40,
    },
    data: {
      kind: 'start',
      title: 'START',
      subtitle: 'Início do workflow',
    },
  },
  {
    id: 'action_open',
    type: 'studio',
    position: {
      x: 430,
      y: 180,
    },
    data: {
      kind: 'action',
      title: 'Abrir aplicação',
      subtitle: 'navigate · open_application',
      step: {
        id: 'open_application',
        type: 'navigate',
        name: 'Abrir aplicação',
        enabled: true,
        url: '{{application.url}}',
      },
    },
  },
  {
    id: 'condition_department',
    type: 'studio',
    position: {
      x: 430,
      y: 340,
    },
    data: {
      kind: 'condition',
      title: 'CONDITION',
      expression: '{{department}} == "IT"',
    },
  },
  {
    id: 'action_it',
    type: 'studio',
    position: {
      x: 150,
      y: 540,
    },
    data: {
      kind: 'action',
      title: 'Fluxo IT',
      subtitle: 'wait · action_it',
      step: {
        id: 'action_it',
        type: 'wait',
        name: 'Fluxo IT',
        enabled: true,
        wait_ms: 250,
      },
    },
  },
  {
    id: 'loop_check',
    type: 'studio',
    position: {
      x: 680,
      y: 540,
    },
    data: {
      kind: 'loop',
      title: 'LOOP',
      expression: '{{status}} != "ready"',
      maxIterations: 5,
    },
  },
  {
    id: 'loop_body_action',
    type: 'studio',
    position: {
      x: 680,
      y: 740,
    },
    data: {
      kind: 'action',
      title: 'Corpo do loop',
      subtitle: 'wait · loop_body',
      step: {
        id: 'loop_body',
        type: 'wait',
        name: 'Corpo do loop',
        enabled: true,
        wait_ms: 250,
      },
    },
  },
  {
    id: '__end__',
    type: 'studio',
    deletable: false,
    position: {
      x: 350,
      y: 940,
    },
    data: {
      kind: 'end',
      title: 'END',
      subtitle: 'Fim do workflow',
    },
  },
]


const initialEdges: Edge[] = [
  {
    id: 'start-open',
    source: '__start__',
    sourceHandle: 'default',
    target: 'action_open',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
  {
    id: 'open-condition',
    source: 'action_open',
    sourceHandle: 'default',
    target: 'condition_department',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
  {
    id: 'condition-true',
    source: 'condition_department',
    sourceHandle: 'true',
    target: 'action_it',
    label: 'true',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
  {
    id: 'condition-false',
    source: 'condition_department',
    sourceHandle: 'false',
    target: 'loop_check',
    label: 'false',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
  {
    id: 'it-end',
    source: 'action_it',
    sourceHandle: 'default',
    target: '__end__',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
  {
    id: 'loop-body',
    source: 'loop_check',
    sourceHandle: 'body',
    target: 'loop_body_action',
    label: 'body',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
  {
    id: 'loop-body-back',
    source: 'loop_body_action',
    sourceHandle: 'default',
    target: 'loop_check',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
  {
    id: 'loop-exit',
    source: 'loop_check',
    sourceHandle: 'exit',
    target: '__end__',
    label: 'exit',
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
  },
]



function canvasFromGraph(
  graph: WorkflowGraph,
): {
  nodes: Node<StudioNodeData>[]
  edges: Edge[]
} {
  const outgoing =
    new Map<string, string[]>()

  for (const node of graph.nodes) {
    outgoing.set(node.id, [])
  }

  for (const edge of graph.edges) {
    outgoing
      .get(edge.source)
      ?.push(edge.target)
  }

  const depth =
    new Map<string, number>()

  depth.set(
    graph.start_node_id,
    0,
  )

  const queue = [
    graph.start_node_id,
  ]

  while (queue.length) {
    const current =
      queue.shift()!

    const currentDepth =
      depth.get(current) ?? 0

    for (
      const target
      of outgoing.get(current) || []
    ) {
      if (depth.has(target)) {
        continue
      }

      depth.set(
        target,
        currentDepth + 1,
      )

      queue.push(target)
    }
  }

  const groups =
    new Map<
      number,
      WorkflowGraph['nodes']
    >()

  for (const node of graph.nodes) {
    const level =
      depth.get(node.id) ?? 0

    const group =
      groups.get(level) || []

    group.push(node)
    groups.set(level, group)
  }

  const nodes:
    Node<StudioNodeData>[] =
    graph.nodes.map((node) => {
      const level =
        depth.get(node.id) ?? 0

      const group =
        groups.get(level) || [node]

      const index =
        group.findIndex(
          (item) =>
            item.id === node.id,
        )

      const x =
        500
        + (
          index
          - (group.length - 1) / 2
        ) * 300

      const y =
        40 + level * 180

      let data: StudioNodeData

      if (node.kind === 'action') {
        data = {
          kind: 'action',
          title:
            node.step?.name
            || node.step?.type
            || 'ACTION',
          subtitle:
            node.step
              ? `${node.step.type} · ${node.step.id}`
              : 'action',
          step:
            node.step || undefined,
        }
      } else if (
        node.kind === 'condition'
      ) {
        data = {
          kind: 'condition',
          title: 'CONDITION',
          expression:
            node.expression,
        }
      } else if (
        node.kind === 'loop'
      ) {
        data = {
          kind: 'loop',
          title: 'LOOP',
          expression:
            node.expression,
          maxIterations:
            node.max_iterations
            ?? undefined,
        }
      } else if (
        node.kind === 'start'
      ) {
        data = {
          kind: 'start',
          title: 'START',
          subtitle:
            'Início do workflow',
        }
      } else {
        data = {
          kind: 'end',
          title: 'END',
          subtitle:
            'Fim do workflow',
        }
      }

      return {
        id: node.id,
        type: 'studio',
        deletable:
          node.kind !== 'start'
          && node.kind !== 'end',
        position: {
          x,
          y,
        },
        data,
      }
    })

  const edges: Edge[] =
    graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle:
        edge.branch,
      label:
        edge.branch === 'default'
          ? undefined
          : edge.branch,
      markerEnd: {
        type:
          MarkerType.ArrowClosed,
      },
    }))

  return {
    nodes,
    edges,
  }
}


function graphFromCanvas(
  nodes: Node<StudioNodeData>[],
  edges: Edge[],
): WorkflowGraphPayload {
  return {
    start_node_id: '__start__',
    end_node_id: '__end__',

    nodes: nodes.map((node) => {
      const data = node.data

      if (data.kind === 'action') {
        return {
          id: node.id,
          kind: data.kind,
          step: data.step,
        }
      }

      if (data.kind === 'condition') {
        return {
          id: node.id,
          kind: data.kind,
          expression:
            data.expression || '',
        }
      }

      if (data.kind === 'loop') {
        return {
          id: node.id,
          kind: data.kind,
          expression:
            data.expression || '',
          max_iterations:
            data.maxIterations,
        }
      }

      return {
        id: node.id,
        kind: data.kind,
      }
    }),

    edges: edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      branch:
        edge.sourceHandle || 'default',
    })),
  }
}



const validActionTypes =
  new Set([
    'navigate',
    'click',
    'fill',
    'wait',
    'select',
    'screenshot',
    'extract_text',
    'assert_text',
    'check',
    'press',
    'hover',
  ])


const selectorActionTypes =
  new Set([
    'click',
    'fill',
    'select',
    'extract_text',
    'assert_text',
    'check',
    'press',
    'hover',
  ])


const validSelectorKinds =
  new Set([
    'css',
    'testid',
    'role',
    'label',
    'placeholder',
    'text',
    'xpath',
  ])


const sensitiveSelector =
  /password|passwd|secret|token|authorization|cookie|credential/i


const variableReference =
  /^{{\s*[A-Za-z_][A-Za-z0-9_.]*\s*}}$/


function validateActionStep(
  step: ActionStep,
  nodeId: string,
): string[] {
  const errors: string[] = []

  if (
    !/^[A-Za-z0-9_-]{1,60}$/.test(
      step.id,
    )
  ) {
    errors.push(
      `ACTION ${nodeId}: Step ID inválido`,
    )
  }

  if (!validActionTypes.has(step.type)) {
    errors.push(
      `ACTION ${nodeId}: tipo inválido`,
    )
  }

  if (
    (step.name || '').length > 120
  ) {
    errors.push(
      `ACTION ${nodeId}: nome excede 120 caracteres`,
    )
  }

  const selectors =
    step.selectors || []

  if (selectors.length > 10) {
    errors.push(
      `ACTION ${nodeId}: máximo de 10 seletores`,
    )
  }

  if (
    selectorActionTypes.has(step.type)
    && selectors.length === 0
  ) {
    errors.push(
      `ACTION ${nodeId}: ${step.type} precisa de seletor`,
    )
  }

  selectors.forEach(
    (selector, index) => {
      if (
        !validSelectorKinds.has(
          selector.kind,
        )
      ) {
        errors.push(
          `ACTION ${nodeId}: seletor ${index + 1} possui tipo inválido`,
        )
      }

      if (
        !selector.value.trim()
        || selector.value.length > 1000
      ) {
        errors.push(
          `ACTION ${nodeId}: seletor ${index + 1} inválido`,
        )
      }

      if (
        (selector.name || '').length
        > 300
      ) {
        errors.push(
          `ACTION ${nodeId}: nome do seletor ${index + 1} excede 300 caracteres`,
        )
      }
    },
  )

  if (
    step.type === 'navigate'
    && !(step.url || '').trim()
  ) {
    errors.push(
      `ACTION ${nodeId}: navigate precisa de URL`,
    )
  }

  if (
    (step.url || '').length > 2000
  ) {
    errors.push(
      `ACTION ${nodeId}: URL excede 2000 caracteres`,
    )
  }

  if (
    (step.value || '').length > 10000
  ) {
    errors.push(
      `ACTION ${nodeId}: value excede 10000 caracteres`,
    )
  }

  const output =
    step.output ?? 'result'

  if (
    !/^[A-Za-z_][A-Za-z0-9_]{0,59}$/.test(
      output,
    )
  ) {
    errors.push(
      `ACTION ${nodeId}: output inválido`,
    )
  }

  const timeout =
    step.timeout_ms ?? 10000

  if (
    timeout < 200
    || timeout > 60000
  ) {
    errors.push(
      `ACTION ${nodeId}: timeout_ms precisa estar entre 200 e 60000`,
    )
  }

  const wait =
    step.wait_ms ?? 1000

  if (
    wait < 0
    || wait > 30000
  ) {
    errors.push(
      `ACTION ${nodeId}: wait_ms precisa estar entre 0 e 30000`,
    )
  }

  const passwordTarget =
    selectors.some(
      (selector) =>
        sensitiveSelector.test(
          selector.value,
        ),
    )

  if (
    step.type === 'fill'
    && (
      step.secret
      || passwordTarget
    )
    && !variableReference.test(
      step.value || '',
    )
  ) {
    errors.push(
      `ACTION ${nodeId}: segredo precisa usar referência {{variavel}}`,
    )
  }

  return errors
}


function validateGraph(
  graph: WorkflowGraphPayload,
): ValidationResult {
  const errors: string[] = []

  const nodeIds =
    graph.nodes.map((node) => node.id)

  const edgeIds =
    graph.edges.map((edge) => edge.id)

  if (
    nodeIds.length
    !== new Set(nodeIds).size
  ) {
    errors.push('IDs de nós duplicados')
  }

  if (
    edgeIds.length
    !== new Set(edgeIds).size
  ) {
    errors.push('IDs de conexões duplicados')
  }

  const nodes = new Map(
    graph.nodes.map(
      (node) => [node.id, node],
    ),
  )

  const start =
    nodes.get(graph.start_node_id)

  const end =
    nodes.get(graph.end_node_id)

  if (!start || start.kind !== 'start') {
    errors.push(
      'START obrigatório não encontrado',
    )
  }

  if (!end || end.kind !== 'end') {
    errors.push(
      'END obrigatório não encontrado',
    )
  }

  const outgoing =
    new Map<string, GraphEdgePayload[]>()

  const incoming =
    new Map<string, GraphEdgePayload[]>()

  for (const node of graph.nodes) {
    outgoing.set(node.id, [])
    incoming.set(node.id, [])

    if (node.kind === 'action') {
      if (!node.step) {
        errors.push(
          `ACTION ${node.id} sem step`,
        )
      } else {
        errors.push(
          ...validateActionStep(
            node.step,
            node.id,
          ),
        )
      }
    }

    if (
      node.kind === 'condition'
      && !node.expression?.trim()
    ) {
      errors.push(
        `CONDITION ${node.id} sem expression`,
      )
    }

    if (node.kind === 'loop') {
      if (!node.expression?.trim()) {
        errors.push(
          `LOOP ${node.id} sem expression`,
        )
      }

      if (
        node.max_iterations === undefined
        || node.max_iterations < 1
        || node.max_iterations > 1000
      ) {
        errors.push(
          `LOOP ${node.id} precisa de max_iterations entre 1 e 1000`,
        )
      }
    }
  }

  const edgeKeys = new Set<string>()

  for (const edge of graph.edges) {
    if (!nodes.has(edge.source)) {
      errors.push(
        `Conexão ${edge.id} possui source inexistente`,
      )
      continue
    }

    if (!nodes.has(edge.target)) {
      errors.push(
        `Conexão ${edge.id} possui target inexistente`,
      )
      continue
    }

    if (
      !allowedBranches.has(
        edge.branch as EdgeBranch,
      )
    ) {
      errors.push(
        `Branch inválida em ${edge.id}`,
      )
    }

    if (edge.source === edge.target) {
      errors.push(
        `Self-loop não permitido em ${edge.source}`,
      )
    }

    const key =
      `${edge.source}|${edge.target}|${edge.branch}`

    if (edgeKeys.has(key)) {
      errors.push(
        `Conexão duplicada: ${edge.id}`,
      )
    }

    edgeKeys.add(key)

    outgoing.get(edge.source)?.push(edge)
    incoming.get(edge.target)?.push(edge)
  }

  if (
    incoming.get(graph.start_node_id)
      ?.length
  ) {
    errors.push(
      'START não pode possuir entrada',
    )
  }

  if (
    outgoing.get(graph.end_node_id)
      ?.length
  ) {
    errors.push(
      'END não pode possuir saída',
    )
  }

  for (const node of graph.nodes) {
    const branches =
      (
        outgoing.get(node.id)
        || []
      ).map(
        (edge) => edge.branch,
      )

    if (
      node.kind === 'start'
      || node.kind === 'action'
    ) {
      if (
        branches.length !== 1
        || branches[0] !== 'default'
      ) {
        errors.push(
          `${node.kind.toUpperCase()} ${node.id} precisa de uma saída default`,
        )
      }
    }

    if (node.kind === 'end') {
      if (branches.length !== 0) {
        errors.push(
          'END não pode possuir saída',
        )
      }
    }

    if (node.kind === 'condition') {
      if (
        branches.length !== 2
        || !branches.includes('true')
        || !branches.includes('false')
      ) {
        errors.push(
          `CONDITION ${node.id} precisa das branches true e false`,
        )
      }
    }

    if (node.kind === 'loop') {
      if (
        branches.length !== 2
        || !branches.includes('body')
        || !branches.includes('exit')
      ) {
        errors.push(
          `LOOP ${node.id} precisa das branches body e exit`,
        )
      }
    }
  }

  if (start) {
    const reachable = new Set<string>()
    const stack = [
      graph.start_node_id,
    ]

    while (stack.length) {
      const current =
        stack.pop()!

      if (reachable.has(current)) {
        continue
      }

      reachable.add(current)

      for (
        const edge
        of outgoing.get(current) || []
      ) {
        stack.push(edge.target)
      }
    }

    const unreachable =
      graph.nodes
        .map((node) => node.id)
        .filter(
          (id) => !reachable.has(id),
        )

    if (unreachable.length) {
      errors.push(
        `Nós inalcançáveis: ${unreachable.join(', ')}`,
      )
    }
  }

  if (end) {
    const reachesEnd =
      new Set<string>()

    const stack = [
      graph.end_node_id,
    ]

    while (stack.length) {
      const current =
        stack.pop()!

      if (reachesEnd.has(current)) {
        continue
      }

      reachesEnd.add(current)

      for (
        const edge
        of incoming.get(current) || []
      ) {
        stack.push(edge.source)
      }
    }

    const deadEnds =
      graph.nodes
        .map((node) => node.id)
        .filter(
          (id) => !reachesEnd.has(id),
        )

    if (deadEnds.length) {
      errors.push(
        `Nós sem caminho até END: ${deadEnds.join(', ')}`,
      )
    }
  }

  const visited = new Set<string>()
  const active: string[] = []
  const activeSet = new Set<string>()

  function visit(nodeId: string) {
    if (activeSet.has(nodeId)) {
      const index =
        active.indexOf(nodeId)

      const cycle =
        active.slice(index)

      const containsLoop =
        cycle.some(
          (id) =>
            nodes.get(id)?.kind === 'loop',
        )

      if (!containsLoop) {
        errors.push(
          `Ciclo sem LOOP: ${cycle.join(' → ')}`,
        )
      }

      return
    }

    if (visited.has(nodeId)) {
      return
    }

    active.push(nodeId)
    activeSet.add(nodeId)

    for (
      const edge
      of outgoing.get(nodeId) || []
    ) {
      visit(edge.target)
    }

    active.pop()
    activeSet.delete(nodeId)
    visited.add(nodeId)
  }

  if (start) {
    visit(graph.start_node_id)
  }

  return {
    ok: errors.length === 0,
    errors,
  }
}


function branchAllowed(
  kind: StudioNodeKind,
  branch: string,
) {
  if (
    kind === 'start'
    || kind === 'action'
  ) {
    return branch === 'default'
  }

  if (kind === 'condition') {
    return (
      branch === 'true'
      || branch === 'false'
    )
  }

  if (kind === 'loop') {
    return (
      branch === 'body'
      || branch === 'exit'
    )
  }

  return false
}


function App() {
  const [
    session,
    setSession,
  ] = useState<AuthSession | null>(
    null,
  )

  const [
    workflows,
    setWorkflows,
  ] = useState<Workflow[]>([])

  const [
    workflowListLoading,
    setWorkflowListLoading,
  ] = useState(false)

  const [
    workflowListError,
    setWorkflowListError,
  ] = useState('')

  const [
    selectedWorkflow,
    setSelectedWorkflow,
  ] = useState<Workflow | null>(
    null,
  )

  const [
    loadedVersion,
    setLoadedVersion,
  ] = useState<WorkflowVersion | null>(
    null,
  )


  const [
    versionDialogOpen,
    setVersionDialogOpen,
  ] = useState(false)


  const [
    applicationsOpen,
    setApplicationsOpen,
  ] = useState(false)

  const [
    applications,
    setApplications,
  ] = useState<Application[]>([])

  const [
    applicationsLoading,
    setApplicationsLoading,
  ] = useState(false)

  const [
    applicationCreating,
    setApplicationCreating,
  ] = useState(false)

  const [
    applicationError,
    setApplicationError,
  ] = useState('')

  const [
    versionList,
    setVersionList,
  ] = useState<WorkflowVersion[]>([])

  const [
    versionListLoading,
    setVersionListLoading,
  ] = useState(false)

  const [
    versionError,
    setVersionError,
  ] = useState('')

  const [
    versionPublishing,
    setVersionPublishing,
  ] = useState(false)

  const [
    workflowLoading,
    setWorkflowLoading,
  ] = useState(false)

  const [
    workflowLoadError,
    setWorkflowLoadError,
  ] = useState('')

  const [
    saveLoading,
    setSaveLoading,
  ] = useState(false)

  const [
    saveMessage,
    setSaveMessage,
  ] = useState('')

  const [
    saveError,
    setSaveError,
  ] = useState('')


  const [
    saveConflict,
    setSaveConflict,
  ] = useState(false)

  const [
    conflictReloading,
    setConflictReloading,
  ] = useState(false)


  const [
    isDirty,
    setIsDirty,
  ] = useState(false)


  const [
    executionDialogOpen,
    setExecutionDialogOpen,
  ] = useState(false)


  const [
    historyOpen,
    setHistoryOpen,
  ] = useState(false)

  const [
    historyLoading,
    setHistoryLoading,
  ] = useState(false)

  const [
    historyError,
    setHistoryError,
  ] = useState('')

  const [
    executionHistory,
    setExecutionHistory,
  ] = useState<Execution[]>([])


  const [
    historyDetailOpen,
    setHistoryDetailOpen,
  ] = useState(false)

  const [
    historyDetailLoading,
    setHistoryDetailLoading,
  ] = useState(false)

  const [
    historyDetailError,
    setHistoryDetailError,
  ] = useState('')

  const [
    historyDetailExecution,
    setHistoryDetailExecution,
  ] = useState<Execution | null>(
    null,
  )

  const [
    historyDetailLogs,
    setHistoryDetailLogs,
  ] = useState<ExecutionLog[]>([])

  const [
    executionInput,
    setExecutionInput,
  ] = useState('{}')

  const [
    executionLoading,
    setExecutionLoading,
  ] = useState(false)


  const [
    executionCancelling,
    setExecutionCancelling,
  ] = useState(false)

  const [
    executionError,
    setExecutionError,
  ] = useState('')

  const [
    currentExecution,
    setCurrentExecution,
  ] = useState<Execution | null>(
    null,
  )


  const [
    executionLogs,
    setExecutionLogs,
  ] = useState<ExecutionLog[]>([])

  const currentExecutionId =
    currentExecution?.id

  useEffect(() => {
    const handleBeforeUnload = (
      event: BeforeUnloadEvent,
    ) => {
      if (!isDirty) {
        return
      }

      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener(
      'beforeunload',
      handleBeforeUnload,
    )

    return () => {
      window.removeEventListener(
        'beforeunload',
        handleBeforeUnload,
      )
    }
  }, [isDirty])

  useEffect(() => {
    if (
      !session
      || !executionDialogOpen
      || !currentExecutionId
    ) {
      return
    }

    let stopped = false
    let timer:
      number | undefined

    const refresh = async () => {
      try {
        const [
          execution,
          logs,
        ] = await Promise.all([
          getExecution(
            session.access_token,
            currentExecutionId,
          ),
          getExecutionLogs(
            session.access_token,
            currentExecutionId,
          ),
        ])

        if (stopped) {
          return
        }

        setCurrentExecution(execution)
        setExecutionLogs(logs)

        const finished = [
          'SUCCESS',
          'FAILED',
          'CANCELLED',
        ].includes(
          execution.status,
        )

        if (!finished) {
          timer = window.setTimeout(
            refresh,
            700,
          )
        }
      } catch (exc) {
        if (!stopped) {
          setExecutionError(
            exc instanceof Error
              ? `Falha ao acompanhar execução: ${exc.message}`
              : 'Falha ao acompanhar execução',
          )
        }
      }
    }

    void refresh()

    return () => {
      stopped = true

      if (timer !== undefined) {
        window.clearTimeout(timer)
      }
    }
  }, [
    currentExecutionId,
    executionDialogOpen,
    session,
  ])

  const [
    flowInstance,
    setFlowInstance,
  ] = useState<
    ReactFlowInstance<
      Node<StudioNodeData>,
      Edge
    > | null
  >(null)

  const [
    nodes,
    setNodes,
    onNodesChange,
  ] = useNodesState(initialNodes)

  const [
    edges,
    setEdges,
    onEdgesChange,
  ] = useEdgesState(initialEdges)

  const [
    showValidation,
    setShowValidation,
  ] = useState(false)

  const [
    selectedNodeId,
    setSelectedNodeId,
  ] = useState<string | null>(
    null,
  )


  const selectedNode = useMemo(
    () =>
      nodes.find(
        (node) =>
          node.id === selectedNodeId,
      ) || null,
    [
      nodes,
      selectedNodeId,
    ],
  )


  const handleAuthenticated = useCallback(
    async (
      authenticatedSession: AuthSession,
    ) => {
      setSession(
        authenticatedSession,
      )

      setWorkflowListLoading(true)
      setWorkflowListError('')

      try {
        const rows =
          await listWorkflows(
            authenticatedSession.access_token,
          )

        setWorkflows(rows)
      } catch (exc) {
        setWorkflowListError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao carregar workflows',
        )
      } finally {
        setWorkflowListLoading(false)
      }
    },
    [],
  )


  const openWorkflow = useCallback(
    async (
      item: Workflow,
    ) => {
      if (!session) {
        return
      }

      if (
        isDirty
        && !window.confirm(
          'Existem alterações não salvas. Descartar e abrir outro workflow?',
        )
      ) {
        return
      }

      setSelectedWorkflow(item)
      setWorkflowLoading(true)
      setWorkflowLoadError('')

      try {
        const version =
          await getWorkflowVersion(
            session.access_token,
            item.id,
            item.current_version,
          )

        if (!version.graph) {
          throw new Error(
            'A versão atual não possui graph',
          )
        }

        const canvas =
          canvasFromGraph(
            version.graph,
          )

        setNodes(canvas.nodes)
        setEdges(canvas.edges)
        setLoadedVersion(version)
        setSelectedNodeId(null)
        setShowValidation(false)
        setIsDirty(false)
        setSaveConflict(false)

        window.setTimeout(
          () => {
            flowInstance?.fitView({
              padding: 0.2,
              duration: 300,
            })
          },
          0,
        )
      } catch (exc) {
        setWorkflowLoadError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao abrir workflow',
        )
      } finally {
        setWorkflowLoading(false)
      }
    },
    [
      flowInstance,
      isDirty,
      session,
      setEdges,
      setNodes,
    ],
  )


  const graph = useMemo(
    () =>
      graphFromCanvas(
        nodes,
        edges,
      ),
    [nodes, edges],
  )


  const validation = useMemo(
    () => validateGraph(graph),
    [graph],
  )


  const historicalView = Boolean(
    loadedVersion
    && selectedWorkflow
    && loadedVersion.version
      !== selectedWorkflow.current_version
  )


  const loadApplications = useCallback(
    async () => {
      if (!session) {
        return
      }

      setApplicationsLoading(true)
      setApplicationError('')

      try {
        const rows =
          await listApplications(
            session.access_token,
          )

        setApplications(rows)
      } catch (exc) {
        setApplicationError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao carregar aplicações',
        )
      } finally {
        setApplicationsLoading(false)
      }
    },
    [session],
  )


  const handleCreateApplication = useCallback(
    async (
      input: CreateApplicationInput,
    ) => {
      if (!session) {
        return false
      }

      setApplicationCreating(true)
      setApplicationError('')

      try {
        const created =
          await createApplication(
            session.access_token,
            input,
          )

        setApplications(
          (current) => [
            created,
            ...current.filter(
              (item) =>
                item.id !== created.id,
            ),
          ],
        )

        return true
      } catch (exc) {
        setApplicationError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao criar aplicação',
        )

        return false
      } finally {
        setApplicationCreating(false)
      }
    },
    [session],
  )


  const openWorkflowVersion = useCallback(
    async (
      versionNumber: number,
    ) => {
      if (
        !session
        || !selectedWorkflow
      ) {
        return
      }

      if (
        isDirty
        && !window.confirm(
          'Existem alterações não salvas. Descartar e abrir outra versão?',
        )
      ) {
        return
      }

      setWorkflowLoading(true)
      setWorkflowLoadError('')

      try {
        const version =
          await getWorkflowVersion(
            session.access_token,
            selectedWorkflow.id,
            versionNumber,
          )

        if (!version.graph) {
          throw new Error(
            'A versão selecionada não possui graph',
          )
        }

        const canvas =
          canvasFromGraph(
            version.graph,
          )

        setNodes(canvas.nodes)
        setEdges(canvas.edges)
        setLoadedVersion(version)
        setSelectedNodeId(null)
        setShowValidation(false)
        setIsDirty(false)
        setSaveConflict(false)
        setVersionDialogOpen(false)
        setSaveMessage('')
        setSaveError('')

        window.setTimeout(
          () => {
            flowInstance?.fitView({
              padding: 0.2,
              duration: 300,
            })
          },
          0,
        )
      } catch (exc) {
        setWorkflowLoadError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao abrir versão',
        )
      } finally {
        setWorkflowLoading(false)
      }
    },
    [
      flowInstance,
      isDirty,
      selectedWorkflow,
      session,
      setEdges,
      setNodes,
    ],
  )


  const loadVersions = useCallback(
    async () => {
      if (
        !session
        || !selectedWorkflow
      ) {
        return
      }

      setVersionListLoading(true)
      setVersionError('')

      try {
        const rows =
          await listWorkflowVersions(
            session.access_token,
            selectedWorkflow.id,
          )

        setVersionList(rows)
      } catch (exc) {
        setVersionError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao carregar versões',
        )
      } finally {
        setVersionListLoading(false)
      }
    },
    [
      selectedWorkflow,
      session,
    ],
  )


  const handlePublishWorkflow = useCallback(
    async () => {
      if (
        !session
        || !selectedWorkflow
        || !loadedVersion
      ) {
        return
      }

      setVersionPublishing(true)
      setVersionError('')

      try {
        const published =
          await publishWorkflow(
            session.access_token,
            selectedWorkflow.id,
          )

        setLoadedVersion(
          published,
        )

        const versions =
          await listWorkflowVersions(
            session.access_token,
            selectedWorkflow.id,
          )

        setVersionList(versions)

        const workflows =
          await listWorkflows(
            session.access_token,
          )

        setWorkflows(workflows)
      } catch (exc) {
        setVersionError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao publicar versão',
        )
      } finally {
        setVersionPublishing(false)
      }
    },
    [
      loadedVersion,
      selectedWorkflow,
      session,
    ],
  )


  const reloadAfterConflict = useCallback(
    async () => {
      if (
        !session
        || !selectedWorkflow
      ) {
        return
      }

      setConflictReloading(true)
      setSaveError('')

      try {
        const workflow =
          await getWorkflow(
            session.access_token,
            selectedWorkflow.id,
          )

        const version =
          await getWorkflowVersion(
            session.access_token,
            workflow.id,
            workflow.current_version,
          )

        if (!version.graph) {
          throw new Error(
            'A versão atual não possui graph',
          )
        }

        const canvas =
          canvasFromGraph(
            version.graph,
          )

        setSelectedWorkflow(workflow)
        setLoadedVersion(version)
        setNodes(canvas.nodes)
        setEdges(canvas.edges)
        setSelectedNodeId(null)

        setIsDirty(false)
        setShowValidation(false)
        setSaveConflict(false)

        setSaveMessage(
          `Recarregado · v${workflow.current_version} · rev. ${workflow.revision}`,
        )

        const rows =
          await listWorkflows(
            session.access_token,
          )

        setWorkflows(rows)

        window.setTimeout(
          () => {
            flowInstance?.fitView({
              padding: 0.2,
              duration: 300,
            })
          },
          0,
        )
      } catch (exc) {
        setSaveError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao recarregar workflow',
        )
      } finally {
        setConflictReloading(false)
      }
    },
    [
      flowInstance,
      selectedWorkflow,
      session,
      setEdges,
      setNodes,
    ],
  )


  const handleSaveWorkflow = useCallback(
    async () => {
      if (
        !session
        || !selectedWorkflow
        || !loadedVersion
        || !validation.ok
      ) {
        return
      }

      setSaveLoading(true)
      setSaveMessage('')
      setSaveError('')

      try {
        const saved =
          await saveWorkflow(
            session.access_token,
            selectedWorkflow.id,
            {
              application_id:
                selectedWorkflow.application_id,
              name:
                loadedVersion.name,
              operation:
                loadedVersion.operation,
              timeout_seconds:
                loadedVersion.timeout_seconds,
              revision:
                selectedWorkflow.revision,
              graph: graph as WorkflowGraph,
            },
          )

        const version =
          await getWorkflowVersion(
            session.access_token,
            saved.id,
            saved.current_version,
          )

        setSelectedWorkflow(saved)
        setLoadedVersion(version)
        setIsDirty(false)
        setSaveConflict(false)

        const rows =
          await listWorkflows(
            session.access_token,
          )

        setWorkflows(rows)

        setSaveMessage(
          `Salvo · v${saved.current_version} · rev. ${saved.revision}`,
        )
      } catch (exc) {
        const message =
          exc instanceof Error
            ? exc.message
            : 'Falha ao salvar workflow'

        if (
          message
          === 'Workflow alterado por outro usuário; recarregue'
        ) {
          setSaveConflict(true)
          setSaveError('')
        } else {
          setSaveError(message)
        }
      } finally {
        setSaveLoading(false)
      }
    },
    [
      graph,
      loadedVersion,
      selectedWorkflow,
      session,
      validation.ok,
    ],
  )


  const openExecutionHistoryDetail = useCallback(
    async (
      selected: Execution,
    ) => {
      if (!session) {
        return
      }

      setHistoryOpen(false)
      setHistoryDetailOpen(true)
      setHistoryDetailLoading(true)
      setHistoryDetailError('')
      setHistoryDetailExecution(selected)
      setHistoryDetailLogs([])

      try {
        const [
          execution,
          logs,
        ] = await Promise.all([
          getExecution(
            session.access_token,
            selected.id,
          ),
          getExecutionLogs(
            session.access_token,
            selected.id,
          ),
        ])

        setHistoryDetailExecution(
          execution,
        )

        setHistoryDetailLogs(
          logs,
        )
      } catch (exc) {
        setHistoryDetailError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao carregar execução',
        )
      } finally {
        setHistoryDetailLoading(false)
      }
    },
    [session],
  )


  const loadExecutionHistory = useCallback(
    async () => {
      if (!session) {
        return
      }

      setHistoryLoading(true)
      setHistoryError('')

      try {
        const rows =
          await listExecutions(
            session.access_token,
            30,
            0,
          )

        setExecutionHistory(rows)
      } catch (exc) {
        setHistoryError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao carregar histórico',
        )
      } finally {
        setHistoryLoading(false)
      }
    },
    [session],
  )


  const handleCancelExecution = useCallback(
    async () => {
      if (
        !session
        || !currentExecutionId
      ) {
        return
      }

      setExecutionCancelling(true)
      setExecutionError('')

      try {
        const execution =
          await cancelExecution(
            session.access_token,
            currentExecutionId,
          )

        setCurrentExecution(
          execution,
        )
      } catch (exc) {
        setExecutionError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao cancelar execução',
        )
      } finally {
        setExecutionCancelling(false)
      }
    },
    [
      currentExecutionId,
      session,
    ],
  )


  const handleExecuteWorkflow = useCallback(
    async () => {
      if (
        !session
        || !selectedWorkflow
      ) {
        return
      }

      setExecutionLoading(true)
      setExecutionCancelling(false)
      setExecutionError('')
      setCurrentExecution(null)
      setExecutionLogs([])

      try {
        const parsed =
          JSON.parse(executionInput)

        if (
          parsed === null
          || Array.isArray(parsed)
          || typeof parsed !== 'object'
        ) {
          throw new Error(
            'O input precisa ser um objeto JSON',
          )
        }

        const execution =
          await executeWorkflow(
            session.access_token,
            selectedWorkflow.id,
            {
              input: parsed,
            },
          )

        setCurrentExecution(
          execution,
        )
      } catch (exc) {
        setExecutionError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao iniciar execução',
        )
      } finally {
        setExecutionLoading(false)
      }
    },
    [
      executionInput,
      selectedWorkflow,
      session,
    ],
  )


  const updateSelectedNode = useCallback(
    (
      data: InspectorNodeData,
    ) => {
      if (
        !selectedNodeId
        || historicalView
      ) {
        return
      }

      setNodes((currentNodes) =>
        currentNodes.map(
          (node) =>
            node.id === selectedNodeId
              ? {
                  ...node,
                  data:
                    data as StudioNodeData,
                }
              : node,
        ),
      )

      setSaveMessage('')
      setSaveError('')
      setShowValidation(true)
      setIsDirty(true)
    },
    [
      historicalView,
      selectedNodeId,
      setNodes,
    ],
  )


  const onConnect = useCallback(
    (connection: Connection) => {
      if (historicalView) {
        return
      }

      if (
        !connection.source
        || !connection.target
      ) {
        return
      }

      if (
        connection.source
        === connection.target
      ) {
        return
      }

      const sourceNode =
        nodes.find(
          (node) =>
            node.id
            === connection.source,
        )

      const targetNode =
        nodes.find(
          (node) =>
            node.id
            === connection.target,
        )

      if (
        !sourceNode
        || !targetNode
      ) {
        return
      }

      if (
        sourceNode.data.kind === 'end'
        || targetNode.data.kind === 'start'
      ) {
        return
      }

      const branch =
        connection.sourceHandle
        || 'default'

      if (
        !branchAllowed(
          sourceNode.data.kind,
          branch,
        )
      ) {
        return
      }

      const branchAlreadyUsed =
        edges.some(
          (edge) =>
            edge.source
              === connection.source
            && (
              edge.sourceHandle
              || 'default'
            ) === branch,
        )

      if (branchAlreadyUsed) {
        return
      }

      setIsDirty(true)

      setEdges((currentEdges) =>
        addEdge(
          {
            ...connection,
            id:
              `edge-${crypto.randomUUID()}`,
            label:
              branch === 'default'
                ? undefined
                : branch,
            markerEnd: {
              type:
                MarkerType.ArrowClosed,
            },
          },
          currentEdges,
        ),
      )

      setShowValidation(false)
    },
    [
      edges,
      historicalView,
      nodes,
      setEdges,
    ],
  )


  const addNode = useCallback(
    (
      kind:
        | 'action'
        | 'condition'
        | 'loop',
    ) => {
      if (historicalView) {
        return
      }

      const suffix =
        crypto
          .randomUUID()
          .slice(0, 8)

      const id =
        `${kind}_${suffix}`

      let data: StudioNodeData

      if (kind === 'condition') {
        data = {
          kind,
          title: 'CONDITION',
          expression:
            '{{variable}} == "value"',
        }
      } else if (kind === 'loop') {
        data = {
          kind,
          title: 'LOOP',
          expression:
            '{{status}} != "ready"',
          maxIterations: 5,
        }
      } else {
        data = {
          kind,
          title: 'Nova ação',
          subtitle:
            `wait · step_${suffix}`,
          step: {
            id: `step_${suffix}`,
            type: 'wait',
            name: 'Nova ação',
            enabled: true,
            wait_ms: 1000,
          },
        }
      }

      setIsDirty(true)

      setNodes((currentNodes) => [
        ...currentNodes,
        {
          id,
          type: 'studio',
          position: {
            x:
              250
              + (
                currentNodes.length
                % 4
              ) * 180,
            y:
              300
              + currentNodes.length
              * 25,
          },
          data,
        },
      ])

      setShowValidation(false)
    },
    [
      historicalView,
      setNodes,
    ],
  )


  if (!session) {
    return (
      <Login
        onAuthenticated={
          handleAuthenticated
        }
      />
    )
  }

  return (
    <div className="studio-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">
            AUTOMAÇÃO DE IDENTIDADES
          </span>

          <h1>
            Workflow Designer
          </h1>

          <p>
            React Flow · Phase 2
            {' · '}
            {session.username}
            {' · '}
            {session.role}
          </p>
        </div>

        <div className="topbar-actions">
          <button
            type="button"
            onClick={() => {
              setApplicationsOpen(true)
              void loadApplications()
            }}
          >
            Aplicações
          </button>
          <button
            type="button"
            disabled={
              !selectedWorkflow
              || !loadedVersion
            }
            onClick={() => {
              setVersionDialogOpen(true)
              void loadVersions()
            }}
          >
            Versões
          </button>
          <button
            type="button"
            onClick={() => {
              setHistoryOpen(true)
              void loadExecutionHistory()
            }}
          >
            Histórico
          </button>
          <button
            type="button"
            disabled={
              !selectedWorkflow
              || !loadedVersion
              || historicalView
              || isDirty
              || !validation.ok
              || ![
                'ADMIN',
                'DEVELOPER',
                'OPERATOR',
              ].includes(
                session.role,
              )
            }
            title={
              !selectedWorkflow
                ? 'Selecione um workflow'
                : historicalView
                  ? 'Versões históricas são somente leitura'
                  : isDirty
                    ? 'Salve as alterações antes de executar'
                    : !validation.ok
                      ? 'Corrija o workflow antes de executar'
                      : 'Executar workflow'
            }
            onClick={() => {
              setExecutionError('')
              setExecutionCancelling(false)
              setCurrentExecution(null)
              setExecutionLogs([])
              setExecutionDialogOpen(true)
            }}
          >
            ▶ Executar
          </button>

          <button
            type="button"
            onClick={() =>
              setShowValidation(true)
            }
          >
            Validar
          </button>

          <button
            type="button"
            className="button-primary"
            disabled={
              !validation.ok
              || !selectedWorkflow
              || !loadedVersion
              || historicalView
              || saveConflict
              || !isDirty
              || saveLoading
              || !['ADMIN', 'DEVELOPER'].includes(
                session.role,
              )
            }
            title={
              !selectedWorkflow
                ? 'Selecione um workflow real'
                : historicalView
                  ? 'Versões históricas são somente leitura'
                  : saveConflict
                    ? 'Recarregue o workflow antes de salvar novamente'
                    : !isDirty
                      ? 'Nenhuma alteração para salvar'
                    : !validation.ok
                      ? 'Corrija o grafo antes de salvar'
                      : 'Salvar versão atual'
            }
            onClick={() => {
              void handleSaveWorkflow()
            }}
          >
            {saveLoading
              ? 'Salvando...'
              : 'Salvar workflow'}
          </button>
        </div>
      </header>

      {saveConflict && (
        <div className="conflict-banner">
          <div>
            <strong>
              ⚠ Conflito de edição
            </strong>

            <span>
              Este workflow foi alterado por outro usuário
              enquanto você estava editando.
              Suas alterações locais não foram salvas.
            </span>
          </div>

          <button
            type="button"
            disabled={conflictReloading}
            onClick={() => {
              void reloadAfterConflict()
            }}
          >
            {conflictReloading
              ? 'Recarregando...'
              : 'Recarregar versão atual'}
          </button>
        </div>
      )}

      {(saveMessage || saveError) && (
        <div
          className={
            saveError
              ? 'save-banner save-banner--error'
              : 'save-banner save-banner--ok'
          }
        >
          {saveError || saveMessage}
        </div>
      )}

      <ApplicationsDialog
        open={applicationsOpen}
        loading={applicationsLoading}
        creating={applicationCreating}
        error={applicationError}
        applications={applications}
        canCreate={
          ['ADMIN', 'DEVELOPER'].includes(
            session.role,
          )
        }
        onRefresh={() => {
          void loadApplications()
        }}
        onCreate={handleCreateApplication}
        onClose={() =>
          setApplicationsOpen(false)
        }
      />

      <VersionDialog
        open={versionDialogOpen}
        loading={versionListLoading}
        publishing={versionPublishing}
        error={versionError}
        currentVersion={
          selectedWorkflow?.current_version
          ?? null
        }
        versions={versionList}
        canPublish={
          !isDirty
          && ['ADMIN', 'DEVELOPER'].includes(
            session.role,
          )
        }
        onRefresh={() => {
          void loadVersions()
        }}
        onPublish={() => {
          if (
            window.confirm(
              `Publicar a versão v${selectedWorkflow?.current_version ?? ''}?`,
            )
          ) {
            void handlePublishWorkflow()
          }
        }}
        onSelect={(version) => {
          void openWorkflowVersion(
            version.version,
          )
        }}
        onClose={() =>
          setVersionDialogOpen(false)
        }
      />

      <ExecutionHistory
        open={historyOpen}
        loading={historyLoading}
        error={historyError}
        executions={executionHistory}
        onRefresh={() => {
          void loadExecutionHistory()
        }}
        onSelect={(execution) => {
          void openExecutionHistoryDetail(
            execution,
          )
        }}
        onClose={() =>
          setHistoryOpen(false)
        }
      />

      <ExecutionDetail
        open={historyDetailOpen}
        loading={historyDetailLoading}
        error={historyDetailError}
        execution={historyDetailExecution}
        logs={historyDetailLogs}
        onBack={() => {
          setHistoryDetailOpen(false)
          setHistoryOpen(true)
          void loadExecutionHistory()
        }}
        onClose={() =>
          setHistoryDetailOpen(false)
        }
      />

      <ExecutionDialog
        open={executionDialogOpen}
        workflowName={
          loadedVersion?.name
          || selectedWorkflow?.name
          || 'Workflow'
        }
        inputJson={executionInput}
        loading={executionLoading}
        error={executionError}
        execution={currentExecution}
        logs={executionLogs}
        cancelling={executionCancelling}
        onInputChange={setExecutionInput}
        onRun={() => {
          void handleExecuteWorkflow()
        }}
        onCancel={() => {
          if (
            window.confirm(
              'Solicitar cancelamento desta execução?',
            )
          ) {
            void handleCancelExecution()
          }
        }}
        onClose={() =>
          setExecutionDialogOpen(false)
        }
      />

      <main className="designer-layout">
        <aside className="palette">
          <div className="workflow-browser">
            <div className="workflow-browser__head">
              <div>
                <span>
                  WORKFLOWS
                </span>

                <strong>
                  Processos reais
                </strong>
              </div>

              {!workflowListLoading
                && !workflowListError
                && (
                  <small>
                    {workflows.length}
                  </small>
                )}
            </div>

            {workflowListLoading && (
              <div className="workflow-browser__message">
                Carregando workflows...
              </div>
            )}

            {workflowListError && (
              <div
                className={
                  'workflow-browser__message workflow-browser__message--error'
                }
              >
                {workflowListError}
              </div>
            )}

            {!workflowListLoading
              && !workflowListError
              && workflows.length === 0
              && (
                <div className="workflow-browser__message">
                  Nenhum workflow cadastrado.
                </div>
              )}

            {!workflowListLoading
              && !workflowListError
              && workflows.length > 0
              && (
                <div className="workflow-browser__list">
                  {workflows.map(
                    (item) => (
                      <button
                        type="button"
                        className={
                          'workflow-row'
                          + (
                            selectedWorkflow?.id
                            === item.id
                              ? ' workflow-row--active'
                              : ''
                          )
                        }
                        key={item.id}
                        title={item.id}
                        disabled={
                          workflowLoading
                          && selectedWorkflow?.id
                            === item.id
                        }
                        onClick={() => {
                          void openWorkflow(
                            item,
                          )
                        }}
                      >
                        <strong>
                          {item.name}
                        </strong>

                        <small>
                          {item.operation}
                          {' · '}
                          v{item.current_version}
                          {' · '}
                          rev. {item.revision}
                        </small>
                      </button>
                    ),
                  )}
                </div>
              )}

            {workflowLoadError && (
              <div
                className={
                  'workflow-browser__message workflow-browser__message--error'
                }
              >
                {workflowLoadError}
              </div>
            )}
          </div>

          <div className="palette-header">
            <span>
              COMPONENTES
            </span>

            <strong>
              Adicionar nó
            </strong>
          </div>

          <button
            type="button"
            className="palette-item"
            disabled={historicalView}
            onClick={() =>
              addNode('action')
            }
          >
            <span className="palette-icon">
              ⚙
            </span>

            <span>
              <strong>ACTION</strong>
              <small>
                Executa uma ação RPA
              </small>
            </span>
          </button>

          <button
            type="button"
            className="palette-item"
            disabled={historicalView}
            onClick={() =>
              addNode('condition')
            }
          >
            <span className="palette-icon">
              ◇
            </span>

            <span>
              <strong>
                CONDITION
              </strong>

              <small>
                Branch true / false
              </small>
            </span>
          </button>

          <button
            type="button"
            className="palette-item"
            disabled={historicalView}
            onClick={() =>
              addNode('loop')
            }
          >
            <span className="palette-icon">
              ↻
            </span>

            <span>
              <strong>LOOP</strong>

              <small>
                Body / exit com limite
              </small>
            </span>
          </button>

          <div
            className={
              validation.ok
                ? 'validation-box validation-box--ok'
                : 'validation-box validation-box--error'
            }
          >
            <strong>
              {validation.ok
                ? '✓ Graph Contract válido'
                : `⚠ ${validation.errors.length} problema(s)`}
            </strong>

            <p>
              {validation.ok
                ? 'O canvas pode ser convertido para o contrato do backend.'
                : 'Use Validar para visualizar os erros.'}
            </p>

            {showValidation
              && !validation.ok
              && (
                <ul>
                  {validation.errors.map(
                    (error) => (
                      <li key={error}>
                        {error}
                      </li>
                    ),
                  )}
                </ul>
              )}
          </div>
        </aside>

        <section className="canvas-panel">
          <div className="canvas-toolbar">
            <div>
              <strong>
                {loadedVersion
                  ? loadedVersion.name
                  : 'Canvas'}
              </strong>

              <span>
                {loadedVersion
                  ? (
                      `v${loadedVersion.version}`
                      + ` · ${loadedVersion.status}`
                      + ` · ${loadedVersion.operation}`
                    )
                  : 'Arraste nós e conecte os handles'}
              </span>
            </div>

            {isDirty
              && !historicalView
              && (
                <span className="dirty-badge">
                  ● Alterações não salvas
                </span>
              )}

            {historicalView
              && selectedWorkflow
              && loadedVersion
              && (
                <div className="historical-view">
                  <span>
                    SOMENTE LEITURA · v{loadedVersion.version}
                  </span>

                  <button
                    type="button"
                    onClick={() => {
                      void openWorkflowVersion(
                        selectedWorkflow.current_version,
                      )
                    }}
                  >
                    Voltar para v{selectedWorkflow.current_version}
                  </button>
                </div>
              )}

            <div className="canvas-stats">
              <span>
                {nodes.length} nós
              </span>

              <span>
                {edges.length} conexões
              </span>

              <span>
                {validation.ok
                  ? '✓ válido'
                  : '⚠ inválido'}
              </span>
            </div>
          </div>

          <div className="canvas">
            <ReactFlow
              nodes={nodes}
              onInit={setFlowInstance}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={(changes) => {
                if (
                  !historicalView
                  && changes.some(
                    (change) =>
                      [
                        'add',
                        'remove',
                        'replace',
                      ].includes(
                        change.type,
                      ),
                  )
                ) {
                  setIsDirty(true)
                }

                onNodesChange(changes)
              }}
              onEdgesChange={(changes) => {
                if (
                  !historicalView
                  && changes.some(
                    (change) =>
                      [
                        'add',
                        'remove',
                        'replace',
                      ].includes(
                        change.type,
                      ),
                  )
                ) {
                  setIsDirty(true)
                }

                onEdgesChange(changes)
              }}
              onConnect={onConnect}
              nodesDraggable={!historicalView}
              nodesConnectable={!historicalView}
              onNodeClick={(
                _event,
                node,
              ) => {
                if (!historicalView) {
                  setSelectedNodeId(
                    node.id,
                  )
                }
              }}
              onPaneClick={() => {
                setSelectedNodeId(null)
              }}
              fitView
              snapToGrid
              snapGrid={[20, 20]}
              minZoom={0.35}
              maxZoom={1.8}
              deleteKeyCode={
                historicalView
                  ? null
                  : [
                      'Backspace',
                      'Delete',
                    ]
              }
            >
              <Background
                gap={20}
                size={1}
              />

              <MiniMap
                pannable
                zoomable
              />

              <Controls />
            </ReactFlow>
          </div>
        </section>

          <NodeInspector
            nodeId={selectedNodeId}
            data={
              selectedNode
                ? selectedNode.data
                : null
            }
            onChange={updateSelectedNode}
            onClose={() => setSelectedNodeId(null)}
          />
      </main>
    </div>
  )
}


export default App
