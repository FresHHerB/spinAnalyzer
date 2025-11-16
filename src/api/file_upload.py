"""
API endpoints para upload e processamento de arquivos
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from pathlib import Path
import shutil
import uuid
from datetime import datetime
from loguru import logger

from src.parsers.unified_parser import UnifiedParser, HandFormat
from src.services.index_builder import IndexBuilder

router = APIRouter(prefix="/upload", tags=["upload"])

# Diretórios
UPLOAD_DIR = Path("uploads")
TEMP_DIR = UPLOAD_DIR / "temp"
PROCESSED_DIR = UPLOAD_DIR / "processed"
PHH_OUTPUT_DIR = Path("dataset/phh_hands")
INDICES_DIR = Path("indices")

# Criar diretórios se não existirem
for dir_path in [UPLOAD_DIR, TEMP_DIR, PROCESSED_DIR, PHH_OUTPUT_DIR, INDICES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Estado do processamento (em memória, substituir por DB em produção)
processing_jobs: Dict[str, Dict] = {}


def process_uploaded_file(
    job_id: str,
    file_path: Path,
    original_filename: str,
    filters: Optional[Dict] = None
):
    """
    Processa arquivo em background

    Args:
        job_id: ID do job de processamento
        file_path: Caminho do arquivo temporário
        original_filename: Nome original do arquivo
        filters: Filtros para aplicar
    """
    try:
        # Atualizar status
        processing_jobs[job_id]["status"] = "processing"
        processing_jobs[job_id]["stage"] = "parsing"

        logger.info(f"Iniciando processamento: {original_filename}")

        # Criar parser
        parser = UnifiedParser(output_dir=PHH_OUTPUT_DIR)

        # Processar arquivo
        phh_files = parser.parse_file(file_path, filters=filters)

        processing_jobs[job_id]["stage"] = "building_indices"
        processing_jobs[job_id]["phh_files_generated"] = len(phh_files)

        # Reconstruir índices se houver novos arquivos PHH
        if phh_files:
            logger.info(f"Reconstruindo índices com {len(phh_files)} novos arquivos...")

            # IndexBuilder reconstruirá todos os índices
            builder = IndexBuilder(
                phh_dir=PHH_OUTPUT_DIR,
                indices_dir=INDICES_DIR
            )

            stats = builder.build_all_indices()

            processing_jobs[job_id]["index_stats"] = stats

        # Mover arquivo processado
        processed_path = PROCESSED_DIR / f"{job_id}_{original_filename}"
        shutil.move(file_path, processed_path)

        # Atualizar status final
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["stage"] = "done"
        processing_jobs[job_id]["processed_path"] = str(processed_path)
        processing_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        processing_jobs[job_id]["parser_stats"] = parser.stats

        logger.success(f"Processamento concluído: {original_filename}")

    except Exception as e:
        logger.error(f"Erro ao processar {original_filename}: {e}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["error"] = str(e)
        processing_jobs[job_id]["failed_at"] = datetime.now().isoformat()


@router.post("/file")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    heads_up_only: bool = True
):
    """
    Upload de arquivo para processamento

    Args:
        file: Arquivo .txt (PokerStars) ou .xml (iPoker)
        heads_up_only: Filtrar apenas mãos heads-up

    Returns:
        job_id para monitoramento do processamento
    """
    # Validar extensão
    allowed_extensions = [".txt", ".xml", ".log"]
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado. Aceito: {', '.join(allowed_extensions)}"
        )

    # Gerar ID único para o job
    job_id = str(uuid.uuid4())

    # Salvar arquivo temporário
    temp_path = TEMP_DIR / f"{job_id}_{file.filename}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {e}")

    # Registrar job
    processing_jobs[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "file_size": temp_path.stat().st_size,
        "status": "queued",
        "stage": "queued",
        "created_at": datetime.now().isoformat(),
        "filters": {"heads_up_only": heads_up_only}
    }

    # Adicionar tarefa em background
    background_tasks.add_task(
        process_uploaded_file,
        job_id=job_id,
        file_path=temp_path,
        original_filename=file.filename,
        filters={"heads_up_only": heads_up_only}
    )

    logger.info(f"Arquivo recebido: {file.filename} ({temp_path.stat().st_size} bytes)")

    return {
        "job_id": job_id,
        "filename": file.filename,
        "status": "queued",
        "message": "Arquivo recebido e enfileirado para processamento"
    }


@router.post("/files")
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    heads_up_only: bool = True
):
    """
    Upload de múltiplos arquivos

    Args:
        files: Lista de arquivos
        heads_up_only: Filtrar apenas mãos heads-up

    Returns:
        Lista de job_ids
    """
    results = []

    for file in files:
        try:
            result = await upload_file(background_tasks, file, heads_up_only)
            results.append(result)
        except HTTPException as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": e.detail
            })

    return {
        "total_files": len(files),
        "jobs": results
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Consulta status de processamento

    Args:
        job_id: ID do job

    Returns:
        Status atual do processamento
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return processing_jobs[job_id]


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    Lista jobs de processamento

    Args:
        status: Filtrar por status (queued, processing, completed, failed)
        limit: Número máximo de resultados

    Returns:
        Lista de jobs
    """
    jobs = list(processing_jobs.values())

    # Filtrar por status
    if status:
        jobs = [j for j in jobs if j["status"] == status]

    # Ordenar por data (mais recentes primeiro)
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Limitar resultados
    jobs = jobs[:limit]

    return {
        "total": len(jobs),
        "jobs": jobs
    }


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """
    Remove job da lista

    Args:
        job_id: ID do job

    Returns:
        Confirmação
    """
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    job = processing_jobs[job_id]

    # Deletar arquivo processado se existir
    if "processed_path" in job:
        processed_path = Path(job["processed_path"])
        if processed_path.exists():
            processed_path.unlink()

    # Remover do registro
    del processing_jobs[job_id]

    return {"message": "Job removido com sucesso"}


@router.post("/rebuild-indices")
async def rebuild_indices(background_tasks: BackgroundTasks):
    """
    Reconstrói todos os índices FAISS

    Returns:
        job_id para monitoramento
    """
    job_id = str(uuid.uuid4())

    processing_jobs[job_id] = {
        "job_id": job_id,
        "filename": "index_rebuild",
        "status": "queued",
        "stage": "queued",
        "created_at": datetime.now().isoformat()
    }

    async def rebuild_task(job_id: str):
        try:
            processing_jobs[job_id]["status"] = "processing"
            processing_jobs[job_id]["stage"] = "building_indices"

            builder = IndexBuilder(
                phh_dir=PHH_OUTPUT_DIR,
                indices_dir=INDICES_DIR
            )

            stats = builder.build_all_indices()

            processing_jobs[job_id]["status"] = "completed"
            processing_jobs[job_id]["stage"] = "done"
            processing_jobs[job_id]["index_stats"] = stats
            processing_jobs[job_id]["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            processing_jobs[job_id]["status"] = "failed"
            processing_jobs[job_id]["error"] = str(e)

    background_tasks.add_task(rebuild_task, job_id)

    return {
        "job_id": job_id,
        "message": "Reconstrução de índices iniciada"
    }
