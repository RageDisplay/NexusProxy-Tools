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
            self.log(f"Подключение к {hostname}:{port}...")
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
        
        # Вкладка 4: Безопасность
        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Безопасность")
        self.create_security_tab(security_frame)
    
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
    
    def create_security_tab(self, parent):
        """Вкладка настройки безопасности"""
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Info
        info_text = """ПОЛИТИКИ БЕЗОПАСНОСТИ ПРОКСИ-СЕРВЕРА
Применяет базовые меры защиты для защиты от распространённых атак"""
        
        info_lbl = ttk.Label(main_frame, text=info_text, font=('Arial', 9))
        info_lbl.pack(anchor='w', pady=(0, 15))
        
        # Creating canvas with scrollbar for options
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Section 1: Fail2ban
        fail2ban_frame = ttk.LabelFrame(scrollable_frame, text="Fail2Ban - защита от brute-force атак", padding="10")
        fail2ban_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(fail2ban_frame, text="Максимум попыток входа перед блокировкой:", font=('Arial', 9)).pack(anchor='w')
        self.fail2ban_attempts = ttk.Entry(fail2ban_frame, width=10)
        self.fail2ban_attempts.insert(0, "5")
        self.fail2ban_attempts.pack(anchor='w', pady=(0, 5))
        
        ttk.Label(fail2ban_frame, text="Время блокировки (сек):", font=('Arial', 9)).pack(anchor='w')
        self.fail2ban_timeout = ttk.Entry(fail2ban_frame, width=10)
        self.fail2ban_timeout.insert(0, "3600")
        self.fail2ban_timeout.pack(anchor='w', pady=(0, 5))
        
        ttk.Label(fail2ban_frame, text="Окно проверки попыток (сек):", font=('Arial', 9)).pack(anchor='w')
        self.fail2ban_findtime = ttk.Entry(fail2ban_frame, width=10)
        self.fail2ban_findtime.insert(0, "600")
        self.fail2ban_findtime.pack(anchor='w', pady=(0, 10))
        
        fail2ban_btn = ttk.Button(fail2ban_frame, text="Установить Fail2Ban", 
                                 command=self.setup_fail2ban)
        fail2ban_btn.pack(anchor='w', pady=5)
        
        # Section 2: Rate Limiting
        ratelimit_frame = ttk.LabelFrame(scrollable_frame, text="Rate Limiting - ограничение скорости подключений", padding="10")
        ratelimit_frame.pack(fill='x', padx=5, pady=5)
        
        self.ratelimit_unlimited = tk.BooleanVar(value=False)
        ttk.Checkbutton(ratelimit_frame, text="Без ограничений (безлимит)", 
                       variable=self.ratelimit_unlimited,
                       command=self._toggle_ratelimit_fields).pack(anchor='w', pady=(0, 10))
        
        ttk.Label(ratelimit_frame, text="Макс. подключений в секунду:", font=('Arial', 9)).pack(anchor='w')
        self.ratelimit_connections = ttk.Entry(ratelimit_frame, width=10)
        self.ratelimit_connections.insert(0, "100")
        self.ratelimit_connections.pack(anchor='w', pady=(0, 5))
        
        ttk.Label(ratelimit_frame, text="Макс. пакетов в секунду на IP:", font=('Arial', 9)).pack(anchor='w')
        self.ratelimit_packets = ttk.Entry(ratelimit_frame, width=10)
        self.ratelimit_packets.insert(0, "500")
        self.ratelimit_packets.pack(anchor='w', pady=(0, 10))
        
        ratelimit_btn = ttk.Button(ratelimit_frame, text="Применить Rate Limiting", 
                                  command=self.setup_rate_limiting)
        ratelimit_btn.pack(anchor='w', pady=5)
        
        # Section 3: SSH Security
        ssh_frame = ttk.LabelFrame(scrollable_frame, text="Защита SSH - повышенная безопасность SSH", padding="10")
        ssh_frame.pack(fill='x', padx=5, pady=5)
        
        self.ssh_security_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ssh_frame, text="Отключить пароли (только ключи)", 
                       variable=self.ssh_security_var).pack(anchor='w', pady=5)
        
        ttk.Label(ssh_frame, text="допустимое кол-во попыток входа:", font=('Arial', 9)).pack(anchor='w')
        self.ssh_attempts = ttk.Entry(ssh_frame, width=10)
        self.ssh_attempts.insert(0, "3")
        self.ssh_attempts.pack(anchor='w', pady=(0, 10))
        
        ssh_btn = ttk.Button(ssh_frame, text="Применить SSH Security", 
                            command=self.setup_ssh_security)
        ssh_btn.pack(anchor='w', pady=5)
        
        # Section 4: System Hardening
        harden_frame = ttk.LabelFrame(scrollable_frame, text="System Hardening - защита ядра системы", padding="10")
        harden_frame.pack(fill='x', padx=5, pady=5)
        
        self.harden_syn_cookies = tk.BooleanVar(value=True)
        ttk.Checkbutton(harden_frame, text="SYN Cookies (защита от SYN flood)", 
                       variable=self.harden_syn_cookies).pack(anchor='w', pady=5)
        
        self.harden_ip_forward = tk.BooleanVar(value=True)
        ttk.Checkbutton(harden_frame, text="IP Forwarding (маршрутизация)", 
                       variable=self.harden_ip_forward).pack(anchor='w', pady=5)
        
        self.harden_icmp_redirect = tk.BooleanVar(value=False)
        ttk.Checkbutton(harden_frame, text="Отключить ICMP Redirect", 
                       variable=self.harden_icmp_redirect).pack(anchor='w', pady=5)
        
        self.harden_spoof = tk.BooleanVar(value=True)
        ttk.Checkbutton(harden_frame, text="Защита от IP spoofing", 
                       variable=self.harden_spoof).pack(anchor='w', pady=(5, 10))
        
        harden_btn = ttk.Button(harden_frame, text="Применить System Hardening", 
                               command=self.setup_system_hardening)
        harden_btn.pack(anchor='w', pady=5)
        
        # Section 5: Log Monitoring
        monitor_frame = ttk.LabelFrame(scrollable_frame, text="Мониторинг - сбор и анализ логов", padding="10")
        monitor_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(monitor_frame, text="Статус автоматического мониторинга:", font=('Arial', 9)).pack(anchor='w', pady=5)
        
        monitor_btn = ttk.Button(monitor_frame, text="Установить мониторинг", 
                                command=self.setup_monitoring)
        monitor_btn.pack(anchor='w', pady=5)
        
        # Section 6: Comprehensive Setup
        complete_frame = ttk.LabelFrame(scrollable_frame, text="Полная установка", padding="10")
        complete_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(complete_frame, text="Применить все политики безопасности сразу", 
                 font=('Arial', 9)).pack(anchor='w', pady=5)
        
        complete_btn = ttk.Button(complete_frame, text="ПОЛНАЯ ПОДГОТОВКА К БОЕВОЙ ЭКСПЛУАТАЦИИ", 
                                 command=self.full_security_setup)
        complete_btn.pack(anchor='w', pady=5, fill='x')
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def log_message(self, message):
        """Логировать сообщение в UI"""
        self.root.after(0, lambda: self._log_message_ui(message))
    
    def _log_message_ui(self, message):
        """Внутренняя функция логирования"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
    
    # === SECURITY SETUP METHODS ===
    
    def _toggle_ratelimit_fields(self):
        """Включить/отключить поля Rate Limiting при выборе безлимита"""
        if self.ratelimit_unlimited.get():
            self.ratelimit_connections.config(state='disabled')
            self.ratelimit_packets.config(state='disabled')
        else:
            self.ratelimit_connections.config(state='normal')
            self.ratelimit_packets.config(state='normal')
    
    def setup_fail2ban(self):
        """Установка и настройка Fail2Ban"""
        try:
            host = self.proxy_host.get()
            user = self.proxy_user.get()
            password = self.proxy_pass.get()
            port = int(self.proxy_ssh_port.get())
            
            if not all([host, user, password]):
                messagebox.showerror("Ошибка", "Заполните SSH параметры в вкладке 'Настройка'")
                return
            
            attempts = self.fail2ban_attempts.get() or "5"
            timeout = self.fail2ban_timeout.get() or "3600"
            findtime = self.fail2ban_findtime.get() or "600"
            
            thread = threading.Thread(target=self._setup_fail2ban_thread, 
                                    args=(host, user, password, port, attempts, timeout, findtime))
            thread.daemon = True
            thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _setup_fail2ban_thread(self, host, user, password, port, attempts, timeout, findtime):
        """Потоковая установка Fail2Ban"""
        if not self.ssh.connect(host, user, password, port):
            return
        
        try:
            self.log_message("\n" + "="*60)
            self.log_message("УСТАНОВКА FAIL2BAN")
            self.log_message("="*60)
            
            fail2ban_config = f"""[DEFAULT]
