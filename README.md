# CARE-n8n

CARE-n8n 是 CARE 專案的本機 n8n 自動化流程環境，使用 Docker Compose 啟動 n8n 以及多媒體處理需要的本機服務。

目前包含：

- n8n：流程編排與 webhook 自動化
- Local ASR：FastAPI 語音轉文字服務
- Local Parser：FastAPI 檔案解析服務

> TTS 已從 n8n 專案移除；CARE 後端目前使用自己的本地 TTS 流程。

## 服務位址

啟動後可使用以下服務：

- n8n：`http://localhost:5678`
- local-asr：`http://localhost:8200`
- local-parser：`http://localhost:8100`

## 專案結構

- `docker-compose.yml`：n8n、ASR、Parser 的本機 compose 設定
- `local_asr/`：語音轉文字服務
- `local_parser/`：檔案解析服務
- `resources/workflows/`：n8n workflow 匯出檔與測試文件
- `local_asr_cache/`：Whisper / Hugging Face 模型快取
- `n8n_data/`：n8n 本機資料、設定與 workflows

## 啟動

### 1. 前置需求

- Docker Desktop
- Docker Compose（`docker compose`）

### 2. 啟動服務

在 `CARE-n8n` 目錄執行：

```bash
docker compose up -d
```

查看狀態與 logs：

```bash
docker compose ps
docker compose logs -f
```

### 3. 匯入 workflow

第一次啟動或新環境部署時，請先在 n8n UI 匯入 workflow。

1. 開啟 `http://localhost:5678`
2. 進入 n8n workflow 匯入頁面
3. 匯入 `resources/workflows/mutimedia process.json`
4. 啟用 workflow
5. 使用 curl、Postman 或 client 測試 webhook

## 本機服務測試

### ASR health check

```bash
curl http://localhost:8200/health
```

### ASR 轉錄測試

```bash
curl -X POST "http://localhost:8200/transcribe" \
  -F "file=@./sample.wav" \
  -F "language=zh" \
  -F "task=transcribe"
```

### Parser health check

```bash
curl http://localhost:8100/health
```

### Parser 支援格式

```bash
curl http://localhost:8100/supported-types
```

### Parser 解析測試

```bash
curl -X POST "http://localhost:8100/parse" \
  -F "file=@./sample.txt" \
  -F "include_metadata=true" \
  -F "source=manual-test"
```

## 環境變數

- `ASR_BACKEND`：ASR 後端，預設 `faster-whisper`
- `ASR_MODEL_ID`：ASR 模型，預設 `MediaTek-Research/Breeze-ASR-26`
- `ASR_DEVICE`：推論裝置，例如 `cuda:0` 或 `cpu`
- `ASR_TORCH_DTYPE`：推論 dtype，例如 `float16`、`bfloat16`、`float32`
- `ASR_CHUNK_LENGTH_SECONDS`：音訊切段秒數，預設 `30`
- `ASR_LONG_AUDIO_THRESHOLD_SECONDS`：長音訊門檻秒數，預設 `30`
- `WHISPER_MODEL`：faster-whisper fallback 模型，預設 `small`
- `WHISPER_COMPUTE_TYPE`：faster-whisper compute type，預設 `int8`
- `PARSER_MAX_FILE_SIZE_MB`：Parser 檔案大小上限，預設 `20`

## 停止服務

停止容器：

```bash
docker compose down
```

停止容器並刪除 volume：

```bash
docker compose down -v
```

## 注意事項

- 第一次啟動 ASR 時可能需要下載模型，時間會比較久。
- n8n webhook URL 會依 workflow active 狀態而不同，測試前請確認 workflow 已啟用。
- 若 Docker Desktop 在 build 或 pull image 後發生 API timeout，可重啟 Docker Desktop 後再執行 `docker compose up -d`。
