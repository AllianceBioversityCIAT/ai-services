#!/usr/bin/env python
"""
Script para configurar el cronjob de limpieza de LanceDB

Este script facilita la instalación del script db_cleaner.py como un cronjob
que se ejecutará diariamente a medianoche. Debe ejecutarse con privilegios
suficientes para modificar el crontab.

Uso:
    python setup_db_cleaner_cron.py install   # Instala el cronjob
    python setup_db_cleaner_cron.py remove    # Elimina el cronjob
    python setup_db_cleaner_cron.py status    # Muestra el estado del cronjob
"""

import os
import sys
import subprocess
from pathlib import Path
from crontab import CronTab  # Requiere python-crontab: pip install python-crontab

# Obtener la ruta absoluta del script de limpieza
CURRENT_DIR = Path(__file__).resolve().parent
DB_CLEANER_SCRIPT = CURRENT_DIR / "db_cleaner.py"
PROJECT_ROOT = CURRENT_DIR.parent.parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
CRON_COMMENT = "lancedb_cleaner"  # Identificador para el cronjob
PYTHON_BIN = sys.executable


def check_requirements():
    """Verifica que se cumplan los requisitos para ejecutar el script"""
    if not DB_CLEANER_SCRIPT.exists():
        print(f"❌ Error: No se encontró el script db_cleaner.py en {DB_CLEANER_SCRIPT}")
        return False
    
    # Asegurarse de que el script sea ejecutable
    try:
        os.chmod(DB_CLEANER_SCRIPT, 0o755)
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo hacer ejecutable el script: {e}")
    
    # Verificar que el directorio de logs exista o crearlo
    if not LOG_DIR.exists():
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            print(f"✅ Directorio de logs creado: {LOG_DIR}")
        except Exception as e:
            print(f"❌ Error: No se pudo crear el directorio de logs: {e}")
            return False
    
    return True


def get_cron_command():
    """Genera el comando cron con rutas absolutas para mayor seguridad"""
    log_file = LOG_DIR / "db_cleaner_cron.log"
    return f"{PYTHON_BIN} {DB_CLEANER_SCRIPT} >> {log_file} 2>&1"


def install_cron():
    """Instala el cronjob para ejecutar el script diariamente a medianoche"""
    if not check_requirements():
        return False
    
    try:
        # Acceder al crontab del usuario actual
        cron = CronTab(user=True)
        
        # Eliminar jobs existentes con el mismo comentario (para evitar duplicados)
        cron.remove_all(comment=CRON_COMMENT)
        
        # Crear un nuevo job que se ejecute a medianoche
        job = cron.new(command=get_cron_command(), comment=CRON_COMMENT)
        job.setall('0 0 * * *')  # Medianoche todos los días
        
        # Guardar los cambios en el crontab
        cron.write()
        
        print(f"✅ Cronjob instalado correctamente. Se ejecutará a medianoche.")
        print(f"   Comando: {job.command}")
        print(f"   Programación: {job.slices}")
        return True
        
    except Exception as e:
        print(f"❌ Error al instalar el cronjob: {e}")
        return False


def remove_cron():
    """Elimina el cronjob del limpiador de LanceDB"""
    try:
        cron = CronTab(user=True)
        
        # Buscar y eliminar el job por su comentario
        if cron.remove_all(comment=CRON_COMMENT):
            cron.write()
            print("✅ Cronjob eliminado correctamente.")
            return True
        else:
            print("ℹ️ No se encontró ningún cronjob para eliminar.")
            return False
            
    except Exception as e:
        print(f"❌ Error al eliminar el cronjob: {e}")
        return False


def show_status():
    """Muestra el estado actual del cronjob"""
    try:
        cron = CronTab(user=True)
        jobs = list(cron.find_comment(CRON_COMMENT))
        
        if not jobs:
            print("ℹ️ No hay ningún cronjob instalado para la limpieza de LanceDB.")
            return
            
        print(f"✅ Cronjob configurado para la limpieza de LanceDB:")
        for job in jobs:
            print(f"   Comando: {job.command}")
            print(f"   Programación: {job.slices}")
            # Calcular la próxima ejecución
            schedule = job.schedule(date_from=job.next())
            next_run = schedule.get_next()
            print(f"   Próxima ejecución: {next_run}")
            
    except Exception as e:
        print(f"❌ Error al verificar el estado del cronjob: {e}")


def test_script():
    """Ejecuta el script de limpieza en modo de prueba"""
    if not check_requirements():
        return False
        
    print(f"🧪 Ejecutando el script db_cleaner.py en modo de prueba...")
    try:
        result = subprocess.run([PYTHON_BIN, str(DB_CLEANER_SCRIPT)], 
                               capture_output=True, text=True)
        
        print("\n--- SALIDA DEL SCRIPT ---")
        print(result.stdout)
        
        if result.stderr:
            print("\n--- ERRORES ---")
            print(result.stderr)
            
        print(f"\n✅ Script ejecutado con código de salida: {result.returncode}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error al ejecutar el script: {e}")
        return False


def print_usage():
    """Muestra el mensaje de ayuda"""
    print(f"""
Uso: {sys.argv[0]} <comando>

Comandos disponibles:
  install   - Instala el cronjob para ejecutar el script diariamente a medianoche
  remove    - Elimina el cronjob
  status    - Muestra el estado actual del cronjob
  test      - Ejecuta el script db_cleaner.py en modo de prueba
  help      - Muestra este mensaje de ayuda
""")


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print_usage()
        return 1
        
    command = sys.argv[1].lower()
    
    if command == "install":
        return 0 if install_cron() else 1
    elif command == "remove":
        return 0 if remove_cron() else 1
    elif command == "status":
        show_status()
        return 0
    elif command == "test":
        return 0 if test_script() else 1
    elif command in ["help", "-h", "--help"]:
        print_usage()
        return 0
    else:
        print(f"❌ Comando desconocido: {command}")
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())