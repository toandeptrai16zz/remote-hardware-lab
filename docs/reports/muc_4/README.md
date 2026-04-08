# Mục 4: Báo cáo CI/CD và Triển khai Kubernetes

## 1. Tổng quan triển khai
Để loại bỏ sự rườm rà của Docker Compose gốc, dự án đã đóng gói môi trường thành Cụm (Cluster) dưới nguyên lý của Kubernetes. Kiến trúc này đóng vai trò quyết định trong việc mở rộng quy mô.

## 2. Continuous Integration (GitHub Actions)
Được cấu hình trong `.github/workflows/ci.yml`.
- Tự động hóa quá trình chạy Test mỗi khi Push hoặc tạo Pull Request.
- Ngăn ngừa tính năng lỗi bằng `pytest`, đảm bảo dự án ở trạng thái ổn định nhất trước khi cập bến môi trường máy chủ Lab.

## 3. Cấu hình Kubernetes (Manifests)
- `db-deployment.yaml`: Phát khởi cơ sở dữ liệu MySQL vào Pod độc lập, ẩn hoàn toàn với bên ngoài. Lộ cổng `3306` qua cấu trúc Service nội bộ.
- `api-deployment.yaml`: Bản lề của toàn hệ thống Web IDE, được áp nhãn Deployments, dễ dàng scale Replicas. Mở kết nối HTTP ngoài qua cổng NodePort `30005`.

## 4. Automation Deployment Script
Một script bash `deploy_k8s.sh` được tạo sẵn trên Ubuntu, tương tác trực tiếp với API của k3s/Minikube tạo môi trường One-Click-Install.
