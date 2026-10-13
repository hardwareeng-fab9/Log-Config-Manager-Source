# TestPath Manager v1.2 — JSON Data Manager

Ứng dụng Windows (Python/Tkinter) dùng để quản lý đường dẫn test và tài khoản Engineer. **Tất cả dữ liệu đang dùng được lưu trong `data/paths.json` và `data/accounts.json`.** Không cần tạo Project/Account ở lần chạy đầu.

## 1. Chạy source và build EXE

- Yêu cầu: Python **3.10+** trên Windows, có Tkinter (thường được cài kèm Python chính thức). Runtime không cần thư viện ngoài.
- Chạy: nhấp `run-source.bat`, hoặc chạy `python main.py`.
- Test: `python -m unittest discover -s tests -v`.
- Build Windows EXE (no console): nhấp `build-exe.bat`. Batch sẽ cài PyInstaller nếu chưa có, sau đó build `dist/TestPathManager.exe`.
- Khi chạy EXE, file JSON ở **`dist/data/`** ngay cạnh EXE. Lần chạy đầu sẽ tự tạo file JSON nếu chưa có.
- Nên đặt app ở thư mục có quyền ghi, ví dụ `D:\Tools\TestPathManager`, tránh thư mục `Program Files`.

**Quan trọng:** Build trên Windows để tạo EXE Windows. File EXE không chứa dữ liệu JSON. Script build không ghi đè JSON/TXT của bản cũ.

## 2. Giao diện

**Phía trên:** TabControl 2 tab:

- **Path Management:** Add, Edit, Update / Save, Cancel, Delete, Choose File, Choose Folder, Check Entered Path, Check Selected, Check All, Reload JSON.
- **Engineer Accounts:** Add/Edit/Delete tài khoản, Project Name tùy chọn (rỗng -> `DEFAULT`), User Name và Password. Để trống mật khẩu khi Edit sẽ giữ mật khẩu đã lưu.

**Phía dưới:** EVENT LOG hiển thị hành động, lỗi và kết quả kiểm tra Path. Nút Clear View xóa log trên giao diện, không xóa file JSON.

Khi xóa hoặc lưu có **popup xác nhận**. Nếu `accounts.json` chưa có account: không yêu cầu mật khẩu. Khi chủ động thêm Engineer account đầu tiên: mật khẩu được yêu cầu cho các thao tác Add/Edit/Delete tiếp theo. Nếu chỉ có một account: chỉ cần nhập mật khẩu trong popup. Không có wizard bắt buộc khởi tạo account/project.

## 3. Cấu trúc JSON

### `data/paths.json`

```json
{
  "version": 1,
  "paths": [
    {
      "id": "P0001",
      "name": "FCT-770731",
      "path": "D:/FCT/770731",
      "type": "folder",
      "status": "EXISTS",
      "last_checked": "2026-10-13T10:30:00+07:00"
    }
  ]
}
```

Giải thích:

- `id`: tự tăng theo dạng `P0001`, `P0002`, ...
- `name`: tên hiển thị trong GUI.
- `path`: đường dẫn file, folder hoặc đường dẫn chia sẻ Windows (`\\server\share`). Ký tự `\` phải escape thành `\\` nếu nhập trực tiếp trong JSON; GUI tự xử lý.
- `type`: `file`, `folder`, `unknown`; tự xác định khi file/folder đang tồn tại.
- `status`: `EXISTS`, `MISSING`, `INVALID`, `UNSUPPORTED`, `UNCHECKED`. Kiểm tra đường dẫn **trên máy đang chạy app**. HTTP/HTTPS không được tính là local path.
- `last_checked`: thời gian kiểm tra gần nhất, có múi giờ; rỗng nếu import từ TXT cũ (không có thông tin này).

### `data/accounts.json`

```json
{
  "version": 1,
  "accounts": [
    {
      "id": "A0001",
      "project_name": "FCT-770731",
      "user_name": "engineer01",
      "password_hash": "pbkdf2_sha256$390000$...$...",
      "role": "engineer",
      "enabled": true
    }
  ]
}
```

- `id`: tự tăng theo dạng `A0001`, `A0002`, ...
- `project_name`: tên project hoặc `DEFAULT`.
- `user_name`: tên Engineer.
- `password_hash`: PBKDF2-HMAC-SHA256 + random salt, không phải mật khẩu thô. Dữ liệu mẫu phía trên chỉ minh họa, **không phải hash hợp lệ**. Hãy dùng GUI để thêm tài khoản.
- `role`, `enabled`: trường dự phòng cho phân quyền mở rộng. GUI hiện tạo tài khoản với `role="engineer"`, `enabled=true`; các account đang `enabled=true` đều có thể xác nhận thao tác. Giao diện chưa có chức năng chỉnh role/enabled.

Các bản ghi trong file được lưu dạng JSON UTF-8 dễ đọc (indent 2) và ghi bằng file tạm + thay thế để tránh ghi dở khi gặp lỗi. App từ chối nội dung JSON sai cú pháp, sai version, thiếu trường hoặc trùng ID, **không tự xóa/làm mới dữ liệu lỗi**.

Trong bộ source, thư mục `templates/` có hai file JSON rỗng minh họa. Ứng dụng **tự tạo `data/*.json` tại lần chạy đầu**, không cần chép template và không cần đăng ký tài khoản.

## 4. Tự chuyển dữ liệu TXT v1.1 sang JSON

### Cách nâng cấp từ phiên bản cũ

1. **Sao lưu** toàn bộ thư mục `data` đang dùng.
2. Dùng bộ source mới hoặc thay thế EXE v1.1 bằng EXE v1.2.
3. Đảm bảo thư mục `data` bên cạnh EXE chứa `paths.txt` / `accounts.txt` cũ nhưng **chưa có** các file JSON tương ứng.
4. Chạy app; app tự nhập từng file TXT cũ sang JSON với đầy đủ ID/Name/Path/Status/Project/User và **giữ nguyên password hash** để mật khẩu Engineer cũ vẫn sử dụng được.
5. Event Log báo số bản ghi đã import. Các file `.txt` cũ **không bị sửa hay xóa**, dùng làm bản sao lưu.

Ví dụ:

```text
TestPathManager.exe
└── data/
    ├── paths.txt         # còn lại như bản cũ, làm backup
    ├── accounts.txt      # còn lại như bản cũ, làm backup
    ├── paths.json        # sinh sau khi mở v1.2
    └── accounts.json     # sinh sau khi mở v1.2
```

Nếu đã có `paths.json` thì app **ưu tiên JSON**, không import lại `paths.txt`. Tương tự cho accounts. Nếu muốn di chuyển từ một bộ TXT khác, cần sao lưu JSON hiện có và chủ động xử lý chuyển đổi, **không xóa JSON khi chưa backup**. Việc chỉ đặt TXT cạnh một JSON có sẵn **không** ghi đè dữ liệu JSON.

## 5. Chức năng và lưu ý vận hành

- **Add/Edit Path:** Có thể nhập trực tiếp hoặc Choose File/Folder; `status`, `type`, `last_checked` cập nhật khi lưu. Trường hợp đường dẫn chưa tồn tại, `type="unknown"`; nếu chỉnh tên nhưng không đổi path thì có thể giữ type cũ.
- **Check Selected/Check All:** Cập nhật `status`, `type` (nếu tìm được) và `last_checked` vào JSON; không cần nhập password.
- **Xóa account cuối:** Phải xác thực + xác nhận thêm rằng thao tác này tắt chế độ bảo vệ. App không khởi tạo lại account khi mở lần sau.
- **Reload JSON:** Đọc lại dữ liệu JSON; hỏi xác nhận nếu đang sửa chưa lưu.
- **Không kết nối GitHub** trong v1.2; JSON hiện lưu local, không tải hoặc push dữ liệu trực tuyến.
- Nếu Operator có quyền ghi/xóa `data/accounts.json` trực tiếp trên Windows, popup mật khẩu **không phải bảo vệ an toàn tuyệt đối**. Giới hạn quyền NTFS/Windows hoặc dùng dịch vụ backend với phân quyền nếu triển khai multi-user. Đặt mật khẩu GUI không thể thay thế quyền filesystem.
- Nên backup hai file JSON, đặc biệt trước khi nâng cấp. Không commit thông tin tài khoản thật hay dữ liệu nhạy cảm lên public repo.

## 6. Cấu trúc dự án

```text
TestPath-Manager-v1.2/
├── main.py
├── app/
│   ├── __init__.py
│   ├── gui.py          # Tkinter / popup / event log
│   ├── storage.py      # JSON I/O, auto import TXT v1.1, validation
│   └── security.py     # PBKDF2 hash / verification
├── data/
│   └── README.txt      # paths.json/accounts.json tạo tự động
├── templates/
│   ├── paths.json
│   └── accounts.json
├── tests/
│   ├── test_core.py
│   └── test_gui.py
├── build-exe.bat
├── run-source.bat
├── requirements.txt
└── README.md
```
