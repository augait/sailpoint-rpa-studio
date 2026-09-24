type SelectorKind =
  | 'css'
  | 'testid'
  | 'role'
  | 'label'
  | 'placeholder'
  | 'text'
  | 'xpath'


type InspectorSelector = {
  kind: SelectorKind
  value: string
  name?: string | null
}


type InspectorStep = {
  id: string
  type: string
  name?: string
  enabled?: boolean
  selectors?: InspectorSelector[]
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


const actionTypes = [
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
]


const selectorKinds:
  SelectorKind[] = [
    'css',
    'testid',
    'role',
    'label',
    'placeholder',
    'text',
    'xpath',
  ]


const selectorActions =
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


const valueActions =
  new Set([
    'fill',
    'select',
    'assert_text',
    'check',
    'press',
  ])


function normalizeStepType(
  step: InspectorStep,
  type: string,
): InspectorStep {
  const needsSelector =
    selectorActions.has(type)

  const selectors =
    needsSelector
      ? (
          step.selectors?.length
            ? step.selectors
            : [
                {
                  kind: 'css' as const,
                  value: '',
                },
              ]
        )
      : step.selectors || []

  return {
    ...step,
    type,
    selectors,
    url:
      type === 'navigate'
        ? (
            step.url
            || '{{application.url}}'
          )
        : step.url || '',
    value:
      step.value || '',
    output:
      step.output || 'result',
    timeout_ms:
      step.timeout_ms ?? 10000,
    wait_ms:
      step.wait_ms ?? 1000,
    secret:
      type === 'fill'
        ? Boolean(step.secret)
        : false,
  }
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
        nextStep.name
        || nextStep.type
        || 'ACTION',
      subtitle:
        `${nextStep.type} · ${nextStep.id}`,
      step: nextStep,
    })
  }


  function changeStepType(
    type: string,
  ) {
    if (!data?.step) {
      return
    }

    const nextStep =
      normalizeStepType(
        data.step,
        type,
      )

    onChange({
      ...data,
      title:
        nextStep.name
        || nextStep.type,
      subtitle:
        `${nextStep.type} · ${nextStep.id}`,
      step: nextStep,
    })
  }


  function updateSelector(
    index: number,
    patch:
      Partial<InspectorSelector>,
  ) {
    if (!data?.step) {
      return
    }

    const selectors = [
      ...(data.step.selectors || []),
    ]

    selectors[index] = {
      ...selectors[index],
      ...patch,
    }

    updateStep({
      selectors,
    })
  }


  function addSelector() {
    if (!data?.step) {
      return
    }

    const selectors =
      data.step.selectors || []

    if (selectors.length >= 10) {
      return
    }

    updateStep({
      selectors: [
        ...selectors,
        {
          kind: 'css',
          value: '',
        },
      ],
    })
  }


  function removeSelector(
    index: number,
  ) {
    if (!data?.step) {
      return
    }

    updateStep({
      selectors:
        (
          data.step.selectors
          || []
        ).filter(
          (_, itemIndex) =>
            itemIndex !== index,
        ),
    })
  }


  const step = data.step

  const requiresSelectors =
    Boolean(
      step
      && selectorActions.has(
        step.type,
      ),
    )

  const usesValue =
    Boolean(
      step
      && valueActions.has(
        step.type,
      ),
    )


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
              <label className="inspector-check">
                <input
                  type="checkbox"
                  checked={
                    step.enabled !== false
                  }
                  onChange={(event) =>
                    updateStep({
                      enabled:
                        event.target.checked,
                    })
                  }
                />

                Etapa habilitada
              </label>

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

                <select
                  value={step.type}
                  onChange={(event) =>
                    changeStepType(
                      event.target.value,
                    )
                  }
                >
                  {actionTypes.map(
                    (type) => (
                      <option
                        value={type}
                        key={type}
                      >
                        {type}
                      </option>
                    ),
                  )}
                </select>
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
                      maxLength={2000}
                      onChange={(event) =>
                        updateStep({
                          url:
                            event.target.value,
                        })
                      }
                    />

                    <small>
                      Pode usar
                      {' {{application.url}}'}.
                    </small>
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
                              event.target.value,
                            ),
                        })
                      }
                    />
                  </label>
                )}

              {usesValue && (
                <label>
                  Valor

                  <textarea
                    value={
                      step.value || ''
                    }
                    maxLength={10000}
                    rows={3}
                    spellCheck={false}
                    onChange={(event) =>
                      updateStep({
                        value:
                          event.target.value,
                      })
                    }
                  />

                  <small>
                    Variáveis:
                    {' {{username}}, {{email}}, {{password}}'}
                  </small>
                </label>
              )}

              {step.type === 'fill' && (
                <label className="inspector-check">
                  <input
                    type="checkbox"
                    checked={
                      Boolean(
                        step.secret,
                      )
                    }
                    onChange={(event) =>
                      updateStep({
                        secret:
                          event.target.checked,
                      })
                    }
                  />

                  Valor sensível / segredo
                </label>
              )}

              {step.type === 'extract_text'
                && (
                  <label>
                    Output variable

                    <input
                      value={
                        step.output
                        || 'result'
                      }
                      maxLength={60}
                      onChange={(event) =>
                        updateStep({
                          output:
                            event.target.value,
                        })
                      }
                    />
                  </label>
                )}

              {step.type !== 'wait' && (
                <label>
                  Timeout (ms)

                  <input
                    type="number"
                    min={200}
                    max={60000}
                    value={
                      step.timeout_ms
                      ?? 10000
                    }
                    onChange={(event) =>
                      updateStep({
                        timeout_ms:
                          Number(
                            event.target.value,
                          ),
                      })
                    }
                  />
                </label>
              )}

              {requiresSelectors && (
                <div className="inspector__selectors">
                  <div className="inspector__section-head">
                    <span>
                      SELETORES
                    </span>

                    <button
                      type="button"
                      onClick={addSelector}
                      disabled={
                        (
                          step.selectors
                          || []
                        ).length >= 10
                      }
                    >
                      + Adicionar
                    </button>
                  </div>

                  {(
                    step.selectors
                    || []
                  ).map(
                    (
                      selector,
                      index,
                    ) => (
                      <div
                        className="inspector__selector-editor"
                        key={index}
                      >
                        <div className="inspector__selector-row">
                          <select
                            aria-label={
                              `Tipo seletor ${index + 1}`
                            }
                            value={
                              selector.kind
                            }
                            onChange={(event) =>
                              updateSelector(
                                index,
                                {
                                  kind:
                                    (event.target.value as SelectorKind),
                                },
                              )
                            }
                          >
                            {selectorKinds.map(
                              (kind) => (
                                <option
                                  value={kind}
                                  key={kind}
                                >
                                  {kind}
                                </option>
                              ),
                            )}
                          </select>

                          <button
                            type="button"
                            className="inspector__remove"
                            onClick={() =>
                              removeSelector(
                                index,
                              )
                            }
                            title="Remover seletor"
                          >
                            ×
                          </button>
                        </div>

                        <input
                          aria-label={
                            `Valor seletor ${index + 1}`
                          }
                          value={
                            selector.value
                          }
                          maxLength={1000}
                          placeholder={
                            selector.kind
                            === 'css'
                              ? '#username'
                              : 'valor do seletor'
                          }
                          onChange={(event) =>
                            updateSelector(
                              index,
                              {
                                value:
                                  event
                                    .target
                                    .value,
                              },
                            )
                          }
                        />

                        {selector.kind
                          === 'role'
                          && (
                            <input
                              aria-label={
                                `Nome role ${index + 1}`
                              }
                              value={
                                selector.name
                                || ''
                              }
                              maxLength={300}
                              placeholder="Nome acessível opcional"
                              onChange={(event) =>
                                updateSelector(
                                  index,
                                  {
                                    name:
                                      event
                                        .target
                                        .value,
                                  },
                                )
                              }
                            />
                          )}
                      </div>
                    ),
                  )}

                  {!step.selectors?.length && (
                    <small>
                      Esta ação precisa de
                      pelo menos um seletor.
                    </small>
                  )}
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
