import os
import logging

def find_string_in_xml(target):
    # Configura o logging para gravar em search.log
    logging.basicConfig(
        filename='search.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    logging.info("=== Iniciando busca por '%s' em arquivos XML ===", target)

    # Pasta onde está este script
    dir_path = os.path.dirname(os.path.abspath(__file__))
    encontrados = []

    # Itera sobre todos os arquivos da pasta
    for nome_arquivo in os.listdir(dir_path):
        if nome_arquivo.lower().endswith('.xml'):
            caminho = os.path.join(dir_path, nome_arquivo)
            logging.info("Verificando arquivo: %s", nome_arquivo)
            try:
                with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
                    # Leitura linha a linha para não carregar tudo na memória
                    for linha in f:
                        if target in linha:
                            encontrados.append(nome_arquivo)
                            logging.info("→ Encontrado em: %s", nome_arquivo)
                            break  # sai do loop de linhas assim que achar
            except Exception as e:
                logging.error("Erro ao ler %s: %s", nome_arquivo, e)

    # Exibe resultado na tela
    if encontrados:
        print("String encontrada nos seguintes arquivos XML:")
        for arq in encontrados:
            print(f" - {arq}")
    else:
        print("Nenhum arquivo XML contém a string informada.")
    logging.info("=== Busca concluída. Arquivos encontrados: %s ===", encontrados)

if __name__ == '__main__':
    TARGET = "11514730121"
    find_string_in_xml(TARGET)
