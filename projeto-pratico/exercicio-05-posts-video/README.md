# Exercício 05 - Posts de Vídeo

> Sistema completo de upload, encoding, e streaming de vídeos, mostrando diferentes abordagens e otimizações.

---

## 📋 Objetivo

Implementar sistema de vídeos escalável, explorando:
- Upload de arquivos grandes (multipart, chunked, resumable)
- Encoding de vídeo (FFmpeg, múltiplas resoluções)
- Streaming (HLS, DASH, progressive download)
- Storage (S3, MinIO, CDN)
- Background processing (Celery)
- Progress tracking em tempo real

---

## 🎯 O Que Vamos Aprender

1. **Upload**: multipart, chunked, resumable upload
2. **Storage**: local, S3, CDN
3. **Encoding**: FFmpeg, adaptive bitrate streaming
4. **Streaming**: HLS vs DASH vs Progressive
5. **Background jobs**: Celery para processing pesado
6. **Progress tracking**: WebSocket para updates em tempo real
7. **Otimizações**: thumbnail generation, metadata extraction

---

## 📊 Comparação de Abordagens

### 1. Upload de Vídeo

#### Abordagem A: Upload Simples (Até 100MB)

```python
# routes/videos.py
from fastapi import UploadFile, HTTPException
import aiofiles
import os

@app.post("/videos/upload")
async def upload_video_simple(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    """
    Upload simples: arquivo completo de uma vez

    ⚠️  Limitações:
    - Tamanho máximo limitado (100MB)
    - Sem retry se falhar
    - Bloqueia durante upload
    - Consome muita memória
    """
    # Validar tipo de arquivo
    if not file.content_type.startswith("video/"):
        raise HTTPException(400, "File must be a video")

    # Validar tamanho (max 100MB)
    MAX_SIZE = 100 * 1024 * 1024  # 100MB
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Seek back to start

    if size > MAX_SIZE:
        raise HTTPException(413, f"File too large. Max {MAX_SIZE / 1024 / 1024}MB")

    # Gerar nome único
    import uuid
    filename = f"{uuid.uuid4()}.mp4"
    filepath = f"/tmp/uploads/{filename}"

    # Salvar arquivo
    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Criar registro no banco
    video = Video(
        filename=filename,
        filepath=filepath,
        user_id=current_user.id,
        status="uploaded",
        size_bytes=size
    )
    db.add(video)
    db.commit()

    return {"video_id": video.id, "status": "uploaded"}
```

**Prós:**
- Simples de implementar
- Funciona para vídeos pequenos

**Contras:**
- ❌ Não escala para arquivos grandes (>100MB)
- ❌ Sem progresso de upload
- ❌ Sem retry
- ❌ Usa muita memória

**Use quando:** MVP, vídeos pequenos (<100MB)

---

#### Abordagem B: Chunked Upload (Até 5GB)

