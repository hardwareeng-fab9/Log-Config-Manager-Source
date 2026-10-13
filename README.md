# TestPath Manager (TPM) — v1.1 (optional Engineer setup)

Ứng dụng Windows dùng **Python + Tkinter** để quản lý đường dẫn và tài khoản Engineer của trạm test. Source chạy bằng Python, có batch build `.exe` **không hiện console**.

## 1. Chức năng

**Giao diện gồm 2 khu vực:**

- **TabControl phía trên** với 2 tab:
  - **Path Management**: xem danh sách, Add, Edit, Update/Save, Cancel, Delete; nhập path trực tiếp hoặc Choose File / Choose Folder; Check Entered Path / Check Selected / Check All; Reload TXT.
  - **Engineer Accounts**: xem danh sách, Add, Edit, Update/Save, Cancel, Delete; có Project Name, User Name và Password.
- **Event Log phía dưới**: hiển thị các thao tác, trạng thái kiểm tra, lỗi và các lần xác thực. Log chỉ tồn tại trong phiên chạy, nút Clear View xóa phần hiển thị.

**Mặc định không bắt buộc tạo Project hoặc tài khoản Engineer.** Khi `accounts.txt` chưa có tài khoản, app mở trực tiếp vào giao diện chính, có thể thêm/sửa/xóa path ngay và chỉ hiện popup xác nhận Save/Delete (không hỏi mật khẩu).

**Chỉ khi bạn chủ động tạo tài khoản Engineer**, chế độ xác thực mới bật. Các thao tác thay đổi bản ghi (thêm/sửa/xóa path hoặc account) khi đó yêu cầu xác thực. Nếu chỉ có 1 tài khoản Engineer, popup chỉ yêu cầu **mật khẩu**; nếu có nhiều tài khoản thì chọn Project, tên Engineer và nhập mật khẩu.

Việc cập nhật trạng thái trong lúc kiểm tra path không yêu cầu xác thực. Bạn có thể xóa cả tài khoản cuối cùng sau khi nhập đúng mật khẩu và xác nhận cảnh báo; lúc này chế độ mật khẩu sẽ tắt.

## 2. Cấu trúc thư mục

```text
TestPath-Manager/
├── main.py
├── app/
│   ├── __init__.py
│   ├── gui.py
│   ├── security.py
│   └── storage.py
├── data/
│   ├── paths.txt
│   └── accounts.txt
├── tests/
│   └── test_core.py
├── requirements.txt
├── run-source.bat
├── build-exe.bat
└── README.md
```

Hai file `.txt` là dữ liệu runtime, **không nằm trong EXE**. EXE sẽ tự sử dụng thư mục `data` ở **cùng cấp với EXE**. Khi chuyển EXE sang máy khác, nhớ chuyển cả thư mục `data` (hoặc để chương trình tạo mới).

## 3. Cấu trúc dữ liệu TXT

File `.txt` sử dụng **UTF-8 + tab-separated values (TSV)**, mở bằng Notepad hoặc Excel được. Dòng đầu phải giữ nguyên các tên cột, được ngăn cách bởi ký tự Tab.

### data/paths.txt

```text
id    name          path                                     status
P0001 Pytest Folder C:\ATE\pytest-cfind                      EXISTS
P0002 Log Directory D:\ATE\TestLogs                          MISSING
```

Trên file thực tế, các cột cách nhau bằng **Tab**, không phải các dấu cách như minh họa bên trên. Những trạng thái có thể xuất hiện: `EXISTS`, `MISSING`, `INVALID`, `UNSUPPORTED` (trường hợp nhập URL HTTP/HTTPS thay vì đường dẫn local/UNC).

### data/accounts.txt

```text
id    project_name   user_name   password
A0001 04151-System   engineer01  pbkdf2_sha256$390000$...$...
```

**Lưu ý:** giá trị trong cột `password` là **hash một chiều PBKDF2-HMAC-SHA256 có salt riêng**. Không thể hiển thị lại mật khẩu từ file. Khi cần đổi mật khẩu, Engineer đã được cấp quyền vào tab Accounts → Edit → nhập mật khẩu mới → Update/Save.

**Không tự nhập mật khẩu plaintext vào `accounts.txt`.** Tạo người dùng từ GUI để hệ thống hash đúng định dạng.

## 4. Chạy bằng source

1. Cài **Python 3.10 trở lên** trên Windows, nhớ chọn Tkinter (mặc định trong bộ cài chính thức).
2. Giải nén source vào thư mục có quyền ghi, ví dụ `D:\Tools\TestPath-Manager`.
3. Chạy `run-source.bat` hoặc lệnh `python main.py`.
4. App mở **ngay vào giao diện chính**, không có popup bắt đăng ký Project hoặc tài khoản, kể cả khi `accounts.txt` đang trống.
5. Bạn có thể thêm, sửa, kiểm tra và xóa Path trực tiếp. Tab Engineer Accounts chỉ dùng khi bạn muốn **tự bật** chế độ bảo vệ bằng mật khẩu.

Ứng dụng runtime **không yêu cầu cài thêm thư viện ngoài**. `tkinter`, `hashlib`, `csv` đều có sẵn trong bản Python Windows thông thường.

## 5. Build EXE (Windows)

Chạy **`build-exe.bat`**. Batch sẽ dùng Python hiện có, tự cài **PyInstaller** nếu chưa có và tạo:

```text
dist/
├── TestPathManager.exe
└── data/
    ├── paths.txt
    └── accounts.txt
```