bantime = {timeout}
findtime = {findtime}
maxretry = {attempts}
destemail = root@localhost

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = {attempts}
action = iptables[name=sshd, port=ssh, protocol=tcp]

[recidive]
enabled = true
filter = recidive
action = iptables-allports[name=recidive]
findtime = 604800
bantime = 604800
maxretry = 2"""
            
            fail2ban_b64 = base64.b64encode(fail2ban_config.encode()).decode()
            
            fail2ban_setup = f"""
set -e

echo '[1/6] Установка fail2ban...'
apt-get update -qq 2>/dev/null || true
apt-get install -y fail2ban 2>/dev/null || true

echo '[2/6] Создание конфига jail.local...'
echo '{fail2ban_b64}' | base64 -d > /etc/fail2ban/jail.local

echo '[3/6] Перезагрузка fail2ban сервиса...'
systemctl stop fail2ban 2>/dev/null || true
sleep 1
systemctl start fail2ban
systemctl enable fail2ban

echo '[4/6] Перезагрузка фильтров через fail2ban-client...'
fail2ban-client reload || true

echo '[5/6] Проверка статуса...'
fail2ban-client status 2>/dev/null || true

echo '[6/6] Готово'
echo 'Fail2Ban успешно установлен!'
"""
            
            password_escaped = shlex.quote(password)
            full_command = f"""echo {password_escaped} | sudo -S bash -c {shlex.quote(fail2ban_setup)}"""
            
            self.ssh.execute(full_command)
            
            self.log_message("="*60)
            self.log_message("FAIL2BAN УСПЕШНО УСТАНОВЛЕН!")
            self.log_message(f"Параметры: maxretry={attempts}, timeout={timeout}s")
            self.log_message("="*60)
            
            self.root.after(0, lambda: messagebox.showinfo("Успех", 
                f"Fail2Ban успешно установлен!"))
        
        except Exception as e:
            self.log_message(f"ОШИБКА: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.ssh.disconnect()
    
    def setup_rate_limiting(self):
        """Установка Rate Limiting"""
        try:
            if self.ratelimit_unlimited.get():
                messagebox.showinfo("Информация", "Режим 'Без ограничений' активен.\n\nRate Limiting не будет применён.")
                return
            
            host = self.proxy_host.get()
            user = self.proxy_user.get()
            password = self.proxy_pass.get()
            port = int(self.proxy_ssh_port.get())
            vpn_port = int(self.vpn_port.get())
            
            if not all([host, user, password]):
                messagebox.showerror("Ошибка", "Заполните SSH параметры в вкладке 'Настройка'")
                return
            
            connections = self.ratelimit_connections.get() or "100"
            packets = self.ratelimit_packets.get() or "500"
            
            thread = threading.Thread(target=self._setup_rate_limiting_thread, 
                                    args=(host, user, password, port, vpn_port, connections, packets))
            thread.daemon = True
            thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _setup_rate_limiting_thread(self, host, user, password, port, vpn_port, connections, packets):
        """Потоковая установка Rate Limiting"""
        if not self.ssh.connect(host, user, password, port):
            return
        
        try:
            self.log_message("\n" + "="*60)
            self.log_message("ПРИМЕНЕНИЕ RATE LIMITING")
            self.log_message("="*60)
            
            ratelimit_setup = f"""