```python
# routes/videos.py
from fastapi import Request
from typing import Optional

@app.post("/videos/upload/init")
async def init_chunked_upload(
    filename: str,
    total_size: int,
    mime_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inicia upload em chunks

    Cliente divide arquivo em chunks de 5MB e envia um por vez
    """
    import uuid

    upload_id = str(uuid.uuid4())

    # Criar registro de upload
    upload = VideoUpload(
        upload_id=upload_id,
        user_id=current_user.id,
        filename=filename,
        total_size=total_size,
        mime_type=mime_type,
        chunks_uploaded=0,
        status="in_progress"
    )
    db.add(upload)
    db.commit()

    return {
        "upload_id": upload_id,
        "chunk_size": 5 * 1024 * 1024,  # 5MB chunks
        "total_chunks": (total_size // (5 * 1024 * 1024)) + 1
    }


@app.post("/videos/upload/chunk")
async def upload_chunk(
    upload_id: str,
    chunk_number: int,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload de um chunk

    Cliente envia chunks sequencialmente
    Servidor vai montando o arquivo
    """
    # Buscar upload
    upload = db.query(VideoUpload).filter(
        VideoUpload.upload_id == upload_id,
        VideoUpload.user_id == current_user.id
    ).first()

    if not upload:
        raise HTTPException(404, "Upload not found")

    if upload.status != "in_progress":
        raise HTTPException(400, "Upload is not in progress")

    # Salvar chunk
    chunk_dir = f"/tmp/uploads/{upload_id}"
    os.makedirs(chunk_dir, exist_ok=True)
    chunk_path = f"{chunk_dir}/chunk_{chunk_number}"

    async with aiofiles.open(chunk_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Atualizar progresso
    upload.chunks_uploaded += 1

    # Calcular progresso
    total_chunks = (upload.total_size // (5 * 1024 * 1024)) + 1
    progress = (upload.chunks_uploaded / total_chunks) * 100

    db.commit()

    return {
        "chunk_number": chunk_number,
        "progress": round(progress, 2),
        "status": "chunk_uploaded"
    }


@app.post("/videos/upload/complete")
async def complete_chunked_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Finaliza upload: junta todos os chunks

    Inicia encoding em background
    """
    upload = db.query(VideoUpload).filter(
        VideoUpload.upload_id == upload_id,
        VideoUpload.user_id == current_user.id
    ).first()

    if not upload:
        raise HTTPException(404, "Upload not found")

    # Juntar chunks
    chunk_dir = f"/tmp/uploads/{upload_id}"
    output_path = f"/tmp/videos/{upload_id}.mp4"

    # Merge chunks
    with open(output_path, "wb") as outfile:
        chunk_num = 0
        while True:
            chunk_path = f"{chunk_dir}/chunk_{chunk_num}"
            if not os.path.exists(chunk_path):
                break

            with open(chunk_path, "rb") as infile:
                outfile.write(infile.read())

            chunk_num += 1

    # Remover chunks
    import shutil
    shutil.rmtree(chunk_dir)

    # Criar vídeo no banco
    video = Video(
        user_id=current_user.id,
        filename=upload.filename,
        filepath=output_path,
        size_bytes=upload.total_size,
        status="processing"
    )
    db.add(video)
    upload.status = "completed"
    db.commit()

    # Iniciar encoding em background (Celery)
    from tasks import encode_video_task
    encode_video_task.delay(video.id)

    return {
        "video_id": video.id,
        "status": "processing",
        "message": "Video is being encoded"
    }
```

**Prós:**
- ✅ Suporta arquivos grandes (até 5GB)
- ✅ Progresso de upload
- ✅ Pode fazer retry de chunks individuais
- ✅ Menor uso de memória

**Contras:**
- Mais complexo
- Cliente precisa implementar chunking

**Use quando:** Arquivos grandes (>100MB), precisa progresso

---

#### Abordagem C: Resumable Upload com S3 Multipart (Produção)