- Đây là **EXE GUI không mở thêm cửa sổ CMD** khi chạy.
- `build-exe.bat` cần mạng nếu máy chưa cài PyInstaller.
- Chạy batch build **trên Windows** để tạo EXE Windows.
- Nếu file `dist/data/*.txt` đã tồn tại, batch **không ghi đè**, giữ dữ liệu cũ.
- Các file data phải nằm trong thư mục có quyền ghi của người chạy ứng dụng; nếu lưu trong `C:\Program Files` mặc định có thể bị chặn ghi.

## 6. Cách sử dụng ngắn gọn

**Thêm path:** Path Management → Add → Name → nhập Path hoặc Choose File/Folder → Check Entered Path → Update/Save → Confirm. Không cần tài khoản khi `accounts.txt` trống.

**Sửa path:** chọn dòng → Edit → sửa Name/Path → Update/Save → Confirm; nếu đã cấu hình tài khoản Engineer, sẽ yêu cầu xác thực.

**Xóa path:** chọn dòng → Delete → Confirm; nếu đã cấu hình tài khoản Engineer, sẽ yêu cầu xác thực.

**Kiểm tra path:** chọn dòng → Check Selected, hoặc nhấn Check All. Giá trị status được cập nhật trong `paths.txt` nếu có thay đổi. `EXISTS` nghĩa là file hoặc thư mục tồn tại tại **máy đang chạy app**; hỗ trợ đường dẫn local, mapped drive và UNC nếu Windows truy cập được.

**Thêm/sửa account (không bắt buộc):** Engineer Accounts → Add / Edit → nhập User Name, Password; Project Name có thể bỏ trống (tự dùng `DEFAULT`). Nếu Edit và muốn giữ mật khẩu cũ, để trống ô New Password. Nhấn Update/Save → Confirm.

**Bật bảo vệ mật khẩu:** tạo tài khoản Engineer đầu tiên từ tab Engineer Accounts, không cần đăng nhập hay khai báo project trước. Từ lúc tạo xong, app hỏi mật khẩu khi thêm/sửa/xóa.

**Tắt bảo vệ mật khẩu:** vào tab Engineer Accounts, chọn tài khoản cuối cùng → Delete → nhập đúng mật khẩu → xác nhận cảnh báo tắt bảo vệ. Nếu file `accounts.txt` trống ngay từ đầu, không cần làm gì cả.

## 7. Ranh giới bảo mật quan trọng

**Quan trọng:** Khi chưa có tài khoản Engineer, app **không có khóa chỉnh sửa**; bất kỳ người dùng Windows nào mở app và có quyền ghi dữ liệu đều có thể thay đổi Path. Đây là lựa chọn phù hợp nếu bạn dùng app riêng và không cần khóa Operator.

Khi bật bảo vệ, popup mật khẩu **chỉ bảo vệ thao tác bên trong GUI**, không thay thế phân quyền file trên hệ điều hành. Nếu Test Operator có quyền ghi/xóa trực tiếp thư mục `data`, họ có thể sửa `paths.txt`, `accounts.txt` bằng Notepad hoặc xóa chúng để khởi tạo lại tài khoản.

**Để phân quyền Engineer/Operator thực sự có hiệu lực trên trạm test:**

1. Lưu `data` vào thư mục được bảo vệ bằng **Windows NTFS ACL**, ngăn tài khoản Windows của Operator sửa hoặc xóa (và ngăn thay thế các file).
2. Cho phép Engineer hoặc một Windows service/agent chạy có quyền ghi để lưu thay đổi. Nếu Operator không có quyền ghi, app cũng không thể lưu thay đổi trong phiên Operator, kể cả sau khi nhập mật khẩu Engineer; khi đó phải có service hoặc khởi chạy ứng dụng dưới Windows identity có quyền phù hợp.
3. Không đặt quyền Modify/Full Control của thư mục `data` cho toàn bộ nhóm `Users` nếu đây là dữ liệu cần bảo vệ.
4. Sao lưu định kỳ cả `data/paths.txt` và `data/accounts.txt`.
5. Giữ bản source/EXE ngoài tầm sửa đổi của Operator; nếu họ có thể thay EXE hoặc chạy mã tùy ý với quyền ghi file, xác thực ở GUI không ngăn được.

Nếu bỏ qua NTFS ACL, đây là một **ứng dụng quản lý chống thao tác nhầm** khi đã bật mật khẩu, không phải hệ thống chống can thiệp có chủ đích. Bản hiện tại sử dụng **file cục bộ**, chưa có chức năng đồng bộ GitHub hoặc quản lý nhiều máy qua server. `Check Path` không xác thực URL từ GitHub.

## 8. Kiểm tra core

```cmd
python -m unittest discover -s tests -v
```

## 9. Thay đổi phiên bản v1.1

- Bỏ popup bắt buộc `First-run Engineer Account Setup` lúc khởi động và khi Reload TXT.
- Mặc định mở app ngay cả khi danh sách `accounts.txt` trống.
- Khi chưa tạo Engineer, thao tác Path không hỏi mật khẩu; vẫn hiện popup xác nhận lưu/xóa.
- Project Name trong màn hình thêm account là tùy chọn, mặc định `DEFAULT` nếu bỏ trống.
- Khi chỉ có một account, popup xác thực chỉ hỏi mật khẩu.
- Cho phép xóa account cuối cùng sau xác thực để tắt chế độ bảo vệ.
- Các file `paths.txt`/`accounts.txt` cũ vẫn dùng nguyên; nên sao lưu thư mục `data` trước khi nâng cấp.
