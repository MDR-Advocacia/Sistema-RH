document.getElementById('formFuncionario').addEventListener('submit', async function (e) {
  e.preventDefault();

  const formData = new FormData(this);
  const data = {
    nome: formData.get('nome'),
    cpf: formData.get('cpf'),
    cargo: formData.get('cargo'),
    setor: formData.get('setor'),
    email: formData.get('email'),
    data_admissao: formData.get('data_admissao'),
    sistemas: formData.getAll('sistemas')
  };

  const res = await fetch('/cadastrar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  const resultado = await res.json();
  document.getElementById('resultado').innerText = resultado.message;
});

document.getElementById('botao-voltar').addEventListener('click', function() {
    window.location.href = '/';
});