```python
# services/s3_upload.py
import boto3
from botocore.config import Config

class S3UploadService:
    """
    Upload para S3 com multipart upload

    Vantagens:
    - Resumable: pode pausar e continuar
    - Paralelo: múltiplos chunks simultâneos
    - Gerenciado pela AWS
    - Até 5TB por arquivo
    """

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version='s3v4')
        )
        self.bucket = settings.S3_BUCKET

    def initiate_multipart_upload(
        self,
        key: str,
        content_type: str
    ) -> str:
        """Inicia multipart upload no S3"""
        response = self.s3_client.create_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            ContentType=content_type,
            # Configurar ACL e storage class
            ACL='private',
            StorageClass='INTELLIGENT_TIERING'  # Otimiza custos automaticamente
        )

        return response['UploadId']

    def generate_presigned_url_for_part(
        self,
        key: str,
        upload_id: str,
        part_number: int,
        expires_in: int = 3600
    ) -> str:
        """
        Gera URL presigned para cliente fazer upload direto para S3

        Cliente não precisa passar pelo servidor!
        Reduz carga no servidor drasticamente
        """
        url = self.s3_client.generate_presigned_url(
            'upload_part',
            Params={
                'Bucket': self.bucket,
                'Key': key,
                'UploadId': upload_id,
                'PartNumber': part_number
            },
            ExpiresIn=expires_in
        )

        return url

    def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: list
    ):
        """Finaliza multipart upload"""
        response = self.s3_client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )

        return response['Location']  # URL do arquivo no S3

    def abort_multipart_upload(self, key: str, upload_id: str):
        """Cancela upload (libera storage)"""
        self.s3_client.abort_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id
        )


# routes/videos.py
@app.post("/videos/upload/s3/init")
async def init_s3_upload(
    filename: str,
    content_type: str,
    total_size: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inicia upload direto para S3

    Cliente receberá URLs presigned e fará upload DIRETO para S3
    Servidor não processa bytes do vídeo!
    """
    s3_service = S3UploadService()

    # Gerar key única no S3
    import uuid
    key = f"videos/{current_user.id}/{uuid.uuid4()}/{filename}"

    # Iniciar multipart upload no S3
    upload_id = s3_service.initiate_multipart_upload(key, content_type)

    # Calcular número de partes (5MB cada)
    PART_SIZE = 5 * 1024 * 1024
    total_parts = (total_size // PART_SIZE) + 1

    # Gerar URLs presigned para cada parte
    presigned_urls = []
    for part_num in range(1, total_parts + 1):
        url = s3_service.generate_presigned_url_for_part(
            key, upload_id, part_num
        )
        presigned_urls.append({
            "part_number": part_num,
            "url": url
        })

    # Salvar no banco
    video = Video(
        user_id=current_user.id,
        filename=filename,
        s3_key=key,
        s3_upload_id=upload_id,
        size_bytes=total_size,
        status="uploading"
    )
    db.add(video)
    db.commit()

    return {
        "video_id": video.id,
        "upload_id": upload_id,
        "part_size": PART_SIZE,
        "total_parts": total_parts,
        "presigned_urls": presigned_urls
    }


@app.post("/videos/upload/s3/complete")
async def complete_s3_upload(
    video_id: int,
    parts: List[dict],  # [{"part_number": 1, "etag": "abc..."}]
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Finaliza upload S3

    Cliente já fez upload direto para S3
    Servidor apenas finaliza e inicia encoding
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(404, "Video not found")

    s3_service = S3UploadService()

    # Completar multipart upload no S3
    s3_url = s3_service.complete_multipart_upload(
        video.s3_key,
        video.s3_upload_id,
        parts
    )

    # Atualizar vídeo
    video.s3_url = s3_url
    video.status = "processing"
    db.commit()

    # Iniciar encoding em background
    from tasks import encode_video_task
    encode_video_task.delay(video.id)

    return {
        "video_id": video.id,
        "s3_url": s3_url,
        "status": "processing"
    }
```

**Prós:**
- ✅ Upload DIRETO para S3 (servidor não processa bytes!)
- ✅ Resumable (pode pausar e continuar)
- ✅ Paralelo (múltiplos chunks simultâneos)
- ✅ Até 5TB por arquivo
- ✅ Reduz carga no servidor drasticamente

**Contras:**
- Requer AWS (ou MinIO compatível)
- Cliente mais complexo

**Use quando:** Produção, arquivos grandes, precisa escalar

---

## 🎬 Encoding de Vídeo

### FFmpeg: A Ferramenta Universal

