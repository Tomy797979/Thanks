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
.manual-badge {
    display:inline-block; background:rgba(210,153,34,0.15);
    border:1px solid rgba(210,153,34,0.4); border-radius:6px;
    padding:2px 10px; font-size:0.72rem; color:#d29922;
    font-family:'JetBrains Mono',monospace;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🚀 GitHub File Uploader</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Upload files → Raw GitHub links tự động</div>', unsafe_allow_html=True)

# ── Đọc Secrets (tự động) hoặc fallback về manual input ──────

def get_secret(key):
    """Đọc từ st.secrets nếu có, ngược lại trả về None."""
    try:
        return st.secrets[key]
    except Exception:
        return None

_token    = get_secret("GITHUB_TOKEN")
_username = get_secret("GITHUB_USERNAME")
_repo     = get_secret("GITHUB_REPO")
_branch   = get_secret("GITHUB_BRANCH") or "main"

secrets_loaded = all([_token, _username, _repo])

# ── Functions ─────────────────────────────────────────────────

def build_raw_url(username, repo, branch, filepath):
    return f"https://raw.githubusercontent.com/{username}/{repo}/refs/heads/{branch}/{filepath}"

def get_file_sha(token, username, repo, branch, remote_path):
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{remote_path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
    return r.json().get("sha") if r.status_code == 200 else None

def upload_to_github(token, username, repo, branch, remote_path, file_bytes, commit_msg):
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
    return requests.put(url, headers=headers, json=payload, timeout=300)

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

# ── Session state ─────────────────────────────────────────────
if "all_links" not in st.session_state:
    st.session_state.all_links = []

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📤 Upload Files", "📂 Lấy link từ repo"])

# ══════════════════════════════════════════════════════════════
# TAB 1 – UPLOAD
# ══════════════════════════════════════════════════════════════
with tab1:

    # ── GitHub Config section ─────────────────────────────────
    st.subheader("⚙️ GitHub Config")

    if secrets_loaded:
        st.markdown(
            f'<span class="secret-badge">🔒 Secrets đã load tự động</span> '
            f'&nbsp; <code>{_username}</code> / <code>{_repo}</code> / branch: <code>{_branch}</code>',
            unsafe_allow_html=True
        )
        st.caption("Thông tin lấy từ Streamlit Secrets — không cần nhập tay.")

        # Vẫn cho phép override nếu muốn
        with st.expander("🔧 Override thủ công (tuỳ chọn)"):
            token_in    = st.text_input("GitHub Token", type="password", value="", placeholder="Để trống = dùng Secret")
            username_in = st.text_input("Username", value="", placeholder=_username)
            repo_in     = st.text_input("Repository", value="", placeholder=_repo)
            branch_in   = st.text_input("Branch", value="", placeholder=_branch)

        token    = token_in    or _token
        username = username_in or _username
        repo     = repo_in     or _repo
        branch   = branch_in   or _branch

    else:
        st.markdown('<span class="manual-badge">⚠️ Chưa có Secrets — nhập tay bên dưới</span>', unsafe_allow_html=True)
        st.caption("Hoặc vào Streamlit Cloud → Settings → Secrets để cấu hình tự động.")

        col1, col2 = st.columns(2)
        with col1:
            token    = st.text_input("GitHub Token", type="password", placeholder="ghp_xxxx...")
            username = st.text_input("GitHub Username", placeholder="ahai72160")
        with col2:
            repo   = st.text_input("Repository", placeholder="cloud_storage_save_anything_here")
            branch = st.text_input("Branch", value="main")

    st.divider()

    # ── Subfolder + Upload ────────────────────────────────────
    subfolder = st.text_input("Subfolder (để trống = root)", placeholder="audio/  hoặc  video/")

    st.subheader("📁 Chọn file (tối đa 100MB / file)")
    uploaded = st.file_uploader("Kéo thả file vào đây", accept_multiple_files=True, label_visibility="collapsed")

    if uploaded:
        st.caption(f"📌 Đã chọn {len(uploaded)} file(s):")
        for f in uploaded:
            size_mb = len(f.getvalue()) / 1024 / 1024
            icon = "🔴" if size_mb > 100 else "🟢"
            st.caption(f"  {icon} `{f.name}` — {size_mb:.2f} MB")

    commit_msg = st.text_input("Commit message", value=f"Upload {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if st.button("🚀 Upload lên GitHub", type="primary", use_container_width=True):
        errors = []
        if not token:    errors.append("GitHub Token")
        if not username: errors.append("Username")
        if not repo:     errors.append("Repository")
        if not uploaded: errors.append("File cần upload")

        if errors:
            st.error(f"⚠️ Thiếu: {', '.join(errors)}")
        else:
            new_links   = []
            progress_bar = st.progress(0)

            for i, file in enumerate(uploaded):
                file_bytes = file.getvalue()
                size_mb    = len(file_bytes) / 1024 / 1024

                if size_mb > 100:
                    st.warning(f"⚠️ Bỏ qua `{file.name}` — {size_mb:.1f}MB > 100MB")
                    continue

                sf          = subfolder.strip().strip("/")
                remote_path = f"{sf}/{file.name}" if sf else file.name
                slot        = st.empty()
                slot.info(f"⏳ Đang upload `{file.name}` ({size_mb:.2f} MB)...")

                try:
                    resp = upload_to_github(token, username, repo, branch, remote_path, file_bytes, commit_msg)
                    if resp.status_code in (200, 201):
                        raw_url = build_raw_url(username, repo, branch, remote_path)
                        new_links.append(raw_url)
                        slot.success(f"✅ `{file.name}` → OK")
                    else:
                        err = resp.json().get("message", resp.text[:200])
                        slot.error(f"❌ `{file.name}` → {err}")
                except requests.exceptions.Timeout:
                    slot.error(f"❌ `{file.name}` → Timeout! File quá lớn hoặc mạng chậm.")
                except Exception as e:
                    slot.error(f"❌ `{file.name}` → {e}")

                progress_bar.progress((i + 1) / len(uploaded))
                time.sleep(0.3)

            progress_bar.empty()
            st.session_state.all_links.extend(new_links)

            if new_links:
                st.balloons()
                st.success(f"🎉 Upload thành công {len(new_links)} file!")

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
            f'<span class="secret-badge">🔒 Dùng Secrets</span> '
            f'&nbsp; <code>{_username}/{_repo}</code> branch <code>{_branch}</code>',
            unsafe_allow_html=True
        )

    ext_input = st.text_input(
        "Lọc đuôi file (để trống = lấy tất cả)",
        value=".mp3, .mp4",
        placeholder=".mp3, .mp4, .jpg, .png",
    )

    if st.button("🔍 Quét repo", type="primary", use_container_width=True):
        t2 = token    if "token"    in dir() and token    else _token
        u2 = username if "username" in dir() and username else _username
        r2 = repo     if "repo"     in dir() and repo     else _repo
        b2 = branch   if "branch"   in dir() and branch   else _branch

        if not all([t2, u2, r2]):
            st.error("⚠️ Chưa có thông tin GitHub. Điền ở tab Upload hoặc cấu hình Secrets.")
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
                st.info(f"Không tìm thấy file nào với đuôi: {exts or 'tất cả'}")

st.markdown("""
<div style="text-align:center;color:#444;font-size:0.7rem;font-family:monospace;margin-top:2rem;">
    GitHub File Uploader · Streamlit Secrets + GitHub API
</div>
""", unsafe_allow_html=True)
