import re

def limpar_cpf(cpf_raw):
    """
    Recebe qualquer bagunça (123.456.789-00, 12345678900, AD_teste)
    Retorna formatado: 123.456.789-00
    Retorna None se for inválido.
    """
    if not cpf_raw or "Anonimizado" in cpf_raw or "AD_" in cpf_raw:
        return None
    
    # Remove tudo que não é dígito
    apenas_digitos = re.sub(r'[^0-9]', '', str(cpf_raw))
    
    if len(apenas_digitos) != 11:
        return None
    
    # Formata
    return f"{apenas_digitos[:3]}.{apenas_digitos[3:6]}.{apenas_digitos[6:9]}-{apenas_digitos[9:]}"

def limpar_telefone(tel_raw):
    """
    Padroniza telefones para (XX) 9XXXX-XXXX ou (XX) XXXX-XXXX.
    Suporta entradas como: 84999998888, (84) 99999-8888, 84 9 9999 8888
    """
    if not tel_raw or "Anonimizado" in tel_raw:
        return None
        
    nums = re.sub(r'[^0-9]', '', str(tel_raw))
    
    # Se começar com 55 (DDI Brasil) e for longo, remove
    if len(nums) > 11 and nums.startswith('55'):
        nums = nums[2:]
        
    if len(nums) == 11: # Celular com DDD (84988887777)
        return f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
    elif len(nums) == 10: # Fixo com DDD (8432321111)
        return f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
    
    return tel_raw # Retorna original se não conseguiu formatar

def limpar_cargo(cargo_raw):
    """Remove placeholders como <Cargo Não Informado>"""
    if not cargo_raw or "<" in cargo_raw or "Não Informado" in cargo_raw:
        return None
    return cargo_raw.strip()

def limpar_setor(setor_raw):
    """Remove placeholders como <Setor Não Informado>"""
    if not setor_raw or "<" in setor_raw or "Não Informado" in setor_raw:
        return None
    return setor_raw.strip()