# ?? API ?踵?蝷箔? & ??Ⅳ

## 璁膩

?祆?瑼?蝷箸???賜? API ?踵??澆????? HTTP ??Ⅳ??

---

## 憭?擃???API

### Webhook URL
```
POST http://localhost:5678/webhook/multimedia-process
```

### ?????踵?

#### ?喲/閬頧???
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "type": "audio",
  "data": {
    "text": "頧????砍摰?,
    "confidence": 0.95,
    "language": "zh",
    "duration_seconds": 120
  },
  "processedAt": "2024-07-08T10:30:45Z"
}
```

#### ?? OCR ??
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "type": "image",
  "data": {
    "text": "??銝剔????批捆\n?憭?\n??霅蝯?",
    "languages": [
      {
        "code": "zh",
        "confidence": 0.98
      }
    ],
    "primary_language": "zh",
    "text_regions": 3
  },
  "processedAt": "2024-07-08T10:30:45Z"
}
```

#### ??閫????
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "type": "document",
  "data": {
    "text": "????瑼??砍摰?,
    "pages": 5,
    "format": "pdf",
    "metadata": {
      "title": "??璅?",
      "author": "雿?蝔?,
      "created": "2024-07-01"
    }
  },
  "processedAt": "2024-07-08T10:30:45Z"
}
```

### ???航炊?踵?

#### 瑼?憿?銝??(415)
```json
HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json

{
  "status": "error",
  "code": "UNSUPPORTED_FILE_TYPE",
  "message": "File type exe is not supported",
  "supported": {
    "audio": ["mp3", "wav", "m4a", "flac", "ogg", "opus"],
    "video": ["mp4", "mov", "avi", "mkv", "webm"],
    "image": ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "svg"],
    "document": ["txt", "md", "csv", "json", "pdf", "docx", "xlsx", "pptx", "html", "htm"]
  }
}
```

#### 瑼?憭芸之 (413)
```json
HTTP/1.1 413 Payload Too Large
Content-Type: application/json

{
  "status": "error",
  "code": "FILE_TOO_LARGE",
  "message": "File size 150MB exceeds maximum 100MB",
  "timestamp": "2024-07-08T10:30:45Z"
}
```

#### 瑼??箇征 (400)
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "status": "error",
  "code": "FILE_EMPTY",
  "message": "File is empty",
  "timestamp": "2024-07-08T10:30:45Z"
}
```

#### 瘝??舀???(400)
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "status": "error",
  "code": "NO_EXTENSION",
  "message": "File has no extension",
  "timestamp": "2024-07-08T10:30:45Z"
}
```

#### 瘝?銝瑼? (400)
```json
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "status": "error",
  "code": "NO_FILE",
  "message": "No file provided",
  "timestamp": "2024-07-08T10:30:45Z"
}
```

#### ??頞? (504)
```json
HTTP/1.1 504 Gateway Timeout
Content-Type: application/json

{
  "status": "error",
  "code": "PROCESSING_TIMEOUT",
  "message": "Request exceeded maximum time of 300 seconds",
  "timestamp": "2024-07-08T10:30:45Z"
}
```

#### ?折???航炊 (500)
```json
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "status": "error",
  "code": "PROCESSING_ERROR",
  "message": "ASR service returned error: Connection refused",
  "timestamp": "2024-07-08T10:30:45Z"
}
```

---


## n8n Admin API

### ?”撌乩?瘚?
```
GET http://localhost:5678/api/v1/workflows
```

#### ???踵? (200)
```json
{
  "data": [
    {
      "id": "yKC658rkbLy0I3KC",
      "name": "multimedia process - optimized",
      "active": true,
      "nodes": 11,
      "connections": {
        "Webhook": [["Validate & Parse File"]],
        "Validate & Parse File": [["Switch"]],
        ...
      }
    },
  ],
  "nodesExist": true
}
```

### ???桀極雿?
```
GET http://localhost:5678/api/v1/workflows/{workflow_id}
```

#### ???踵? (200)
```json
{
  "id": "yKC658rkbLy0I3KC",
  "name": "multimedia process - optimized",
  "active": true,
  "nodes": [...],
  "connections": {...},
  "settings": {
    "executionOrder": "v1",
    "binaryMode": "separate"
  },
  "createdAt": "2024-07-01T10:00:00Z",
  "updatedAt": "2024-07-08T15:30:45Z"
}
```

### ?”撌乩?瘚銵?
```
GET http://localhost:5678/api/v1/workflows/{workflow_id}/executions
```

#### ???踵? (200)
```json
{
  "data": [
    {
      "id": "exec-123456",
      "workflowId": "yKC658rkbLy0I3KC",
      "mode": "webhook",
      "status": "success",
      "startedAt": "2024-07-08T10:30:00Z",
      "stoppedAt": "2024-07-08T10:30:45Z",
      "executionTime": 45000,
      "data": {...}
    }
  ],
  "nodesExist": true
}
```

---

## ??Ⅳ蝮賜?

| 隞?Ⅳ | ?怎儔 | ?湔 |
|------|------|------|
| **200** | OK | ???? |
| **400** | Bad Request | 撽?憭望??撩撠?閬???|
| **413** | Payload Too Large | 瑼?頞?憭批?? |
| **415** | Unsupported Media Type | 銝??瑼?憿? |
| **504** | Gateway Timeout | 隢?頞? |
| **500** | Internal Server Error | ?折???航炊 |

---

## cURL 皜祈岫蝷箔?

### 皜祈岫憭?擃???

#### 銝?喲瑼?
```bash
curl -F "file=@audio.mp3" \
  http://localhost:5678/webhook/multimedia-process
```

#### 銝??瑼?
```bash
curl -F "file=@image.png" \
  http://localhost:5678/webhook/multimedia-process
```


### ?脣?撌乩?瘚?銵?
```bash
curl -X GET http://localhost:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  | jq '.'
```

---

## 撣貊撌亙

### Postman
- 撠: `CARE_n8n_Collection.postman_collection.json`
- ?舀?: ?芸??啣?霈??葫閰西??

### cURL
- 蝪∪?翰??皜祈岫
- ?舀????HTTP ?寞?
- ?拙??單?芸???

### Insomnia
- 憿撮 Postman ?隞??
- ???舀 GraphQL
- ?啣?蝞∠?

---

**?敺??*: 2024-07-08  
**?**: 2.0
