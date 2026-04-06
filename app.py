import streamlit as st
import requests
import base64
import os
import time
from datetime import datetime

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="GitHub File Uploader",
    page_icon="🚀",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Sora:wght@300;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
    background: #0a0a0f;
    color: #e8e8f0;
}

.stApp {
    background: linear-gradient(135deg, #0a0a0f 0%, #0f0f1a 50%, #0a0a0f 100%);
}

/* Title */
.main-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #7c6af7, #a78bfa, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.2rem;
    letter-spacing: -1px;
}
.sub-title {
    text-align: center;
    color: #6b6b8a;
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 2rem;
}

/* Card */
.card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(124,106,247,0.25);
    border-radius: 16px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(10px);
}
.card-title {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #7c6af7;
    margin-bottom: 0.8rem;
    font-family: 'JetBrains Mono', monospace;
}

/* Input overrides */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(124,106,247,0.3) !important;
    border-radius: 10px !important;
    color: #e8e8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #7c6af7 !important;
    box-shadow: 0 0 0 2px rgba(124,106,247,0.2) !important;
}

/* File uploader */
.stFileUploader > div {
    background: rgba(255,255,255,0.03) !important;
    border: 2px dashed rgba(124,106,247,0.4) !important;
    border-radius: 12px !important;
}
.stFileUploader > div:hover {
    border-color: #7c6af7 !important;
    background: rgba(124,106,247,0.05) !important;
}

