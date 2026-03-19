# CARE-n8n

CARE-n8n 是一套以 Docker Compose 為核心的本機自動化流程環境，整合以下能力：

- n8n：流程編排與 webhook 自動化
- Local ASR：以 FastAPI + faster-whisper 提供語音轉文字 API
- Local Parser：本地解析服務（供 workflow 串接使用）

此專案適合用於「先接收音訊，再經由 workflow 呼叫本地服務處理」的開發場景。

## 快速簡介

目前 `docker-compose.yml` 主要服務與連接埠如下：

- `n8n`：`http://localhost:5678`
- `local-asr`：`http://localhost:8200`
- `local-parser`：`http://localhost:8100`

## 專案結構

- `docker-compose.yml`：整體服務編排
- `local_asr/`：ASR 服務（FastAPI）
- `local_parser/`：Parser 服務
- `local_asr_cache/`：Whisper/Hugging Face 模型快取
- `n8n_data/`：n8n 設定、資料與 workflows

## 開發指引

### 1. 先決條件

- 已安裝 Docker Desktop
- 可使用 `docker compose` 指令

### 2. 啟動環境

在專案根目錄執行：

```bash
docker compose up -d
```

查看狀態：

```bash
docker compose ps
docker compose logs -f
```

### 3. 先匯入 workflow，再開始使用

第一次啟動或新環境部署時，請先在 n8n UI 匯入 workflow，再進行 webhook 或 API 測試。

1. 開啟 `http://localhost:5678`
2. 進入 n8n 的 workflow 匯入頁面（Import）
3. 匯入專案提供的 workflow JSON
4. 啟用 workflow（Active）
5. 再用 curl 或其他 client 呼叫 webhook

> 若尚未匯入 workflow，webhook URL 可能不存在或回傳非預期結果。

### 4. 本地服務驗證

ASR 健康檢查：

```bash
curl http://localhost:8200/health
```

ASR 轉錄測試：

```bash
curl -X POST "http://localhost:8200/transcribe" \
  -F "file=@./sample.wav" \
  -F "language=zh" \
  -F "task=transcribe"
```

Parser 健康檢查：

```bash
curl http://localhost:8100/health
```

Parser 支援格式查詢：

```bash
curl http://localhost:8100/supported-types
```

Parser 解析測試：

```bash
curl -X POST "http://localhost:8100/parse" \
  -F "file=@./sample.txt" \
  -F "include_metadata=true" \
  -F "source=manual-test"
```

## 常用環境變數

- `WHISPER_MODEL`：預設 `small`，可改為 `tiny`、`base`、`medium`、`large-v3`
- `WHISPER_COMPUTE_TYPE`：預設 `int8`，可依硬體改為 `float16`
- `PARSER_MAX_FILE_SIZE_MB`：Parser 服務檔案大小限制（預設 `20`）

## 停止與清理

停止服務：

```bash
docker compose down
```

連同 volume 一起清除（會刪除資料）：

```bash
docker compose down -v
```

## 備註

- 第一次載入 Whisper 模型會較慢，屬正常現象。
- 若連接埠衝突，請調整 `docker-compose.yml` 的對外映射設定。
