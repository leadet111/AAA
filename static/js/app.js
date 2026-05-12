/**
 * 穿搭发型顾问 PWA - 前端主逻辑
 * 单页应用，支持页面切换、图片上传、问卷、分析、结果展示
 * API v1 兼容：PWA 和原生APP共用同一套后端
 */

// ============ 状态管理 ============
const state = {
  currentPage: 'home',
  activeTab: 'home',
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
  historyList: [],
  historyDetailId: null,
  historyDetailData: null,
  profileEditing: false,
  isLoading: false,
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

  const tabPages = ['home', 'history', 'profile'];
  const showTab = tabPages.includes(state.currentPage);

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
    case 'history':
      app.appendChild(renderHistory());
      break;
    case 'historyDetail':
      app.appendChild(renderHistoryDetail());
      break;
    case 'profile':
      app.appendChild(renderProfile());
      break;
  }

  if (showTab) {
    app.appendChild(renderTabBar());
  }
}

// ============ 底部 Tab 导航 ============
function renderTabBar() {
  const div = document.createElement('div');
  div.className = 'tab-bar';
  const tabs = [
    { key: 'home', label: '首页', icon: '👗' },
    { key: 'history', label: '历史', icon: '📜' },
    { key: 'profile', label: '我的', icon: '👤' },
  ];
  div.innerHTML = tabs.map(t => `
    <div class="tab-item ${state.activeTab === t.key ? 'active' : ''}" onclick="switchTab('${t.key}')">
      <div class="tab-icon">${t.icon}</div>
      <div class="tab-label">${t.label}</div>
    </div>
  `).join('');
  return div;
}

function switchTab(tab) {
  state.activeTab = tab;
  navigate(tab);
}

