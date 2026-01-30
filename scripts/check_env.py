#!/usr/bin/env python3
import sys
import os
import shutil
import importlib.util

# Cores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def log_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def log_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def check_python_version():
    required_major = 3
    required_minor = 11
    current = sys.version_info
    
    if current.major < required_major or (current.major == required_major and current.minor < required_minor):
        log_error(f"Python version mismatch: required >= {required_major}.{required_minor}, found {current.major}.{current.minor}")
        return False
    log_success(f"Python version {current.major}.{current.minor} detected")
    return True

def check_file_exists(filepath, description):
    if os.path.isfile(filepath):
        log_success(f"File '{description}' found: {filepath}")
        return True
    else:
        log_error(f"File '{description}' missing: {filepath}")
        return False

def check_command(command):
    if shutil.which(command):
        log_success(f"Command '{command}' found")
        return True
    else:
        log_warning(f"Command '{command}' not found in PATH")
        return False

def check_dependencies():
    # Check simple imports from requirements (pacotes críticos)
    packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("dotenv", "python-dotenv"),
        ("twilio", "twilio"),
        ("structlog", "structlog"),
        ("sqlalchemy", "sqlalchemy") # Pode ser necessário se usar ORM, mas requirements diz supabase
    ]
    
    missing = []
    for module_name, package_name in packages:
        try:
            if importlib.util.find_spec(module_name) is None:
                missing.append(package_name)
        except (ImportError, ValueError):
            missing.append(package_name)
    
    if missing:
        log_error(f"Missing Python packages: {', '.join(missing)}")
        print(f"   👉 Run 'make install' to fix.")
        return False
    
    log_success("Core Python packages installed")
    return True

def check_env_vars():
    env_path = ".env"
    if not os.path.exists(env_path):
        return False 
    
    try:
        # Tenta usar dotenv se instalado
        from dotenv import dotenv_values
        config = dotenv_values(env_path)
        
        # Lista de variáveis críticas que não deveriam estar vazias
        critical_vars = [
            "DATABASE_URL",
            "SUPABASE_URL", 
            "SUPABASE_KEY"
        ]
        
        missing_vars = [var for var in critical_vars if not config.get(var)]
        
        if missing_vars:
            log_warning(f"Missing or empty values in .env for: {', '.join(missing_vars)}")
            # Não falha o script, apenas avisa
            return True
        
        log_success("Critical environment variables are set")
        return True
    except ImportError:
        return False

def main():
    print("🔍 Checking local environment requirements...\n")
    all_ok = True
    
    # 1. Python Version
    if not check_python_version(): all_ok = False
    
    # 2. System Tools
    if not check_command("docker"): 
        log_warning("Docker not found (recommended for DB/Redis)")
        # Não falha hard se o usuário rodar serviços externos
    if not check_command("git"): all_ok = False
    
    # Check for Redis (Server or CLI)
    if not check_command("redis-server") and not check_command("redis-cli"):
        log_warning("Redis not found (redis-server or redis-cli). Required if running locally without Docker.")
    
    # 3. Files
    if not check_file_exists(".env", ".env configuration"):
        print(f"   👉 Copy .env.example to .env and configure it: 'cp .env.example .env'")
        all_ok = False
    
    # 4. Dependencies
    if not check_dependencies(): all_ok = False
    
    # 5. Env Vars
    if os.path.exists(".env"):
        check_env_vars()
    
    print("\n" + "="*40)
    if all_ok:
        print(f"{GREEN}🎉 Environment looks good! You are ready to run.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}💥 Some requirements are missing. Please fix them above.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
