type InspectorStep = {
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


export type InspectorNodeData = {
  kind:
    | 'start'
    | 'end'
    | 'action'
    | 'condition'
    | 'loop'
  title: string
  subtitle?: string
  expression?: string
  maxIterations?: number
  step?: InspectorStep
}


type NodeInspectorProps = {
  nodeId: string | null
  data: InspectorNodeData | null
  onChange: (
    data: InspectorNodeData,
  ) => void
  onClose: () => void
}


export function NodeInspector({
  nodeId,
  data,
  onChange,
  onClose,
}: NodeInspectorProps) {
  if (!nodeId || !data) {
    return (
      <aside className="inspector">
        <div className="inspector__empty">
          <span>PROPRIEDADES</span>

          <strong>
            Nenhum nó selecionado
          </strong>

          <p>
            Clique em um nó do canvas
            para editar suas propriedades.
          </p>
        </div>
      </aside>
    )
  }


  function update(
    patch: Partial<InspectorNodeData>,
  ) {
    onChange({
      ...data!,
      ...patch,
    })
  }


  function updateStep(
    patch: Partial<InspectorStep>,
  ) {
    if (!data?.step) {
      return
    }

    const nextStep = {
      ...data.step,
      ...patch,
    }

    onChange({
      ...data,
      title:
        patch.name !== undefined
          ? patch.name || data.title
          : data.title,
      subtitle:
        `${nextStep.type} · ${nextStep.id}`,
      step: nextStep,
    })
  }


  const step = data.step


  return (
    <aside className="inspector">
      <div className="inspector__head">
        <div>
          <span>
            PROPRIEDADES
          </span>

          <strong>
            {data.kind.toUpperCase()}
          </strong>
        </div>

        <button
          type="button"
          onClick={onClose}
          title="Fechar propriedades"
        >
          ×
        </button>
      </div>

      <div className="inspector__body">
        <label>
          Node ID

          <input
            value={nodeId}
            disabled
          />
        </label>

        {data.kind === 'condition' && (
          <label>
            Expression

            <textarea
              value={
                data.expression || ''
              }
              onChange={(event) =>
                update({
                  expression:
                    event.target.value,
                })
              }
              rows={4}
              spellCheck={false}
            />

            <small>
              Ex.: {'{{department}} == "IT"'}
            </small>
          </label>
        )}

        {data.kind === 'loop' && (
          <>
            <label>
              Expression

              <textarea
                value={
                  data.expression || ''
                }
                onChange={(event) =>
                  update({
                    expression:
                      event.target.value,
                  })
                }
                rows={4}
                spellCheck={false}
              />

              <small>
                Condição avaliada antes
                de cada iteração.
              </small>
            </label>

            <label>
              Máximo de iterações

              <input
                type="number"
                min={1}
                max={1000}
                value={
                  data.maxIterations ?? 1
                }
                onChange={(event) =>
                  update({
                    maxIterations:
                      Number(
                        event.target.value,
                      ),
                  })
                }
              />
            </label>
          </>
        )}

        {data.kind === 'action'
          && step
          && (
            <>
              <label>
                Nome

                <input
                  value={
                    step.name || ''
                  }
                  maxLength={120}
                  onChange={(event) =>
                    updateStep({
                      name:
                        event.target.value,
                    })
                  }
                />
              </label>

              <label>
                Tipo

                <input
                  value={step.type}
                  disabled
                />

                <small>
                  A troca de tipo será
                  adicionada junto ao
                  editor completo de ações.
                </small>
              </label>

              <label>
                Step ID

                <input
                  value={step.id}
                  disabled
                />
              </label>

              {step.type === 'navigate'
                && (
                  <label>
                    URL

                    <input
                      value={
                        step.url || ''
                      }
                      onChange={(event) =>
                        updateStep({
                          url:
                            event.target.value,
                        })
                      }
                    />
                  </label>
                )}

              {step.type === 'wait'
                && (
                  <label>
                    Wait (ms)

                    <input
                      type="number"
                      min={0}
                      max={30000}
                      value={
                        step.wait_ms
                        ?? 1000
                      }
                      onChange={(event) =>
                        updateStep({
                          wait_ms:
                            Number(
                              event
                                .target
                                .value,
                            ),
                        })
                      }
                    />
                  </label>
                )}

              {step.output !== undefined
                && (
                  <label>
                    Output variable

                    <input
                      value={
                        step.output
                      }
                      onChange={(event) =>
                        updateStep({
                          output:
                            event.target.value,
                        })
                      }
                    />
                  </label>
                )}

              {step.timeout_ms !== undefined
                && (
                  <label>
                    Timeout (ms)

                    <input
                      type="number"
                      min={200}
                      max={60000}
                      value={
                        step.timeout_ms
                      }
                      onChange={(event) =>
                        updateStep({
                          timeout_ms:
                            Number(
                              event
                                .target
                                .value,
                            ),
                        })
                      }
                    />
                  </label>
                )}

              {!!step.selectors?.length && (
                <div className="inspector__selectors">
                  <span>
                    SELETORES
                  </span>

                  {step.selectors.map(
                    (selector, index) => (
                      <div
                        className="inspector__selector"
                        key={
                          `${selector.kind}-${index}`
                        }
                      >
                        <strong>
                          {selector.kind}
                        </strong>

                        <code>
                          {selector.value}
                        </code>
                      </div>
                    ),
                  )}

                  <small>
                    Edição de selectors entra
                    no próximo bloco.
                  </small>
                </div>
              )}
            </>
          )}

        {(data.kind === 'start'
          || data.kind === 'end') && (
          <div className="inspector__notice">
            START e END fazem parte do
            contrato estrutural e não possuem
            propriedades editáveis.
          </div>
        )}
      </div>
    </aside>
  )
}
