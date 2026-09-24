import { useCallback } from 'react'
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
} from '@xyflow/react'

import '@xyflow/react/dist/style.css'
import './App.css'


type StudioNodeKind =
  | 'start'
  | 'end'
  | 'action'
  | 'condition'
  | 'loop'


type StudioNodeData = Record<string, unknown> & {
  kind: StudioNodeKind
  title: string
  subtitle?: string
  expression?: string
  maxIterations?: number
}


function StudioNode({ data }: NodeProps) {
  const node = data as StudioNodeData

  const isStart = node.kind === 'start'
  const isEnd = node.kind === 'end'
  const isCondition = node.kind === 'condition'
  const isLoop = node.kind === 'loop'

  return (
    <div className={`studio-node studio-node--${node.kind}`}>
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
          <strong>{node.title}</strong>

          {node.subtitle && (
            <small>{node.subtitle}</small>
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
          <div className="branch-label branch-label--left">
            true
          </div>

          <div className="branch-label branch-label--right">
            false
          </div>

          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            className="studio-handle studio-handle--left"
            style={{ left: '30%' }}
          />

          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            className="studio-handle studio-handle--right"
            style={{ left: '70%' }}
          />
        </>
      )}

      {isLoop && (
        <>
          <div className="branch-label branch-label--left">
            body
          </div>

          <div className="branch-label branch-label--right">
            exit
          </div>

          <Handle
            type="source"
            position={Position.Bottom}
            id="body"
            className="studio-handle studio-handle--left"
            style={{ left: '30%' }}
          />

          <Handle
            type="source"
            position={Position.Bottom}
            id="exit"
            className="studio-handle studio-handle--right"
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
      x: 180,
      y: 540,
    },
    data: {
      kind: 'action',
      title: 'Fluxo IT',
      subtitle: 'click · action_it',
    },
  },
  {
    id: 'loop_check',
    type: 'studio',
    position: {
      x: 650,
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
    id: '__end__',
    type: 'studio',
    position: {
      x: 430,
      y: 760,
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


function App() {
  const [nodes, setNodes, onNodesChange] =
    useNodesState(initialNodes)

  const [edges, setEdges, onEdgesChange] =
    useEdgesState(initialEdges)


  const onConnect = useCallback(
    (connection: Connection) => {
      const branch =
        connection.sourceHandle || 'default'

      setEdges((currentEdges) =>
        addEdge(
          {
            ...connection,
            id: `edge-${crypto.randomUUID()}`,
            label:
              branch === 'default'
                ? undefined
                : branch,
            markerEnd: {
              type: MarkerType.ArrowClosed,
            },
          },
          currentEdges,
        ),
      )
    },
    [setEdges],
  )


  const addNode = useCallback(
    (kind: StudioNodeKind) => {
      const id =
        kind === 'action'
          ? `action_${crypto.randomUUID().slice(0, 8)}`
          : kind === 'condition'
            ? `condition_${crypto.randomUUID().slice(0, 8)}`
            : `loop_${crypto.randomUUID().slice(0, 8)}`

      const count = nodes.length

      const data: StudioNodeData =
        kind === 'condition'
          ? {
              kind,
              title: 'CONDITION',
              expression: '{{variable}} == "value"',
            }
          : kind === 'loop'
            ? {
                kind,
                title: 'LOOP',
                expression: '{{status}} != "ready"',
                maxIterations: 5,
              }
            : {
                kind,
                title: 'Nova ação',
                subtitle: 'action',
              }

      setNodes((currentNodes) => [
        ...currentNodes,
        {
          id,
          type: 'studio',
          position: {
            x: 250 + (count % 4) * 170,
            y: 250 + count * 28,
          },
          data,
        },
      ])
    },
    [nodes.length, setNodes],
  )


  return (
    <div className="studio-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">
            AUTOMAÇÃO DE IDENTIDADES
          </span>

          <h1>Workflow Designer</h1>

          <p>
            React Flow · Phase 2
          </p>
        </div>

        <div className="topbar-actions">
          <button type="button">
            Validar
          </button>

          <button
            type="button"
            className="button-primary"
          >
            Salvar workflow
          </button>
        </div>
      </header>

      <main className="designer-layout">
        <aside className="palette">
          <div className="palette-header">
            <span>COMPONENTES</span>
            <strong>Adicionar nó</strong>
          </div>

          <button
            type="button"
            className="palette-item"
            onClick={() => addNode('action')}
          >
            <span className="palette-icon">⚙</span>

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
            onClick={() => addNode('condition')}
          >
            <span className="palette-icon">◇</span>

            <span>
              <strong>CONDITION</strong>
              <small>
                Branch true / false
              </small>
            </span>
          </button>

          <button
            type="button"
            className="palette-item"
            onClick={() => addNode('loop')}
          >
            <span className="palette-icon">↻</span>

            <span>
              <strong>LOOP</strong>
              <small>
                Body / exit com limite
              </small>
            </span>
          </button>

          <div className="palette-note">
            <strong>Graph Contract</strong>

            <p>
              Os handles já representam as branches
              aceitas pelo backend.
            </p>
          </div>
        </aside>

        <section className="canvas-panel">
          <div className="canvas-toolbar">
            <div>
              <strong>Canvas</strong>

              <span>
                Arraste nós e conecte os handles
              </span>
            </div>

            <div className="canvas-stats">
              <span>{nodes.length} nós</span>
              <span>{edges.length} conexões</span>
            </div>
          </div>

          <div className="canvas">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
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
