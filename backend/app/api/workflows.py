from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select, update

from backend.app.core.database import get_db
from backend.app.core.security import current_user, roles
from backend.app.models.entities import (
    Application,
    Workflow,
    WorkflowVersion,
    utcnow,
)
from backend.app.rpa.graph import WorkflowGraph, linear_graph_from_steps
from backend.app.schemas.contracts import WorkflowIn
from backend.app.services.audit_service import audit


router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])


class WorkflowWriteIn(WorkflowIn):
    #
    # Durante a transição da UI antiga, graph é opcional.
    #
    # Sem graph:
    #   steps -> linear_graph_from_steps()
    #
    # Com graph:
    #   o grafo enviado vira a fonte funcional da versão.
    #
    graph: dict | None = None


def workflow_payload(
    body: WorkflowWriteIn,
) -> tuple[list[dict], dict]:
    if body.graph is None:
        steps = [
            step.model_dump()
            for step in body.steps
        ]

        graph = linear_graph_from_steps(
            steps
        ).model_dump(mode="json")

        return steps, graph

    try:
        validated_graph = WorkflowGraph.model_validate(
            body.graph
        )

    except ValidationError as exc:
        #
        # Não devolvemos o conteúdo completo do erro.
        # O graph pode referenciar dados sensíveis.
        #
        raise HTTPException(
            422,
            "Graph inválido",
        ) from exc

    #
    # Workflow.steps continua existindo temporariamente
    # para compatibilidade com a UI da Fase 1.
    #
    # Para graph nativo, ele é DERIVADO dos ACTION nodes
    # em vez de confiar em uma segunda fonte enviada pelo
    # cliente.
    #
    steps = [
        node.step.model_dump()
        for node in validated_graph.nodes
        if (
            node.kind == "action"
            and node.step is not None
        )
    ]

    step_ids = [
        step["id"]
        for step in steps
    ]

    if len(step_ids) != len(set(step_ids)):
        raise HTTPException(
            422,
            "IDs de etapas duplicados no graph",
        )

    return (
        steps,
        validated_graph.model_dump(
            mode="json"
        ),
    )


def current_version(db, workflow: Workflow, lock: bool = False) -> WorkflowVersion:
    query = select(WorkflowVersion).where(
        WorkflowVersion.workflow_id == workflow.id,
        WorkflowVersion.version == workflow.current_version,
    )

    if lock:
        query = query.with_for_update()

    version = db.scalar(query)

    if not version:
        raise HTTPException(
            409,
            "Workflow sem versão atual válida",
        )

    return version


def apply_version_data(
    version: WorkflowVersion,
    body: WorkflowWriteIn,
    steps: list[dict],
    graph: dict,
):
    version.application_id = body.application_id
    version.name = body.name
    version.operation = body.operation
    version.steps = steps
    version.graph = graph
    version.timeout_seconds = body.timeout_seconds


@router.get("")
def list_workflows(
    user=Depends(current_user),
    db=Depends(get_db),
):
    return db.scalars(
        select(Workflow)
        .order_by(Workflow.updated_at.desc())
        .limit(500)
    ).all()


@router.get("/{workflow_id}")
def get_workflow(
    workflow_id: str,
    user=Depends(current_user),
    db=Depends(get_db),
):
    record = db.get(Workflow, workflow_id)

    if not record:
        raise HTTPException(404, "Workflow não encontrado")

    return record


@router.get("/{workflow_id}/versions")
def list_versions(
    workflow_id: str,
    user=Depends(current_user),
    db=Depends(get_db),
):
    if not db.get(Workflow, workflow_id):
        raise HTTPException(404, "Workflow não encontrado")

    return db.scalars(
        select(WorkflowVersion)
        .where(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version.desc())
    ).all()


@router.get("/{workflow_id}/versions/{version_number}")
def get_version(
    workflow_id: str,
    version_number: int,
    user=Depends(current_user),
    db=Depends(get_db),
):
    version = db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == version_number,
        )
    )

    if not version:
        raise HTTPException(404, "Versão não encontrada")

    return version


