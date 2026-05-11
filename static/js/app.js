/**
 * 穿搭发型顾问 PWA - 前端主逻辑
 * 单页应用，支持页面切换、图片上传、问卷、分析、结果展示
 * API v1 兼容：PWA 和原生APP共用同一套后端
 */

// ============ 状态管理 ============
const state = {
  currentPage: 'home',
  analysisType: 'full',
  uploadedImage: null,
  survey: {
    faceShape: '',
    bodyType: '',
    skinTone: '',
    height: '',
    occasion: 'daily',
    season: getCurrentSeason(),
  },
  analysisResult: null,
  history: JSON.parse(localStorage.getItem('styleHistory') || '[]'),
  token: localStorage.getItem('styleToken') || null,
  user: JSON.parse(localStorage.getItem('styleUser') || 'null'),
};

// ============ API 工具 ============
const API_BASE = '';

async function apiRequest(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-Client-Type': 'pwa',
    ...options.headers,
  };
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  
  const resp = await fetch(url, { ...options, headers });
  if (resp.status === 401) {
    // token 失效，重新登录
    state.token = null;
    localStorage.removeItem('styleToken');
    await guestLogin();
    return apiRequest(url, options);
  }
  return resp;
}

async function guestLogin() {
  try {
    const resp = await fetch(`${API_BASE}/api/v1/auth/guest`, { method: 'POST' });
    const data = await resp.json();
    if (data.token) {
      state.token = data.token;
      state.user = data.user;
      localStorage.setItem('styleToken', data.token);
      localStorage.setItem('styleUser', JSON.stringify(data.user));
    }
  } catch (e) {
    console.log('游客登录失败', e);
  }
}

// 初始化时自动登录
if (!state.token) {
  guestLogin();
}

function getCurrentSeason() {
  const month = new Date().getMonth() + 1;
  if (month <= 3) return 'spring';
  if (month <= 6) return 'summer';
  if (month <= 9) return 'autumn';
  return 'winter';
}

// ============ 页面渲染 ============
function render() {
  const app = document.getElementById('app');
  app.innerHTML = '';

  switch (state.currentPage) {
    case 'home':
      app.appendChild(renderHome());
      break;
    case 'selectType':
      app.appendChild(renderSelectType());
      break;
    case 'upload':
      app.appendChild(renderUpload());
      break;
    case 'survey':
      app.appendChild(renderSurvey());
      break;
    case 'analyzing':
      app.appendChild(renderAnalyzing());
      break;
    case 'result':
      app.appendChild(renderResult());
      break;
  }
}

// ============ 首页 ============
function renderHome() {
  const div = document.createElement('div');
  div.className = 'page active';
  div.innerHTML = `
    <div class="header">
      <div class="header-icon">👗</div>
      <h1>穿搭发型顾问</h1>
      <p>AI 智能分析 · 个性化推荐</p>
    </div>
    <div class="hero-section">
      <p class="hero-text">
        上传你的照片，回答几个简单问题<br>
        AI 将为你量身推荐穿搭和发型
      </p>
    </div>
    <div style="padding: 0 1rem 1rem;">
      <button class="btn btn-primary" onclick="navigate('selectType')">
        开始形象分析 ✨
      </button>
    </div>
    ${state.history.length > 0 ? `
    <div class="card">
      <div class="card-title">📜 历史记录</div>
      ${state.history.slice(0, 3).map(h => `
        <div style="padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.85rem;">
          <div style="font-weight: 600;">${h.title}</div>
          <div style="color: var(--text-muted); font-size: 0.75rem;">${h.date}</div>
        </div>
      `).join('')}
    </div>
    ` : ''}
    <div class="card">
      <div class="card-title">✨ 功能介绍</div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
        <div style="text-align: center; padding: 0.5rem;">
          <div style="font-size: 1.8rem; margin-bottom: 0.25rem;">👔</div>
          <div style="font-size: 0.8rem; font-weight: 600;">穿搭推荐</div>
          <div style="font-size: 0.7rem; color: var(--text-muted);">根据体型肤色推荐</div>
        </div>
        <div style="text-align: center; padding: 0.5rem;">
          <div style="font-size: 1.8rem; margin-bottom: 0.25rem;">💇</div>
          <div style="font-size: 0.8rem; font-weight: 600;">发型设计</div>
          <div style="font-size: 0.7rem; color: var(--text-muted);">根据脸型匹配发型</div>
        </div>
      </div>
    </div>
    <div style="height: 2rem;"></div>
  `;
  return div;
}