/* Button */
.stButton > button {
    background: linear-gradient(135deg, #7c6af7, #5b4fe0) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.6rem 1.5rem !important;
    width: 100% !important;
    transition: all 0.2s !important;
    letter-spacing: 0.3px !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #8f7fff, #7c6af7) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(124,106,247,0.4) !important;
}

/* Link box */
.link-box {
    background: rgba(56,189,248,0.07);
    border: 1px solid rgba(56,189,248,0.3);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #38bdf8;
    word-break: break-all;
    line-height: 1.8;
    margin-top: 0.8rem;
}
.link-item {
    padding: 4px 0;
    border-bottom: 1px solid rgba(56,189,248,0.1);
}
.link-item:last-child { border-bottom: none; }

/* Combined box */
.combined-box {
    background: rgba(16,185,129,0.07);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 12px;
    padding: 1rem 1.4rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #10b981;
    word-break: break-all;
    line-height: 1.8;
    margin-top: 0.8rem;
}

/* Success / error */
.status-ok  { color: #10b981; font-weight: 600; font-size: 0.85rem; }
.status-err { color: #f87171; font-weight: 600; font-size: 0.85rem; }

/* Divider */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(124,106,247,0.3), transparent);
    margin: 1.5rem 0;
}

/* Select box */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(124,106,247,0.3) !important;
    border-radius: 10px !important;
    color: #e8e8f0 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown('<div class="main-title">🚀 GitHub File Uploader</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Upload files → Get raw GitHub links instantly</div>', unsafe_allow_html=True)

# ── Helper functions ──────────────────────────────────────────

def build_raw_url(username: str, repo: str, branch: str, filepath: str) -> str:
    """Tạo raw GitHub URL từ thông tin repo."""
    return f"https://raw.githubusercontent.com/{username}/{repo}/refs/heads/{branch}/{filepath}"


def upload_to_github(token: str, username: str, repo: str, branch: str,
                     remote_path: str, file_bytes: bytes, message: str) -> dict:
    """Upload hoặc update file lên GitHub qua API."""
    api_url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    # Kiểm tra file đã tồn tại chưa (để lấy sha nếu cần update)
    sha = None
    check = requests.get(api_url, headers=headers, params={"ref": branch})
    if check.status_code == 200:
        sha = check.json().get("sha")

    payload = {
        "message": message,
        "content": base64.b64encode(file_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(api_url, headers=headers, json=payload)
    return resp


def list_repo_files(token: str, username: str, repo: str, branch: str, path: str = "") -> list:
    """Liệt kê tất cả file trong repo (đệ quy)."""
    api_url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(api_url, headers=headers, params={"ref": branch})
    if resp.status_code != 200:
        return []

    files = []
    for item in resp.json():
        if item["type"] == "file":
            files.append(item["path"])
        elif item["type"] == "dir":
            files.extend(list_repo_files(token, username, repo, branch, item["path"]))
    return files


# ── Session state ─────────────────────────────────────────────
if "uploaded_links" not in st.session_state:
    st.session_state.uploaded_links = []

# ── Config card ───────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">⚙️ GitHub Configuration</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    github_token = st.text_input(
        "GitHub Token (ghp_...)",
        type="password",
        placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
        help="Settings → Developer settings → Personal access tokens → Fine-grained tokens. Cấp quyền: Contents (read & write)"
    )
    github_username = st.text_input(
        "GitHub Username",
        placeholder="ahai72160",
    )
with col2:
    github_repo = st.text_input(
        "Repository Name",
        placeholder="cloud_storage_save_anything_here",
    )
    github_branch = st.text_input(
        "Branch",
        value="main",
        placeholder="main",
    )

subfolder = st.text_input(
    "Subfolder (tuỳ chọn)",
    placeholder="videos/  hoặc  audio/  hoặc để trống",
    help="Để trống = upload vào root repo"
)

st.markdown('</div>', unsafe_allow_html=True)

# ── Upload card ───────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title">📁 Upload Files</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Kéo thả hoặc chọn file",
    accept_multiple_files=True,
    label_visibility="collapsed",
)

commit_msg = st.text_input(
    "Commit message",
    value=f"Upload via Streamlit - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
)

st.markdown('</div>', unsafe_allow_html=True)

# ── Upload button ─────────────────────────────────────────────
do_upload = st.button("🚀 Upload lên GitHub", use_container_width=True)

if do_upload:
    # Validate
    missing = []
    if not github_token:   missing.append("GitHub Token")
    if not github_username: missing.append("Username")
    if not github_repo:    missing.append("Repository")
    if not uploaded_files: missing.append("File cần upload")

    if missing:
        st.error(f"⚠️ Thiếu: {', '.join(missing)}")
    else:
        new_links = []
        progress = st.progress(0, text="Đang upload...")

        for i, file in enumerate(uploaded_files):
            filename = file.name
            remote_path = f"{subfolder.strip('/')}/{filename}" if subfolder.strip() else filename
            remote_path = remote_path.lstrip("/")

            file_bytes = file.read()

            with st.spinner(f"Uploading `{filename}`..."):
                resp = upload_to_github(
                    token=github_token,
                    username=github_username,
                    repo=github_repo,
                    branch=github_branch,
                    remote_path=remote_path,
                    file_bytes=file_bytes,
                    message=commit_msg,
                )

            if resp.status_code in (200, 201):
                raw_url = build_raw_url(github_username, github_repo, github_branch, remote_path)
                new_links.append(raw_url)
                st.markdown(f'<p class="status-ok">✅ {filename} → uploaded</p>', unsafe_allow_html=True)
            else:
                err = resp.json().get("message", resp.text)
                st.markdown(f'<p class="status-err">❌ {filename} → {err}</p>', unsafe_allow_html=True)

            progress.progress((i + 1) / len(uploaded_files), text=f"{i+1}/{len(uploaded_files)} files")
            time.sleep(0.3)

        progress.empty()

        # Thêm vào session
        st.session_state.uploaded_links.extend(new_links)

        if new_links:
            st.success(f"🎉 Upload thành công {len(new_links)}/{len(uploaded_files)} files!")

# ── Results ───────────────────────────────────────────────────
if st.session_state.uploaded_links:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">🔗 Raw Links</div>', unsafe_allow_html=True)

    links_html = "".join(
        f'<div class="link-item">📎 {link}</div>'
        for link in st.session_state.uploaded_links
    )
    st.markdown(f'<div class="link-box">{links_html}</div>', unsafe_allow_html=True)

    # Combined string
    combined = ",".join(st.session_state.uploaded_links)
    st.markdown('<div class="card-title" style="margin-top:1.2rem">📋 Combined (dấu phẩy)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="combined-box">{combined}</div>', unsafe_allow_html=True)

    # Copy button via text area
    st.text_area("Copy tại đây:", value=combined, height=80, label_visibility="collapsed")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Xoá danh sách", use_container_width=True):
            st.session_state.uploaded_links = []
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ── Browse existing repo files ─────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="card"><div class="card-title">📂 Lấy link từ repo hiện có</div>', unsafe_allow_html=True)

ext_filter = st.text_input(
    "Lọc theo đuôi file (cách nhau bằng dấu phẩy)",
    placeholder=".mp3, .mp4, .jpg, .png, .pdf",
    value=".mp3, .mp4",
)

if st.button("🔍 Lấy tất cả link từ repo", use_container_width=True):
    if not all([github_token, github_username, github_repo]):
        st.error("⚠️ Điền đủ Token, Username, Repo ở trên trước!")
    else:
        with st.spinner("Đang quét repo..."):
            all_files = list_repo_files(github_token, github_username, github_repo, github_branch)

        exts = [e.strip().lower() for e in ext_filter.split(",") if e.strip()]

        if exts:
            filtered = [f for f in all_files if any(f.lower().endswith(e) for e in exts)]
        else:
            filtered = all_files

        if filtered:
            repo_links = [build_raw_url(github_username, github_repo, github_branch, f) for f in filtered]
            combined_repo = ",".join(repo_links)

            links_html2 = "".join(f'<div class="link-item">📎 {l}</div>' for l in repo_links)
            st.markdown(f'<div class="link-box">{links_html2}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="combined-box">{combined_repo}</div>', unsafe_allow_html=True)
            st.text_area("Copy:", value=combined_repo, height=80, label_visibility="collapsed")

            if st.button("➕ Thêm vào danh sách trên", use_container_width=True):
                st.session_state.uploaded_links.extend(repo_links)
                st.rerun()
        else:
            st.info(f"Không tìm thấy file nào với đuôi: {exts}")

st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; color:#3a3a52; font-size:0.72rem;
            font-family:'JetBrains Mono',monospace; margin-top:2rem; padding-bottom:1rem;">
    GitHub File Uploader · Powered by GitHub API + Streamlit
</div>
""", unsafe_allow_html=True)