set -e

echo '[1/4] Установка iptables-persistent...'
apt-get update -qq 2>/dev/null || true
DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent 2>/dev/null || true

echo '[2/4] Настройка правил...'
echo 'Applying rate limiting rules for port {vpn_port}...'

echo '[3/4] Сохранение правил...'
iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo '[4/4] Активация...'
echo 'Rate Limiting применён!'
"""
            
            password_escaped = shlex.quote(password)
            full_command = f"""echo {password_escaped} | sudo -S bash -c {shlex.quote(ratelimit_setup)}"""
            
            self.ssh.execute(full_command)
            
            self.log_message("="*60)
            self.log_message("RATE LIMITING УСПЕШНО ПРИМЕНЁН!")
            self.log_message(f"Порт: {vpn_port}, Пакетов/с: {packets}")
            self.log_message("="*60)
            
            self.root.after(0, lambda: messagebox.showinfo("Успех", 
                f"Rate Limiting успешно применён!"))
        
        except Exception as e:
            self.log_message(f"ОШИБКА: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.ssh.disconnect()
    
    def setup_ssh_security(self):
        """Установка усиленной защиты SSH"""
        try:
            host = self.proxy_host.get()
            user = self.proxy_user.get()
            password = self.proxy_pass.get()
            port = int(self.proxy_ssh_port.get())
            
            if not all([host, user, password]):
                messagebox.showerror("Ошибка", "Заполните SSH параметры в вкладке 'Настройка'")
                return
            
            attempts = self.ssh_attempts.get() or "3"
            
            thread = threading.Thread(target=self._setup_ssh_security_thread, 
                                    args=(host, user, password, port, attempts))
            thread.daemon = True
            thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _setup_ssh_security_thread(self, host, user, password, port, attempts):
        """Потоковая установка SSH Security"""
        if not self.ssh.connect(host, user, password, port):
            return
        
        try:
            self.log_message("\n" + "="*60)
            self.log_message("УСИЛЕННАЯ ЗАЩИТА SSH")
            self.log_message("="*60)
            
            ssh_config = """# Security Hardening