// ============ 选择分析类型 ============
function renderSelectType() {
  const div = document.createElement('div');
  div.className = 'page active';
  div.innerHTML = `
    <div class="nav-back" onclick="navigate('home')">
      <span>←</span> 返回
    </div>
    <div style="padding: 1.5rem 1rem 1rem; text-align: center;">
      <h2 style="font-size: 1.2rem; margin-bottom: 0.25rem;">选择分析类型</h2>
      <p style="font-size: 0.85rem; color: var(--text-muted);">你想获得哪方面的建议？</p>
    </div>
    <div class="feature-grid" style="padding: 0.5rem 1rem;">
      <div class="feature-card ${state.analysisType === 'outfit' ? 'selected' : ''}" onclick="selectType('outfit')">
        <div class="icon">👔</div>
        <h3>穿搭分析</h3>
        <p>根据体型和肤色<br>推荐今日穿搭</p>
      </div>
      <div class="feature-card ${state.analysisType === 'hair' ? 'selected' : ''}" onclick="selectType('hair')">
        <div class="icon">💇</div>
        <h3>发型设计</h3>
        <p>根据脸型和肤色<br>推荐适合发型</p>
      </div>
      <div class="feature-card ${state.analysisType === 'full' ? 'selected' : ''}" onclick="selectType('full')" style="grid-column: 1 / -1;">
        <div class="icon">✨</div>
        <h3>全套方案</h3>
        <p>穿搭 + 发型 一次性搞定</p>
      </div>
    </div>
    <div class="bottom-bar">
      <button class="btn btn-ghost" onclick="navigate('home')">取消</button>
      <button class="btn btn-primary" onclick="navigate('upload')">下一步</button>
    </div>
  `;
  return div;
}

function selectType(type) {
  state.analysisType = type;
  render();
}

