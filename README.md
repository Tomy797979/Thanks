# 🚀 GitHub File Uploader

Upload file lên GitHub và tự động tạo raw link dạng:
```
https://raw.githubusercontent.com/{username}/{repo}/refs/heads/{branch}/{filename}
```

## 🗂️ Cấu trúc project

```
github_uploader/
├── app.py
├── requirements.txt
└── .streamlit/
    └── config.toml
```

## ▶️ Chạy local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Deploy lên Streamlit Cloud

1. Push toàn bộ thư mục lên GitHub repo của bạn
2. Vào https://share.streamlit.io → **New app**
3. Chọn repo, branch `main`, file `app.py`
4. Nhấn **Deploy**

## 🔑 Tạo GitHub Token

1. GitHub → **Settings** → **Developer settings**
2. → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
3. Cấp quyền **Contents: Read and write** cho repo cần dùng
4. Copy token → dán vào app khi dùng

## ✨ Tính năng

- Upload nhiều file cùng lúc
- Tự động tạo raw link sau khi upload
- Xuất combined link cách nhau dấu phẩy
- Quét toàn bộ repo để lấy link file có sẵn
- Lọc theo đuôi file (.mp3, .mp4, .jpg, ...)
