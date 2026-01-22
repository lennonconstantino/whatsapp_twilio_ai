import os
from pathlib import Path
from typing import Union

def validar_e_verificar_proximo_diretorio(caminho: str) -> dict:
    """
    Valida um path e verifica se existe o próximo diretório especificado.
    
    Args:
        caminho: Path a ser validado (ex: 'src/modules/ai/engines/lchain/feature')
    
    Returns:
        dict com informações sobre a validação e verificação
    """
    # Diretório esperado (hardcoded)
    PROXIMO_DIRETORIO = "finance"
    
    resultado = {
        "path_original": caminho,
        "path_valido": False,
        "path_existe": False,
        "proximo_diretorio_existe": False,
        "caminho_completo": None,
        "mensagem": ""
    }
    
    # Validação do path
    if not caminho or not isinstance(caminho, str):
        resultado["mensagem"] = "Path inválido: deve ser uma string não vazia"
        return resultado
    
    # Remove espaços e barras extras
    caminho = caminho.strip().rstrip('/\\')
    
    if not caminho:
        resultado["mensagem"] = "Path inválido: string vazia após normalização"
        return resultado
    
    # Validação de caracteres perigosos
    caracteres_invalidos = ['..', '\0']
    if any(char in caminho for char in caracteres_invalidos):
        resultado["mensagem"] = f"Path contém caracteres inválidos ou perigosos"
        return resultado
    
    resultado["path_valido"] = True
    
    try:
        # Converte para Path object
        path_obj = Path(caminho)
        
        # Verifica se o path existe
        if path_obj.exists():
            resultado["path_existe"] = True
            
            # Verifica se é um diretório
            if not path_obj.is_dir():
                resultado["mensagem"] = f"O path existe mas não é um diretório"
                return resultado
        else:
            resultado["mensagem"] = f"O path não existe no sistema de arquivos"
            return resultado
        
        # Verifica se existe o próximo diretório
        proximo_path = path_obj / PROXIMO_DIRETORIO
        resultado["caminho_completo"] = str(proximo_path)
        
        if proximo_path.exists() and proximo_path.is_dir():
            resultado["proximo_diretorio_existe"] = True
            resultado["mensagem"] = f"Sucesso! O diretório '{PROXIMO_DIRETORIO}' existe em {caminho}"
        else:
            resultado["mensagem"] = f"O diretório '{PROXIMO_DIRETORIO}' não foi encontrado em {caminho}"
        
    except Exception as e:
        resultado["mensagem"] = f"Erro ao processar path: {str(e)}"
    
    return resultado

def main():
    print("Testando validação e verificação de path...")

# Exemplo de uso
if __name__ == "__main__":
    # Teste 1
    resultado = validar_e_verificar_proximo_diretorio("src/modules/ai/engines/lchain/feature")
    print(f"Path: {resultado['path_original']}")
    print(f"Válido: {resultado['path_valido']}")
    print(f"Existe: {resultado['path_existe']}")
    print(f"Próximo diretório existe: {resultado['proximo_diretorio_existe']}")
    print(f"Mensagem: {resultado['mensagem']}")
    print(f"Caminho completo: {resultado['caminho_completo']}")
    print("-" * 50)
    
    # Teste 2 - Path inválido
    resultado2 = validar_e_verificar_proximo_diretorio("")
    print(f"Mensagem: {resultado2['mensagem']}")