@router.post("", status_code=201)
def create(
    body: WorkflowWriteIn,
    request: Request,
    user=Depends(roles("ADMIN", "DEVELOPER")),
    db=Depends(get_db),
):
    if not db.get(Application, body.application_id):
        raise HTTPException(404, "Aplicação não encontrada")

    steps, graph = workflow_payload(body)

    record = Workflow(
        application_id=body.application_id,
        name=body.name,
        operation=body.operation,
        steps=steps,
        timeout_seconds=body.timeout_seconds,
        current_version=1,
    )

    db.add(record)
    db.flush()

    version = WorkflowVersion(
        workflow_id=record.id,
        version=1,
        status="DRAFT",
        application_id=record.application_id,
        name=record.name,
        operation=record.operation,
        steps=steps,
        graph=graph,
        timeout_seconds=record.timeout_seconds,
        created_by=user.id,
    )

    db.add(version)

    audit(
        db,
        user.username,
        "WORKFLOW_CREATED",
        record.id,
        request.client.host,
        version=1,
    )

    db.commit()
    db.refresh(record)

    return record


@router.put("/{workflow_id}")
def save(
    workflow_id: str,
    body: WorkflowWriteIn,
    request: Request,
    user=Depends(roles("ADMIN", "DEVELOPER")),
    db=Depends(get_db),
):
    if body.revision is None:
        raise HTTPException(
            422,
            "Informe revision para evitar sobrescrever outra edição",
        )

    if not db.get(Application, body.application_id):
        raise HTTPException(404, "Aplicação não encontrada")

    steps, graph = workflow_payload(body)

    record = db.scalar(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .with_for_update()
    )

    if not record:
        raise HTTPException(404, "Workflow não encontrado")

    if record.revision != body.revision:
        raise HTTPException(
            409,
            "Workflow alterado por outro usuário; recarregue",
        )

    version = current_version(db, record, lock=True)

    #
    # Enquanto a versão atual for DRAFT, salvar apenas
    # atualiza esse draft.
    #
    if version.status == "DRAFT":
        apply_version_data(
            version,
            body,
            steps,
            graph,
        )

    #
    # Uma versão publicada é imutável.
    # A primeira edição após o publish cria automaticamente
    # uma nova versão DRAFT.
    #
    elif version.status == "PUBLISHED":
        new_version_number = record.current_version + 1

        version = WorkflowVersion(
            workflow_id=record.id,
            version=new_version_number,
            status="DRAFT",
            application_id=body.application_id,
            name=body.name,
            operation=body.operation,
            steps=steps,
            graph=graph,
            timeout_seconds=body.timeout_seconds,
            created_by=user.id,
        )

        db.add(version)

        record.current_version = new_version_number

        audit(
            db,
            user.username,
            "WORKFLOW_VERSION_CREATED",
            record.id,
            request.client.host,
            version=new_version_number,
        )

    else:
        raise HTTPException(
            409,
            "A versão atual não pode ser editada",
        )

    #
    # Workflow continua representando o draft atual
    # para manter compatibilidade com a UI da Fase 1.
    #
    record.application_id = body.application_id
    record.name = body.name
    record.operation = body.operation
    record.steps = steps
    record.timeout_seconds = body.timeout_seconds

    record.revision += 1
    record.updated_at = utcnow()

    audit(
        db,
        user.username,
        "WORKFLOW_UPDATED",
        record.id,
        request.client.host,
        revision=record.revision,
        version=record.current_version,
    )

    db.commit()
    db.refresh(record)

    return record


@router.post("/{workflow_id}/publish")
def publish(
    workflow_id: str,
    request: Request,
    user=Depends(roles("ADMIN", "DEVELOPER")),
    db=Depends(get_db),
):
    workflow = db.scalar(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .with_for_update()
    )

    if not workflow:
        raise HTTPException(404, "Workflow não encontrado")

    version = current_version(
        db,
        workflow,
        lock=True,
    )

    #
    # Publish é idempotente.
    #
    if version.status == "PUBLISHED":
        return version

    if version.status != "DRAFT":
        raise HTTPException(
            409,
            "Somente versões DRAFT podem ser publicadas",
        )

    if not any(step.get("enabled", True) for step in version.steps):
        raise HTTPException(
            422,
            "Adicione uma etapa habilitada antes de publicar",
        )

    #
    # Apenas uma versão PUBLISHED por workflow.
    #
    db.execute(
        update(WorkflowVersion)
        .where(
            WorkflowVersion.workflow_id == workflow.id,
            WorkflowVersion.status == "PUBLISHED",
            WorkflowVersion.id != version.id,
        )
        .values(status="ARCHIVED")
    )

    version.status = "PUBLISHED"
    version.published_at = utcnow()

    audit(
        db,
        user.username,
        "WORKFLOW_PUBLISHED",
        workflow.id,
        request.client.host,
        version=version.version,
    )

    db.commit()
    db.refresh(version)

    return version
