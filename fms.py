import os
import sys
import time
import psutil
import signal
import subprocess
from threading import Thread

"""
Aluno: Gabriel Viana da Silva
Matrícula: 162633

Para rodar o código, use o comando:
python3 fms.py
"""

# Estado global #
global_cpu_quota = 0.0  # <- Quota de CPU global, definida pelo usuário
global_cpu_used = 0.0   # <- Quota de CPU usada, atualizada pelo monitor
shutdown_flag = False   # <- Flag para encerrar o FMS

def terminate_process_tree(proc: psutil.Process):
    for child in proc.children(recursive=True):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        proc.kill()
    except psutil.NoSuchProcess:
        pass

def monitor_process(proc: psutil.Process, start_time: float, child_cpu_quota: float, memory_limit_mb: float, timeout: float):
    """Monitora o processo em execução."""
    global global_cpu_used, global_cpu_quota, shutdown_flag

    max_memory_mb = 0.0
    last_cpu_time = 0.0

    while proc.is_running():
        try:
            times = proc.cpu_times()
            current_cpu_time = times.user + times.system
            delta_cpu = current_cpu_time - last_cpu_time
            last_cpu_time = current_cpu_time

            global_cpu_used += delta_cpu

            # Memória utilizada e máxima
            mem = proc.memory_info().rss / (1024 * 1024)
            max_memory_mb = max(max_memory_mb, mem)


            if time.time() - start_time > timeout:
                print("Timeout atingido! Encerrando processo.")
                terminate_process_tree(proc)
                break
            if current_cpu_time > child_cpu_quota:
                print(f"Quota de CPU do processo excedida: {current_cpu_time:.2f}s > {child_cpu_quota:.2f}s")
                terminate_process_tree(proc)
                break


            if mem > memory_limit_mb:
                print(f"❌ Memória excedida: {mem:.2f}MB > {memory_limit_mb:.2f}MB")
                terminate_process_tree(proc)
                raise MemoryError

            if global_cpu_used > global_cpu_quota:
                print(f"Quota GLOBAL de CPU excedida: {global_cpu_used:.2f}s > {global_cpu_quota:.2f}s")
                terminate_process_tree(proc)
                shutdown_flag = True
                break

            time.sleep(0.5)

        except psutil.NoSuchProcess:
            break

    print(f"Processo finalizado. CPU usada: {current_cpu_time:.2f}s | Memória máxima: {max_memory_mb:.2f}MB")


def signal_handler(sig, frame):
    global shutdown_flag
    shutdown_flag = True
    print("\nFMS encerrado pelo usuário.")
    sys.exit(0)

def run_fms():
    global global_cpu_quota

    print("FMS")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        try:
            global_cpu_quota = float(input("Defina a quota GLOBAL de tempo de CPU (em segundos): "))
            break
        except ValueError:
            print("Valor inválido. Tente novamente.")

    while not shutdown_flag:
        print("\n🔁 Novo programa para execução")

        binary = input("Caminho do executável: ").strip()
        if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
            print("Arquivo inválido ou não executável.")
            continue

        try:
            child_quota = float(input("Quota de CPU para o processo (segundos): "))
            timeout = float(input("Tempo máximo de execução (timeout em segundos): "))
            mem_limit = float(input("Limite de memória (MB): "))
        except ValueError:
            print("Entrada inválida. Tente novamente.")
            continue
        
        
        print("Iniciando processo...\n")
        try:
            process = subprocess.Popen([binary])
            ps_proc = psutil.Process(process.pid)
            start_time = time.time()

            monitor = Thread(target=monitor_process, args=(ps_proc, start_time, child_quota, mem_limit, timeout))
            monitor.start()
            monitor.join()

        except MemoryError:
            print("Limite de memória global excedido. Encerrando FMS.")
            break
        except SystemExit as e:
            print(str(e))
            break
        except Exception as e:
            print(f"Erro inesperado: {e}")
            break

        print(f"Quota de CPU global restante: {max(global_cpu_quota - global_cpu_used, 0.0):.2f}s")

        if global_cpu_used >= global_cpu_quota:
            print("Quota global esgotada. Encerrando FMS.")
            break

if __name__ == "__main__":
    run_fms()