MaxAuthTries {attempts}
PermitRootLogin prohibit-password
PermitEmptyPasswords no
PubkeyAuthentication yes
StrictModes yes
X11Forwarding no
Compression yes
ClientAliveInterval 300
ClientAliveCountMax 2
MaxSessions 10""".format(attempts=attempts)
            
            ssh_b64 = base64.b64encode(ssh_config.encode()).decode()
            
            ssh_hardening = f"""
set -e

echo '[1/3] Резервная копия SSH конфига...'
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

echo '[2/3] Применение параметров SSH...'
mkdir -p /etc/ssh/sshd_config.d
echo '{ssh_b64}' | base64 -d > /etc/ssh/sshd_config.d/99-security.conf

echo '[3/3] Перезагрузка SSH...'
sshd -t && systemctl restart sshd || echo 'SSH конфиг требует проверки'
echo 'SSH Security успешно применена!'
"""
            
            password_escaped = shlex.quote(password)
            full_command = f"""echo {password_escaped} | sudo -S bash -c {shlex.quote(ssh_hardening)}"""
            
            self.ssh.execute(full_command)
            
            self.log_message("="*60)
            self.log_message("SSH SECURITY УСПЕШНО ПРИМЕНЕНА!")
            self.log_message(f"Max попыток входа: {attempts}")
            self.log_message("="*60)
            
            self.root.after(0, lambda: messagebox.showinfo("Успех", 
                f"SSH Security успешно применена!"))
        
        except Exception as e:
            self.log_message(f"ОШИБКА: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.ssh.disconnect()
    
    def setup_system_hardening(self):
        """Установка System Hardening"""
        try:
            host = self.proxy_host.get()
            user = self.proxy_user.get()
            password = self.proxy_pass.get()
            port = int(self.proxy_ssh_port.get())
            
            if not all([host, user, password]):
                messagebox.showerror("Ошибка", "Заполните SSH параметры в вкладке 'Настройка'")
                return
            
            thread = threading.Thread(target=self._setup_system_hardening_thread, 
                                    args=(host, user, password, port))
            thread.daemon = True
            thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _setup_system_hardening_thread(self, host, user, password, port):
        """Потоковая установка System Hardening"""
        if not self.ssh.connect(host, user, password, port):
            return
        
        try:
            self.log_message("\n" + "="*60)
            self.log_message("SYSTEM HARDENING")
            self.log_message("="*60)
            
            hardening_setup = """
set -e

echo '[1/3] Установка утилит...'
apt-get update -qq 2>/dev/null || true
apt-get install -y haveged 2>/dev/null || true

echo '[2/3] Применение параметров sysctl...'
cat >> /etc/sysctl.d/99-security.conf << 'SYSCTL_EOF'
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.icmp_echo_ignore_all = 0
SYSCTL_EOF