// ============ 上传照片 ============
function renderUpload() {
  const div = document.createElement('div');
  div.className = 'page active has-bottom-bar';
  div.innerHTML = `
    <div class="nav-back" onclick="navigate('selectType')">
      <span>←</span> 返回
    </div>
    <div class="steps">
      <div class="step-dot active"></div>
      <div class="step-dot"></div>
      <div class="step-dot"></div>
    </div>
    <div style="padding: 0.5rem 1rem 0.5rem;">
      <h2 style="font-size: 1.1rem;">上传照片</h2>
      <p style="font-size: 0.85rem; color: var(--text-muted);">
        ${state.analysisType === 'hair' ? '请上传正面清晰的头像照片' :
          state.analysisType === 'outfit' ? '请上传全身照或半身照' :
          '请上传全身照或头像照片（至少一张）'}
      </p>
    </div>
    ${state.uploadedImage ? `
      <div class="preview-container">
        <img src="${state.uploadedImage}" alt="preview">
        <button class="preview-remove" onclick="removeImage()">×</button>
      </div>
    ` : `
      <div class="upload-area" onclick="document.getElementById('fileInput').click()">
        <div class="icon">📷</div>
        <h3>点击拍照或从相册选择</h3>
        <p>支持 JPG、PNG 格式</p>
      </div>
      <input type="file" id="fileInput" class="upload-input" accept="image/*" capture="user" onchange="handleFileSelect(event)">
    `}
    <div class="tip-card">
      <strong>💡 小贴士</strong><br>
      ${state.analysisType === 'hair' ? '光线充足、正面清晰的头像能让分析更准确' :
        state.analysisType === 'outfit' ? '自然光下、站姿端正的全身照效果最好' :
        '建议上传全身照，如不方便也可只传头像'}
    </div>
    <div class="bottom-bar">
      <button class="btn btn-ghost" onclick="skipUpload()">跳过</button>
      <button class="btn btn-primary" onclick="navigate('survey')">下一步</button>
    </div>
  `;
  return div;
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  // 压缩图片
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const maxWidth = 800;
      const scale = Math.min(1, maxWidth / img.width);
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      state.uploadedImage = canvas.toDataURL('image/jpeg', 0.85);
      render();
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function removeImage() {
  state.uploadedImage = null;
  render();
}

function skipUpload() {
  state.uploadedImage = null;
  navigate('survey');
}

// ============ 问卷 ============
function renderSurvey() {
  const div = document.createElement('div');
  div.className = 'page active has-bottom-bar';

  const faceOptions = [
    { value: '', label: '请选择脸型' },
    { value: 'round', label: '圆形脸' },
    { value: 'square', label: '方形脸' },
    { value: 'long', label: '长形脸' },
    { value: 'heart', label: '心形脸' },
    { value: 'oval', label: '鹅蛋脸' },
    { value: 'diamond', label: '菱形脸' },
  ];

  const bodyOptions = [
    { value: '', label: '请选择体型' },
    { value: 'slim_tall', label: '瘦高型' },
    { value: 'balanced', label: '匀称型' },
    { value: 'slightly_chubby', label: '微胖型' },
    { value: 'athletic', label: '壮实型' },
    { value: 'petite', label: '娇小型' },
    { value: 'pear', label: '梨形身材' },
    { value: 'apple', label: '苹果型身材' },
    { value: 'hourglass', label: '沙漏型身材' },
  ];

  const skinOptions = [
    { value: '', label: '请选择肤色色调' },
    { value: 'warm', label: '暖色调（偏黄/桃）' },
    { value: 'cool', label: '冷色调（偏粉/蓝）' },
    { value: 'neutral', label: '中性色调' },
  ];

  const occasionOptions = [
    { value: 'daily', label: '日常休闲' },
    { value: 'work', label: '职场通勤' },
    { value: 'date', label: '约会聚会' },
    { value: 'sport', label: '运动健身' },
    { value: 'formal', label: '正式场合' },
  ];

  const seasonOptions = [
    { value: 'spring', label: '春季' },
    { value: 'summer', label: '夏季' },
    { value: 'autumn', label: '秋季' },
    { value: 'winter', label: '冬季' },
  ];

  div.innerHTML = `
    <div class="nav-back" onclick="navigate('upload')">
      <span>←</span> 返回
    </div>
    <div class="steps">
      <div class="step-dot"></div>
      <div class="step-dot active"></div>
      <div class="step-dot"></div>
    </div>
    <div style="padding: 0.5rem 1rem 0.5rem;">
      <h2 style="font-size: 1.1rem;">补充信息</h2>
      <p style="font-size: 0.85rem; color: var(--text-muted);">这些信息能帮助 AI 更精准地为你推荐</p>
    </div>
    <div class="card">
      <div class="form-group">
        <label class="form-label">脸型 *</label>
        <select class="form-select" id="faceShape" onchange="updateSurvey('faceShape', this.value)">
          ${faceOptions.map(o => `<option value="${o.value}" ${state.survey.faceShape === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">体型 *</label>
        <select class="form-select" id="bodyType" onchange="updateSurvey('bodyType', this.value)">
          ${bodyOptions.map(o => `<option value="${o.value}" ${state.survey.bodyType === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">肤色色调 *</label>
        <select class="form-select" id="skinTone" onchange="updateSurvey('skinTone', this.value)">
          ${skinOptions.map(o => `<option value="${o.value}" ${state.survey.skinTone === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
      ${state.analysisType !== 'hair' ? `
      <div class="form-group">
        <label class="form-label">场合</label>
        <select class="form-select" id="occasion" onchange="updateSurvey('occasion', this.value)">
          ${occasionOptions.map(o => `<option value="${o.value}" ${state.survey.occasion === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
      ` : ''}
      <div class="form-group">
        <label class="form-label">季节</label>
        <select class="form-select" id="season" onchange="updateSurvey('season', this.value)">
          ${seasonOptions.map(o => `<option value="${o.value}" ${state.survey.season === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
    </div>
    <div class="tip-card warn">
      <strong>⚠️ 不知道怎么判断？</strong><br>
      脸型：测量额头、颧骨、下颌宽度对比；<br>
      肤色：看血管颜色（绿=暖，紫=冷，都有=中性）
    </div>
    <div class="bottom-bar">
      <button class="btn btn-ghost" onclick="navigate('upload')">上一步</button>
      <button class="btn btn-primary" onclick="startAnalyze()">开始分析 ✨</button>
    </div>
  `;
  return div;
}

function updateSurvey(key, value) {
  state.survey[key] = value;
}

// ============ 分析中 ============
function renderAnalyzing() {
  const div = document.createElement('div');
  div.className = 'page active';
  div.innerHTML = `
    <div class="analyzing">
      <div class="analyzing-icon">✨</div>
      <h2>AI 正在分析你的形象...</h2>
      <p>结合脸型、体型、肤色为你匹配最佳方案</p>
      <div class="progress-bar">
        <div class="progress-fill"></div>
      </div>
    </div>
  `;
  return div;
}

async function startAnalyze() {
  // 验证必填
  if (!state.survey.faceShape || !state.survey.bodyType || !state.survey.skinTone) {
    alert('请填写脸型、体型和肤色色调');
    return;
  }

  navigate('analyzing');

  // 模拟分析延迟
  await new Promise(r => setTimeout(r, 2000));

  try {
    const response = await apiRequest(`${API_BASE}/api/v1/analyze`, {
      method: 'POST',
      body: JSON.stringify({
        image: state.uploadedImage,
        survey: state.survey,
        type: state.analysisType,
        client_type: 'pwa',
      }),
    });

    const data = await response.json();

    if (data.error) {
      alert(data.error);
      navigate('survey');
      return;
    }

    state.analysisResult = data.result || data;

    // 保存历史
    const historyItem = {
      title: `${result.traits.faceShape} · ${result.traits.bodyType} · ${result.traits.skinTone}`,
      date: new Date().toLocaleDateString('zh-CN'),
      type: state.analysisType,
    };
    state.history.unshift(historyItem);
    if (state.history.length > 10) state.history.pop();
    localStorage.setItem('styleHistory', JSON.stringify(state.history));

    navigate('result');
  } catch (err) {
    console.error(err);
    alert('分析失败，请检查网络后重试');
    navigate('survey');
  }
}

// ============ 结果页 ============
function renderResult() {
  const div = document.createElement('div');
  div.className = 'page active has-bottom-bar';
  const r = state.analysisResult;
  if (!r) {
    div.innerHTML = '<div class="card">暂无分析结果</div>';
    return div;
  }

  let html = `
    <div class="nav-back" onclick="navigate('home')">
      <span>←</span> 返回首页
    </div>
    <div class="result-header">
      <h2 style="font-size: 1.3rem; margin-bottom: 0.25rem;">你的形象分析报告</h2>
      <p style="font-size: 0.85rem; opacity: 0.9;">基于 AI 分析 + 专业知识库</p>
      <div class="traits-tags">
        <span class="trait-tag">${r.traits.faceShape}</span>
        <span class="trait-tag">${r.traits.bodyType}</span>
        <span class="trait-tag">${r.traits.skinTone}</span>
      </div>
    </div>
  `;

  // 分析总结
  html += `
    <div class="card" style="margin-top: -1rem; position: relative; z-index: 2;">
      <div class="card-title">📝 形象特征</div>
      ${r.analysis.face ? `<p style="font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.5rem;"><strong>脸型：</strong>${r.analysis.face}</p>` : ''}
      ${r.analysis.body ? `<p style="font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.5rem;"><strong>体型：</strong>${r.analysis.body}</p>` : ''}
      ${r.analysis.skin ? `<p style="font-size: 0.85rem; color: var(--text-light);"><strong>肤色：</strong>${r.analysis.skin}</p>` : ''}
    </div>
  `;

  // 穿搭推荐
  if (r.outfit) {
    html += `<div class="section-title">👔 穿搭推荐</div>`;
    r.outfit.items.forEach((item, i) => {
      html += `
        <div class="outfit-card">
          <div class="outfit-card-header style-${i + 1}">
            <h4>${item.name}</h4>
            <p>${item.description}</p>
          </div>
          <div class="outfit-items">
            ${Object.entries(item.items).map(([key, val]) => `
              <div class="outfit-item">
                <span class="outfit-item-icon">${getItemIcon(key)}</span>
                <span class="outfit-item-label">${getItemLabel(key)}</span>
                <span>${val}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    });

    // 颜色建议
    if (r.outfit.colorAdvice) {
      html += `
        <div class="card">
          <div class="card-title">🎨 颜色建议</div>
          <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.8rem; color: var(--success); font-weight: 600; margin-bottom: 0.35rem;">✓ 推荐色系</div>
            <div class="color-palette">
              ${r.outfit.colorAdvice.recommended.map(c => `<span class="color-chip">${c}</span>`).join('')}
            </div>
          </div>
          <div>
            <div style="font-size: 0.8rem; color: var(--danger); font-weight: 600; margin-bottom: 0.35rem;">✗ 谨慎选择</div>
            <div class="color-palette">
              ${r.outfit.colorAdvice.avoid.map(c => `<span class="color-chip">${c}</span>`).join('')}
            </div>
          </div>
        </div>
      `;
    }

    // 体型穿搭技巧
    if (r.outfit.bodyTips && r.outfit.bodyTips.length) {
      html += `
        <div class="card">
          <div class="card-title">💡 穿搭技巧</div>
          <ul class="tips-list">
            ${r.outfit.bodyTips.map(t => `<li>${t}</li>`).join('')}
          </ul>
        </div>
      `;
    }
  }

  // 发型推荐
  if (r.hair) {
    html += `<div class="section-title">💇 发型推荐</div>`;
    r.hair.items.forEach(item => {
      html += `
        <div class="hair-card">
          <h4>${item.name}</h4>
          <div class="meta">长度：${item.length} · ${item.face_shapes.map(f => f).join('/')}</div>
          <p>${item.description}</p>
          ${item.care_tips ? `
            <ul class="tips-list">
              ${item.care_tips.map(t => `<li>${t}</li>`).join('')}
            </ul>
          ` : ''}
        </div>
      `;
    });

    // 发色建议
    if (r.hair.colorAdvice) {
      html += `
        <div class="card">
          <div class="card-title">🎨 发色建议</div>
          <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.8rem; color: var(--success); font-weight: 600; margin-bottom: 0.35rem;">✓ 推荐发色</div>
            <div class="color-palette">
              ${r.hair.colorAdvice.recommended.map(c => `<span class="color-chip">${c}</span>`).join('')}
            </div>
          </div>
          <div>
            <div style="font-size: 0.8rem; color: var(--danger); font-weight: 600; margin-bottom: 0.35rem;">✗ 避免发色</div>
            <div class="color-palette">
              ${r.hair.colorAdvice.avoid.map(c => `<span class="color-chip">${c}</span>`).join('')}
            </div>
          </div>
        </div>
      `;
    }

    // 脸型发型技巧
    if (r.hair.faceTips && r.hair.faceTips.length) {
      html += `
        <div class="card">
          <div class="card-title">💡 发型技巧</div>
          <ul class="tips-list">
            ${r.hair.faceTips.map(t => `<li>${t}</li>`).join('')}
          </ul>
        </div>
      `;
    }
  }

  html += `
    <div style="height: 2rem;"></div>
    <div class="bottom-bar">
      <button class="btn btn-ghost" onclick="navigate('home')">返回首页</button>
      <button class="btn btn-secondary" onclick="shareResult()">分享结果</button>
    </div>
  `;

  div.innerHTML = html;
  return div;
}

function getItemIcon(key) {
  const icons = { top: '👕', outer: '🧥', bottom: '👖', shoes: '👟', accessories: '💍' };
  return icons[key] || '✨';
}

function getItemLabel(key) {
  const labels = { top: '上装', outer: '外套', bottom: '下装', shoes: '鞋履', accessories: '配饰' };
  return labels[key] || key;
}

function shareResult() {
  const text = `我的形象分析结果：${state.analysisResult.traits.faceShape} · ${state.analysisResult.traits.bodyType} · ${state.analysisResult.traits.skinTone}`;
  if (navigator.share) {
    navigator.share({ title: '穿搭发型顾问', text });
  } else {
    // 复制到剪贴板
    navigator.clipboard.writeText(text).then(() => alert('分析结果已复制到剪贴板'));
  }
}

// ============ 导航 ============
function navigate(page) {
  state.currentPage = page;
  render();
  window.scrollTo(0, 0);
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', render);
