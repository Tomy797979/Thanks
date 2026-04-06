import streamlit as st
import requests
import base64
import time
from datetime import datetime

st.set_page_config(
    page_title="GitHub File Uploader",
    page_icon="🚀",
    layout="centered",
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Sora:wght@300;600;800&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

.main-title {
    font-size: 2rem; font-weight: 800;
    background: linear-gradient(90deg, #7c6af7, #38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center; margin-bottom: 0.2rem;
}
.sub {
    text-align: center; color: #888;
    font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
    margin-bottom: 1.5rem;
}
.link-box {
    background: #0d1117; border: 1px solid #30363d;
    border-radius: 10px; padding: 1rem 1.2rem;
    font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
    color: #58a6ff; word-break: break-all; line-height: 2;
}
.combined-box {
    background: #0d1117; border: 1px solid #238636;
    border-radius: 10px; padding: 1rem 1.2rem;
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    color: #3fb950; word-break: break-all; line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🚀 GitHub File Uploader</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Upload files → Raw GitHub links tự động</div>', unsafe_allow_html=True)

# ── Functions ─────────────────────────────────────────────────

def build_raw_url(username, repo, branch, filepath):
    return f"https://raw.githubusercontent.com/{username}/{repo}/refs/heads/{branch}/{filepath}"


def get_file_sha(token, username, repo, branch, remote_path):
    """Lấy SHA của file nếu đã tồn tại (cần để update)."""
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    r = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def upload_chunk_base64(token, username, repo, branch, remote_path, file_bytes, commit_msg):
    """Upload file lên GitHub (hỗ trợ tới ~100MB qua base64 API)."""
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    sha = get_file_sha(token, username, repo, branch, remote_path)
    payload = {
        "message": commit_msg,
        "content": base64.b64encode(file_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload, timeout=300)
    return resp


def list_repo_files(token, username, repo, branch, path=""):
    """Liệt kê file trong repo (đệ quy)."""
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
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


# ── Session state ─────────────────────────────────────────────
if "all_links" not in st.session_state:
    st.session_state.all_links = []

# ── Tab layout ────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📤 Upload Files", "📂 Lấy link từ repo"])

# ══════════════════════════════════════════════════════════════
# TAB 1 – UPLOAD
# ══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("⚙️ GitHub Config")

    col1, col2 = st.columns(2)
    with col1:
        token    = st.text_input("GitHub Token", type="password", placeholder="ghp_xxxx...",
                                 help="Personal access token, cấp quyền Contents: read & write")
        username = st.text_input("GitHub Username", placeholder="ahai72160")
    with col2:
        repo   = st.text_input("Repository", placeholder="cloud_storage_save_anything_here")
        branch = st.text_input("Branch", value="main")

    subfolder = st.text_input("Subfolder (tuỳ chọn, để trống = root)",
                              placeholder="audio/ hoặc video/")

    st.divider()
    st.subheader("📁 Chọn file (tối đa 100MB / file)")

    # Tăng giới hạn upload lên 200MB tổng
    uploaded = st.file_uploader(
        "Kéo thả file vào đây",
        accept_multiple_files=True,
        type=None,                 # cho phép mọi loại file
        label_visibility="collapsed",
    )

    if uploaded:
        st.caption(f"📌 Đã chọn {len(uploaded)} file(s):")
        for f in uploaded:
            size_mb = len(f.getvalue()) / 1024 / 1024
            color = "🔴" if size_mb > 100 else "🟢"
            st.caption(f"  {color} `{f.name}` — {size_mb:.2f} MB")

    commit_msg = st.text_input(
        "Commit message",
        value=f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    if st.button("🚀 Upload lên GitHub", type="primary", use_container_width=True):
        errors = []
        if not token:    errors.append("GitHub Token")
        if not username: errors.append("Username")
        if not repo:     errors.append("Repository")
        if not uploaded: errors.append("File")

        if errors:
            st.error(f"⚠️ Thiếu: {', '.join(errors)}")
        else:
            new_links = []
            progress_bar = st.progress(0)

            for i, file in enumerate(uploaded):
                file_bytes = file.getvalue()
                size_mb = len(file_bytes) / 1024 / 1024

                if size_mb > 100:
                    st.warning(f"⚠️ Bỏ qua `{file.name}` — {size_mb:.1f}MB > 100MB giới hạn")
                    continue

                sf = subfolder.strip().strip("/")
                remote_path = f"{sf}/{file.name}" if sf else file.name

                status_text = st.empty()
                status_text.info(f"⏳ Đang upload `{file.name}` ({size_mb:.2f} MB)...")

                try:
                    resp = upload_chunk_base64(
                        token, username, repo, branch,
                        remote_path, file_bytes, commit_msg
                    )

                    if resp.status_code in (200, 201):
                        raw_url = build_raw_url(username, repo, branch, remote_path)
                        new_links.append(raw_url)
                        status_text.success(f"✅ `{file.name}` → Upload thành công!")
                    else:
                        err_msg = resp.json().get("message", resp.text[:200])
                        status_text.error(f"❌ `{file.name}` → Lỗi: {err_msg}")

                except requests.exceptions.Timeout:
                    status_text.error(f"❌ `{file.name}` → Timeout! File quá lớn hoặc mạng chậm.")
                except Exception as e:
                    status_text.error(f"❌ `{file.name}` → {str(e)}")

                progress_bar.progress((i + 1) / len(uploaded))
                time.sleep(0.5)

            progress_bar.empty()
            st.session_state.all_links.extend(new_links)

            if new_links:
                st.balloons()
                st.success(f"🎉 Upload xong {len(new_links)} file!")

    # ── Hiển thị kết quả ─────────────────────────────────────
    if st.session_state.all_links:
        st.divider()
        st.subheader("🔗 Raw Links")

        links_html = "".join(
            f"<div>📎 {l}</div>" for l in st.session_state.all_links
        )
        st.markdown(f'<div class="link-box">{links_html}</div>', unsafe_allow_html=True)

        combined = ",".join(st.session_state.all_links)
        st.subheader("📋 Combined (dấu phẩy)")
        st.markdown(f'<div class="combined-box">{combined}</div>', unsafe_allow_html=True)
        st.text_area("✂️ Copy tại đây:", value=combined, height=100, label_visibility="visible")

        if st.button("🗑️ Xoá danh sách", use_container_width=True):
            st.session_state.all_links = []
            st.rerun()

# ══════════════════════════════════════════════════════════════
# TAB 2 – BROWSE REPO
# ══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📂 Lấy link tất cả file trong repo")
    st.caption("Điền thông tin GitHub bên tab Upload trước, rồi quét tại đây.")

    ext_input = st.text_input(
        "Lọc theo đuôi file (để trống = lấy tất cả)",
        placeholder=".mp3, .mp4, .jpg, .png",
        value=".mp3, .mp4",
    )

    if st.button("🔍 Quét repo", type="primary", use_container_width=True):
        # Lấy giá trị từ tab1 — dùng lại biến đã khai báo
        _token    = token    if "token"    in dir() else ""
        _username = username if "username" in dir() else ""
        _repo     = repo     if "repo"     in dir() else ""
        _branch   = branch   if "branch"   in dir() else "main"

        if not all([_token, _username, _repo]):
            st.error("⚠️ Điền Token, Username, Repo ở tab Upload trước!")
        else:
            with st.spinner("Đang quét repo..."):
                all_files = list_repo_files(_token, _username, _repo, _branch)

            exts = [e.strip().lower() for e in ext_input.split(",") if e.strip()]
            filtered = (
                [f for f in all_files if any(f.lower().endswith(e) for e in exts)]
                if exts else all_files
            )

            if filtered:
                repo_links = [build_raw_url(_username, _repo, _branch, f) for f in filtered]
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
                st.info(f"Không tìm thấy file nào với đuôi: {exts or 'tất cả'}")

# ── Footer ────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;color:#555;font-size:0.7rem;
            font-family:monospace;margin-top:2rem;">
    GitHub File Uploader · GitHub API + Streamlit Cloud
</div>
""", unsafe_allow_html=True)
