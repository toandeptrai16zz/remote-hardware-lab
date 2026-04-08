#!/bin/bash
echo "================================================="
echo "   TRIỂN KHAI KUBERNETES - EPU IOT LAB PLATFORM  "
echo "================================================="

echo "[1] Áp dụng Database và API..."
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml

echo "[2] Thiết lập Hệ thống Giám sát (Monitoring)..."
kubectl apply -f k8s/monitoring/prometheus.yaml
kubectl apply -f k8s/monitoring/grafana.yaml

echo "Hoàn tất kịch bản triển khai! Kiểm tra trạng thái Pods bằng:"
echo "kubectl get pods"
