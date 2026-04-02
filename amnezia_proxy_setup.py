#!/usr/bin/env python3
"""
Amnezia Proxy Setup
автоматическая подготовка удалённого сервера к проксированию Amnezia WG
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import paramiko
import threading
from datetime import datetime
import re
import sys
import shlex
import base64

class SSHManager:
    """Управление SSH соединением и выполнением команд"""
    
    def __init__(self):
        self.client = None
        self.logger_callback = None
        self._ssh_password = None
    
    def set_logger(self, callback):
        """Установить callback для логирования"""
        self.logger_callback = callback
    
    def log(self, message):
        """Логировать сообщение"""
        if self.logger_callback:
            self.logger_callback(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def connect(self, hostname, username, password, port=22):
        """Подключиться к серверу по SSH"""
        try:
            self.log(f"🔌 Подключение к {hostname}:{port}...")
            self._ssh_password = password
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname, 
                port=port, 
                username=username, 
                password=password, 
                timeout=30,
                allow_agent=False,
                look_for_keys=False,
                banner_timeout=30
            )
            self.log(f"SSH подключено к {hostname}:{port}")
            return True
        except paramiko.ssh_exception.AuthenticationException as e:
            self.log(f"Ошибка SSH: Неправильный логин или пароль")
            self.log(f"Пользователь: {username}")
            self.log(f"Хост: {hostname}:{port}")
            return False
        except (paramiko.ssh_exception.NoValidConnectionsError, ConnectionRefusedError):
            self.log(f"Ошибка SSH: Соединение отклонено (Connection refused)")
            self.log(f"Проверьте:")
            self.log(f"    - IP адрес правильный? {hostname}")
            self.log(f"    - SSH порт открыт? {port}")
            self.log(f"    - SSH демон запущен на сервере?")
            return False
        except (TimeoutError, OSError, paramiko.ssh_exception.SSHException) as e:
            error_str = str(e).lower()
            self.log(f"Ошибка SSH: {str(e)}")
            if "timed out" in error_str or "timeout" in error_str:
                self.log(f"Сервер не отвечает в течение 30 секунд!")
                self.log(f"Проверьте:")
                self.log(f"    - IP адрес: {hostname}")
                self.log(f"    - Портал открыт: {port}")
                self.log(f"    - Firewall не блокирует подключение")
                self.log(f"    - Сервер включен и доступен в интернете")
            return False
        except Exception as e:
            self.log(f"Неизвестная ошибка SSH: {str(e)}")
            return False
    
    def execute(self, command, use_sudo=False):
        """Выполнить команду на сервере"""
        if not self.client:
            self.log("SSH клиент не подключен")
            return False
        
        try:
            # Если нужен sudo, используем echo для передачи пароля
            if use_sudo:
                # Экранируем пароль для безопасности
                password_escaped = shlex.quote(self._ssh_password)
                command = f"echo {password_escaped} | sudo -S -p '' {command}"
            
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            if output:
                self.log(output.strip())
            if error:
                self.log(f"{error.strip()}")
            
            return True
        except Exception as e:
            self.log(f"Ошибка выполнения: {str(e)}")
            return False
    
    def disconnect(self):
        """Отключиться от сервера"""
        if self.client:
            self.client.close()
            self.client = None
            self.log("Отключено от сервера")


class AmneziaProxySetupApp:
    """Главное приложение"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("NexusProxy - Tools for Amnezia WG")
        self.root.geometry("950x800")
        self.ssh = SSHManager()
        self.ssh.set_logger(self.log_message)
        
        # Создать UI
        self.create_widgets()
    
    def create_widgets(self):
        """Создать элементы интерфейса"""
        # Вкладки
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Вкладка 1: Настройка
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Настройка серверов")
        self.create_config_tab(config_frame)
        
        # Вкладка 2: Статус
        status_frame = ttk.Frame(notebook)
        notebook.add(status_frame, text="Статус")
        self.create_status_tab(status_frame)
        
        # Вкладка 3: Редактор конфига
        editor_frame = ttk.Frame(notebook)
        notebook.add(editor_frame, text="Редактор конфига")
        self.create_editor_tab(editor_frame)
    
    def create_config_tab(self, parent):
        """Вкладка настройки серверов"""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Info
        info_text = """Укажите адреса двух серверов и порт:
1. Прокси-сервер - промежуточный Linux сервер
2. Целевой VPN-сервер - текущий VPN сервер
3. Порт - одинаковый для обоих (кастомный порт Amnezia WG)"""
        
        info_lbl = ttk.Label(main_frame, text=info_text, font=('Arial', 9))
        info_lbl.pack(anchor='w', pady=(0, 15))
        
        # Proxy Server Section
        proxy_lbl = ttk.Label(main_frame, text="Прокси-сервер", font=('Arial', 10, 'bold'))
        proxy_lbl.pack(anchor='w', pady=(10, 5))
        
        ttk.Label(main_frame, text="IP адрес или домен:").pack(anchor='w')
        self.proxy_host = ttk.Entry(main_frame, width=50)
        self.proxy_host.pack(anchor='w', pady=(0, 5))
        
        ttk.Label(main_frame, text="SSH пользователь:").pack(anchor='w')
        self.proxy_user = ttk.Entry(main_frame, width=50)
        self.proxy_user.insert(0, "root")
        self.proxy_user.pack(anchor='w', pady=(0, 5))
        
        ttk.Label(main_frame, text="SSH пароль:").pack(anchor='w')
        self.proxy_pass = ttk.Entry(main_frame, width=50, show="*")
        self.proxy_pass.pack(anchor='w', pady=(0, 5))
        
        ttk.Label(main_frame, text="SSH порт:").pack(anchor='w')
        self.proxy_ssh_port = ttk.Entry(main_frame, width=50)
        self.proxy_ssh_port.insert(0, "22")
        self.proxy_ssh_port.pack(anchor='w', pady=(0, 15))
        
        # VPN Server Section
        vpn_lbl = ttk.Label(main_frame, text="Целевой VPN-сервер (куда перенаправляем)", font=('Arial', 10, 'bold'))
        vpn_lbl.pack(anchor='w', pady=(10, 5))
        
        ttk.Label(main_frame, text="IP адрес или домен:").pack(anchor='w')
        self.vpn_host = ttk.Entry(main_frame, width=50)
        self.vpn_host.pack(anchor='w', pady=(0, 15))
        
        # Port Section
        port_lbl = ttk.Label(main_frame, text="UDP Порт (одинаковый для обоих серверов)", font=('Arial', 10, 'bold'))
        port_lbl.pack(anchor='w', pady=(10, 5))
        
        ttk.Label(main_frame, text="Порт Amnezia WG:").pack(anchor='w')
        self.vpn_port = ttk.Entry(main_frame, width=50)
        self.vpn_port.insert(0, "37884")
        self.vpn_port.pack(anchor='w', pady=(0, 15))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(anchor='w', pady=10)
        
        test_btn = ttk.Button(button_frame, text="Проверить SSH", 
                            command=self.test_ssh)
        test_btn.pack(side='left', padx=5)
        
        setup_btn = ttk.Button(button_frame, text="Подготовить сервер", 
                             command=self.setup_server)
        setup_btn.pack(side='left', padx=5)
    
    def create_status_tab(self, parent):
        """Вкладка статуса"""
        frame = ttk.Frame(parent, padding="10")
        frame.pack(fill='both', expand=True)
        
        self.status_text = scrolledtext.ScrolledText(frame, height=30, width=100, font=('Courier', 9))
        self.status_text.pack(fill='both', expand=True, pady=(0, 10))
        
        clear_btn = ttk.Button(frame, text="Очистить лог", 
                              command=lambda: self.status_text.delete('1.0', tk.END))
        clear_btn.pack(anchor='w')
    
    def create_editor_tab(self, parent):
        """Вкладка редактора конфига"""
        frame = ttk.Frame(parent, padding="10")
        frame.pack(fill='both', expand=True)
        
        info_lbl = ttk.Label(frame, text="Замените Endpoint на адрес сервера-прокси:")
        info_lbl.pack(anchor='w', pady=(0, 5))
        
        self.config_text = scrolledtext.ScrolledText(frame, height=25, width=100, font=('Courier', 9))
        self.config_text.pack(fill='both', expand=True, pady=(0, 10))
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(anchor='w')
        
        load_btn = ttk.Button(button_frame, text="Загрузить конфиг", 
                            command=self.load_config)
        load_btn.pack(side='left', padx=5)
        
        save_btn = ttk.Button(button_frame, text="Сохранить конфиг", 
                            command=self.save_config)
        save_btn.pack(side='left', padx=5)
        
        replace_btn = ttk.Button(button_frame, text="Заменить Endpoint", 
                               command=self.replace_endpoint)
        replace_btn.pack(side='left', padx=5)
    
    def log_message(self, message):
        """Логировать сообщение в UI"""
        self.root.after(0, lambda: self._log_message_ui(message))
    
    def _log_message_ui(self, message):
        """Внутренняя функция логирования"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
    
    def test_ssh(self):
        """Проверить SSH соединение"""
        try:
            host = self.proxy_host.get()
            user = self.proxy_user.get()
            password = self.proxy_pass.get()
            port = int(self.proxy_ssh_port.get())
            
            if not all([host, user, password]):
                messagebox.showerror("Ошибка", "Заполните все поля для SSH")
                return
            
            self.log_message("\n" + "="*60)
            self.log_message("ПРОВЕРКА SSH СОЕДИНЕНИЯ")
            self.log_message("="*60)
            self.log_message(f"Хост: {host}")
            self.log_message(f"Порт: {port}")
            self.log_message(f"Пользователь: {user}")
            self.log_message("Ожидание ответа (до 30 секунд)...")
            
            thread = threading.Thread(target=self._test_ssh_thread, args=(host, user, password, port))
            thread.daemon = True
            thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _test_ssh_thread(self, host, user, password, port):
        """Тест SSH в отдельном потоке"""
        if self.ssh.connect(host, user, password, port):
            self.log_message("SSH соединение успешно!")
            self.log_message("="*60)
            self.root.after(0, lambda: messagebox.showinfo("Успех", "SSH соединение успешно!\n\nМожете подготавливать сервер."))
            self.ssh.disconnect()
        else:
            self.log_message("="*60)
            self.root.after(0, lambda: messagebox.showerror("Ошибка", 
                "Не удалось подключиться по SSH.\n\nОшибка отображена в логе выше."))

    
    def setup_server(self):
        """Подготовить сервер"""
        try:
            host = self.proxy_host.get()
            user = self.proxy_user.get()
            password = self.proxy_pass.get()
            port = int(self.proxy_ssh_port.get())
            vpn_host = self.vpn_host.get()
            vpn_port = int(self.vpn_port.get())
            
            if not all([host, user, password, vpn_host, vpn_port]):
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            
            thread = threading.Thread(target=self._setup_server_thread, 
                                    args=(host, user, password, port, vpn_host, vpn_port))
            thread.daemon = True
            thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _setup_server_thread(self, host, user, password, port, vpn_host, vpn_port):
        """Подготовка сервера в отдельном потоке"""
        if not self.ssh.connect(host, user, password, port):
            return
        
        try:
            self.log_message("\n" + "="*60)
            self.log_message("НАЧАЛО ПОДГОТОВКИ ПРОКСИ-СЕРВЕРА")
            self.log_message("="*60)
            
            self.log_message(f"\nПрокси: {host}:{vpn_port}")
            self.log_message(f"Целевой VPN: {vpn_host}:{vpn_port}")
            
            # Создаем один большой скрипт для выполнения всех команд с sudo
            proxy_script = f"""#!/bin/bash
