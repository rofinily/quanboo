import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import json

class KubeCPApp:
    def __init__(self, master):
        self.master = master
        master.title("kubecp（Kubernetes 文件传输工具）")

        self.kubeconfig_var = tk.StringVar()
        self.namespace_var = tk.StringVar()
        self.pod_var = tk.StringVar()
        self.container_var = tk.StringVar()
        self.local_file_var = tk.StringVar()
        self.container_path_var = tk.StringVar()

        self.create_widgets()

    def create_widgets(self):
        # Kubeconfig
        tk.Label(self.master, text="kubeconfig 文件路径").grid(row=0, column=0)
        tk.Entry(self.master, textvariable=self.kubeconfig_var).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.master, text="选择文件", command=self.select_kubeconfig).grid(row=0, column=2)

        # Namespace
        tk.Label(self.master, text="Namespace").grid(row=1, column=0)
        self.namespace_select = tk.Listbox(self.master, listvariable=self.namespace_var)
        self.namespace_select.grid(row=1, column=1, padx=5, pady=5)

        # Pod
        tk.Label(self.master, text="Pod").grid(row=2, column=0)
        self.pod_select = tk.Listbox(self.master, listvariable=self.pod_var)
        self.pod_select.grid(row=2, column=1, padx=5, pady=5)

        # Container
        tk.Label(self.master, text="Container（可选）").grid(row=3, column=0)
        self.container_select = tk.Listbox(self.master, listvariable=self.container_var)
        self.container_select.grid(row=3, column=1, padx=5, pady=5)

        # Local file
        tk.Label(self.master, text="请选择要传输的本地文件").grid(row=4, column=0)
        tk.Entry(self.master, textvariable=self.local_file_var).grid(row=4, column=1, padx=5, pady=5)
        tk.Button(self.master, text="选择文件", command=self.select_local_file).grid(row=4, column=2)

        # Container Path
        tk.Label(self.master, text="请选择容器内的目标路径").grid(row=5, column=0)
        tk.Entry(self.master, textvariable=self.container_path_var).grid(row=5, column=1, padx=5, pady=5)

        # Buttons
        tk.Button(self.master, text="开始传输", command=self.transfer_file).grid(row=6, column=0, padx=5, pady=10)
        tk.Button(self.master, text="取消传输", command=self.cancel_transfer).grid(row=6, column=1, padx=5, pady=10)

    def select_kubeconfig(self):
        file_path = filedialog.askopenfilename(filetypes=[("Kubeconfig files", "*.yml;*.yaml")])
        if file_path:
            self.kubeconfig_var.set(file_path)
            self.update_namespace_list(file_path)

    def select_local_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.local_file_var.set(file_path)

    def update_namespace_list(self, kubeconfig_path):
        try:
            command = ["kubectl", "--kubeconfig", kubeconfig_path, "get", "ns", "-o", "json"]
            output = subprocess.check_output(command)
            namespaces = json.loads(output)
            namespace_names = [ns['metadata']['name'] for ns in namespaces['items']]
            self.namespace_select.delete(0, tk.END)
            for ns in namespace_names:
                self.namespace_select.insert(tk.END, ns)

            if namespace_names:
                self.namespace_select.select_set(0)
                self.update_pod_list(kubeconfig_path, namespace_names[0])
        except Exception as e:
            messagebox.showerror("错误", f"获取 namespaces 时出错: {e}")

    def update_pod_list(self, kubeconfig_path, namespace):
        try:
            command = ["kubectl", "--kubeconfig", kubeconfig_path, "get", "pods", "-n", namespace, "-o", "json"]
            output = subprocess.check_output(command)
            pods = json.loads(output)
            pod_names = [pod['metadata']['name'] for pod in pods['items']]
            self.pod_select.delete(0, tk.END)
            for pod in pod_names:
                self.pod_select.insert(tk.END, pod)

            if pod_names:
                self.pod_select.select_set(0)
                self.update_container_list(kubeconfig_path, namespace, pod_names[0])
        except Exception as e:
            messagebox.showerror("错误", f"获取 pods 时出错: {e}")

    def update_container_list(self, kubeconfig_path, namespace, pod):
        try:
            command = ["kubectl", "--kubeconfig", kubeconfig_path, "get", "pod", pod, "-n", namespace, "-o", "json"]
            output = subprocess.check_output(command)
            containers = json.loads(output)
            container_names = [container['name'] for container in containers['spec']['containers']]
            self.container_select.delete(0, tk.END)
            for container in container_names:
                self.container_select.insert(tk.END, container)
        except Exception as e:
            messagebox.showerror("错误", f"获取 containers 时出错: {e}")

    def transfer_file(self):
        kubeconfig = self.kubeconfig_var.get()
        namespace = self.namespace_select.get(tk.ACTIVE)
        pod = self.pod_select.get(tk.ACTIVE)
        local_file = self.local_file_var.get()
        container_path = self.container_path_var.get()

        if not (kubeconfig and namespace and pod and local_file and container_path):
            messagebox.showerror("错误", "请填写所有必要信息")
            return

        cmd = ["kubectl", "--kubeconfig", kubeconfig, "-n", namespace, "cp", local_file, f"{pod}:{container_path}"]
        if self.container_select.curselection():
            container = self.container_select.get(tk.ACTIVE)
            cmd += ["-c", container]

        try:
            subprocess.check_output(cmd)
            messagebox.showinfo("成功", "文件传输成功！")
        except Exception as e:
            messagebox.showerror("传输失败", f"传输失败: {e}")

    def cancel_transfer(self):
        # Functionality for canceling transfer can be implemented
        # if needed, we can consider using threading.
        pass


if __name__ == "__main__":
    root = tk.Tk()
    app = KubeCPApp(root)
    root.mainloop()
