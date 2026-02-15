import hvac
import requests
import kubernetes.client
from kubernetes import config
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# برای غیرفعال کردن هشدارهای SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# غیرفعال کردن SSL verification برای تمام درخواست‌ها
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# آدرس Vault (URL مربوط به Vault شما)
vault_url = 'http://10.211.55.50:8200'  # به آدرس Vault خود تغییر دهید

# توکن Vault برای احراز هویت
vault_token = 'hvs.token'  # توکن Vault خود را وارد کنید

# درخواست به Vault برای گرفتن توکن Kubernetes با استفاده از API Vault
role = 'my-role'  # نام رول Vault که تنظیم کرده‌اید
namespace = 'sample'  # namespace مورد نظر

# مسیر API Vault برای گرفتن توکن Kubernetes
url = f"{vault_url}/v1/kubernetes/creds/{role}"

# هدرهای درخواست (Authorization با استفاده از توکن Vault)
headers = {
    "X-Vault-Token": vault_token
}

# داده‌هایی که برای درخواست ارسال می‌شود (namespace)
data = {
    "kubernetes_namespace": namespace
}

# ارسال درخواست POST به Vault برای دریافت توکن Kubernetes
response = requests.post(url, headers=headers, json=data, verify=False)  # Bypass SSL verification for Vault

# بررسی وضعیت درخواست
if response.status_code == 200:
    # استخراج توکن Kubernetes از پاسخ
    k8s_token = response.json()['data']['service_account_token']
    print("Kubernetes Token:", k8s_token)
    
    # حالا می‌توانید از توکن برای اتصال به Kubernetes API استفاده کنید
    configuration = kubernetes.client.Configuration()
    configuration.host = 'https://10.211.55.50:6443'  # یا آدرس مناسب Kubernetes API خود را وارد کنید
    configuration.api_key = {"authorization": "Bearer " + k8s_token}
    api_client = kubernetes.client.ApiClient(configuration)

    # غیرفعال کردن بررسی SSL برای Kubernetes API
    configuration.verify_ssl = False  # Bypass SSL verification for Kubernetes API

    # درخواست لیست پادها در namespace مورد نظر
    v1 = kubernetes.client.CoreV1Api(api_client)
    pods = v1.list_namespaced_pod(namespace)

    # نمایش نام پادها
    for pod in pods.items:
        print(f"Pod name: {pod.metadata.name}")
else:
    print(f"Failed to get Kubernetes token: {response.status_code}, {response.text}") 