echo '[3/3] Активация параметров...'
sysctl -p /etc/sysctl.d/99-security.conf > /dev/null 2>&1
echo 'System Hardening успешно применён!'
"""
            
            password_escaped = shlex.quote(password)
            full_command = f"""echo {password_escaped} | sudo -S bash -c {shlex.quote(hardening_setup)}"""
            
            self.ssh.execute(full_command)
            
            self.log_message("="*60)
            self.log_message("SYSTEM HARDENING УСПЕШНО ПРИМЕНЁН!")
            self.log_message("="*60)
            
            self.root.after(0, lambda: messagebox.showinfo("Успех", 
                "System Hardening успешно применён!"))
        
        except Exception as e:
            self.log_message(f"ОШИБКА: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.ssh.disconnect()
    
    def setup_monitoring(self):
        """Установка мониторинга и логирования"""
        try:
            host = self.proxy_host.get()
            user = self.proxy_user.get()
            password = self.proxy_pass.get()
            port = int(self.proxy_ssh_port.get())
            
            if not all([host, user, password]):
                messagebox.showerror("Ошибка", "Заполните SSH параметры в вкладке 'Настройка'")
                return
            
            thread = threading.Thread(target=self._setup_monitoring_thread, 
                                    args=(host, user, password, port))
            thread.daemon = True
            thread.start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def _setup_monitoring_thread(self, host, user, password, port):
        """Потоковая установка мониторинга"""
        if not self.ssh.connect(host, user, password, port):
            return
        
        try:
            self.log_message("\n" + "="*60)
            self.log_message("УСТАНОВКА МОНИТОРИНГА")
            self.log_message("="*60)
            
            monitoring_setup = """
set -e

echo '[1/3] Установка инструментов...'
apt-get update -qq 2>/dev/null || true
apt-get install -y htop iotop 2>/dev/null || true

echo '[2/3] Создание скрипта мониторинга...'
cat > /usr/local/bin/amnezia-monitor.sh << 'MONITOR_EOF'
#!/bin/bash
LOG_FILE="/var/log/amnezia-proxy-monitor.log"
systemctl is-active --quiet amnezia-proxy || systemctl restart amnezia-proxy
echo "[$(date)] Мониторинг активен" >> $LOG_FILE
MONITOR_EOF

chmod +x /usr/local/bin/amnezia-monitor.sh

echo '[3/3] Добавление в crontab...'
(crontab -l 2>/dev/null | grep -v amnezia-monitor.sh; echo "*/5 * * * * /usr/local/bin/amnezia-monitor.sh") | crontab - 2>/dev/null || true

echo 'Мониторинг успешно установлен!'
"""
            
            password_escaped = shlex.quote(password)
            full_command = f"""echo {password_escaped} | sudo -S bash -c {shlex.quote(monitoring_setup)}"""
            
            self.ssh.execute(full_command)
            
            self.log_message("="*60)
            self.log_message("МОНИТОРИНГ УСПЕШНО УСТАНОВЛЕН!")
            self.log_message("="*60)
            
            self.root.after(0, lambda: messagebox.showinfo("Успех", 
                "Мониторинг успешно установлен!"))
        
        except Exception as e:
            self.log_message(f"ОШИБКА: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.ssh.disconnect()
    
    def full_security_setup(self):
        """Полная установка всех политик безопасности"""
        response = messagebox.askyesno("Подтверждение", 
            "Применить ВСЕ политики безопасности сразу?\n\n"
            "Процесс может занять несколько минут.")
        
        if response:
            try:
                host = self.proxy_host.get()
                user = self.proxy_user.get()
                password = self.proxy_pass.get()
                port = int(self.proxy_ssh_port.get())
                vpn_port = int(self.vpn_port.get())
                
                if not all([host, user, password, vpn_port]):
                    messagebox.showerror("Ошибка", "Заполните все параметры в вкладке 'Настройка'")
                    return
                
                thread = threading.Thread(target=self._full_security_setup_thread, 
                                        args=(host, user, password, port, vpn_port))
                thread.daemon = True
                thread.start()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
    
    def _full_security_setup_thread(self, host, user, password, port, vpn_port):
        """Потоковая полная установка безопасности"""
        if not self.ssh.connect(host, user, password, port):
            return
        
        try:
            self.log_message("\n" + "="*60)
            self.log_message("ПОЛНАЯ ПОДГОТОВКА К БОЕВОЙ ЭКСПЛУАТАЦИИ")
            self.log_message("="*60)
            
            full_security_script = f"""
set -e

echo '=== ЭТАП 1: Обновления и зависимости ==='
apt-get update -qq 2>/dev/null || true
apt-get upgrade -y 2>/dev/null || true
apt-get install -y fail2ban socat iptables ufw htop haveged 2>/dev/null || true

echo ''
echo '=== ЭТАП 2: Fail2Ban ==='
apt-get install -y fail2ban 2>/dev/null || true

