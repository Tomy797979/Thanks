import streamlit as st
import requests
import base64
import time
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
.sub { text-align:center; color:#888; font-family:'JetBrains Mono',monospace; font-size:0.8rem; margin-bottom:1.5rem; }
.link-box {
    background:#0d1117; border:1px solid #30363d; border-radius:10px;
    padding:1rem 1.2rem; font-family:'JetBrains Mono',monospace;
    font-size:0.72rem; color:#58a6ff; word-break:break-all; line-height:2;
}
.combined-box {
    background:#0d1117; border:1px solid #238636; border-radius:10px;
    padding:1rem 1.2rem; font-family:'JetBrains Mono',monospace;
    font-size:0.7rem; color:#3fb950; word-break:break-all; line-height:1.8;
}
.secret-badge {
    display:inline-block; background:rgba(63,185,80,0.15);
    border:1px solid rgba(63,185,80,0.4); border-radius:6px;
    padding:2px 10px; font-size:0.72rem; color:#3fb950;
    font-family:'JetBrains Mono',monospace;
}
.info-badge {
    display:inline-block; background:rgba(56,189,248,0.1);
    border:1px solid rgba(56,189,248,0.3); border-radius:6px;
    padding:2px 10px; font-size:0.72rem; color:#38bdf8;
    font-family:'JetBrains Mono',monospace;
}
.warn-badge {
    display:inline-block; background:rgba(210,153,34,0.15);
    border:1px solid rgba(210,153,34,0.4); border-radius:6px;
    padding:2px 10px; font-size:0.72rem; color:#d29922;
    font-family:'JetBrains Mono',monospace;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🚀 GitHub File Uploader</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Upload files lớn → Raw GitHub links tự động · Hỗ trợ tới 100MB</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# GITHUB GIT DATA API — hỗ trợ file lớn (không bị giới hạn 25MB)
# Flow: tạo blob → lấy tree hiện tại → tạo tree mới → commit → update ref
# ══════════════════════════════════════════════════════════════

def gh_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

def get_branch_sha(token, username, repo, branch):
    """Lấy SHA commit mới nhất của branch."""
    url = f"https://api.github.com/repos/{username}/{repo}/git/ref/heads/{branch}"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    r.raise_for_status()
    return r.json()["object"]["sha"]

def get_tree_sha(token, username, repo, commit_sha):
    """Lấy SHA của tree từ commit."""
    url = f"https://api.github.com/repos/{username}/{repo}/git/commits/{commit_sha}"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    r.raise_for_status()
    return r.json()["tree"]["sha"]

def create_blob(token, username, repo, file_bytes):
    """Tạo blob từ nội dung file — KHÔNG giới hạn 25MB như Contents API."""
    url = f"https://api.github.com/repos/{username}/{repo}/git/blobs"
    payload = {
        "content": base64.b64encode(file_bytes).decode("utf-8"),
        "encoding": "base64",
    }
    r = requests.post(url, headers=gh_headers(token), json=payload, timeout=600)
    r.raise_for_status()
    return r.json()["sha"]

def create_tree(token, username, repo, base_tree_sha, file_path, blob_sha):
    """Tạo tree mới chứa file."""
    url = f"https://api.github.com/repos/{username}/{repo}/git/trees"
    payload = {
        "base_tree": base_tree_sha,
        "tree": [{
            "path": file_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        }],
    }
    r = requests.post(url, headers=gh_headers(token), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["sha"]

def create_commit(token, username, repo, message, tree_sha, parent_sha):
    """Tạo commit mới."""
    url = f"https://api.github.com/repos/{username}/{repo}/git/commits"
    payload = {
        "message": message,
        "tree": tree_sha,
        "parents": [parent_sha],
    }
    r = requests.post(url, headers=gh_headers(token), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["sha"]

def update_ref(token, username, repo, branch, commit_sha):
    """Cập nhật branch HEAD sang commit mới."""
    url = f"https://api.github.com/repos/{username}/{repo}/git/refs/heads/{branch}"
    payload = {"sha": commit_sha, "force": False}
    r = requests.patch(url, headers=gh_headers(token), json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def upload_large_file(token, username, repo, branch, remote_path, file_bytes, commit_msg):
    """
    Upload file lên GitHub dùng Git Data API.
    Không bị giới hạn 25MB của Contents API.
    Hỗ trợ tới ~100MB (giới hạn của GitHub push).
    """
    # Bước 1: Lấy commit SHA hiện tại của branch
    commit_sha = get_branch_sha(token, username, repo, branch)

    # Bước 2: Lấy tree SHA từ commit đó
    tree_sha = get_tree_sha(token, username, repo, commit_sha)

    # Bước 3: Tạo blob từ nội dung file
    blob_sha = create_blob(token, username, repo, file_bytes)

    # Bước 4: Tạo tree mới chứa file
    new_tree_sha = create_tree(token, username, repo, tree_sha, remote_path, blob_sha)

    # Bước 5: Tạo commit mới
    new_commit_sha = create_commit(token, username, repo, commit_msg, new_tree_sha, commit_sha)

    # Bước 6: Cập nhật branch HEAD
    update_ref(token, username, repo, branch, new_commit_sha)

def build_raw_url(username, repo, branch, filepath):
    return f"https://raw.githubusercontent.com/{username}/{repo}/refs/heads/{branch}/{filepath}"

def list_repo_files(token, username, repo, branch, path=""):
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
    if r.status_code != 200:
        return []
    files = []
    for item in r.json():
        if item["type"] == "file":
            files.append(item["path"])
        elif item["type"] == "dir":
            files.extend(list_repo_files(token, username, repo, branch, item["path"]))
    return files

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
secrets_loaded = all([_token, _username, _repo])

if "all_links" not in st.session_state:
    st.session_state.all_links = []

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📤 Upload Files", "📂 Lấy link từ repo"])

# ══════════════════════════════════════════════════════════════
# TAB 1 – UPLOAD
# ══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("⚙️ GitHub Config")

    if secrets_loaded:
        st.markdown(
            f'<span class="secret-badge">🔒 Secrets đã load</span>'
            f'&nbsp;&nbsp;<code>{_username}</code> / <code>{_repo}</code> / branch: <code>{_branch}</code>',
            unsafe_allow_html=True,
        )
        with st.expander("🔧 Override thủ công"):
            token_ov    = st.text_input("Token", type="password", placeholder="Để trống = dùng Secret")
            username_ov = st.text_input("Username", placeholder=_username)
            repo_ov     = st.text_input("Repository", placeholder=_repo)
            branch_ov   = st.text_input("Branch", placeholder=_branch)
        token    = token_ov    or _token
        username = username_ov or _username
        repo     = repo_ov     or _repo
        branch   = branch_ov   or _branch
    else:
        st.markdown('<span class="warn-badge">⚠️ Chưa có Secrets — nhập tay</span>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            token    = st.text_input("GitHub Token", type="password", placeholder="ghp_xxxx...")
            username = st.text_input("GitHub Username", placeholder="ahai72160")
        with col2:
            repo   = st.text_input("Repository", placeholder="cloud_storage_save_anything_here")
            branch = st.text_input("Branch", value="main")

    st.divider()

    # Giới hạn upload Streamlit = 200MB (cấu hình trong config.toml)
    st.subheader("📁 Chọn file")
    st.markdown(
        '<span class="info-badge">ℹ️ Git Data API · Hỗ trợ file lớn tới ~100MB</span>',
        unsafe_allow_html=True,
    )
    st.caption("Lưu ý: File > 100MB GitHub sẽ từ chối. File WAV/MP4 lớn nên convert sang MP3/compressed MP4 trước.")

    subfolder = st.text_input("Subfolder (để trống = root)", placeholder="audio/  hoặc  video/")
    uploaded  = st.file_uploader("Kéo thả file vào đây", accept_multiple_files=True, label_visibility="collapsed")

    if uploaded:
        st.caption(f"📌 {len(uploaded)} file(s):")
        for f in uploaded:
            mb = len(f.getvalue()) / 1024 / 1024
            icon = "🔴" if mb > 100 else ("🟡" if mb > 50 else "🟢")
            st.caption(f"  {icon} `{f.name}` — {mb:.2f} MB")

    commit_msg = st.text_input("Commit message", value=f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}")

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

            for i, file in enumerate(uploaded):
                file_bytes = file.getvalue()
                mb         = len(file_bytes) / 1024 / 1024

                if mb > 100:
                    st.warning(f"⚠️ Bỏ qua `{file.name}` — {mb:.1f}MB vượt giới hạn 100MB của GitHub")
                    progress_bar.progress((i + 1) / len(uploaded))
                    continue

                sf          = subfolder.strip().strip("/")
                remote_path = f"{sf}/{file.name}" if sf else file.name
                slot        = st.empty()

                # Hiển thị progress từng bước
                slot.info(f"⏳ **`{file.name}`** ({mb:.2f} MB)\n\nĐang tạo blob...")

                try:
                    # Bước 1-2: lấy refs
                    commit_sha = get_branch_sha(token, username, repo, branch)
                    tree_sha   = get_tree_sha(token, username, repo, commit_sha)

                    slot.info(f"⏳ **`{file.name}`** — Đang upload nội dung file ({mb:.1f}MB)...")
                    blob_sha = create_blob(token, username, repo, file_bytes)

                    slot.info(f"⏳ **`{file.name}`** — Đang tạo commit...")
                    new_tree_sha   = create_tree(token, username, repo, tree_sha, remote_path, blob_sha)
                    new_commit_sha = create_commit(token, username, repo, commit_msg, new_tree_sha, commit_sha)
                    update_ref(token, username, repo, branch, new_commit_sha)

                    raw_url = build_raw_url(username, repo, branch, remote_path)
                    new_links.append(raw_url)
                    slot.success(f"✅ **`{file.name}`** → Upload thành công!")

                except requests.exceptions.HTTPError as e:
                    err_body = ""
                    try:
                        err_body = e.response.json().get("message", "")
                    except Exception:
                        pass
                    slot.error(f"❌ **`{file.name}`** → HTTP {e.response.status_code}: {err_body or str(e)}")

                except requests.exceptions.Timeout:
                    slot.error(f"❌ **`{file.name}`** → Timeout! Thử lại hoặc giảm kích thước file.")

                except Exception as e:
                    slot.error(f"❌ **`{file.name}`** → {e}")

                progress_bar.progress((i + 1) / len(uploaded))
                time.sleep(0.3)

            progress_bar.empty()
            st.session_state.all_links.extend(new_links)

            if new_links:
                st.balloons()
                st.success(f"🎉 Upload thành công {len(new_links)}/{len(uploaded)} file!")

    # ── Kết quả ───────────────────────────────────────────────
    if st.session_state.all_links:
        st.divider()
        st.subheader("🔗 Raw Links")
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
    st.subheader("📂 Lấy link tất cả file trong repo")

    if secrets_loaded:
        st.markdown(
            f'<span class="secret-badge">🔒 Secrets</span>'
            f'&nbsp;&nbsp;<code>{_username}/{_repo}</code> · branch <code>{_branch}</code>',
            unsafe_allow_html=True,
        )

    ext_input = st.text_input("Lọc đuôi file (để trống = lấy tất cả)", value=".mp3, .mp4, .wav",
                               placeholder=".mp3, .mp4, .wav, .jpg")

    if st.button("🔍 Quét repo", type="primary", use_container_width=True):
        t2 = (token    if "token"    in dir() and token    else None) or _token
        u2 = (username if "username" in dir() and username else None) or _username
        r2 = (repo     if "repo"     in dir() and repo     else None) or _repo
        b2 = (branch   if "branch"   in dir() and branch   else None) or _branch

        if not all([t2, u2, r2]):
            st.error("⚠️ Chưa có thông tin GitHub.")
        else:
            with st.spinner("Đang quét repo..."):
                all_files = list_repo_files(t2, u2, r2, b2)

            exts     = [e.strip().lower() for e in ext_input.split(",") if e.strip()]
            filtered = [f for f in all_files if any(f.lower().endswith(e) for e in exts)] if exts else all_files

            if filtered:
                repo_links = [build_raw_url(u2, r2, b2, f) for f in filtered]
                combined2  = ",".join(repo_links)

                st.success(f"✅ Tìm thấy {len(repo_links)} file")
                links_html2 = "".join(f"<div>📎 {l}</div>" for l in repo_links)
                st.markdown(f'<div class="link-box">{links_html2}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="combined-box">{combined2}</div>', unsafe_allow_html=True)
                st.text_area("✂️ Copy:", value=combined2, height=100, label_visibility="visible")

                if st.button("➕ Thêm vào danh sách tab Upload"):
                    st.session_state.all_links.extend(repo_links)
                    st.success("✅ Đã thêm!")
            else:
                st.info(f"Không tìm thấy file nào với đuôi: {exts}")

st.markdown("""
<div style="text-align:center;color:#444;font-size:0.7rem;font-family:monospace;margin-top:2rem;">
    GitHub File Uploader · Git Data API · Streamlit Cloud
</div>
""", unsafe_allow_html=True)
