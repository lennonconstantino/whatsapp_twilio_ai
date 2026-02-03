import ast
import os
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

def get_python_files(root_dir: str) -> List[str]:
    python_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files

def get_module_name(file_path: str, root_dir: str) -> str:
    rel_path = os.path.relpath(file_path, root_dir)
    return rel_path.replace(os.path.sep, ".").replace(".py", "")

def resolve_import(module_name: str, import_level: int, current_module: str) -> str:
    if import_level == 0:
        return module_name
    
    parts = current_module.split(".")
    if import_level > len(parts):
        return None  # Invalid relative import
        
    base = ".".join(parts[:-import_level])
    if base:
        return f"{base}.{module_name}" if module_name else base
    return module_name

def extract_imports(file_path: str, root_dir: str) -> Set[str]:
    imports = set()
    current_module = get_module_name(file_path, root_dir)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
            
        for node in ast.walk(tree):
            # Ignorar imports dentro de if TYPE_CHECKING
            # (Isso é uma simplificação, idealmente checaríamos o pai do nó)
            
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    level = node.level
                    resolved = resolve_import(node.module, level, current_module)
                    if resolved:
                        imports.add(resolved)
                elif node.level > 0:
                     # Relative import without module (from . import foo)
                     resolved = resolve_import("", node.level, current_module)
                     if resolved:
                         imports.add(resolved)
                         
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        
    return imports

def find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    visited = set()
    stack = []
    cycles = []
    
    def dfs(node, path):
        if node in path:
            cycle = path[path.index(node):] + [node]
            cycles.append(cycle)
            return
        
        if node in visited:
            return
            
        visited.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            dfs(neighbor, path)
            
        path.pop()

    # Ordenar nós para determinismo
    nodes = sorted(list(graph.keys()))
    for node in nodes:
        if node not in visited:
            dfs(node, [])
            
    return cycles

def main():
    root_dir = os.path.abspath("src")
    if not os.path.exists(root_dir):
        print(f"Directory {root_dir} not found.")
        return

    files = get_python_files(root_dir)
    module_map = {get_module_name(f, os.getcwd()): f for f in files}
    # Ajuste: module names devem ser relativos a 'src' para matching interno, 
    # mas o projeto usa imports absolutos começando com 'src.'.
    # Vamos considerar que todos os imports internos começam com 'src.'
    
    internal_modules = set()
    for f in files:
        # Ex: src/main.py -> src.main
        mod_name = get_module_name(f, os.getcwd()) 
        internal_modules.add(mod_name)

    graph = defaultdict(set)
    
    print(f"Analyzing {len(files)} files in {root_dir}...")
    
    for file_path in files:
        module_name = get_module_name(file_path, os.getcwd())
        raw_imports = extract_imports(file_path, os.getcwd())
        
        for imp in raw_imports:
            # Filtrar apenas imports que são deste projeto (começam com src.)
            # E verificar se é um módulo conhecido
            
            # Tentar match exato ou match de pacote pai
            # Ex: import src.core.config -> depende de src.core.config
            
            target = None
            if imp in internal_modules:
                target = imp
            else:
                # Checar se é um subpacote/submódulo
                # Se importamos 'src.modules.ai.utils.helper', e existe 'src.modules.ai.utils.py', a dependência é essa
                # Mas geralmente imports apontam para arquivos.
                # Vamos simplificar: se o import começa com 'src.', vamos ver qual arquivo ele toca.
                
                parts = imp.split(".")
                for i in range(len(parts), 0, -1):
                    candidate = ".".join(parts[:i])
                    if candidate in internal_modules:
                        target = candidate
                        break
            
            if target and target != module_name:
                graph[module_name].add(target)

    print("Detecting cycles...")
    cycles = find_cycles(graph)
    
    # Remover ciclos duplicados (A->B->A é o mesmo que B->A->B)
    unique_cycles = set()
    final_cycles = []
    
    for cycle in cycles:
        # Normalizar ciclo rodando para o menor elemento primeiro
        # Ex: ['b', 'c', 'a', 'b'] -> ('a', 'b', 'c')
        
        # O ciclo vem como [A, B, C, A]. Pegamos apenas os únicos: [A, B, C]
        path = cycle[:-1] 
        if not path: continue
        
        # Rotacionar para começar com o menor string lexicamente
        min_idx = path.index(min(path))
        rotated = tuple(path[min_idx:] + path[:min_idx])
        
        if rotated not in unique_cycles:
            unique_cycles.add(rotated)
            final_cycles.append(cycle)

    if final_cycles:
        print(f"\nFound {len(final_cycles)} circular dependencies:")
        for i, cycle in enumerate(final_cycles, 1):
            print(f"\nCycle {i}:")
            for node in cycle:
                print(f"  -> {node}")
    else:
        print("\nNo circular dependencies found.")

if __name__ == "__main__":
    main()