```python
# tasks/video_encoding.py
from celery import Task
import subprocess
import os

@celery_app.task(bind=True, name='tasks.encode_video')
def encode_video_task(self, video_id: int):
    """
    Encoda vídeo em múltiplas resoluções

    Gera:
    - 1080p (FullHD)
    - 720p (HD)
    - 480p (SD)
    - 360p (Mobile)
    - Thumbnails
    """
    db = SessionLocal()
    video = db.query(Video).filter(Video.id == video_id).first()

    try:
        video.status = "encoding"
        db.commit()

        # Extrair metadados
        metadata = extract_video_metadata(video.filepath)
        video.duration_seconds = metadata['duration']
        video.width = metadata['width']
        video.height = metadata['height']
        db.commit()

        # Definir resoluções baseado na resolução original
        resolutions = get_encoding_resolutions(metadata['height'])

        # Encodar cada resolução
        for resolution in resolutions:
            output_path = encode_resolution(
                video.filepath,
                resolution,
                on_progress=lambda progress: update_progress(video_id, progress)
            )

            # Salvar variant no banco
            variant = VideoVariant(
                video_id=video.id,
                resolution=resolution['height'],
                filepath=output_path,
                bitrate=resolution['bitrate']
            )
            db.add(variant)
            db.commit()

        # Gerar thumbnail
        thumbnail_path = generate_thumbnail(video.filepath, at_second=1)
        video.thumbnail_url = upload_to_s3(thumbnail_path)

        # Gerar HLS manifest
        generate_hls_manifest(video)

        video.status = "ready"
        db.commit()

    except Exception as e:
        video.status = "error"
        video.error_message = str(e)
        db.commit()
        raise

    finally:
        db.close()


def extract_video_metadata(filepath: str) -> dict:
    """Extrai metadados do vídeo com FFprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,duration,bit_rate',
        '-of', 'json',
        filepath
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    stream = data['streams'][0]
    return {
        'width': int(stream['width']),
        'height': int(stream['height']),
        'duration': float(stream.get('duration', 0)),
        'bitrate': int(stream.get('bit_rate', 0))
    }


def get_encoding_resolutions(original_height: int) -> list:
    """
    Decide quais resoluções encodar baseado na original

    Exemplo: vídeo 1080p → encodar 720p, 480p, 360p
    """
    all_resolutions = [
        {'height': 1080, 'bitrate': '5000k', 'name': '1080p'},
        {'height': 720, 'bitrate': '2800k', 'name': '720p'},
        {'height': 480, 'bitrate': '1400k', 'name': '480p'},
        {'height': 360, 'bitrate': '800k', 'name': '360p'},
    ]

    # Só encodar resoluções menores ou iguais à original
    return [r for r in all_resolutions if r['height'] <= original_height]


def encode_resolution(
    input_path: str,
    resolution: dict,
    on_progress=None
) -> str:
    """
    Encoda vídeo em uma resolução específica

    Codec: H.264 (compatibilidade universal)
    Audio: AAC
    Container: MP4
    """
    output_path = input_path.replace('.mp4', f"_{resolution['name']}.mp4")

    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf', f"scale=-2:{resolution['height']}",  # Manter aspect ratio
        '-c:v', 'libx264',  # Codec H.264
        '-preset', 'medium',  # Balance speed/quality
        '-crf', '23',  # Constant Rate Factor (qualidade)
        '-c:a', 'aac',  # Audio codec
        '-b:a', '128k',  # Audio bitrate
        '-b:v', resolution['bitrate'],  # Video bitrate
        '-movflags', '+faststart',  # Otimizar para streaming
        '-progress', 'pipe:1',  # Progress para stdout
        '-y',  # Overwrite
        output_path
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    # Parsear progresso
    for line in process.stdout:
        if line.startswith('out_time_ms='):
            time_us = int(line.split('=')[1])
            # Calcular % baseado na duração
            if on_progress:
                on_progress(time_us)

    process.wait()

    if process.returncode != 0:
        raise Exception(f"FFmpeg failed with code {process.returncode}")

    return output_path


def generate_thumbnail(filepath: str, at_second: int = 1) -> str:
    """Gera thumbnail do vídeo"""
    output_path = filepath.replace('.mp4', '_thumb.jpg')

    cmd = [
        'ffmpeg',
        '-i', filepath,
        '-ss', str(at_second),  # Segundo do vídeo
        '-vframes', '1',  # 1 frame apenas
        '-vf', 'scale=640:360',  # Tamanho do thumbnail
        '-y',
        output_path
    ]

    subprocess.run(cmd, check=True)
    return output_path


def generate_hls_manifest(video: Video):
    """
    Gera manifest HLS para adaptive streaming

    HLS (HTTP Live Streaming):
    - Divide vídeo em segmentos de 6 segundos
    - Cliente escolhe resolução dinamicamente
    - Usado por: Apple, YouTube, Twitch
    """
    variants = video.variants  # 1080p, 720p, 480p, 360p

    # Gerar segmentos HLS para cada variant
    for variant in variants:
        output_dir = f"/tmp/hls/{video.id}/{variant.resolution}p"
        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-i', variant.filepath,
            '-codec', 'copy',  # Não re-encodar
            '-start_number', '0',
            '-hls_time', '6',  # Segmentos de 6s
            '-hls_list_size', '0',  # Todos os segmentos no playlist
            '-f', 'hls',
            f"{output_dir}/index.m3u8"
        ]

        subprocess.run(cmd, check=True)

        # Upload para S3
        upload_directory_to_s3(output_dir, f"videos/{video.id}/{variant.resolution}p")

    # Gerar master playlist
    master_playlist = generate_master_playlist(variants)
    upload_to_s3_text(master_playlist, f"videos/{video.id}/master.m3u8")


def generate_master_playlist(variants: list) -> str:
    """
    Gera master playlist HLS

    Cliente baixa este arquivo primeiro e escolhe qual resolução usar
    """
    lines = ['#EXTM3U', '#EXT-X-VERSION:3']

    for variant in variants:
        lines.append(
            f"#EXT-X-STREAM-INF:BANDWIDTH={variant.bitrate},RESOLUTION={variant.width}x{variant.height}"
        )
        lines.append(f"{variant.resolution}p/index.m3u8")

    return '\n'.join(lines)
```