// ============ 首页 ============
function renderHome() {
  const div = document.createElement('div');
  div.className = 'page active tab-page';
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
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>📜 最近分析</span>
        <span style="font-size:0.75rem;color:var(--primary);" onclick="switchTab('history')">查看全部 →</span>
      </div>
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
  if (!state.survey.faceShape || !state.survey.bodyType || !state.survey.skinTone) {
    alert('请填写脸型、体型和肤色色调');
    return;
  }

  navigate('analyzing');
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

    const historyItem = {
      title: `${state.analysisResult.traits.faceShape} · ${state.analysisResult.traits.bodyType} · ${state.analysisResult.traits.skinTone}`,
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

  html += renderResultContent(r);

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

// ============ 结果内容渲染（复用） ============
function renderResultContent(r) {
  let html = '';

  html += `
    <div class="card" style="margin-top: -1rem; position: relative; z-index: 2;">
      <div class="card-title">📝 形象特征</div>
      ${r.analysis.face ? `<p style="font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.5rem;"><strong>脸型：</strong>${r.analysis.face}</p>` : ''}
      ${r.analysis.body ? `<p style="font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.5rem;"><strong>体型：</strong>${r.analysis.body}</p>` : ''}
      ${r.analysis.skin ? `<p style="font-size: 0.85rem; color: var(--text-light);"><strong>肤色：</strong>${r.analysis.skin}</p>` : ''}
    </div>
  `;

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

  return html;
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
    navigator.clipboard.writeText(text).then(() => alert('分析结果已复制到剪贴板'));
  }
}

// ============ 历史记录页 ============
async function loadHistory() {
  state.isLoading = true;
  render();
  try {
    const resp = await apiRequest(`${API_BASE}/api/v1/analyze/history?page=1&per_page=50`);
    const data = await resp.json();
    state.historyList = data.items || [];
  } catch (e) {
    console.error('加载历史失败', e);
  }
  state.isLoading = false;
  render();
}

function renderHistory() {
  const div = document.createElement('div');
  div.className = 'page active tab-page';

  let html = `
    <div class="page-header">
      <h1>分析历史</h1>
      <p>查看你之前的形象分析报告</p>
    </div>
  `;

  if (state.isLoading) {
    html += `<div class="empty-state"><div class="spinner"></div><p>加载中...</p></div>`;
  } else if (state.historyList.length === 0) {
    html += `
      <div class="empty-state">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">📜</div>
        <p>暂无分析记录</p>
        <p style="font-size: 0.8rem; color: var(--text-muted);">完成一次形象分析后，记录会显示在这里</p>
        <button class="btn btn-primary" style="margin-top: 1rem;" onclick="switchTab('home')">去分析</button>
      </div>
    `;
  } else {
    html += `<div class="history-list">`;
    state.historyList.forEach(item => {
      const typeLabels = { outfit: '穿搭', hair: '发型', full: '全套' };
      const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString('zh-CN') : '';
      html += `
        <div class="history-item" onclick="openHistoryDetail(${item.id})">
          <div class="history-item-main">
            <div class="history-item-type">${typeLabels[item.analysis_type] || item.analysis_type}</div>
            <div class="history-item-traits">
              ${item.traits.face_shape || ''} · ${item.traits.body_type || ''} · ${item.traits.skin_tone || ''}
            </div>
            <div class="history-item-date">${dateStr}</div>
          </div>
          <div class="history-item-arrow">→</div>
        </div>
      `;
    });
    html += `</div>`;
  }

  html += `<div style="height: 2rem;"></div>`;
  div.innerHTML = html;
  return div;
}

async function openHistoryDetail(id) {
  state.historyDetailId = id;
  state.historyDetailData = null;
  navigate('historyDetail');

  try {
    const resp = await apiRequest(`${API_BASE}/api/v1/analyze/history/${id}`);
    const data = await resp.json();
    if (data.error) {
      alert(data.error);
      navigate('history');
      return;
    }
    state.historyDetailData = data;
    render();
  } catch (e) {
    console.error('加载详情失败', e);
    alert('加载失败，请重试');
    navigate('history');
  }
}

function renderHistoryDetail() {
  const div = document.createElement('div');
  div.className = 'page active has-bottom-bar';

  if (!state.historyDetailData) {
    div.innerHTML = `
      <div class="nav-back" onclick="navigate('history')"><span>←</span> 返回</div>
      <div class="empty-state"><div class="spinner"></div><p>加载中...</p></div>
    `;
    return div;
  }

  const d = state.historyDetailData;
  const r = d.result || {};
  const dateStr = d.created_at ? new Date(d.created_at).toLocaleDateString('zh-CN') : '';

  let html = `
    <div class="nav-back" onclick="navigate('history')">
      <span>←</span> 返回
    </div>
    <div class="result-header" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
      <h2 style="font-size: 1.2rem; margin-bottom: 0.25rem;">历史分析报告</h2>
      <p style="font-size: 0.8rem; opacity: 0.9;">${dateStr}</p>
      <div class="traits-tags">
        <span class="trait-tag">${r.traits?.faceShape || d.traits?.face_shape || ''}</span>
        <span class="trait-tag">${r.traits?.bodyType || d.traits?.body_type || ''}</span>
        <span class="trait-tag">${r.traits?.skinTone || d.traits?.skin_tone || ''}</span>
      </div>
    </div>
  `;

  if (r.analysis || r.outfit || r.hair) {
    html += renderResultContent(r);
  } else {
    html += `<div class="card"><p>暂无详细结果数据</p></div>`;
  }

  html += `
    <div style="height: 2rem;"></div>
    <div class="bottom-bar">
      <button class="btn btn-ghost" onclick="navigate('history')">返回历史</button>
    </div>
  `;

  div.innerHTML = html;
  return div;
}

// ============ 个人中心页 ============
async function loadProfile() {
  state.isLoading = true;
  render();
  try {
    const resp = await apiRequest(`${API_BASE}/api/v1/auth/me`);
    const data = await resp.json();
    if (data.user) {
      state.user = data.user;
      localStorage.setItem('styleUser', JSON.stringify(data.user));
    }
  } catch (e) {
    console.error('加载用户失败', e);
  }
  state.isLoading = false;
  render();
}

function renderProfile() {
  const div = document.createElement('div');
  div.className = 'page active tab-page';

  const u = state.user || {};
  const p = u.profile || {};

  let html = `
    <div class="page-header">
      <h1>我的档案</h1>
      <p>管理你的形象资料</p>
    </div>
  `;

  if (state.profileEditing) {
    html += renderProfileEdit(u, p);
  } else {
    html += renderProfileView(u, p);
  }

  html += `<div style="height: 2rem;"></div>`;
  div.innerHTML = html;
  return div;
}

function renderProfileView(u, p) {
  return `
    <div class="card profile-card">
      <div class="profile-avatar">${u.username ? u.username[0] : '👤'}</div>
      <div class="profile-name">${u.username || '游客用户'}</div>
      <div class="profile-id">ID: ${u.id || '-'}</div>
    </div>

    <div class="card">
      <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>📝 形象档案</span>
        <span style="font-size:0.75rem;color:var(--primary);" onclick="toggleProfileEdit()">编辑</span>
      </div>
      <div class="profile-field">
        <span class="profile-field-label">脸型</span>
        <span class="profile-field-value">${p.face_shape ? labelOf('faceShape', p.face_shape) : '未设置'}</span>
      </div>
      <div class="profile-field">
        <span class="profile-field-label">体型</span>
        <span class="profile-field-value">${p.body_type ? labelOf('bodyType', p.body_type) : '未设置'}</span>
      </div>
      <div class="profile-field">
        <span class="profile-field-label">肤色</span>
        <span class="profile-field-value">${p.skin_tone ? labelOf('skinTone', p.skin_tone) : '未设置'}</span>
      </div>
      <div class="profile-field">
        <span class="profile-field-label">身高</span>
        <span class="profile-field-value">${p.height ? p.height + ' cm' : '未设置'}</span>
      </div>
      <div class="profile-field">
        <span class="profile-field-label">体重</span>
        <span class="profile-field-value">${p.weight ? p.weight + ' kg' : '未设置'}</span>
      </div>
      <div class="profile-field">
        <span class="profile-field-label">风格偏好</span>
        <span class="profile-field-value">${u.style_preference || '未设置'}</span>
      </div>
    </div>

    <div style="padding: 0 1rem;">
      <button class="btn btn-primary" style="width:100%; margin-top: 0.5rem;" onclick="switchTab('home')">
        去形象分析 ✨
      </button>
    </div>
  `;
}

function renderProfileEdit(u, p) {
  const faceOptions = [
    { value: '', label: '请选择' },
    { value: 'round', label: '圆形脸' },
    { value: 'square', label: '方形脸' },
    { value: 'long', label: '长形脸' },
    { value: 'heart', label: '心形脸' },
    { value: 'oval', label: '鹅蛋脸' },
    { value: 'diamond', label: '菱形脸' },
  ];
  const bodyOptions = [
    { value: '', label: '请选择' },
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
    { value: '', label: '请选择' },
    { value: 'warm', label: '暖色调' },
    { value: 'cool', label: '冷色调' },
    { value: 'neutral', label: '中性色调' },
  ];

  return `
    <div class="card">
      <div class="card-title">编辑档案</div>
      <div class="form-group">
        <label class="form-label">昵称</label>
        <input type="text" class="form-input" id="edit-username" value="${u.username || ''}" placeholder="输入昵称">
      </div>
      <div class="form-group">
        <label class="form-label">脸型</label>
        <select class="form-select" id="edit-face_shape">
          ${faceOptions.map(o => `<option value="${o.value}" ${p.face_shape === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">体型</label>
        <select class="form-select" id="edit-body_type">
          ${bodyOptions.map(o => `<option value="${o.value}" ${p.body_type === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">肤色</label>
        <select class="form-select" id="edit-skin_tone">
          ${skinOptions.map(o => `<option value="${o.value}" ${p.skin_tone === o.value ? 'selected' : ''}>${o.label}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">身高 (cm)</label>
        <input type="number" class="form-input" id="edit-height" value="${p.height || ''}" placeholder="例如 165">
      </div>
      <div class="form-group">
        <label class="form-label">体重 (kg)</label>
        <input type="number" class="form-input" id="edit-weight" value="${p.weight || ''}" placeholder="例如 55">
      </div>
      <div class="form-group">
        <label class="form-label">风格偏好</label>
        <input type="text" class="form-input" id="edit-style_preference" value="${u.style_preference || ''}" placeholder="例如 简约、复古、甜美">
      </div>
    </div>
    <div class="bottom-bar">
      <button class="btn btn-ghost" onclick="toggleProfileEdit()">取消</button>
      <button class="btn btn-primary" onclick="saveProfile()">保存</button>
    </div>
  `;
}

function toggleProfileEdit() {
  state.profileEditing = !state.profileEditing;
  render();
}

async function saveProfile() {
  const data = {
    username: document.getElementById('edit-username').value.trim() || null,
    face_shape: document.getElementById('edit-face_shape').value || null,
    body_type: document.getElementById('edit-body_type').value || null,
    skin_tone: document.getElementById('edit-skin_tone').value || null,
    height: document.getElementById('edit-height').value ? parseInt(document.getElementById('edit-height').value) : null,
    weight: document.getElementById('edit-weight').value ? parseInt(document.getElementById('edit-weight').value) : null,
    style_preference: document.getElementById('edit-style_preference').value.trim() || null,
  };

  try {
    const resp = await apiRequest(`${API_BASE}/api/v1/auth/profile`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    const result = await resp.json();
    if (result.user) {
      state.user = result.user;
      localStorage.setItem('styleUser', JSON.stringify(result.user));
    }
    state.profileEditing = false;
    render();
  } catch (e) {
    console.error('保存失败', e);
    alert('保存失败，请重试');
  }
}

function labelOf(type, value) {
  const maps = {
    faceShape: { round: '圆形脸', square: '方形脸', long: '长形脸', heart: '心形脸', oval: '鹅蛋脸', diamond: '菱形脸' },
    bodyType: { slim_tall: '瘦高型', balanced: '匀称型', slightly_chubby: '微胖型', athletic: '壮实型', petite: '娇小型', pear: '梨形身材', apple: '苹果型身材', hourglass: '沙漏型身材' },
    skinTone: { warm: '暖色调', cool: '冷色调', neutral: '中性色调' },
  };
  return (maps[type] && maps[type][value]) || value;
}

// ============ 导航 ============
function navigate(page) {
  state.currentPage = page;
  if (page === 'history' && state.historyList.length === 0) {
    loadHistory();
  }
  if (page === 'profile' && !state.user) {
    loadProfile();
  }
  render();
  window.scrollTo(0, 0);
}

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', render);
