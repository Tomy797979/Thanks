import streamlit as st
import requests
import base64
import time
import re
from datetime import datetime

st.set_page_config(page_title="GitHub File Uploader", page_icon="🚀", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Sora:wght@300;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
.main-title {
    font-size:2rem; font-weight:800;
    background:linear-gradient(90deg,#7c6af7,#38bdf8);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    text-align:center; margin-bottom:0.2rem;
}
.sub { text-align:center;color:#888;font-family:'JetBrains Mono',monospace;font-size:0.8rem;margin-bottom:1.5rem; }
.link-box {
    background:#0d1117;border:1px solid #30363d;border-radius:10px;
    padding:1rem 1.2rem;font-family:'JetBrains Mono',monospace;
    font-size:0.72rem;color:#58a6ff;word-break:break-all;line-height:2;
}
.combined-box {
    background:#0d1117;border:1px solid #238636;border-radius:10px;
    padding:1rem 1.2rem;font-family:'JetBrains Mono',monospace;
    font-size:0.7rem;color:#3fb950;word-break:break-all;line-height:1.8;
}
.badge-green  { display:inline-block;background:rgba(63,185,80,0.15);border:1px solid rgba(63,185,80,0.4);border-radius:6px;padding:2px 10px;font-size:0.72rem;color:#3fb950;font-family:'JetBrains Mono',monospace; }
.badge-blue   { display:inline-block;background:rgba(56,189,248,0.1);border:1px solid rgba(56,189,248,0.3);border-radius:6px;padding:2px 10px;font-size:0.72rem;color:#38bdf8;font-family:'JetBrains Mono',monospace; }
.badge-yellow { display:inline-block;background:rgba(210,153,34,0.15);border:1px solid rgba(210,153,34,0.4);border-radius:6px;padding:2px 10px;font-size:0.72rem;color:#d29922;font-family:'JetBrains Mono',monospace; }
.badge-purple { display:inline-block;background:rgba(124,106,247,0.15);border:1px solid rgba(124,106,247,0.4);border-radius:6px;padding:2px 10px;font-size:0.72rem;color:#a78bfa;font-family:'JetBrains Mono',monospace; }
.method-box {
    background:#161b22;border:1px solid #30363d;border-radius:12px;
    padding:1rem 1.2rem;margin:0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🚀 GitHub File Uploader</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Auto raw link · ≤ 25MB via Repo API · 25MB–2GB via Releases</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def gh_headers(token, extra=None):
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    if extra:
        h.update(extra)
    return h

def build_raw_url(username, repo, branch, filepath):
    return f"https://raw.githubusercontent.com/{username}/{repo}/refs/heads/{branch}/{filepath}"

# ── Repo Contents API (≤ 25MB) ────────────────────────────────

def get_file_sha(token, username, repo, branch, remote_path):
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}"
    r = requests.get(url, headers=gh_headers(token), params={"ref": branch}, timeout=15)
    return r.json().get("sha") if r.status_code == 200 else None

def upload_small_file(token, username, repo, branch, remote_path, file_bytes, commit_msg):
    """Contents API — nhanh, đơn giản, nhưng giới hạn ~25MB."""
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}"
    sha = get_file_sha(token, username, repo, branch, remote_path)
    payload = {
        "message": commit_msg,
        "content": base64.b64encode(file_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=gh_headers(token, {"Content-Type": "application/json"}),
                     json=payload, timeout=120)
    return r

# ── GitHub Releases API (tới 2GB) ─────────────────────────────

def get_or_create_release(token, username, repo, tag="uploads"):
    """Lấy hoặc tạo Release với tag cho trước."""
    # Thử lấy release có sẵn
    url = f"https://api.github.com/repos/{username}/{repo}/releases/tags/{tag}"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    if r.status_code == 200:
        return r.json()

    # Tạo release mới nếu chưa có
    url2 = f"https://api.github.com/repos/{username}/{repo}/releases"
    payload = {
        "tag_name": tag,
        "name": f"📦 File Storage — {tag}",
        "body": "Auto-created by GitHub File Uploader. Files uploaded here are accessible via direct URL.",
        "draft": False,
        "prerelease": False,
    }
    r2 = requests.post(url2, headers=gh_headers(token, {"Content-Type": "application/json"}),
                       json=payload, timeout=30)
    r2.raise_for_status()
    return r2.json()

def delete_existing_asset(token, username, repo, release_id, filename):
    """Xoá asset cũ cùng tên nếu đã tồn tại (để upload lại)."""
    url = f"https://api.github.com/repos/{username}/{repo}/releases/{release_id}/assets"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    if r.status_code != 200:
        return
    for asset in r.json():
        if asset["name"] == filename:
            del_url = f"https://api.github.com/repos/{username}/{repo}/releases/assets/{asset['id']}"
            requests.delete(del_url, headers=gh_headers(token), timeout=15)

def upload_release_asset(token, username, repo, release_id, upload_url, filename, file_bytes):
    """Upload file lên GitHub Release — hỗ trợ tới 2GB."""
    # Xoá asset cũ nếu trùng tên
    delete_existing_asset(token, username, repo, release_id, filename)

    # Chuẩn bị upload URL (bỏ {?name,label} template)
    base_url = re.sub(r"\{[^}]*\}", "", upload_url)
    upload_endpoint = f"{base_url}?name={requests.utils.quote(filename)}"

    # Detect content type
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_map = {
        "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg",
        "mp4": "video/mp4",  "mov": "video/quicktime", "avi": "video/x-msvideo",
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "gif": "image/gif",  "pdf": "application/pdf",
        "zip": "application/zip",
    }
    content_type = mime_map.get(ext, "application/octet-stream")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": content_type,
    }
    r = requests.post(upload_endpoint, headers=headers, data=file_bytes, timeout=600)
    r.raise_for_status()
    return r.json()

def get_release_direct_url(username, repo, tag, filename):
    """Tạo URL download trực tiếp của file trong Release."""
    return f"https://github.com/{username}/{repo}/releases/download/{tag}/{requests.utils.quote(filename)}"

def list_repo_files(token, username, repo, branch, path=""):
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
    r = requests.get(url, headers=gh_headers(token), params={"ref": branch}, timeout=15)
    if r.status_code != 200:
        return []
    files = []
    for item in r.json():
        if item["type"] == "file":
            files.append(item["path"])
        elif item["type"] == "dir":
            files.extend(list_repo_files(token, username, repo, branch, item["path"]))
    return files

def list_release_assets(token, username, repo, tag="uploads"):
    url = f"https://api.github.com/repos/{username}/{repo}/releases/tags/{tag}"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    if r.status_code != 200:
        return []
    assets = r.json().get("assets", [])
    return [a["browser_download_url"] for a in assets]

# ── Secrets ───────────────────────────────────────────────────
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return None

_token    = get_secret("GITHUB_TOKEN")
_username = get_secret("GITHUB_USERNAME")
_repo     = get_secret("GITHUB_REPO")
_branch   = get_secret("GITHUB_BRANCH") or "main"
_tag      = get_secret("GITHUB_RELEASE_TAG") or "uploads"
secrets_loaded = all([_token, _username, _repo])

if "all_links" not in st.session_state:
    st.session_state.all_links = []

# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["📤 Upload Files", "📂 Lấy link từ repo / releases"])

with tab1:

    # ── Config ────────────────────────────────────────────────
    st.subheader("⚙️ GitHub Config")
    if secrets_loaded:
        st.markdown(
            f'<span class="badge-green">🔒 Secrets loaded</span>&nbsp;&nbsp;'
            f'<code>{_username}</code> / <code>{_repo}</code> · branch <code>{_branch}</code>',
            unsafe_allow_html=True,
        )
        with st.expander("🔧 Override thủ công"):
            token_ov    = st.text_input("Token", type="password", placeholder="Để trống = dùng Secret")
            username_ov = st.text_input("Username", placeholder=_username)
            repo_ov     = st.text_input("Repository", placeholder=_repo)
            branch_ov   = st.text_input("Branch", placeholder=_branch)
            tag_ov      = st.text_input("Release tag", placeholder=_tag)
        token    = token_ov    or _token
        username = username_ov or _username
        repo     = repo_ov     or _repo
        branch   = branch_ov   or _branch
        tag      = tag_ov      or _tag
    else:
        st.markdown('<span class="badge-yellow">⚠️ Chưa có Secrets — nhập tay</span>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            token    = st.text_input("GitHub Token", type="password", placeholder="ghp_xxxx...")
            username = st.text_input("Username", placeholder="ahai72160")
        with col2:
            repo   = st.text_input("Repository", placeholder="cloud_storage_save_anything_here")
            branch = st.text_input("Branch", value="main")
        tag = st.text_input("Release tag (cho file lớn)", value="uploads",
                            help="Tên tag của GitHub Release dùng để lưu file lớn")

    st.divider()

    # ── Method info ───────────────────────────────────────────
    st.subheader("📊 Phương thức upload tự động")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
<div class="method-box">
<span class="badge-blue">≤ 25 MB</span><br><br>
<b>Repo Contents API</b><br>
<small style="color:#888">→ Raw link thông thường<br>
<code>raw.githubusercontent.com/...</code></small>
</div>
""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""
<div class="method-box">
<span class="badge-purple">&gt; 25 MB · tới 2 GB</span><br><br>
<b>GitHub Releases API</b><br>
<small style="color:#888">→ Direct download link<br>
<code>github.com/.../releases/download/...</code></small>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Upload ────────────────────────────────────────────────
    subfolder = st.text_input("Subfolder (chỉ áp dụng file ≤ 25MB, để trống = root)",
                              placeholder="audio/  hoặc  video/")
    uploaded  = st.file_uploader("Kéo thả file vào đây (tối đa 2GB / file với Releases)",
                                 accept_multiple_files=True, label_visibility="collapsed")

    if uploaded:
        st.caption(f"📌 {len(uploaded)} file(s):")
        for f in uploaded:
            mb   = len(f.getvalue()) / 1024 / 1024
            method = "🟢 Repo API" if mb <= 25 else "🟣 Releases"
            st.caption(f"  {method} · `{f.name}` — {mb:.2f} MB")

    commit_msg = st.text_input("Commit message (cho file ≤ 25MB)",
                               value=f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if st.button("🚀 Upload lên GitHub", type="primary", use_container_width=True):
        errs = []
        if not token:    errs.append("Token")
        if not username: errs.append("Username")
        if not repo:     errs.append("Repository")
        if not uploaded: errs.append("File")
        if errs:
            st.error(f"⚠️ Thiếu: {', '.join(errs)}")
        else:
            new_links    = []
            progress_bar = st.progress(0)
            release_info = None  # lazy-load khi cần

            for i, file in enumerate(uploaded):
                file_bytes = file.getvalue()
                mb         = len(file_bytes) / 1024 / 1024
                slot       = st.empty()

                # ── File nhỏ ≤ 25MB: dùng Contents API ──────
                if mb <= 25:
                    sf          = subfolder.strip().strip("/")
                    remote_path = f"{sf}/{file.name}" if sf else file.name
                    slot.info(f"⏳ **`{file.name}`** ({mb:.2f} MB) — Repo Contents API...")
                    try:
                        resp = upload_small_file(token, username, repo, branch,
                                                 remote_path, file_bytes, commit_msg)
                        if resp.status_code in (200, 201):
                            raw_url = build_raw_url(username, repo, branch, remote_path)
                            new_links.append(raw_url)
                            slot.success(f"✅ **`{file.name}`** → `{raw_url}`")
                        else:
                            err = resp.json().get("message", resp.text[:200])
                            slot.error(f"❌ **`{file.name}`** → {err}")
                    except Exception as e:
                        slot.error(f"❌ **`{file.name}`** → {e}")

                # ── File lớn > 25MB: dùng Releases API ──────
                else:
                    slot.info(f"⏳ **`{file.name}`** ({mb:.1f} MB) — GitHub Releases API...")
                    try:
                        # Lấy release 1 lần rồi cache
                        if release_info is None:
                            slot.info(f"⏳ **`{file.name}`** — Đang chuẩn bị Release `{tag}`...")
                            release_info = get_or_create_release(token, username, repo, tag)

                        rid        = release_info["id"]
                        upload_url = release_info["upload_url"]

                        slot.info(f"⏳ **`{file.name}`** ({mb:.1f} MB) — Đang upload lên Release...")
                        asset     = upload_release_asset(token, username, repo, rid,
                                                         upload_url, file.name, file_bytes)
                        dl_url    = asset.get("browser_download_url", "")
                        new_links.append(dl_url)
                        slot.success(f"✅ **`{file.name}`** ({mb:.1f}MB) → Releases · `{dl_url}`")

                    except requests.exceptions.HTTPError as e:
                        try:
                            msg = e.response.json().get("message", "")
                        except Exception:
                            msg = str(e)
                        slot.error(f"❌ **`{file.name}`** → HTTP {e.response.status_code}: {msg}")
                    except Exception as e:
                        slot.error(f"❌ **`{file.name}`** → {e}")

                progress_bar.progress((i + 1) / len(uploaded))
                time.sleep(0.2)

            progress_bar.empty()
            st.session_state.all_links.extend(new_links)
            if new_links:
                st.balloons()
                st.success(f"🎉 Upload thành công {len(new_links)}/{len(uploaded)} file!")

    # ── Kết quả ───────────────────────────────────────────────
    if st.session_state.all_links:
        st.divider()
        st.subheader("🔗 Links")
        links_html = "".join(f"<div>📎 {l}</div>" for l in st.session_state.all_links)
        st.markdown(f'<div class="link-box">{links_html}</div>', unsafe_allow_html=True)

        combined = ",".join(st.session_state.all_links)
        st.subheader("📋 Combined (dấu phẩy)")
        st.markdown(f'<div class="combined-box">{combined}</div>', unsafe_allow_html=True)
        st.text_area("✂️ Copy:", value=combined, height=100, label_visibility="visible")

        if st.button("🗑️ Xoá danh sách", use_container_width=True):
            st.session_state.all_links = []
            st.rerun()

# ══════════════════════════════════════════════════════════════
# TAB 2 – BROWSE
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📂 Lấy link từ Repo & Releases")

    t2 = _token;    u2 = _username;    r2 = _repo;    b2 = _branch;    g2 = _tag

    ext_input = st.text_input("Lọc đuôi file (để trống = tất cả)", value=".mp3, .mp4, .wav")

    col_browse1, col_browse2 = st.columns(2)

    with col_browse1:
        if st.button("🔍 Quét Repo (file ≤ 25MB)", use_container_width=True):
            if not all([t2, u2, r2]):
                st.error("⚠️ Chưa có thông tin GitHub.")
            else:
                with st.spinner("Đang quét repo..."):
                    all_files = list_repo_files(t2, u2, r2, b2)
                exts     = [e.strip().lower() for e in ext_input.split(",") if e.strip()]
                filtered = [f for f in all_files if any(f.lower().endswith(e) for e in exts)] if exts else all_files
                if filtered:
                    repo_links = [build_raw_url(u2, r2, b2, f) for f in filtered]
                    combined_r = ",".join(repo_links)
                    st.success(f"✅ {len(repo_links)} file trong repo")
                    links_html = "".join(f"<div>📎 {l}</div>" for l in repo_links)
                    st.markdown(f'<div class="link-box">{links_html}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="combined-box">{combined_r}</div>', unsafe_allow_html=True)
                    st.text_area("Copy repo:", value=combined_r, height=80, label_visibility="visible")
                else:
                    st.info("Không tìm thấy file phù hợp.")

    with col_browse2:
        if st.button("🔍 Quét Releases (file lớn)", use_container_width=True):
            if not all([t2, u2, r2]):
                st.error("⚠️ Chưa có thông tin GitHub.")
            else:
                with st.spinner(f"Đang lấy assets từ Release `{g2}`..."):
                    asset_urls = list_release_assets(t2, u2, r2, g2)
                exts = [e.strip().lower() for e in ext_input.split(",") if e.strip()]
                filtered2 = [u for u in asset_urls if any(u.lower().endswith(e) for e in exts)] if exts else asset_urls
                if filtered2:
                    combined_a = ",".join(filtered2)
                    st.success(f"✅ {len(filtered2)} file trong Releases")
                    links_html2 = "".join(f"<div>📎 {u}</div>" for u in filtered2)
                    st.markdown(f'<div class="link-box">{links_html2}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="combined-box">{combined_a}</div>', unsafe_allow_html=True)
                    st.text_area("Copy releases:", value=combined_a, height=80, label_visibility="visible")
                else:
                    st.info(f"Không có asset nào trong Release `{g2}` với đuôi đó.")

st.markdown("""
<div style="text-align:center;color:#444;font-size:0.7rem;font-family:monospace;margin-top:2rem;">
    GitHub File Uploader · Repo API ≤ 25MB · Releases API ≤ 2GB
</div>
""", unsafe_allow_html=True)