socat UDP-LISTEN:{vpn_port},reuseaddr,fork UDP:{vpn_host}:{vpn_port}
exit 0
"""
            
            systemd_service = """[Unit]
Description=Amnezia WG UDP Proxy Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/amnezia-proxy.sh
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
            
            # Выполняем весь скрипт с sudo за один раз
            self.log_message("\n[1-6] Выполнение полной подготовки сервера...")
            
            # Кодируем содержимое файлов в base64 для безопасной передачи
            proxy_b64 = base64.b64encode(proxy_script.encode()).decode()
            service_b64 = base64.b64encode(systemd_service.encode()).decode()
            
            # Создаем один скрипт с base64 декодированием
            setup_all = f"""
set -e

echo '[1/6] Обновление системы...'
apt-get update -qq 2>/dev/null || true
apt-get upgrade -y 2>/dev/null || true

echo '[2/6] Установка зависимостей...'
apt-get install -y socat netcat-traditional iptables ufw 2>/dev/null || true

echo '[3/6] Создание скрипта прокси...'
echo '{proxy_b64}' | base64 -d > /usr/local/bin/amnezia-proxy.sh
chmod +x /usr/local/bin/amnezia-proxy.sh

echo '[4/6] Установка systemd сервиса...'
echo '{service_b64}' | base64 -d > /etc/systemd/system/amnezia-proxy.service
systemctl daemon-reload
systemctl enable amnezia-proxy
systemctl start amnezia-proxy

echo '[5/6] Настройка firewall...'
ufw allow {vpn_port}/udp 2>/dev/null || true

echo '[6/6] Проверка статуса...'
systemctl status amnezia-proxy --no-pager || true

echo 'Все готово!'
"""
            
            password_escaped = shlex.quote(password)
            full_command = f"""echo {password_escaped} | sudo -S bash -c {shlex.quote(setup_all)}"""
            
            self.ssh.execute(full_command)
            
            self.log_message("\n" + "="*60)
            self.log_message("СЕРВЕР УСПЕШНО ПОДГОТОВЛЕН!")
            self.log_message("="*60)
            self.log_message(f"\nДЛЯ КОНФИГА VPN ИСПОЛЬЗУЙТЕ:")
            self.log_message(f"   Endpoint = {host}:{vpn_port}")
            self.log_message("\nЗамените в вашем конфиге:")
            self.log_message(f"   БЫЛО:  Endpoint = (старый адрес)")
            self.log_message(f"   СТАЛО: Endpoint = {host}:{vpn_port}")
            self.log_message("\nВсё готово к использованию!")
            
            self.root.after(0, lambda: messagebox.showinfo("Успех", 
                f"Сервер успешно подготовлен!\n\nИспользуйте Endpoint:\n{host}:{vpn_port}"))
        
        except Exception as e:
            self.log_message(f"\nОШИБКА: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.ssh.disconnect()
    
    def load_config(self):
        """Загрузить конфиг файл"""
        filename = filedialog.askopenfilename(
            title="Выберите конфиг файл",
            filetypes=[("Config files", "*.conf"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.config_text.delete('1.0', tk.END)
                    self.config_text.insert('1.0', f.read())
                self.log_message(f"Конфиг загружен: {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при загрузке: {str(e)}")
    
    def save_config(self):
        """Сохранить конфиг файл"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить конфиг",
            filetypes=[("Config files", "*.conf"), ("All files", "*.*")],
            defaultextension=".conf"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.config_text.get('1.0', tk.END))
                self.log_message(f"Конфиг сохранён: {filename}")
                messagebox.showinfo("Успех", "Конфиг успешно сохранён!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении: {str(e)}")
    
    def replace_endpoint(self):
        """Заменить Endpoint в конфиге"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Замена Endpoint")
        dialog.geometry("400x150")
        
        ttk.Label(dialog, text="Новый Endpoint:").pack(anchor='w', padx=10, pady=(10, 5))
        endpoint_entry = ttk.Entry(dialog, width=40)
        endpoint_entry.pack(padx=10, pady=(0, 10))
        
        def do_replace():
            new_endpoint = endpoint_entry.get()
            if new_endpoint:
                text = self.config_text.get('1.0', tk.END)
                text = re.sub(r'Endpoint\s*=\s*[^\n]+', f'Endpoint = {new_endpoint}', text)
                self.config_text.delete('1.0', tk.END)
                self.config_text.insert('1.0', text)
                self.log_message(f"Endpoint изменён на: {new_endpoint}")
                dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(anchor='e', padx=10, pady=10)
        
        ttk.Button(button_frame, text="OK", command=do_replace).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side='left', padx=5)


def main():
    """Главная функция"""
    root = tk.Tk()
    app = AmneziaProxySetupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