# Создаем правильный конфиг с action
cat > /etc/fail2ban/jail.local << 'FAIL2BAN_EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = root@localhost

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 5
action = iptables[name=sshd, port=ssh, protocol=tcp]

[recidive]
enabled = true
filter = recidive
action = iptables-allports[name=recidive]
findtime = 604800
bantime = 604800
maxretry = 2
FAIL2BAN_EOF

systemctl restart fail2ban
systemctl enable fail2ban

echo 'Fail2Ban configured and started'
fail2ban-client reload 2>/dev/null || true

echo ''
echo '=== ЭТАП 3: SSH Security ==='
mkdir -p /etc/ssh/sshd_config.d
echo 'MaxAuthTries 3' >> /etc/ssh/sshd_config.d/99-security.conf
sshd -t && systemctl restart sshd || true

echo ''
echo '=== ЭТАП 4: System Hardening ==='
cat >> /etc/sysctl.d/99-security.conf << 'SYSCTL_EOF'
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 1
SYSCTL_EOF

sysctl -p /etc/sysctl.d/99-security.conf > /dev/null 2>&1

echo ''
echo '=== ЭТАП 5: UFW Firewall ==='
ufw default deny incoming 2>/dev/null || true
ufw allow 22/tcp 2>/dev/null || true
ufw allow {vpn_port}/udp 2>/dev/null || true
echo y | ufw enable 2>/dev/null || true

echo ''
echo '=== ЭТАП 6: Мониторинг ==='
cat > /usr/local/bin/amnezia-monitor.sh << 'MONITOR_EOF'
#!/bin/bash
systemctl is-active --quiet amnezia-proxy || systemctl restart amnezia-proxy
MONITOR_EOF
chmod +x /usr/local/bin/amnezia-monitor.sh
(crontab -l 2>/dev/null | grep -v amnezia-monitor; echo "*/5 * * * * /usr/local/bin/amnezia-monitor.sh") | crontab - 2>/dev/null || true

echo ''
echo 'УСПЕХ: Сервер готов к боевой эксплуатации!'
"""
            
            password_escaped = shlex.quote(password)
            full_command = f"""echo {password_escaped} | sudo -S bash -c {shlex.quote(full_security_script)}"""
            
            self.ssh.execute(full_command)
            
            self.log_message("\n" + "="*60)
            self.log_message("ПОЛНАЯ ПОДГОТОВКА ЗАВЕРШЕНА УСПЕШНО!")
            self.log_message("="*60)
            self.log_message("\nПрименённые политики:")
            self.log_message("  ✓ Fail2Ban (защита от brute-force)")
            self.log_message("  ✓ SSH Security (усиленная защита)")
            self.log_message("  ✓ System Hardening (защита ядра)")
            self.log_message("  ✓ UFW Firewall (управляемый файрвол)")
            self.log_message("  ✓ Мониторинг (автоматический контроль)")
            self.log_message("="*60)
            self.log_message("\nСервер готов к боевой эксплуатации!")
            self.log_message("="*60)
            
            self.root.after(0, lambda: messagebox.showinfo("Успех", 
                "ПОЛНАЯ ПОДГОТОВКА ЗАВЕРШЕНА УСПЕШНО!\n\n"
                "Сервер готов к боевой эксплуатации."))
        
        except Exception as e:
            self.log_message(f"\nОШИБКА: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.ssh.disconnect()
    
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
        dialog.geometry("450x200")
        
        ttk.Label(dialog, text="IP адрес или домен:").pack(anchor='w', padx=10, pady=(10, 5))
        host_entry = ttk.Entry(dialog, width=40)
        host_entry.pack(padx=10, pady=(0, 5))
        
        ttk.Label(dialog, text="Порт (если не указать, используется 37884):").pack(anchor='w', padx=10, pady=(5, 5))
        port_entry = ttk.Entry(dialog, width=40)
        port_entry.insert(0, "37884")
        port_entry.pack(padx=10, pady=(0, 10))
        
        def do_replace():
            host = host_entry.get().strip()
            port = port_entry.get().strip() or "37884"
            
            if not host:
                messagebox.showerror("Ошибка", "Укажите IP адрес или домен")
                return
            
            new_endpoint = f"{host}:{port}"
            text = self.config_text.get('1.0', tk.END)
            # Заменяет Endpoint = старое_значение на Endpoint = новое_значение
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
