# 穿搭发型顾问 - API 接口文档

> **PWA 和原生APP共用同一套后端 API**
> **新增：AI性别识别、三种性别方案、发质分类打理、商品搜索链接**

## 基础信息

| 项目 | 值 |
|------|-----|
| 基础URL | `https://nuozhong.cn/api/v1` |
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
      "skin_tone": null,
      "gender": null
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
  "skin_tone": "warm",
  "gender": "female",
  "height": 165,
  "weight": 55,
  "style_preference": "简约"
}
```

## 核心分析接口

### POST `/analyze` - 形象分析
上传照片 + 问卷，AI自动识别性别，返回穿搭/发型推荐（含三种性别方案）。

**请求头：**
```http
Authorization: Bearer <token>
Content-Type: application/json
X-Client-Type: ios
```

**请求体：**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",  // 可选，用于AI性别识别
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
    "detected_gender": {
      "gender": "female",
      "label": "女性",
      "confidence": 0.92,
      "provider": "mock"
    },
    "genderSchemes": {
      "user": {
        "gender": "female",
        "label": "女性",
        "is_primary": true,
        "hint": "AI识别你的性别为「女性」，这是为你量身定制的方案",
        "outfit": {
          "items": [
            {
              "id": "o1",
              "name": "职场干练风",
              "description": "...",
              "items": {"top": "...", "outer": "...", "bottom": "...", "shoes": "...", "accessories": "..."},
              "product_links": [
                {"title": "[上装] 白色垂感衬衫", "search_url": "https://s.taobao.com/search?q=...", "platform": "淘宝"}
              ]
            }
          ],
          "other_choices": [
            {"id": "o2", "name": "韩系温柔风", "description": "..."}
          ],
          "colorAdvice": {...},
          "bodyTips": ["..."]
        },
        "hair": {
          "items": [
            {
              "id": "h1",
              "name": "法式空气刘海长卷发",
              "description": "...",
              "length": "中长发/长发",
              "hair_type_care": {
                "fine": {"tips": ["..."], "products": ["蓬松喷雾", "海盐喷雾"]},
                "coarse": {"tips": ["..."], "products": ["柔顺发膜", "护发精油"]},
                "curly": {"tips": ["..."], "products": ["弹力素", "卷发霜"]},
                "damaged": {"tips": ["..."], "products": ["修复发膜", "护发精油"]},
                "oily": {"tips": ["..."], "products": ["控油洗发水", "清爽发蜡"]},
                "dry": {"tips": ["..."], "products": ["滋润发膜", "护发精油"]}
              },
              "product_links": [
                {"title": "法式空气刘海长卷发 造型", "search_url": "https://s.taobao.com/search?q=...", "platform": "淘宝"}
              ]
            }
          ],
          "other_choices": [
            {"id": "h2", "name": "层次感锁骨发", "description": "...", "length": "锁骨发"}
          ],
          "faceTips": ["..."],
          "colorAdvice": {...}
        }
      },
      "unisex": {
        "gender": "unisex",
        "label": "中性",
        "is_primary": false,
        "hint": "中性风格，简约百搭，适合追求无性别穿搭的你",
        "outfit": {...},
        "hair": {...}
      },
      "other": {
        "gender": "male",
        "label": "男性",
        "is_primary": false,
        "hint": "尝试「男性」风格，发现不一样的自己。每个人都有探索不同风格的权利 ✨",
        "outfit": {...},
        "hair": {...}
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

## 性别识别配置

### 百度AI人脸检测（推荐）
配置环境变量：
```bash
BAIDU_API_KEY=你的API Key
BAIDU_SECRET_KEY=你的Secret Key
```

### 阿里云视觉智能
```bash
ALIYUN_API_KEY=你的API Key
```

### 本地Stable Diffusion（图片生成）
```bash
SD_API_URL=http://127.0.0.1:7860
```

### Replicate（图片生成）
```bash
REPLICATE_API_TOKEN=你的Token
```

## 知识库接口

### GET `/knowledge` - 获取知识库元数据
无需认证，返回脸型/体型/肤色枚举值，供APP下拉选择使用。

**响应：**
```json
{
  "face_shapes": ["round", "square", "long", "heart", "oval", "diamond"],
  "body_types": ["slim_tall", "balanced", "slightly_chubby", "athletic", "petite", "pear", "apple", "hourglass"],
  "skin_tones": ["warm", "cool", "neutral"],
  "hair_types": ["fine", "coarse", "curly", "damaged", "oily", "dry"],
  "version": "2.0.0"
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
    'image': base64Image,  // 可选，用于AI性别识别
  }),
);

final result = jsonDecode(analyzeResponse.body)['result'];
final detectedGender = result['detected_gender'];
final schemes = result['genderSchemes'];
// schemes['user'] - 用户性别方案
// schemes['unisex'] - 中性方案
// schemes['other'] - 另一性别方案
```

### 数据存储策略
- **Token**：存 Keychain/Keystore
- **用户档案**：首次分析后缓存到本地，后续直接读取
- **分析历史**：调用 `/analyze/history` 同步，支持离线查看
- **知识库**：调用 `/knowledge` 获取版本号，有更新时全量同步
- **性别**：AI自动识别，无需用户手动填写

### 图片上传
1. 前端压缩图片至 800px 宽，JPEG 质量 85%
2. Base64 编码后放入 `image` 字段
3. 后端自动识别性别并返回三种方案

## Swagger 在线文档

启动服务后访问：
```
https://nuozhong.cn/apidocs/
```
