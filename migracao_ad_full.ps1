# --- SCRIPT HIERARQUICO MDR (BASEADO EM GRUPOS) ---

function Garanta-OU {
    param ($Nome, $CaminhoPai)
    $Existe = Get-ADOrganizationalUnit -Filter "Name -eq '$Nome'" -SearchBase $CaminhoPai -ErrorAction SilentlyContinue
    if (-not $Existe) {
        Write-Host "Criando: $Nome" -ForegroundColor White
        New-ADOrganizationalUnit -Name $Nome -Path $CaminhoPai
    }
}

# 1. ESTRUTURA
Garanta-OU -Nome "00_Triagem" -CaminhoPai "OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "01_Juridico" -CaminhoPai "OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "02_Administrativo" -CaminhoPai "OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "TI" -CaminhoPai "OU=02_Administrativo,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "RH_DP" -CaminhoPai "OU=02_Administrativo,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "03_Trabalhista" -CaminhoPai "OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "02_Ativo_Autor" -CaminhoPai "OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "01_Passivo_Reu" -CaminhoPai "OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "Geral_Adm" -CaminhoPai "OU=02_Administrativo,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "BB_Defesa" -CaminhoPai "OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "Geral_Reu" -CaminhoPai "OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "BB_Acordos" -CaminhoPai "OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "BB_Cadastro" -CaminhoPai "OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "BB_Negocial" -CaminhoPai "OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "BB_Recursos" -CaminhoPai "OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "Geral_Autor" -CaminhoPai "OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "BB_Processual" -CaminhoPai "OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"
Garanta-OU -Nome "BB_Encerramento" -CaminhoPai "OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local"

