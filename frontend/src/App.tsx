import {
  useCallback,
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
import {
  getWorkflowVersion,
  listWorkflows,
  saveWorkflow,
  type AuthSession,
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
  selectors?: Array<{
    kind: string
    value: string
    name?: string | null
  }>
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

    if (
      node.kind === 'action'
      && !node.step
    ) {
      errors.push(
        `ACTION ${node.id} sem step`,
      )
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
        setShowValidation(false)

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

        const rows =
          await listWorkflows(
            session.access_token,
          )

        setWorkflows(rows)

        setSaveMessage(
          `Salvo · v${saved.current_version} · rev. ${saved.revision}`,
        )
      } catch (exc) {
        setSaveError(
          exc instanceof Error
            ? exc.message
            : 'Falha ao salvar workflow',
        )
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


  const onConnect = useCallback(
    (connection: Connection) => {
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
    [setNodes],
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
              || saveLoading
              || !['ADMIN', 'DEVELOPER'].includes(
                session.role,
              )
            }
            title={
              !selectedWorkflow
                ? 'Selecione um workflow real'
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
              onNodesChange={
                onNodesChange
              }
              onEdgesChange={
                onEdgesChange
              }
              onConnect={onConnect}
              fitView
              snapToGrid
              snapGrid={[20, 20]}
              minZoom={0.35}
              maxZoom={1.8}
              deleteKeyCode={[
                'Backspace',
                'Delete',
              ]}
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
      </main>
    </div>
  )
}


export default App
