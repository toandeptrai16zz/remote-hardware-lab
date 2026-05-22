# Quy Trinh Nap Code Dau-Cuoi

Nguon doi chieu code:

- `routes/user.py::flash_sketch_api`
- `services/arduino.py::get_user_assigned_device`
- `services/arduino.py::perform_upload_worker`
- `services/arduino.py::get_hardware_lock`

## Noi dung slide dung voi code hien tai

**Quy Trinh Nap Code Dau-Cuoi**  
Smart Routing -> Queue Reserve -> Compile -> Lock -> Pause Serial -> Upload -> Release

- User gui yeu cau nap code qua route `/user/<username>/flash`.
- Backend dung Smart Routing de chon cong co queue thap nhat va reserve queue ngay lap tuc.
- Worker nen chay ngam de HTTP request khong bi timeout.
- Code duoc compile trong sandbox container bang `arduino-cli compile`.
- Neu compile loi: stream log loi ve giao dien qua Socket.IO, ghi log, giam queue va ket thuc.
- Neu compile thanh cong: tien trinh vao file lock `fcntl` theo tung cong `/dev/ttyUSBx`.
- Khi toi luot nap: backend kick Serial Monitor frontend, force close serial port server-side va dong tien trinh dang giu cong neu co.
- Upload firmware bang `arduino-cli upload -p <port> --fqbn <board_fqbn>`, retry toi da 3 lan neu loi ket noi.
- Hoan tat: release lock, giam queue, cap nhat metric USB available va thong bao ket qua realtime.

## Diem can tranh ghi sai

- Khong ghi "neu cong bi chiem thi huy tien trinh". Code hien tai **cho doi lock**, khong huy ngay.
- Khong ghi "compile loi thi release lock". Compile duoc chay **truoc khi vao hardware lock**, nen compile loi chi giam queue va ket thuc.
- Khong ghi chac chan "chmod 666 /dev/ttyUSBx ngay truoc upload" trong flow nay. Permission co helper rieng o Docker manager/user route, con upload worker goi `arduino-cli upload`.

## File hinh

`docs/reports/end_to_end_flash_flow_2026-05-22.svg`