# 2. USUARIOS
try { Get-ADUser -Identity "usuario" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: usuario -> Triagem" -ForegroundColor Yellow } catch { }
try { Get-ADUser -Identity "rildon.pereira" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rildon.pereira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "rildon.pereira" -Title "Não Informado" -OfficePhone "(84) 99802-4000" -EmployeeID "01672980461" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "pedro.alecrim" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: pedro.alecrim -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "pedro.alecrim" -Title "Não Informado" -OfficePhone "(84) 99210-0671" -EmployeeID "70020549458" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "alvaro.alves" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: alvaro.alves -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "alvaro.alves" -Title "Advogado(a)" -OfficePhone "84996312684" -EmployeeID "10382521480" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "ingrid.ribeiro" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: ingrid.ribeiro -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "ingrid.ribeiro" -Title "Advogado(a)" -OfficePhone "83 993851616" -EmployeeID "09343294433" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "joao.lopes" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: joao.lopes -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "joao.lopes" -Title "Advogado(a)" -OfficePhone "84981770301" -EmployeeID "12339292409" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "christiane.cardoso" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: christiane.cardoso -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "christiane.cardoso" -Title "Advogado(a)" -OfficePhone "84986112500" -EmployeeID "05468630435" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "jesebel.silva" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: jesebel.silva -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "jesebel.silva" -Title "Advogado(a)" -OfficePhone "(84) 99402-5530" -EmployeeID "04603866461" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "landi.silva" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: landi.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "landi.silva" -OfficePhone "(83) 99193-6295 (mãe)" -EmployeeID "05473146473" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "gabriel.oliveira" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: gabriel.oliveira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "gabriel.oliveira" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "giovane.silva" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: giovane.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "giovane.silva" -Title "Advogado(a)" -OfficePhone "(84) 99663-1843" -EmployeeID "13207476473" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "jose.carvalho" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: jose.carvalho -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "jose.carvalho" -Title "Advogado(a)" -OfficePhone "(84) 99208-5972" -EmployeeID "12244537439" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "pedro.almeida" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: pedro.almeida -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "pedro.almeida" -Title "Assistente Jurídico" -OfficePhone "84996764357" -EmployeeID "70969236409" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "cinthia.silva" | Move-ADObject -TargetPath "OU=03_Trabalhista,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: cinthia.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "cinthia.silva" -Title "Assistente Jurídico" -OfficePhone "84999540123" -EmployeeID "70285046462" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "felipa.saraiva" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: felipa.saraiva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "felipa.saraiva" -Title "Estagiario(a)" -OfficePhone "849116482" -EmployeeID "70036954489" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "fernanda.romano" | Move-ADObject -TargetPath "OU=BB_Acordos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: fernanda.romano -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "fernanda.romano" -Title "Assistente Jurídico" -OfficePhone "84988159761" -EmployeeID "13266844424" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "alexia.fernandes" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: alexia.fernandes -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "alexia.fernandes" -Title "Não Informado" -OfficePhone "84996006501" -EmployeeID "12372203436" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "allan.soares" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: allan.soares -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "allan.soares" -Title "Não Informado" -OfficePhone "8499918-4225" -EmployeeID "11713733412" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "diego.nascimento" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: diego.nascimento -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "diego.nascimento" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "jennifer.rodrigues" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: jennifer.rodrigues -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "jennifer.rodrigues" -Title "Assistente Jurídico" -OfficePhone "84 98104-8884" -EmployeeID "70929869400" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "weuder.martins" | Move-ADObject -TargetPath "OU=Geral_Adm,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: weuder.martins -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "weuder.martins" -Title "Sócio/Diretor" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "bruna.ribeiro" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: bruna.ribeiro -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "bruna.ribeiro" -Title "Sócio/Diretor" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "sayonara.silva" | Move-ADObject -TargetPath "OU=RH_DP,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: sayonara.silva -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "sayonara.silva" -Title "Coordenador(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "marcos.rodrigues" | Move-ADObject -TargetPath "OU=03_Trabalhista,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marcos.rodrigues -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "marcos.rodrigues" -Title "Sócio/Diretor" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "bruno.filho" | Move-ADObject -TargetPath "OU=BB_Encerramento,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: bruno.filho -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "bruno.filho" -Title "Advogado(a)" -OfficePhone "(84) 99669-2049" -EmployeeID "01767641435" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "carlos.bezerra" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: carlos.bezerra -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "carlos.bezerra" -Title "Não Informado" -OfficePhone "84986278618" -EmployeeID "70445481480" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "ana.nascimento" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: ana.nascimento -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "ana.nascimento" -Title "Advogado(a)" -OfficePhone "84994278869" -EmployeeID "09613735470" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "jonilson.junior" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: jonilson.junior -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "jonilson.junior" -Title "Não Informado" -OfficePhone "84981811597" -EmployeeID "09841732424" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "vitor.fernandes" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: vitor.fernandes -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "vitor.fernandes" -Title "Estagiario(a)" -OfficePhone "84 98633-7894" -EmployeeID "15230884436" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "glpi" | Move-ADObject -TargetPath "OU=Geral_Adm,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: glpi -> Grupos_AD" -ForegroundColor Cyan } catch { }
try { Get-ADUser -Identity "paulo.almeida" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: paulo.almeida -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "paulo.almeida" -Title "Assistente Jurídico" -OfficePhone "84 94222266" -EmployeeID "10674015479" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "rafael.bezerra" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rafael.bezerra -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "rafael.bezerra" -Title "Assistente Jurídico" -OfficePhone "84991269574" -EmployeeID "12133303430" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "diarkelangelo.souza" | Move-ADObject -TargetPath "OU=Geral_Adm,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: diarkelangelo.souza -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "diarkelangelo.souza" -Title "Assistente Jurídico" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "jose.jales" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: jose.jales -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "jose.jales" -Title "Advogado(a)" -OfficePhone "(84) 98108-5374" -EmployeeID "04866012420" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "rodrigo.cavalcanti" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rodrigo.cavalcanti -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "rodrigo.cavalcanti" -Title "Sócio/Diretor" -OfficePhone "84996256733" -EmployeeID "00858007401" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "luana.alves" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: luana.alves -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "luana.alves" -Title "Advogado(a)" -OfficePhone "84999296199" -EmployeeID "07598913463" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "gustavo.abdias" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: gustavo.abdias -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "gustavo.abdias" -Title "Assistente Jurídico" -OfficePhone "84 9857-8353" -EmployeeID "10850736455" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "dayvison.souza" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: dayvison.souza -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "dayvison.souza" -Title "Assistente Jurídico" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.rodrigues" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.rodrigues -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "maria.rodrigues" -Title "Advogado(a)" -OfficePhone "84 99697-9340" -EmployeeID "13133801481" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "marcelli.nascimento" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marcelli.nascimento -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "marcelli.nascimento" -Title "Assistente Jurídico" -OfficePhone "21980923994" -EmployeeID "18024049708" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "mateus.brito" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: mateus.brito -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "mateus.brito" -Title "Estagiario(a)" -OfficePhone "84 99670-2503" -EmployeeID "09000010462" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "melissa.santos" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: melissa.santos -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "melissa.santos" -Title "Advogado(a)" -OfficePhone "84999283737" -EmployeeID "08043121419" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "shirley.oliveira" | Move-ADObject -TargetPath "OU=BB_Encerramento,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: shirley.oliveira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "shirley.oliveira" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "arlisson.silva" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: arlisson.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "arlisson.silva" -Title "Advogado(a)" -OfficePhone "84996302766" -EmployeeID "01830804405" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "leticia.baptista" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: leticia.baptista -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "leticia.baptista" -Title "Estagiario(a)" -OfficePhone "(84) 99181-6633" -EmployeeID "13493706650" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "amanda.silva" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: amanda.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "amanda.silva" -Title "Estagiario(a)" -OfficePhone "84 997052757" -EmployeeID "71672469481" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "caio.galvao" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: caio.galvao -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "caio.galvao" -Title "Estagiario(a)" -OfficePhone "(84) 99692-3693" -EmployeeID "08821766411" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "marcus.gomes" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marcus.gomes -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "marcus.gomes" -Title "Assistente Jurídico" -OfficePhone "(84) 99633-8771" -EmployeeID "07043075459" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "hellen.fernandes" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: hellen.fernandes -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "hellen.fernandes" -Title "Advogado(a)" -OfficePhone "8499997-6224" -EmployeeID "08758385452" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "celio.junior" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: celio.junior -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "celio.junior" -Title "Assistente Jurídico" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "elane.tomaz" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: elane.tomaz -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "elane.tomaz" -Title "Estagiario(a)" -OfficePhone "84 994990951" -EmployeeID "70701757442" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "tayna.souza" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: tayna.souza -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "tayna.souza" -Title "Estagiario(a)" -OfficePhone "(84) 99210-4750" -EmployeeID "10824096428" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "debora.oliveira" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: debora.oliveira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "debora.oliveira" -Title "Estagiario(a)" -OfficePhone "(84)981392518" -EmployeeID "10622654403" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "sthefanie.queiroz" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: sthefanie.queiroz -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "sthefanie.queiroz" -Title "Advogado(a)" -OfficePhone "84981391998" -EmployeeID "11109978413" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "marilia.oliveira" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marilia.oliveira -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "marilia.oliveira" -Title "Assistente Jurídico" -OfficePhone "84988859342" -EmployeeID "10544598431" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "afonso.souza" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: afonso.souza -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "afonso.souza" -Title "Estagiario(a)" -OfficePhone "84996060709" -EmployeeID "06339542417" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "michelle.ferreira" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: michelle.ferreira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "michelle.ferreira" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "alyssa.silva" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: alyssa.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "alyssa.silva" -Title "Advogado(a)" -OfficePhone "84996994977" -EmployeeID "11182041400" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "wilton.lima" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: wilton.lima -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "wilton.lima" -Title "Advogado(a)" -OfficePhone "84999145248" -EmployeeID "06758129411" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "fernando.noronha" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: fernando.noronha -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "fernando.noronha" -Title "Estagiario(a)" -OfficePhone "(84) 99428-7482" -EmployeeID "70891642412" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "breno.andrade" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: breno.andrade -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "breno.andrade" -Title "Estagiario(a)" -OfficePhone "(84) 98822-6130" -EmployeeID "70393808467" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.hortencio" | Move-ADObject -TargetPath "OU=BB_Encerramento,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.hortencio -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "maria.hortencio" -Title "Estagiario(a)" -OfficePhone "84 98155-4186" -EmployeeID "01702477401" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "axel.brito" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: axel.brito -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "axel.brito" -Title "Estagiario(a)" -OfficePhone "8499972-3865" -EmployeeID "01797431471" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "yasmin.carvalho" | Move-ADObject -TargetPath "OU=BB_Encerramento,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: yasmin.carvalho -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "yasmin.carvalho" -Title "Estagiario(a)" -OfficePhone "084 998355012" -EmployeeID "10524926492" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "eliezer.souza" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: eliezer.souza -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "eliezer.souza" -Title "Assistente Jurídico" -OfficePhone "(84) 99407-1614" -EmployeeID "75140853434" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "yasmim.moura" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: yasmim.moura -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "yasmim.moura" -Title "Estagiario(a)" -OfficePhone "84999066140" -EmployeeID "12723104427" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "luis.martins" | Move-ADObject -TargetPath "OU=03_Trabalhista,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: luis.martins -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "luis.martins" -Title "Estagiario(a)" -OfficePhone "84987570919" -EmployeeID "08064613493" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "pedro.goncalves" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: pedro.goncalves -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "pedro.goncalves" -Title "Estagiario(a)" -OfficePhone "84999424220" -EmployeeID "70913777455" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "cicera.andrade" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: cicera.andrade -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "cicera.andrade" -Title "Estagiario(a)" -OfficePhone "84988807199" -EmployeeID "12067805410" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "antonio.carvalho" | Move-ADObject -TargetPath "OU=03_Trabalhista,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: antonio.carvalho -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "antonio.carvalho" -Title "Advogado(a)" -OfficePhone "84 9166-8770" -EmployeeID "01732154406" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "interno" | Move-ADObject -TargetPath "OU=Geral_Adm,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: interno -> Grupos_AD" -ForegroundColor Cyan } catch { }
try { Get-ADUser -Identity "joao.pereira" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: joao.pereira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "joao.pereira" -Title "Advogado(a)" -OfficePhone "(84) 9.8702-9299" -EmployeeID "04665061475" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "jose.neto" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: jose.neto -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "jose.neto" -Title "Nao Informado" -OfficePhone "84996985082" -EmployeeID "70527418498" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "ligia.lima" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: ligia.lima -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "ligia.lima" -Title "Estagiário(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "alexandre.lima" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: alexandre.lima -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "alexandre.lima" -Title "Assistente Jurídico" -OfficePhone "84988165939" -EmployeeID "70118984411" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "joaquim.lima" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: joaquim.lima -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "joaquim.lima" -Title "Estagiário(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "anne.silva" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: anne.silva -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "anne.silva" -Title "Estagiario(a)" -OfficePhone "(84) 98778-2241" -EmployeeID "12610558457" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "eloiza.santos" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: eloiza.santos -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "eloiza.santos" -Title "Estagiario(a)" -OfficePhone "84 99423-3744" -EmployeeID "70470743417" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.araujo" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.araujo -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "maria.araujo" -Title "Estagiario(a)" -OfficePhone "(84) 98863-9677" -EmployeeID "70990252442" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.cavalcante" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.cavalcante -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "maria.cavalcante" -Title "Estagiario(a)" -EmployeeID "70122152409" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "karolliny.cavalcanti" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: karolliny.cavalcanti -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "karolliny.cavalcanti" -Title "Estagiario(a)" -OfficePhone "(84) 99814-2150" -EmployeeID "09235913462" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "brigida.oliveira" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: brigida.oliveira -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "brigida.oliveira" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "marilia.freitas" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marilia.freitas -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "marilia.freitas" -Title "Estagiario(a)" -OfficePhone "84981338225" -EmployeeID "08978499490" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "arthur.almeida" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: arthur.almeida -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "arthur.almeida" -Title "Advogado(a)" -OfficePhone "(11)949399976" -EmployeeID "38777528883" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "lorena.moraes" | Move-ADObject -TargetPath "OU=BB_Encerramento,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: lorena.moraes -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "lorena.moraes" -OfficePhone "84 988053239" -EmployeeID "70069809410" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "paulo.reis" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: paulo.reis -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "paulo.reis" -Title "Estagiario(a)" -OfficePhone "(84) 98178-2767" -EmployeeID "11156071461" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "priscila.ramos" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: priscila.ramos -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "priscila.ramos" -Title "Advogado(a)" -OfficePhone "(83) 9 9857-6034" -EmployeeID "01143668294" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "luiz.oliveira" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: luiz.oliveira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "luiz.oliveira" -Title "Estagiário(a)" -OfficePhone "84994185088" -EmployeeID "71286522480" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "endrew.ferreira" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: endrew.ferreira -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "endrew.ferreira" -Title "Estagiario(a)" -OfficePhone "84988718433" -EmployeeID "06221138442" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "jessica.rodrigues" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: jessica.rodrigues -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "jessica.rodrigues" -Title "Estagiario(a)" -OfficePhone "(84) 99413-7050" -EmployeeID "70963194410" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "victoria.pereira" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: victoria.pereira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "victoria.pereira" -Title "Estagiario(a)" -OfficePhone "84999196581" -EmployeeID "08465903441" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "raphael.silva" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: raphael.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "raphael.silva" -OfficePhone "84 996133103" -EmployeeID "08479809442" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "geovanna.batista" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: geovanna.batista -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "geovanna.batista" -Title "Advogado(a)" -OfficePhone "84981294900" -EmployeeID "01229378480" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "adja.araujo" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: adja.araujo -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "adja.araujo" -Title "Estagiario(a)" -OfficePhone "84999874879" -EmployeeID "13766190407" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "luana.santos" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: luana.santos -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "luana.santos" -Title "Advogado(a)" -OfficePhone "84996875823" -EmployeeID "01732391459" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "camilla.silva" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: camilla.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "camilla.silva" -Title "Advogado(a)" -OfficePhone "(84) 99827-3152" -EmployeeID "01145434290" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "suenia.silva" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: suenia.silva -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "suenia.silva" -Title "Estagiario(a)" -OfficePhone "84987026239" -EmployeeID "70776344420" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "davi.netto" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: davi.netto -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "davi.netto" -Title "Assistente Jurídico" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "gabriel.barbosa" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: gabriel.barbosa -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "gabriel.barbosa" -Title "Estagiario(a)" -OfficePhone "84991918675" -EmployeeID "13422695435" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "antonio.araujo" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: antonio.araujo -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "antonio.araujo" -Title "Estagiario(a)" -OfficePhone "84996251819" -EmployeeID "70294459456" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "glenda.oliveira" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: glenda.oliveira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "glenda.oliveira" -Title "Estagiario(a)" -OfficePhone "(84) 986097369" -EmployeeID "10949354414" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "LUIS.CUNHA" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: LUIS.CUNHA -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "LUIS.CUNHA" -Title "Estagiario(a)" -OfficePhone "84996639867" -EmployeeID "07990752484" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "enzo.carriço" | Move-ADObject -TargetPath "OU=BB_Defesa,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: enzo.carriço -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "enzo.carriço" -Title "Advogado(a)" -OfficePhone "(84) 99608-3254" -EmployeeID "70426986490" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "leticia.souza" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: leticia.souza -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "leticia.souza" -Title "Estagiario(a)" -OfficePhone "84 999062742" -EmployeeID "01694787427" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "luna.almeida" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: luna.almeida -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "luna.almeida" -Title "Advogado(a)" -OfficePhone "84996252986" -EmployeeID "10399891447" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.ferreira" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.ferreira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "maria.ferreira" -Title "Advogado(a)" -OfficePhone "849 8804-9889" -EmployeeID "10979615402" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "rebeca.silva" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rebeca.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "rebeca.silva" -Title "Estagiário(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "adson.silva" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: adson.silva -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "adson.silva" -Title "Estagiario(a)" -OfficePhone "84987451121" -EmployeeID "70107463466" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "nayara.xavier" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: nayara.xavier -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "nayara.xavier" -Title "Advogado(a)" -OfficePhone "84988568014" -EmployeeID "08997488481" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "mel.firmino" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: mel.firmino -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "mel.firmino" -Title "Estagiário(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "yasmin.falcao" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: yasmin.falcao -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "yasmin.falcao" -Title "Estagiario(a)" -OfficePhone "84988855280" -EmployeeID "13537584431" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "giulia.estevam" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: giulia.estevam -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "giulia.estevam" -Title "Assistente Jurídico" -OfficePhone "84987157089" -EmployeeID "10437490475" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "suemy.ferreira" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: suemy.ferreira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "suemy.ferreira" -Title "Estagiário(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "bruna.araujo" | Move-ADObject -TargetPath "OU=BB_Defesa,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: bruna.araujo -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "bruna.araujo" -Title "Assistente Jurídico" -OfficePhone "84991182622" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "marcos.bezerra" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marcos.bezerra -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "marcos.bezerra" -Title "Advogado(a)" -OfficePhone "84 999416343" -EmployeeID "09253924489" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "pedro.magalhaes" | Move-ADObject -TargetPath "OU=BB_Recursos,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: pedro.magalhaes -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "pedro.magalhaes" -Title "Estagiario(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "murilo.silva" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: murilo.silva -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "murilo.silva" -Title "Não Informado" -OfficePhone "84991415330" -EmployeeID "13674395401" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "vinicius.adeodato" | Move-ADObject -TargetPath "OU=Geral_Reu,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: vinicius.adeodato -> Grupos_AD" -ForegroundColor Cyan } catch { }
try { Get-ADUser -Identity "THAISE.SILVA" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: THAISE.SILVA -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "THAISE.SILVA" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "daniella.dutra" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: daniella.dutra -> Triagem" -ForegroundColor Yellow } catch { }
try { Get-ADUser -Identity "larissa.vaz" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: larissa.vaz -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "larissa.vaz" -Title "Estagiario(a)" -OfficePhone "(84) 99108-5185" -EmployeeID "70591381613" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.dantas" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.dantas -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "maria.dantas" -Title "Estagiário(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.farias" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.farias -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "maria.farias" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "julia.nunes" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: julia.nunes -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "julia.nunes" -OfficePhone "(84) 99962-9984" -EmployeeID "09390525470" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "rayana.aider" | Move-ADObject -TargetPath "OU=BB_Processual,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rayana.aider -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "rayana.aider" -Title "Advogado(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "wilson.basilio" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: wilson.basilio -> Triagem" -ForegroundColor Yellow } catch { }
try { Get-ADUser -Identity "marilia.nunes" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marilia.nunes -> Triagem" -ForegroundColor Yellow } catch { }
try { Get-ADUser -Identity "cleyton.ferreira" | Move-ADObject -TargetPath "OU=Geral_Adm,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: cleyton.ferreira -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "cleyton.ferreira" -Title "Analista de Suporte" -OfficePhone "(84) 98145-7521" -EmployeeID "13576377484" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "ana.feitosa" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: ana.feitosa -> Triagem" -ForegroundColor Yellow } catch { }
try { Get-ADUser -Identity "yan.montenegro" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: yan.montenegro -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "yan.montenegro" -Title "Nao Informado" -OfficePhone "84 99709 1324" -EmployeeID "12093292475" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "leticia.pinto" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: leticia.pinto -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "leticia.pinto" -Title "Estagiario(a)" -OfficePhone "(84) 9 9894-4895" -EmployeeID "70318139480" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "marina.liberato" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: marina.liberato -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "marina.liberato" -Title "Estagiario(a)" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "andrehelly.santos" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: andrehelly.santos -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "andrehelly.santos" -Title "Advogado(a)" -OfficePhone "84 999061318" -EmployeeID "08897710492" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "thiago.franca" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: thiago.franca -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "thiago.franca" -Title "Estagiario(a)" -OfficePhone "84988918534" -EmployeeID "12223083471" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "ricardo.junior" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: ricardo.junior -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "ricardo.junior" -Title "Estagiario(a)" -OfficePhone "84 981395574" -EmployeeID "11104330423" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.silveira" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.silveira -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "maria.silveira" -Title "Estagiario(a)" -OfficePhone "(84) 981910606" -EmployeeID "10612161447" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "rayssa.moura" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rayssa.moura -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "rayssa.moura" -Title "Estagiario(a)" -OfficePhone "(84) 99632-1274" -EmployeeID "06946411382" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "aderbal.neto" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: aderbal.neto -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "aderbal.neto" -Title "Estagiario(a)" -OfficePhone "(84) 998065555" -EmployeeID "10185220428" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "dermesson.feitosa" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: dermesson.feitosa -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "dermesson.feitosa" -Title "Advogado(a)" -OfficePhone "84 99666-2312" -EmployeeID "09303368444" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "rafaely.dias" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rafaely.dias -> Grupos_AD" -ForegroundColor Cyan } catch { }
Set-ADUser -Identity "rafaely.dias" -Title "Advogado(a)" -OfficePhone "(84) 996477669" -EmployeeID "08615528497" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "maria.lopes" | Move-ADObject -TargetPath "OU=BB_Cadastro,OU=01_Passivo_Reu,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: maria.lopes -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "maria.lopes" -Title "Estagiario(a)" -OfficePhone "(84) 99677 0016" -EmployeeID "11417396407" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "elena.araujo" | Move-ADObject -TargetPath "OU=Geral_Autor,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: elena.araujo -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "elena.araujo" -Title "Advogado(a)" -OfficePhone "(84) 998024791" -EmployeeID "12447279469" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "erica.lima" | Move-ADObject -TargetPath "OU=BB_Processual,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: erica.lima -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "erica.lima" -Title "Advogado(a)" -OfficePhone "(84)98741-8598" -EmployeeID "01785545450" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "igor.albuquerque" | Move-ADObject -TargetPath "OU=TI,OU=02_Administrativo,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: igor.albuquerque -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "igor.albuquerque" -Title "Estagiario(a)" -OfficePhone "84996563819" -EmployeeID "70102223475" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "alvaro.aguiar" | Move-ADObject -TargetPath "OU=00_Triagem,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: alvaro.aguiar -> Triagem" -ForegroundColor Yellow } catch { }
Set-ADUser -Identity "alvaro.aguiar" -Title "Advogado(a)" -OfficePhone "84987275504" -EmployeeID "08870556484" -ErrorAction SilentlyContinue
try { Get-ADUser -Identity "rayana.rodrigues" | Move-ADObject -TargetPath "OU=BB_Negocial,OU=02_Ativo_Autor,OU=01_Juridico,OU=MDR,DC=mdr,DC=local" -ErrorAction Stop; Write-Host "OK: rayana.rodrigues -> RH" -ForegroundColor Green } catch { }
Set-ADUser -Identity "rayana.rodrigues" -Title "Advogado(a)" -OfficePhone "84999123817" -EmployeeID "10227514416" -ErrorAction SilentlyContinue
