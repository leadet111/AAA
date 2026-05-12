# 穿搭发型顾问 - 部署指南

> 面向 Linux 云服务器（Ubuntu/Debian），使用 Nginx + Waitress + SQLite 架构。

## 1. 服务器准备

租一台云服务器（阿里云/腾讯云/AWS/Vultr 等）：
- **系统**: Ubuntu 22.04 LTS 或 Debian 12
- **配置**: 1核2G 起步（个人使用足够）
- **带宽**: 3Mbps 起步

购买域名并完成备案（国内服务器需要）。

### 1.1 连接服务器

```bash
ssh root@你的服务器IP
```

### 1.2 更新系统并安装依赖

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git
```

## 2. 部署代码

### 2.1 创建目录并上传代码

```bash
mkdir -p /var/www
cd /var/www

# 方式1: 用 git clone（推荐）
git clone <你的代码仓库地址> style-advisor

# 方式2: 用 scp/rsync 从本地上传
# scp -r ./style-advisor root@服务器IP:/var/www/

cd /var/www/style-advisor
```

### 2.2 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.3 配置环境变量

```bash
cp .env.example .env
nano .env
```

至少修改以下两项（生成强密钥）：

```bash
# 生成密钥命令
python3 -c "import secrets; print(secrets.token_hex(32))"
```

填入 `.env`：

```env
FLASK_ENV=production
SECRET_KEY=生成的32位十六进制密钥
JWT_SECRET_KEY=生成的另一组32位十六进制密钥
```

### 2.4 初始化数据库

```bash
source .venv/bin/activate
python -c "from run import app, db; app.app_context().push(); db.create_all()"
```

### 2.5 测试生产启动

```bash
source .venv/bin/activate
python run_production.py
```

看到监听提示后，按 `Ctrl+C` 停止，继续配置 systemd。

## 3. 配置 systemd 服务（开机自启）

```bash
cp style-advisor.service /etc/systemd/system/
# 根据实际情况编辑服务文件中的路径
nano /etc/systemd/system/style-advisor.service
```

然后启用并启动：

```bash
systemctl daemon-reload
systemctl enable style-advisor
systemctl start style-advisor
systemctl status style-advisor
```

查看日志：

```bash
journalctl -u style-advisor -f
```

## 4. 配置 Nginx 反向代理

### 4.1 复制配置模板

```bash
cp nginx.conf.example /etc/nginx/sites-available/style-advisor
nano /etc/nginx/sites-available/style-advisor
```

将 `your-domain.com` 替换为你的实际域名。

### 4.2 启用站点

```bash
ln -s /etc/nginx/sites-available/style-advisor /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## 5. 配置 HTTPS（Let's Encrypt）

```bash
certbot --nginx -d your-domain.com -d www.your-domain.com
```

按提示操作，选择自动重定向 HTTP 到 HTTPS。

验证自动续期：

```bash
certbot renew --dry-run
```

## 6. 域名绑定

在你的域名服务商后台，添加 A 记录：
- **主机记录**: `@`（根域名）和 `www`
- **记录值**: 你的服务器公网 IP
- **TTL**: 默认

等待 DNS 生效（通常几分钟到几小时），然后访问 `https://your-domain.com`。

## 7. PWA 验证

在 Chrome 中打开你的网站，按 `F12` → `Application` → `Manifest` 和 `Service Workers`，确认：
- Manifest 正常加载
- Service Worker 已注册并激活
- 图标显示正确

在手机浏览器（Chrome/Safari）中打开，测试"添加到主屏幕"功能。

## 8. 日常维护

### 查看服务状态
```bash
systemctl status style-advisor
```

### 重启服务
```bash
systemctl restart style-advisor
```

### 查看日志
```bash
journalctl -u style-advisor -n 100
```

### 备份数据
```bash
# SQLite 数据库 + 上传的文件
tar czvf backup-$(date +%Y%m%d).tar.gz /var/www/style-advisor/app.db /var/www/style-advisor/data
```

### 更新代码后重启
```bash
cd /var/www/style-advisor
git pull
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart style-advisor
```

## 9. 常见问题

**Q: 访问网站显示 502 Bad Gateway？**
A: 检查 Waitress 是否在运行：`systemctl status style-advisor`，查看 Nginx 错误日志：`tail /var/log/nginx/error.log`。

**Q: HTTPS 证书过期？**
A: certbot 会自动续期，可手动测试：`certbot renew --dry-run`。

**Q: 上传图片失败？**
A: 检查 `/var/www/style-advisor/data/user_uploads` 目录权限：`chown -R www-data:www-data /var/www/style-advisor/data`。

**Q: PWA 无法添加到主屏幕？**
A: 必须开启 HTTPS，且 manifest.json 和 Service Worker 路径正确。在 Chrome DevTools 的 Lighthouse 中运行 PWA 审计排查。
