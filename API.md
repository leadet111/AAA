# 穿搭发型顾问 - API 接口文档

> **PWA 和原生APP共用同一套后端 API**

## 基础信息

| 项目 | 值 |
|------|-----|
| 基础URL | `http://<host>:5001/api/v1` |
| 数据格式 | JSON |
| 认证方式 | Bearer Token (JWT) |
| 客户端标识 | `X-Client-Type: pwa / ios / android` |

## 认证接口

### POST `/auth/guest` - 游客登录
无需任何参数，自动创建游客账号并返回 JWT Token。

**请求：**
```json
{}
```

**响应：**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "username": null,
    "profile": {
      "face_shape": null,
      "body_type": null,
      "skin_tone": null
    }
  },
  "is_guest": true
}
```

### POST `/auth/phone` - 手机号登录（预留）
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

### GET `/auth/me` - 获取当前用户
```http
Authorization: Bearer <token>
```

### PUT `/auth/profile` - 更新用户档案
```http
Authorization: Bearer <token>
Content-Type: application/json
```
```json
{
  "username": "小明",
  "face_shape": "oval",
  "body_type": "hourglass",
  "skin_tone": "warm"
}
```

## 核心分析接口

### POST `/analyze` - 形象分析
上传照片 + 问卷，返回穿搭/发型推荐。

**请求头：**
```http
Authorization: Bearer <token>
Content-Type: application/json
X-Client-Type: ios
```

**请求体：**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",  // 可选
  "survey": {
    "faceShape": "oval",       // 必填: round/square/long/heart/oval/diamond
    "bodyType": "hourglass",    // 必填: slim_tall/balanced/slightly_chubby/athletic/petite/pear/apple/hourglass
    "skinTone": "warm",         // 必填: warm/cool/neutral
    "occasion": "daily",        // 可选: daily/work/date/sport/formal
    "season": "spring"          // 可选: spring/summer/autumn/winter
  },
  "type": "full",               // outfit / hair / full
  "client_type": "ios"
}
```

**响应：**
```json
{
  "id": 1,
  "result": {
    "traits": {
      "faceShape": "鹅蛋脸",
      "bodyType": "沙漏型身材",
      "skinTone": "暖色调肤色"
    },
    "analysis": {
      "face": "...",
      "body": "...",
      "skin": "..."
    },
    "outfit": {
      "items": [...],
      "colorAdvice": {
        "recommended": ["驼色", "焦糖色", ...],
        "avoid": ["纯白色", "冷紫色", ...]
      },
      "bodyTips": ["..."]
    },
    "hair": {
      "items": [...],
      "faceTips": ["..."],
      "colorAdvice": {
        "recommended": ["焦糖棕", "蜂蜜茶", ...],
        "avoid": ["纯黑色", "冷灰色", ...]
      }
    }
  }
}
```

### GET `/analyze/history` - 分析历史
```http
Authorization: Bearer <token>
```

**查询参数：**
- `page`: 页码（默认1）
- `per_page`: 每页数量（默认20）

### GET `/analyze/history/<id>` - 历史详情
```http
Authorization: Bearer <token>
```

## 知识库接口

### GET `/knowledge` - 获取知识库元数据
无需认证，返回脸型/体型/肤色枚举值，供APP下拉选择使用。

**响应：**
```json
{
  "face_shapes": ["round", "square", "long", "heart", "oval", "diamond"],
  "body_types": ["slim_tall", "balanced", ...],
  "skin_tones": ["warm", "cool", "neutral"],
  "version": "1.0.0"
}
```

## 原生APP接入建议

### Flutter 示例
```dart
// 1. 游客登录
final response = await http.post(
  Uri.parse('$baseUrl/api/v1/auth/guest'),
);
final token = jsonDecode(response.body)['token'];

// 2. 分析请求
final analyzeResponse = await http.post(
  Uri.parse('$baseUrl/api/v1/analyze'),
  headers: {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
    'X-Client-Type': 'ios',
  },
  body: jsonEncode({
    'type': 'full',
    'survey': {
      'faceShape': 'oval',
      'bodyType': 'hourglass',
      'skinTone': 'warm',
    },
  }),
);
```

### 数据存储策略
- **Token**：存 Keychain/Keystore
- **用户档案**：首次分析后缓存到本地，后续直接读取
- **分析历史**：调用 `/analyze/history` 同步，支持离线查看
- **知识库**：调用 `/knowledge` 获取版本号，有更新时全量同步

### 图片上传
1. 前端压缩图片至 800px 宽，JPEG 质量 85%
2. Base64 编码后放入 `image` 字段
3. 后期可扩展为 multipart/form-data 直接上传文件

## Swagger 在线文档

启动服务后访问：
```
http://localhost:5001/apidocs/
```