---

## 📺 Streaming: HLS vs DASH vs Progressive

### HLS (HTTP Live Streaming) - Recomendado

```
✅ Vantagens:
- Adaptive bitrate (muda qualidade automaticamente)
- Compatibilidade universal (iOS, Android, Web)
- Funciona com CDN normal (não precisa streaming server)
- Usado por YouTube, Twitch, Netflix

❌ Desvantagens:
- Latência ~10-30s (não é tempo real)
- Requer encoding em múltiplas resoluções

📁 Estrutura:
videos/
  123/
    master.m3u8       ← Cliente baixa isso primeiro
    1080p/
      index.m3u8      ← Playlist dos segmentos
      segment0.ts
      segment1.ts
      ...
    720p/
      index.m3u8
      segment0.ts
      ...
```

### DASH (Dynamic Adaptive Streaming over HTTP)

```
Similar ao HLS mas padrão aberto
Usado por YouTube (com HLS como fallback)

✅ Vantagens:
- Padrão ISO
- Melhor compressão (codec-agnostic)

❌ Desvantagens:
- iOS não suporta nativamente
- Mais complexo

Use quando: precisa de MUITO controle sobre codecs
```

### Progressive Download

```python
@app.get("/videos/{video_id}/stream")
async def stream_video_progressive(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Streaming progressivo (simples)

    Cliente baixa arquivo MP4 direto
    Pode fazer seek (pular para frente)
    """
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video or video.status != "ready":
        raise HTTPException(404, "Video not found or not ready")

    # Suporte para Range requests (seek)
    range_header = request.headers.get("range")

    return FileResponse(
        video.filepath,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename={video.filename}"
        }
    )
```

**Use quando:** Vídeos pequenos, não precisa adaptive bitrate

---

## 📊 Comparação Final

| Aspecto | Upload Simples | Chunked Upload | S3 Multipart |
|---------|----------------|----------------|--------------|
| **Tamanho max** | 100MB | 5GB | 5TB |
| **Resumable** | ❌ | ❌ | ✅ |
| **Progresso** | ❌ | ✅ | ✅ |
| **Carga servidor** | Alta | Alta | Baixa |
| **Complexidade** | Baixa | Média | Alta |
| **Produção** | ❌ | ⚠️  | ✅ |

| Aspecto | Progressive | HLS | DASH |
|---------|------------|-----|------|
| **Adaptive** | ❌ | ✅ | ✅ |
| **Compatibilidade** | Universal | Universal | ⚠️ iOS |
| **Latência** | Baixa | Média | Média |
| **Complexidade** | Baixa | Média | Alta |
| **Use em** | MVP | Produção | Casos específicos |

---

## 🎯 Decisão: Qual Usar?

### Upload:
- **MVP/Protótipo**: Upload simples
- **Produto real**: Chunked upload
- **Produção escalável**: S3 Multipart com presigned URLs

### Streaming:
- **MVP**: Progressive download
- **Produção**: HLS (adaptive bitrate)
- **Casos específicos**: DASH (controle total de codecs)

---

## 🎓 Conceitos Aprendidos

1. ✅ **Multipart upload**: Arquivos grandes em partes
2. ✅ **Presigned URLs**: Upload direto para S3
3. ✅ **FFmpeg**: Encoding, thumbnails, metadata
4. ✅ **Adaptive bitrate**: Cliente escolhe resolução
5. ✅ **HLS**: Streaming universal
6. ✅ **Background jobs**: Celery para encoding
7. ✅ **Progress tracking**: WebSocket para tempo real

---

## 📚 Próximos Passos

- **Exercício 06**: Likes e comentários
- **Exercício 07**: Feed personalizado com algoritmo
- **Exercício 08**: Notificações em tempo real
- **Exercício 09**: Search e recomendações

---

**Agora você sabe criar um sistema completo de vídeos! 🎬**
